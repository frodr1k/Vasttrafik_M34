"""Tests for the Västtrafik M34 integration init."""
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.vasttrafik_m34 import async_setup_entry, async_unload_entry
from custom_components.vasttrafik_m34.const import DOMAIN


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Centralstationen",
        data={
            "auth_key": "bXlDbGllbnRJZDpteUNsaWVudFNlY3JldA==",
            "station_name": "Centralstationen, Göteborg",
            "station_gid": "9021014001960000",
        },
        source="user",
        unique_id="9021014001960000",
    )


@pytest.fixture
def mock_token_response():
    """Mock successful OAuth2 token response."""
    return {
        "access_token": "mock_access_token_123456",
        "token_type": "Bearer",
        "expires_in": 86400,
    }


async def test_setup_entry_success(
    hass: HomeAssistant, mock_config_entry, mock_token_response
):
    """Test successful setup of a config entry."""
    with patch(
        "custom_components.vasttrafik_m34.aiohttp.ClientSession.post",
    ) as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value=mock_token_response
        )

        with patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            return_value=True,
        ):
            result = await async_setup_entry(hass, mock_config_entry)
            assert result is True


async def test_setup_entry_missing_auth_key(hass: HomeAssistant):
    """Test setup fails when auth_key is missing."""
    entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Test Station",
        data={
            "station_name": "Test Station",
            "station_gid": "9021014001960000",
        },
        source="user",
        unique_id="9021014001960000",
    )

    result = await async_setup_entry(hass, entry)
    assert result is False


async def test_setup_entry_missing_station_gid(hass: HomeAssistant):
    """Test setup fails when station_gid is missing."""
    entry = ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Test Station",
        data={
            "auth_key": "bXlDbGllbnRJZDpteUNsaWVudFNlY3JldA==",
            "station_name": "Test Station",
        },
        source="user",
        unique_id="test_station",
    )

    result = await async_setup_entry(hass, entry)
    assert result is False


async def test_setup_entry_auth_failure(hass: HomeAssistant, mock_config_entry):
    """Test setup raises ConfigEntryNotReady on auth failure."""
    with patch(
        "custom_components.vasttrafik_m34.aiohttp.ClientSession.post",
    ) as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 401
        mock_post.return_value.__aenter__.return_value.text = AsyncMock(
            return_value="Invalid credentials"
        )

        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, mock_config_entry)


async def test_setup_entry_network_error(hass: HomeAssistant, mock_config_entry):
    """Test setup raises ConfigEntryNotReady on network error."""
    with patch(
        "custom_components.vasttrafik_m34.aiohttp.ClientSession.post",
        side_effect=Exception("Network error"),
    ):
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, mock_config_entry)


async def test_unload_entry(hass: HomeAssistant, mock_config_entry):
    """Test unloading a config entry."""
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        return_value=True,
    ):
        result = await async_unload_entry(hass, mock_config_entry)
        assert result is True
