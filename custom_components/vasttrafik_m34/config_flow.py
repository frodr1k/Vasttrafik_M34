"""Config flow for Västtrafik M34 integration."""
from __future__ import annotations

import base64
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# OAuth2 Configuration
TOKEN_URL = "https://ext-api.vasttrafik.se/token"
API_BASE = "https://ext-api.vasttrafik.se/pr/v4"


async def get_access_token(
    hass: HomeAssistant, auth_key: str
) -> tuple[str, int]:
    """Get OAuth2 access token from Västtrafik API.
    
    Args:
        hass: Home Assistant instance
        auth_key: Base64 encoded client_id:client_secret (Authentication Key from portal)
    
    Returns:
        Tuple of (access_token, expires_in_seconds)
    """
    headers = {
        "Authorization": f"Basic {auth_key}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    
    data = {"grant_type": "client_credentials"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(TOKEN_URL, headers=headers, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Token request failed: %s - %s", response.status, error_text)
                    raise CannotConnect(f"Failed to get access token: {response.status}")
                
                result = await response.json()
                return result["access_token"], result.get("expires_in", 86400)
    except aiohttp.ClientError as ex:
        _LOGGER.error("Network error during token request: %s", ex)
        raise CannotConnect(f"Network error: {ex}") from ex


async def validate_auth_key(hass: HomeAssistant, auth_key: str) -> bool:
    """Validate the authentication key by attempting to get an access token."""
    try:
        token, _ = await get_access_token(hass, auth_key)
        return token is not None and len(token) > 0
    except Exception as ex:
        _LOGGER.error("Failed to validate authentication key: %s", ex)
        return False


async def search_stations(
    hass: HomeAssistant, access_token: str, query: str
) -> list[dict[str, str]]:
    """Search for stations using the Västtrafik API v4.
    
    Args:
        hass: Home Assistant instance
        access_token: Valid OAuth2 Bearer token
        query: Search query string
    
    Returns:
        List of station dictionaries with 'gid', 'name', and 'type'
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    
    params = {
        "q": query,
        "limit": 10,
        "types": "stoparea",  # Only search for stop areas
    }
    
    url = f"{API_BASE}/locations/by-text"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 401:
                    raise InvalidAuth("Access token expired or invalid")
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Station search failed: %s - %s", response.status, error_text)
                    raise CannotConnect(f"Failed to search stations: {response.status}")
                
                result = await response.json()
                
                # Parse the results from API v4
                stations = []
                results_list = result.get("results", [])
                
                for location in results_list:
                    if location.get("locationType") == "stoparea":
                        stations.append({
                            "gid": location.get("gid"),
                            "name": location.get("name"),
                            "type": "StopArea",
                        })
                
                return stations
    except aiohttp.ClientError as ex:
        _LOGGER.error("Network error during station search: %s", ex)
        raise CannotConnect(f"Network error: {ex}") from ex


class VasttrafikM34ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Västtrafik M34."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._auth_key: str | None = None
        self._access_token: str | None = None
        self._stations: list[dict[str, str]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - API credentials."""
        errors: dict[str, str] = {}
        
        # Check if we already have a valid auth_key from a previous entry
        existing_entries = self._async_current_entries()
        if existing_entries and not user_input:
            # Use auth_key from first existing entry
            existing_auth_key = existing_entries[0].data.get("auth_key")
            if existing_auth_key:
                try:
                    # Validate the existing auth key
                    is_valid = await validate_auth_key(self.hass, existing_auth_key)
                    if is_valid:
                        # Reuse existing auth key
                        self._auth_key = existing_auth_key
                        self._access_token, _ = await get_access_token(
                            self.hass, self._auth_key
                        )
                        # Skip to station search directly
                        return await self.async_step_station()
                except Exception:
                    # If validation fails, continue to ask for auth_key
                    pass

        if user_input is not None:
            try:
                # Validate authentication key
                is_valid = await validate_auth_key(
                    self.hass,
                    user_input["auth_key"],
                )
                
                if not is_valid:
                    raise InvalidAuth("Invalid authentication key")
                
                # Store auth key and get token
                self._auth_key = user_input["auth_key"]
                self._access_token, _ = await get_access_token(
                    self.hass, self._auth_key
                )
                
                # Move to station search step
                return await self.async_step_station()
                
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("auth_key"): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "auth_key_url": "https://developer.vasttrafik.se/",
            },
        )

    async def async_step_station(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle station search step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if "station_name" in user_input and user_input["station_name"]:
                # User wants to search for stations
                try:
                    self._stations = await search_stations(
                        self.hass, self._access_token, user_input["station_name"]
                    )
                    
                    if not self._stations:
                        errors["base"] = "no_stations_found"
                    else:
                        # Show station selection
                        return await self.async_step_select_station()
                        
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception during station search")
                    errors["base"] = "unknown"

        return self.async_show_form(
            step_id="station",
            data_schema=vol.Schema(
                {
                    vol.Required("station_name"): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "station_example": "e.g., 'Central', 'Brunnsparken', 'Järntorget'",
            },
        )

    async def async_step_select_station(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle station selection step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Find the selected station
            station_gid = user_input["station"]
            selected_station = next(
                (s for s in self._stations if s["gid"] == station_gid), None
            )
            
            if selected_station:
                # Check for duplicates - prevent same station being added twice
                await self.async_set_unique_id(f"vasttrafik_{station_gid}")
                self._abort_if_unique_id_configured()
                
                # Create the config entry
                return self.async_create_entry(
                    title=selected_station["name"],
                    data={
                        "auth_key": self._auth_key,
                        "station_gid": selected_station["gid"],
                        "station_name": selected_station["name"],
                    },
                )
            else:
                errors["base"] = "invalid_station"

        # Create station selector options
        station_options = {
            station["gid"]: station["name"]
            for station in self._stations
        }

        return self.async_show_form(
            step_id="select_station",
            data_schema=vol.Schema(
                {
                    vol.Required("station"): vol.In(station_options),
                }
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
