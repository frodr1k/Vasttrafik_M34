"""Tests for the Västtrafik M34 config flow."""
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.vasttrafik_m34.const import DOMAIN


@pytest.fixture
def mock_setup_entry():
    """Mock setting up a config entry."""
    with patch(
        "custom_components.vasttrafik_m34.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_token_response():
    """Mock successful OAuth2 token response."""
    return {
        "access_token": "mock_access_token_123456",
        "token_type": "Bearer",
        "expires_in": 86400,
    }


@pytest.fixture
def mock_search_response():
    """Mock successful station search response."""
    return {
        "results": [
            {
                "name": "Centralstationen, Göteborg",
                "gid": "9021014001960000",
            },
            {
                "name": "Centralhållplatsen, Göteborg",
                "gid": "9021014001950000",
            },
        ]
    }


async def test_form_user_step(hass: HomeAssistant, mock_setup_entry, mock_token_response):
    """Test the user step of the config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    # Test with valid auth key
    with patch(
        "custom_components.vasttrafik_m34.config_flow.aiohttp.ClientSession.post",
    ) as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value=mock_token_response
        )

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"auth_key": "bXlDbGllbnRJZDpteUNsaWVudFNlY3JldA=="},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "search"


async def test_form_invalid_auth(hass: HomeAssistant):
    """Test we handle invalid auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.vasttrafik_m34.config_flow.aiohttp.ClientSession.post",
    ) as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 401
        mock_post.return_value.__aenter__.return_value.text = AsyncMock(
            return_value="Invalid credentials"
        )

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"auth_key": "invalid_key"},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "user"
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_search_step(
    hass: HomeAssistant, mock_setup_entry, mock_token_response, mock_search_response
):
    """Test the search step of the config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Complete user step
    with patch(
        "custom_components.vasttrafik_m34.config_flow.aiohttp.ClientSession.post",
    ) as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value=mock_token_response
        )

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"auth_key": "bXlDbGllbnRJZDpteUNsaWVudFNlY3JldA=="},
        )

    # Test search step
    with patch(
        "custom_components.vasttrafik_m34.config_flow.aiohttp.ClientSession.get",
    ) as mock_get:
        mock_get.return_value.__aenter__.return_value.status = 200
        mock_get.return_value.__aenter__.return_value.json = AsyncMock(
            return_value=mock_search_response
        )

        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {"search_query": "Central"},
        )

    assert result3["type"] == FlowResultType.FORM
    assert result3["step_id"] == "select"


async def test_form_complete_flow(
    hass: HomeAssistant, mock_setup_entry, mock_token_response, mock_search_response
):
    """Test completing the entire config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Step 1: User (auth key)
    with patch(
        "custom_components.vasttrafik_m34.config_flow.aiohttp.ClientSession.post",
    ) as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value=mock_token_response
        )

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"auth_key": "bXlDbGllbnRJZDpteUNsaWVudFNlY3JldA=="},
        )

    # Step 2: Search
    with patch(
        "custom_components.vasttrafik_m34.config_flow.aiohttp.ClientSession.get",
    ) as mock_get:
        mock_get.return_value.__aenter__.return_value.status = 200
        mock_get.return_value.__aenter__.return_value.json = AsyncMock(
            return_value=mock_search_response
        )

        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {"search_query": "Central"},
        )

    # Step 3: Select
    result4 = await hass.config_entries.flow.async_configure(
        result3["flow_id"],
        {"station_gid": "9021014001960000"},
    )

    assert result4["type"] == FlowResultType.CREATE_ENTRY
    assert result4["title"] == "Centralstationen, Göteborg"
    assert result4["data"] == {
        "auth_key": "bXlDbGllbnRJZDpteUNsaWVudFNlY3JldA==",
        "station_name": "Centralstationen, Göteborg",
        "station_gid": "9021014001960000",
    }


async def test_duplicate_entry(
    hass: HomeAssistant, mock_setup_entry, mock_token_response, mock_search_response
):
    """Test that duplicate entries are prevented."""
    # Create an existing entry
    existing_entry = config_entries.ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Centralstationen, Göteborg",
        data={
            "auth_key": "bXlDbGllbnRJZDpteUNsaWVudFNlY3JldA==",
            "station_name": "Centralstationen, Göteborg",
            "station_gid": "9021014001960000",
        },
        source=config_entries.SOURCE_USER,
        unique_id="9021014001960000",
    )
    existing_entry.add_to_hass(hass)

    # Try to create duplicate
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Step 1: Auth
    with patch(
        "custom_components.vasttrafik_m34.config_flow.aiohttp.ClientSession.post",
    ) as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value=mock_token_response
        )

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"auth_key": "bXlDbGllbnRJZDpteUNsaWVudFNlY3JldA=="},
        )

    # Step 2: Search
    with patch(
        "custom_components.vasttrafik_m34.config_flow.aiohttp.ClientSession.get",
    ) as mock_get:
        mock_get.return_value.__aenter__.return_value.status = 200
        mock_get.return_value.__aenter__.return_value.json = AsyncMock(
            return_value=mock_search_response
        )

        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {"search_query": "Central"},
        )

    # Step 3: Select same station
    result4 = await hass.config_entries.flow.async_configure(
        result3["flow_id"],
        {"station_gid": "9021014001960000"},
    )

    assert result4["type"] == FlowResultType.ABORT
    assert result4["reason"] == "already_configured"


async def test_connection_error(hass: HomeAssistant):
    """Test we handle connection errors."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.vasttrafik_m34.config_flow.aiohttp.ClientSession.post",
        side_effect=Exception("Connection failed"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"auth_key": "bXlDbGllbnRJZDpteUNsaWVudFNlY3JldA=="},
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "user"
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_no_stations_found(
    hass: HomeAssistant, mock_token_response
):
    """Test handling when no stations are found."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Complete user step
    with patch(
        "custom_components.vasttrafik_m34.config_flow.aiohttp.ClientSession.post",
    ) as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value=mock_token_response
        )

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"auth_key": "bXlDbGllbnRJZDpteUNsaWVudFNlY3JldA=="},
        )

    # Search returns empty results
    with patch(
        "custom_components.vasttrafik_m34.config_flow.aiohttp.ClientSession.get",
    ) as mock_get:
        mock_get.return_value.__aenter__.return_value.status = 200
        mock_get.return_value.__aenter__.return_value.json = AsyncMock(
            return_value={"results": []}
        )

        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {"search_query": "NonExistentStation"},
        )

    assert result3["type"] == FlowResultType.FORM
    assert result3["step_id"] == "search"
    assert result3["errors"] == {"base": "no_stations"}
