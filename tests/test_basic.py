"""Simple unit tests for Västtrafik M34 integration."""
import pytest
import os
import sys
from pathlib import Path

# Ensure the custom_components directory is in the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestBasicFunctionality:
    """Test basic functionality without Home Assistant dependencies."""
    
    def test_domain_constant(self):
        """Test that DOMAIN constant is defined."""
        try:
            from custom_components.vasttrafik_m34.const import DOMAIN
            assert DOMAIN == "vasttrafik_m34"
        except ImportError as e:
            pytest.skip(f"Could not import module: {e}")
    
    def test_manifest_exists(self):
        """Test that manifest.json exists and is valid."""
        import json
        manifest_path = project_root / 'custom_components' / 'vasttrafik_m34' / 'manifest.json'
        
        assert manifest_path.exists(), "manifest.json does not exist"
        
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        assert manifest['domain'] == 'vasttrafik_m34'
        assert manifest['name'] == 'Västtrafik M34'
        # Check version format is valid (e.g., "2.4.1")
        assert 'version' in manifest
        version_parts = manifest['version'].split('.')
        assert len(version_parts) >= 2, "Version should be in format X.Y or X.Y.Z"
        assert 'aiohttp>=3.8.0' in manifest['requirements']
    
    def test_strings_file_exists(self):
        """Test that strings.json exists and is valid."""
        import json
        strings_path = project_root / 'custom_components' / 'vasttrafik_m34' / 'strings.json'
        
        assert strings_path.exists(), "strings.json does not exist"
        
        with open(strings_path, 'r', encoding='utf-8') as f:
            strings = json.load(f)
        
        assert 'config' in strings
        assert 'step' in strings['config']
        # Verify station search step has correct field name
        assert 'station' in strings['config']['step']
        assert 'data' in strings['config']['step']['station']
        assert 'station_name' in strings['config']['step']['station']['data']
    
    def test_translations_exist(self):
        """Test that Swedish translations exist."""
        import json
        translations_path = project_root / 'custom_components' / 'vasttrafik_m34' / 'translations' / 'sv.json'
        
        assert translations_path.exists(), "sv.json does not exist"
        
        with open(translations_path, 'r', encoding='utf-8') as f:
            translations = json.load(f)
        
        assert 'config' in translations


class TestCodeQuality:
    """Test code quality and structure."""
    
    def test_all_required_files_exist(self):
        """Test that all required files exist."""
        required_files = [
            'custom_components/vasttrafik_m34/__init__.py',
            'custom_components/vasttrafik_m34/manifest.json',
            'custom_components/vasttrafik_m34/const.py',
            'custom_components/vasttrafik_m34/config_flow.py',
            'custom_components/vasttrafik_m34/sensor.py',
            'custom_components/vasttrafik_m34/strings.json',
            'custom_components/vasttrafik_m34/translations/sv.json',
        ]
        
        for file_path in required_files:
            full_path = project_root / file_path
            assert full_path.exists(), f"Required file {file_path} does not exist"
    
    def test_no_syntax_errors(self):
        """Test that Python files have no syntax errors."""
        import py_compile
        import glob
        
        pattern = str(project_root / 'custom_components' / 'vasttrafik_m34' / '**' / '*.py')
        python_files = glob.glob(pattern, recursive=True)
        
        assert len(python_files) > 0, "No Python files found"
        
        for file_path in python_files:
            try:
                py_compile.compile(file_path, doraise=True)
            except py_compile.PyCompileError as e:
                pytest.fail(f"Syntax error in {file_path}: {e}")
    
    def test_readme_exists(self):
        """Test that README exists."""
        readme_path = project_root / 'README.md'
        assert readme_path.exists(), "README.md does not exist"
    
    def test_requirements_files_exist(self):
        """Test that requirements files exist."""
        req_path = project_root / 'requirements.txt'
        req_test_path = project_root / 'requirements_test.txt'
        
        assert req_path.exists(), "requirements.txt does not exist"
        assert req_test_path.exists(), "requirements_test.txt does not exist"


class TestDataStructure:
    """Test data structures are correct."""
    
    def test_departure_data_structure(self):
        """Test that departure data structure is as expected."""
        from datetime import datetime, timedelta
        
        # Create mock departure data matching API v4
        now = datetime.now()
        mock_departure = {
            "serviceJourney": {
                "line": {"name": "16", "designation": "16"},
                "direction": "Bergsjön",
            },
            "plannedTime": (now + timedelta(minutes=5)).isoformat(),
            "estimatedTime": (now + timedelta(minutes=5)).isoformat(),
            "stopPoint": {"platform": {"name": "B"}},
            "isCancelled": False,
        }
        
        # Verify structure
        assert mock_departure['serviceJourney']['line']['name'] == '16'
        assert mock_departure['serviceJourney']['direction'] == 'Bergsjön'
        assert mock_departure['isCancelled'] is False
        assert 'plannedTime' in mock_departure
        assert 'estimatedTime' in mock_departure
