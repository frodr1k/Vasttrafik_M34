"""Tests for the Västtrafik M34 sensor platform."""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.vasttrafik_m34.sensor import (
    VasttrafikDataUpdateCoordinator,
    VasttrafikM34Sensor,
)


@pytest.fixture
def mock_token_response():
    """Mock successful OAuth2 token response."""
    return {
        "access_token": "mock_access_token_123456",
        "token_type": "Bearer",
        "expires_in": 86400,
    }


@pytest.fixture
def mock_departures_response():
    """Mock successful departures response."""
    now = datetime.now()
    future_time = (now + timedelta(minutes=5)).isoformat()
    
    return {
        "results": [
            {
                "serviceJourney": {
                    "line": {"name": "16", "designation": "16"},
                    "direction": "Bergsjön",
                },
                "plannedTime": future_time,
                "estimatedTime": future_time,
                "stopPoint": {"platform": {"name": "B"}},
                "isCancelled": False,
            },
            {
                "serviceJourney": {
                    "line": {"name": "6", "designation": "6"},
                    "direction": "Chalmers",
                },
                "plannedTime": (now + timedelta(minutes=10)).isoformat(),
                "estimatedTime": (now + timedelta(minutes=12)).isoformat(),
                "stopPoint": {"platform": {"name": "A"}},
                "isCancelled": False,
            },
        ]
    }


@pytest.fixture
def coordinator(hass: HomeAssistant):
    """Create a coordinator instance."""
    return VasttrafikDataUpdateCoordinator(
        hass=hass,
        auth_key="bXlDbGllbnRJZDpteUNsaWVudFNlY3JldA==",
        station_gid="9021014001960000",
    )


async def test_coordinator_update_success(
    coordinator, mock_token_response, mock_departures_response
):
    """Test successful coordinator data update."""
    with patch(
        "custom_components.vasttrafik_m34.sensor.aiohttp.ClientSession.post",
    ) as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value=mock_token_response
        )

        with patch(
            "custom_components.vasttrafik_m34.sensor.aiohttp.ClientSession.get",
        ) as mock_get:
            mock_get.return_value.__aenter__.return_value.status = 200
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(
                return_value=mock_departures_response
            )

            await coordinator._async_update_data()

            assert coordinator.data is not None
            assert "departures" in coordinator.data
            assert len(coordinator.data["departures"]) == 2
            assert coordinator.data["departures"][0]["line_number"] == "16"


async def test_coordinator_token_refresh(
    coordinator, mock_token_response, mock_departures_response
):
    """Test that coordinator refreshes expired tokens."""
    # Set expired token
    coordinator.access_token = "old_token"
    coordinator.token_expiry = datetime.now() - timedelta(minutes=1)

    with patch(
        "custom_components.vasttrafik_m34.sensor.aiohttp.ClientSession.post",
    ) as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        mock_post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value=mock_token_response
        )

        with patch(
            "custom_components.vasttrafik_m34.sensor.aiohttp.ClientSession.get",
        ) as mock_get:
            mock_get.return_value.__aenter__.return_value.status = 200
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(
                return_value=mock_departures_response
            )

            await coordinator._async_update_data()

            assert coordinator.access_token == "mock_access_token_123456"


async def test_coordinator_auth_failure(coordinator):
    """Test coordinator handles authentication failure."""
    with patch(
        "custom_components.vasttrafik_m34.sensor.aiohttp.ClientSession.post",
    ) as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 401
        mock_post.return_value.__aenter__.return_value.text = AsyncMock(
            return_value="Invalid credentials"
        )

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_coordinator_network_error(coordinator):
    """Test coordinator handles network errors."""
    with patch(
        "custom_components.vasttrafik_m34.sensor.aiohttp.ClientSession.post",
        side_effect=Exception("Network error"),
    ):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_sensor_state(hass: HomeAssistant, coordinator, mock_departures_response):
    """Test sensor state formatting."""
    coordinator.data = {
        "departures": [
            {
                "line_number": "16",
                "direction": "Bergsjön",
                "estimated_time": (datetime.now() + timedelta(minutes=2)).isoformat(),
            }
        ],
        "last_update": datetime.now().isoformat(),
    }

    sensor = VasttrafikM34Sensor(
        coordinator=coordinator,
        station_name="Centralstationen",
        station_gid="9021014001960000",
    )

    state = sensor.native_value
    assert "avgångar från Centralstationen" in state


async def test_sensor_no_departures(hass: HomeAssistant, coordinator):
    """Test sensor state when no departures."""
    coordinator.data = {
        "departures": [],
        "last_update": datetime.now().isoformat(),
    }

    sensor = VasttrafikM34Sensor(
        coordinator=coordinator,
        station_name="Centralstationen",
        station_gid="9021014001960000",
    )

    assert sensor.native_value == "Inga avgångar"


async def test_sensor_attributes(hass: HomeAssistant, coordinator):
    """Test sensor attributes contain departure information."""
    coordinator.data = {
        "departures": [
            {
                "line_number": "16",
                "direction": "Bergsjön",
                "estimated_time": (datetime.now() + timedelta(minutes=2)).isoformat(),
                "delay_minutes": 0,
                "track": "B",
                "is_cancelled": False,
                "is_realtime": True,
            }
        ],
        "last_update": datetime.now().isoformat(),
    }

    sensor = VasttrafikM34Sensor(
        coordinator=coordinator,
        station_name="Centralstationen",
        station_gid="9021014001960000",
    )

    attrs = sensor.extra_state_attributes
    assert "station_name" in attrs
    assert attrs["station_name"] == "Centralstationen"
    assert "departures" in attrs
    assert len(attrs["departures"]) == 1
    assert "next_departures" in attrs
    assert attrs["next_departures"][0]["line"] == "16"


async def test_sensor_availability(hass: HomeAssistant, coordinator):
    """Test sensor availability based on coordinator status."""
    sensor = VasttrafikM34Sensor(
        coordinator=coordinator,
        station_name="Centralstationen",
        station_gid="9021014001960000",
    )

    coordinator.last_update_success = True
    assert sensor.available is True

    coordinator.last_update_success = False
    assert sensor.available is False
