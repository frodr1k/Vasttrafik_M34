"""DataUpdateCoordinator for Västtrafik M34."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from aiohttp import ClientError, ClientSession

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    API_BASE,
    CONF_AUTH_KEY,
    CONF_DIRECTION_FILTER,
    CONF_EXCLUDE_CANCELLED,
    CONF_LINE_FILTER,
    CONF_MAX_PER_LINE,
    CONF_STATION_GID,
    CONF_TIME_SPAN_MINUTES,
    CONF_UPDATE_INTERVAL,
    DEFAULT_EXCLUDE_CANCELLED,
    DEFAULT_MAX_PER_LINE,
    DEFAULT_TIME_SPAN_MINUTES,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    TOKEN_URL,
)

_LOGGER = logging.getLogger(__name__)


class VasttrafikDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch departures from Västtrafik API v4."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        session: ClientSession,
    ) -> None:
        """Initialize coordinator."""
        options = entry.options
        interval = options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
            config_entry=entry,
        )
        self.entry = entry
        self.session = session
        self._access_token: str | None = None
        self._token_expires_at = None

    @property
    def station_gid(self) -> str:
        return self.entry.data[CONF_STATION_GID]

    @property
    def auth_key(self) -> str:
        return self.entry.data[CONF_AUTH_KEY]

    @property
    def direction_filter(self) -> str:
        return (self.entry.options.get(CONF_DIRECTION_FILTER) or "").strip()

    @property
    def line_filter(self) -> str:
        return (self.entry.options.get(CONF_LINE_FILTER) or "").strip()

    @property
    def exclude_cancelled(self) -> bool:
        return self.entry.options.get(
            CONF_EXCLUDE_CANCELLED, DEFAULT_EXCLUDE_CANCELLED
        )

    async def _get_access_token(self) -> str:
        """Get or refresh OAuth2 access token."""
        now = dt_util.utcnow()
        if (
            self._access_token
            and self._token_expires_at
            and now < self._token_expires_at
        ):
            return self._access_token

        headers = {
            "Authorization": f"Basic {self.auth_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        try:
            async with self.session.post(
                TOKEN_URL,
                headers=headers,
                data={"grant_type": "client_credentials"},
                timeout=15,
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    _LOGGER.error("Token request failed: %s - %s", response.status, text)
                    raise UpdateFailed(f"Failed to get access token: {response.status}")

                result = await response.json()
                self._access_token = result["access_token"]
                expires_in = int(result.get("expires_in", 86400))
                # Refresh 5 minutes before expiry
                self._token_expires_at = now + timedelta(seconds=max(expires_in - 300, 60))
                return self._access_token
        except ClientError as ex:
            raise UpdateFailed(f"Network error getting token: {ex}") from ex

    def _parse_departure(self, departure: dict[str, Any]) -> dict[str, Any] | None:
        """Parse one departure object from API."""
        service_journey = departure.get("serviceJourney") or {}
        line_obj = service_journey.get("line") or {}

        planned_time = departure.get("plannedTime")
        estimated_time = departure.get("estimatedTime")
        effective_time = estimated_time or planned_time
        if not effective_time:
            return None

        delay_minutes = 0
        if estimated_time and planned_time:
            try:
                planned_dt = dt_util.parse_datetime(planned_time)
                estimated_dt = dt_util.parse_datetime(estimated_time)
                if planned_dt and estimated_dt:
                    delay_minutes = int(
                        (estimated_dt - planned_dt).total_seconds() / 60
                    )
            except (TypeError, ValueError):
                delay_minutes = 0

        track = ""
        stop_point = departure.get("stopPoint") or {}
        platform = stop_point.get("platform")
        if platform:
            track = str(platform)
        elif departure.get("platform"):
            track = str(departure["platform"])

        line_name = line_obj.get("name") or line_obj.get("designation") or "?"
        direction = service_journey.get("direction") or ""
        transport_mode = (line_obj.get("transportMode") or "").lower()

        is_cancelled = bool(departure.get("isCancelled", False))

        return {
            "line": line_name,
            "line_designation": line_obj.get("designation") or "",
            "destination": direction,
            "planned_time": planned_time or "",
            "estimated_time": effective_time,
            "delay_minutes": delay_minutes,
            "track": track,
            "is_cancelled": is_cancelled,
            "is_realtime": estimated_time is not None,
            "transport_mode": transport_mode,
        }

    def _apply_filters(self, departures: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply direction/line/cancelled filters and drop past departures."""
        now = dt_util.now()
        direction_f = self.direction_filter.lower()
        line_f = self.line_filter.lower()
        result: list[dict[str, Any]] = []

        for dep in departures:
            if self.exclude_cancelled and dep.get("is_cancelled"):
                continue

            if direction_f and direction_f not in (dep.get("destination") or "").lower():
                continue

            if line_f:
                line = (dep.get("line") or "").lower()
                designation = (dep.get("line_designation") or "").lower()
                if line_f not in line and line_f not in designation:
                    continue

            # minutes_until
            minutes = 0
            relative = "?"
            departure_hhmm = "?"
            try:
                dt = dt_util.parse_datetime(dep["estimated_time"])
                if dt is None:
                    continue
                dt = dt_util.as_local(dt)
                seconds = (dt - now).total_seconds()
                minutes = int(seconds / 60)
                # Keep "about to leave" (-1 min) as Nu; drop older
                if minutes < -1:
                    continue
                if minutes <= 0:
                    relative = "Nu"
                    minutes = 0
                elif minutes == 1:
                    relative = "1 min"
                else:
                    relative = f"{minutes} min"
                departure_hhmm = dt.strftime("%H:%M")
            except (TypeError, ValueError, KeyError):
                continue

            dep = {
                **dep,
                "departure_time": departure_hhmm,
                "relative_time": relative,
                "minutes_until": minutes,
            }
            result.append(dep)

        # Sort by minutes until
        result.sort(key=lambda d: d.get("minutes_until", 9999))
        return result

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch departures from API."""
        try:
            token = await self._get_access_token()
        except UpdateFailed:
            raise

        options = self.entry.options
        time_span = options.get(CONF_TIME_SPAN_MINUTES, DEFAULT_TIME_SPAN_MINUTES)
        max_per_line = options.get(CONF_MAX_PER_LINE, DEFAULT_MAX_PER_LINE)

        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "timeSpanInMinutes": time_span,
            "maxDeparturesPerLine": max_per_line,
        }
        url = f"{API_BASE}/stop-areas/{self.station_gid}/departures"

        try:
            async with self.session.get(
                url, headers=headers, params=params, timeout=20
            ) as response:
                if response.status == 401:
                    self._access_token = None
                    self._token_expires_at = None
                    raise UpdateFailed("Access token expired, will retry")

                if response.status != 200:
                    text = await response.text()
                    _LOGGER.error(
                        "Departures request failed: %s - %s", response.status, text
                    )
                    raise UpdateFailed(f"Failed to get departures: {response.status}")

                payload = await response.json()
        except ClientError as ex:
            raise UpdateFailed(f"Network error: {ex}") from ex

        raw: list[dict[str, Any]] = []
        for item in payload.get("results") or []:
            parsed = self._parse_departure(item)
            if parsed:
                raw.append(parsed)

        filtered = self._apply_filters(raw)

        return {
            "departures": filtered,
            "last_update": dt_util.now().isoformat(),
            "raw_count": len(raw),
        }
