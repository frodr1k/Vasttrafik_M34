"""Test configuration for Västtrafik M34 integration."""
import pytest
import sys
from pathlib import Path

# Add the custom_components directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_hass():
    """Return a mock Home Assistant instance for tests that need it."""
    from unittest.mock import MagicMock
    
    mock = MagicMock()
    mock.config_entries = MagicMock()
    return mock
