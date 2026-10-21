"""Config and options flow for Västtrafik M34."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_BASE,
    CONF_AUTH_KEY,
    CONF_DIRECTION_FILTER,
    CONF_EXCLUDE_CANCELLED,
    CONF_LINE_FILTER,
    CONF_MAX_PER_LINE,
    CONF_SHOW_DELAY,
    CONF_STATION_GID,
    CONF_STATION_NAME,
    CONF_TIME_SPAN_MINUTES,
    CONF_UPDATE_INTERVAL,
    DEFAULT_EXCLUDE_CANCELLED,
    DEFAULT_MAX_PER_LINE,
    DEFAULT_SHOW_DELAY,
    DEFAULT_TIME_SPAN_MINUTES,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    TOKEN_URL,
)

_LOGGER = logging.getLogger(__name__)


async def get_access_token(hass: HomeAssistant, auth_key: str) -> str:
    """Get OAuth2 access token."""
    session = async_get_clientsession(hass)
    headers = {
        "Authorization": f"Basic {auth_key}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    try:
        async with session.post(
            TOKEN_URL,
            headers=headers,
            data={"grant_type": "client_credentials"},
            timeout=15,
        ) as response:
            if response.status != 200:
                text = await response.text()
                _LOGGER.error("Token request failed: %s - %s", response.status, text)
                raise CannotConnect(f"Failed to get access token: {response.status}")
            result = await response.json()
            token = result.get("access_token")
            if not token:
                raise InvalidAuth("No access token in response")
            return token
    except HomeAssistantError:
        raise
    except Exception as ex:
        raise CannotConnect(f"Network error: {ex}") from ex


async def search_stations(
    hass: HomeAssistant, access_token: str, query: str
) -> list[dict[str, str]]:
    """Search stop areas by name."""
    session = async_get_clientsession(hass)
    headers = {"Authorization": f"Bearer {access_token}"}
    # API: GET /locations/by-text
    url = f"{API_BASE}/locations/by-text"
    params = {"q": query, "types": "stoparea", "limit": 15}
    try:
        async with session.get(url, headers=headers, params=params, timeout=15) as response:
            if response.status != 200:
                text = await response.text()
                _LOGGER.error("Station search failed: %s - %s", response.status, text)
                raise CannotConnect(f"Station search failed: {response.status}")
            data = await response.json()
    except HomeAssistantError:
        raise
    except Exception as ex:
        raise CannotConnect(f"Network error: {ex}") from ex

    stations: list[dict[str, str]] = []
    results = data.get("results") or data.get("stopAreas") or []
    if isinstance(data, list):
        results = data

    for item in results:
        # Support a few possible shapes from API
        gid = item.get("gid") or item.get("stopAreaGid") or item.get("id")
        name = (
            item.get("name")
            or item.get("stopAreaName")
            or item.get("locationName")
            or ""
        )
        if not gid or not name:
            continue
        municipality = ""
        if item.get("municipality"):
            if isinstance(item["municipality"], dict):
                municipality = item["municipality"].get("name") or ""
            else:
                municipality = str(item["municipality"])
        display = f"{name}, {municipality}" if municipality else name
        stations.append({"gid": str(gid), "name": display})

    return stations


class VasttrafikConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Västtrafik M34."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""
        self._auth_key: str | None = None
        self._access_token: str | None = None
        self._stations: list[dict[str, str]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step – auth key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            auth_key = user_input[CONF_AUTH_KEY].strip()
            try:
                token = await get_access_token(self.hass, auth_key)
                self._auth_key = auth_key
                self._access_token = token
                return await self.async_step_station()
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during auth")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_AUTH_KEY): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "portal": "https://developer.vasttrafik.se",
            },
        )

    async def async_step_station(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Search for a station by name."""
        errors: dict[str, str] = {}

        if user_input is not None:
            query = user_input[CONF_STATION_NAME].strip()
            try:
                assert self._access_token is not None
                stations = await search_stations(self.hass, self._access_token, query)
                if not stations:
                    errors["base"] = "no_stations"
                else:
                    self._stations = stations
                    return await self.async_step_select_station()
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during station search")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="station",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATION_NAME): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "station_example": "t.ex. Näverstigen, Central, Brunnsparken",
            },
        )

    async def async_step_select_station(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select station from search results."""
        errors: dict[str, str] = {}

        if user_input is not None:
            station_gid = user_input["station"]
            selected = next(
                (s for s in self._stations if s["gid"] == station_gid), None
            )
            if selected:
                await self.async_set_unique_id(f"vasttrafik_{station_gid}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=selected["name"],
                    data={
                        CONF_AUTH_KEY: self._auth_key,
                        CONF_STATION_GID: selected["gid"],
                        CONF_STATION_NAME: selected["name"],
                    },
                    options={
                        CONF_DIRECTION_FILTER: "",
                        CONF_LINE_FILTER: "",
                        CONF_EXCLUDE_CANCELLED: DEFAULT_EXCLUDE_CANCELLED,
                        CONF_SHOW_DELAY: DEFAULT_SHOW_DELAY,
                        CONF_TIME_SPAN_MINUTES: DEFAULT_TIME_SPAN_MINUTES,
                        CONF_MAX_PER_LINE: DEFAULT_MAX_PER_LINE,
                        CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
                    },
                )
            errors["base"] = "invalid_station"

        station_options = {s["gid"]: s["name"] for s in self._stations}
        return self.async_show_form(
            step_id="select_station",
            data_schema=vol.Schema(
                {
                    vol.Required("station"): vol.In(station_options),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow."""
        return VasttrafikOptionsFlow()


class VasttrafikOptionsFlow(config_entries.OptionsFlow):
    """Handle options (filters, interval, etc.)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DIRECTION_FILTER,
                        default=current.get(CONF_DIRECTION_FILTER, ""),
                    ): str,
                    vol.Optional(
                        CONF_LINE_FILTER,
                        default=current.get(CONF_LINE_FILTER, ""),
                    ): str,
                    vol.Optional(
                        CONF_EXCLUDE_CANCELLED,
                        default=current.get(
                            CONF_EXCLUDE_CANCELLED, DEFAULT_EXCLUDE_CANCELLED
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_SHOW_DELAY,
                        default=current.get(CONF_SHOW_DELAY, DEFAULT_SHOW_DELAY),
                    ): bool,
                    vol.Optional(
                        CONF_TIME_SPAN_MINUTES,
                        default=current.get(
                            CONF_TIME_SPAN_MINUTES, DEFAULT_TIME_SPAN_MINUTES
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=15, max=180)),
                    vol.Optional(
                        CONF_MAX_PER_LINE,
                        default=current.get(CONF_MAX_PER_LINE, DEFAULT_MAX_PER_LINE),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=10)),
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=current.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=30, max=300)),
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
