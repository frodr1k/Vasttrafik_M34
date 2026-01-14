# Integration Tests - Requires Home Assistant

These tests require a full Home Assistant installation to run.

## Why Moved?

These comprehensive integration tests were moved because:
1. They require `pytest-homeassistant-custom-component` which needs full HA installation
2. GitHub Actions would fail without complex HA setup
3. They're valuable for local testing but too heavy for CI/CD

## Running These Tests Locally

If you want to run these comprehensive tests:

### 1. Install Home Assistant test dependencies:
```bash
pip install homeassistant pytest-homeassistant-custom-component
```

### 2. Run the tests:
```bash
pytest tests/integration_tests_backup/ -v
```

## What We Test Instead

The main test suite (`test_basic.py`) covers:
- ✅ File structure validation
- ✅ Manifest correctness
- ✅ No syntax errors
- ✅ Basic functionality mocking
- ✅ Token validation logic
- ✅ Departure data parsing

## Future Improvements

To run full integration tests in CI/CD, we would need:
1. Custom GitHub Actions with HA installation
2. Docker container with HA pre-installed
3. or: Simplified mocks that don't require full HA

For now, basic tests ensure code quality while keeping CI/CD fast and reliable.
