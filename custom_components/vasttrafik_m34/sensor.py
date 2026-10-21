"""Sensor platform for Västtrafik M34."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_DEPARTURE_COUNT,
    ATTR_DEPARTURES,
    ATTR_DEPARTURES_JSON,
    ATTR_DIRECTION_FILTER,
    ATTR_LAST_UPDATE,
    ATTR_LINE_FILTER,
    ATTR_NEXT_DELAY_MINUTES,
    ATTR_NEXT_DEPARTURE_TIME,
    ATTR_NEXT_DESTINATION,
    ATTR_NEXT_IS_REALTIME,
    ATTR_NEXT_LINE,
    ATTR_NEXT_MINUTES_UNTIL,
    ATTR_NEXT_TRACK,
    ATTR_STATION_GID,
    ATTR_STATION_NAME,
    CONF_SHOW_DELAY,
    CONF_STATION_GID,
    CONF_STATION_NAME,
    DEFAULT_SHOW_DELAY,
    DOMAIN,
)
from .coordinator import VasttrafikDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Västtrafik sensor from a config entry."""
    coordinator = entry.runtime_data
    station_name = entry.data[CONF_STATION_NAME]
    station_gid = entry.data[CONF_STATION_GID]
    async_add_entities([VasttrafikM34Sensor(coordinator, entry, station_name, station_gid)])


def _icon_for_mode(mode: str) -> str:
    """Pick icon from transport mode."""
    mode = (mode or "").lower()
    if mode in ("bus", "buss"):
        return "mdi:bus"
    if mode in ("tram", "spårvagn", "sparvagn"):
        return "mdi:tram"
    if mode in ("train", "tåg", "tag", "rail"):
        return "mdi:train"
    if mode in ("ferry", "boat", "färja"):
        return "mdi:ferry"
    return "mdi:bus-clock"


class VasttrafikM34Sensor(CoordinatorEntity[VasttrafikDataUpdateCoordinator], SensorEntity):
    """Departure sensor for one stop area."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self,
        coordinator: VasttrafikDataUpdateCoordinator,
        entry: ConfigEntry,
        station_name: str,
        station_gid: str,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._station_name = station_name
        self._station_gid = station_gid
        self._attr_unique_id = f"vasttrafik_{station_gid}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, station_gid)},
            name=station_name,
            manufacturer="Västtrafik",
            model="M34 Departure Monitor",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.vasttrafik.se",
        )

    @property
    def available(self) -> bool:
        """Return True if coordinator update succeeded."""
        return self.coordinator.last_update_success

    @property
    def icon(self) -> str:
        """Icon from next departure transport mode."""
        deps = (self.coordinator.data or {}).get("departures") or []
        if deps:
            return _icon_for_mode(deps[0].get("transport_mode", ""))
        return "mdi:bus-clock"

    @property
    def native_value(self) -> str | None:
        """State: next departure in compact form."""
        data = self.coordinator.data
        if not data:
            return None

        deps = data.get("departures") or []
        if not deps:
            return "Inga avgångar"

        dep = deps[0]
        show_delay = self._entry.options.get(CONF_SHOW_DELAY, DEFAULT_SHOW_DELAY)
        state = f"kl. {dep.get('departure_time', '?')} ({dep.get('relative_time', '?')})"

        # Visa destination bara om man inte redan filtrerat på riktning
        direction_filter = (self.coordinator.direction_filter or "").strip()
        if not direction_filter:
            dest = dep.get("destination") or ""
            short_dest = dest.split(",")[0].strip() if dest else ""
            if "Resecentrum" in short_dest:
                short_dest = "Resecentrum"
            if short_dest:
                state = f"{state} → {short_dest}"

        delay = int(dep.get("delay_minutes") or 0)
        if show_delay and delay > 0:
            state = f"{state} · +{delay} min"
        elif show_delay and delay < 0:
            state = f"{state} · {delay} min"

        return state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return attributes including next_* and full departure lists."""
        data = self.coordinator.data
        if not data:
            return {}

        deps = data.get("departures") or []
        show_delay = self._entry.options.get(CONF_SHOW_DELAY, DEFAULT_SHOW_DELAY)

        # Legacy human-readable strings
        departure_list: list[str] = []
        for dep in deps[:15]:
            delay = int(dep.get("delay_minutes") or 0)
            delay_str = ""
            if show_delay and delay > 0:
                delay_str = f" (+{delay})"
            elif show_delay and delay < 0:
                delay_str = f" ({delay})"
            cancelled = " [INSTÄLLD]" if dep.get("is_cancelled") else ""
            track = dep.get("track") or ""
            track_str = f" Läge {track}" if track else ""
            departure_list.append(
                f"{dep.get('line', '?')} → {dep.get('destination', '?')} - "
                f"{dep.get('departure_time', '?')} ({dep.get('relative_time', '?')})"
                f"{delay_str}{track_str}{cancelled}"
            )

        attrs: dict[str, Any] = {
            ATTR_STATION_NAME: self._station_name,
            ATTR_STATION_GID: self._station_gid,
            ATTR_DEPARTURE_COUNT: len(deps),
            ATTR_DEPARTURES: departure_list,
            ATTR_DEPARTURES_JSON: deps[:20],
            ATTR_LAST_UPDATE: data.get("last_update"),
            ATTR_DIRECTION_FILTER: self.coordinator.direction_filter or None,
            ATTR_LINE_FILTER: self.coordinator.line_filter or None,
        }

        if deps:
            nxt = deps[0]
            attrs.update(
                {
                    ATTR_NEXT_LINE: nxt.get("line"),
                    ATTR_NEXT_DESTINATION: nxt.get("destination"),
                    ATTR_NEXT_DEPARTURE_TIME: nxt.get("departure_time"),
                    ATTR_NEXT_MINUTES_UNTIL: nxt.get("minutes_until"),
                    ATTR_NEXT_TRACK: nxt.get("track") or None,
                    ATTR_NEXT_DELAY_MINUTES: nxt.get("delay_minutes", 0),
                    ATTR_NEXT_IS_REALTIME: nxt.get("is_realtime", False),
                }
            )
        else:
            attrs.update(
                {
                    ATTR_NEXT_LINE: None,
                    ATTR_NEXT_DESTINATION: None,
                    ATTR_NEXT_DEPARTURE_TIME: None,
                    ATTR_NEXT_MINUTES_UNTIL: None,
                    ATTR_NEXT_TRACK: None,
                    ATTR_NEXT_DELAY_MINUTES: 0,
                    ATTR_NEXT_IS_REALTIME: False,
                }
            )

        return attrs
