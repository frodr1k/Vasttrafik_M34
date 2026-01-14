"""Sensor platform for Västtrafik M34 integration."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import TYPE_CHECKING, Any

import aiohttp

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN

if TYPE_CHECKING:
    from . import VasttrafikConfigEntry

_LOGGER = logging.getLogger(__name__)

# API Configuration
TOKEN_URL = "https://ext-api.vasttrafik.se/token"
API_BASE = "https://ext-api.vasttrafik.se/pr/v4"

SCAN_INTERVAL = timedelta(minutes=1)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VasttrafikConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Västtrafik M34 sensor based on a config entry."""
    auth_key = entry.data["auth_key"]
    station_gid = entry.data["station_gid"]
    station_name = entry.data["station_name"]
    
    # Create coordinator
    coordinator = VasttrafikDataUpdateCoordinator(
        hass,
        auth_key=auth_key,
        station_gid=station_gid,
    )
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    # Store coordinator in runtime_data
    entry.runtime_data = coordinator
    
    # Create sensor
    async_add_entities(
        [VasttrafikM34Sensor(coordinator, station_name, station_gid)],
        True,
    )


class VasttrafikDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Västtrafik data."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        auth_key: str,
        station_gid: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self._auth_key = auth_key
        self._station_gid = station_gid
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None
    
    async def _get_access_token(self) -> str:
        """Get or refresh OAuth2 access token."""
        # Check if we have a valid token
        if (
            self._access_token
            and self._token_expires_at
            and datetime.now() < self._token_expires_at
        ):
            return self._access_token
        
        # Get new token
        headers = {
            "Authorization": f"Basic {self._auth_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        data = {"grant_type": "client_credentials"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(TOKEN_URL, headers=headers, data=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        _LOGGER.error("Token request failed: %s - %s", response.status, error_text)
                        raise UpdateFailed(f"Failed to get access token: {response.status}")
                    
                    result = await response.json()
                    self._access_token = result["access_token"]
                    expires_in = result.get("expires_in", 86400)
                    
                    # Set expiration time with 5 minute buffer
                    self._token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
                    
                    _LOGGER.debug("Got new access token, expires in %s seconds", expires_in)
                    return self._access_token
        except aiohttp.ClientError as ex:
            _LOGGER.error("Network error during token request: %s", ex)
            raise UpdateFailed(f"Network error: {ex}") from ex
    
    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Västtrafik API."""
        try:
            # Get valid access token
            access_token = await self._get_access_token()
            
            # Fetch departures
            headers = {
                "Authorization": f"Bearer {access_token}",
            }
            
            # Get current time in RFC 3339 format
            now = datetime.now().astimezone().isoformat()
            
            params = {
                "timeSpanInMinutes": 60,  # Next hour
                "maxDeparturesPerLine": 2,  # Max 2 per line
            }
            
            url = f"{API_BASE}/stop-areas/{self._station_gid}/departures"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 401:
                        # Token expired, clear it and retry
                        self._access_token = None
                        self._token_expires_at = None
                        raise UpdateFailed("Access token expired, will retry")
                    
                    if response.status != 200:
                        error_text = await response.text()
                        _LOGGER.error("Departures request failed: %s - %s", response.status, error_text)
                        raise UpdateFailed(f"Failed to get departures: {response.status}")
                    
                    result = await response.json()
                    
                    # Parse the response
                    departures = []
                    results_list = result.get("results", [])
                    
                    for departure in results_list:
                        service_journey = departure.get("serviceJourney", {})
                        
                        # Get times
                        planned_time = departure.get("plannedTime")
                        estimated_time = departure.get("estimatedTime")
                        
                        # Calculate delay
                        delay_minutes = 0
                        if estimated_time and planned_time:
                            try:
                                planned_dt = datetime.fromisoformat(planned_time.replace('Z', '+00:00'))
                                estimated_dt = datetime.fromisoformat(estimated_time.replace('Z', '+00:00'))
                                delay_minutes = int((estimated_dt - planned_dt).total_seconds() / 60)
                            except Exception as ex:
                                _LOGGER.debug("Could not calculate delay: %s", ex)
                        
                        # Get track/platform info - stopPoint can be a string or dict
                        track = ""
                        stop_point = departure.get("stopPoint", {})
                        if isinstance(stop_point, dict):
                            platform = stop_point.get("platform", {})
                            if isinstance(platform, dict):
                                track = platform.get("name", "")
                            elif isinstance(platform, str):
                                track = platform
                        
                        departures.append({
                            "line_number": service_journey.get("line", {}).get("name", "?"),
                            "line_designation": service_journey.get("line", {}).get("designation", ""),
                            "direction": service_journey.get("direction", ""),
                            "planned_time": planned_time,
                            "estimated_time": estimated_time or planned_time,
                            "delay_minutes": delay_minutes,
                            "track": track,
                            "is_cancelled": departure.get("isCancelled", False),
                            "is_realtime": estimated_time is not None,
                        })
                    
                    return {
                        "departures": departures,
                        "last_update": datetime.now().isoformat(),
                    }
        
        except aiohttp.ClientError as ex:
            _LOGGER.error("Network error during data update: %s", ex)
            raise UpdateFailed(f"Network error: {ex}") from ex
        except Exception as ex:
            _LOGGER.exception("Unexpected error during data update: %s", ex)
            raise UpdateFailed(f"Unexpected error: {ex}") from ex


class VasttrafikM34Sensor(CoordinatorEntity, SensorEntity):
    """Representation of a Västtrafik M34 sensor."""
    
    _attr_has_entity_name = True
    _attr_name = None  # Will use device name
    
    def __init__(
        self,
        coordinator: VasttrafikDataUpdateCoordinator,
        station_name: str,
        station_gid: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        self._station_name = station_name
        self._station_gid = station_gid
        self._attr_unique_id = f"vasttrafik_{station_gid}"
        self._attr_icon = "mdi:tram"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, station_gid)},
            name=station_name,
            manufacturer="Västtrafik",
            model="M34 Departure Monitor",
            entry_type=DeviceEntryType.SERVICE,
        )
        
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
    
    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        
        departures = self.coordinator.data.get("departures", [])
        if not departures:
            return "Inga avgångar"
        
        # Show number of departures from the station
        return f"{len(departures)} avgångar från {self._station_name}"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}
        
        departures = self.coordinator.data.get("departures", [])
        last_update = self.coordinator.data.get("last_update")
        
        # Format departures for display (legacy string format for backwards compatibility)
        departure_list = []
        # New: Structured JSON array for easy parsing
        departure_details = []
        
        for dep in departures[:15]:  # Show max 15 departures
            estimated_time = dep.get("estimated_time", "")
            
            try:
                dt = datetime.fromisoformat(estimated_time.replace('Z', '+00:00'))
                now = datetime.now().astimezone()
                minutes = int((dt - now).total_seconds() / 60)
                
                # Relative time
                if minutes <= 0:
                    time_str = "Nu"
                elif minutes == 1:
                    time_str = "1 min"
                else:
                    time_str = f"{minutes} min"
                
                # Actual departure time (HH:MM)
                actual_time = dt.strftime("%H:%M")
                
            except Exception:
                time_str = "?"
                actual_time = estimated_time
                minutes = 0
            
            # Delay information
            delay = dep.get("delay_minutes", 0)
            delay_str = ""
            if delay > 0:
                delay_str = f" (+{delay})"
            elif delay < 0:
                delay_str = f" ({delay})"
            
            # Cancelled indicator (no red ball)
            cancelled = " [INSTÄLLD]" if dep.get("is_cancelled") else ""
            
            # Track/platform info
            track = dep.get("track", "")
            track_str = f" Läge {track}" if track else ""
            
            # Format for display: "Linje 16 → Bergsjön - 14:25 (2 min) Läge B"
            departure_list.append(
                f"Linje {dep.get('line_number', '?')} → {dep.get('direction', '?')} - "
                f"{actual_time} ({time_str}){delay_str}{track_str}{cancelled}"
            )
            
            # New structured format
            departure_details.append({
                "line": dep.get("line_number", "?"),
                "destination": dep.get("direction", "?"),
                "departure_time": actual_time,
                "relative_time": time_str,
                "minutes_until": minutes,
                "track": track,
                "delay_minutes": delay,
                "is_cancelled": dep.get("is_cancelled", False),
                "is_realtime": dep.get("is_realtime", False),
                "planned_time": dep.get("planned_time", ""),
                "estimated_time": estimated_time,
            })
        
        return {
            "station_name": self._station_name,
            "station_gid": self._station_gid,
            "departures": departure_list,  # Legacy format (list of strings)
            "departures_json": departure_details,  # New JSON array format
            "departure_count": len(departures),
            "last_update": last_update,
        }
