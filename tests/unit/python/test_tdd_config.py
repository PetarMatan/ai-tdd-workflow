#!/usr/bin/env python3
"""
Unit tests for tdd_config.py
"""

import json
import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add hooks/lib to path
sys.path.insert(0, 'hooks/lib')

# Mock the dependent modules before importing TDDConfig
sys.modules['config_reader'] = MagicMock()
sys.modules['profile_detector'] = MagicMock()
sys.modules['pattern_matcher'] = MagicMock()

from tdd_config import TDDConfig


class TestTDDConfigInit:
    """Tests for TDDConfig initialization."""

    def test_init_with_default_dir(self):
        config = TDDConfig()
        assert config.project_dir == os.path.abspath(".")

    def test_init_with_custom_dir(self):
        config = TDDConfig("/custom/project")
        assert config.project_dir == "/custom/project"

    def test_init_uses_env_vars(self):
        with patch.dict(os.environ, {
            "TDD_INSTALL_DIR": "/install",
            "TDD_CONFIG_FILE": "/custom/config.json",
            "TDD_OVERRIDE_FILE": "/custom/override.json"
        }):
            config = TDDConfig()
            assert config.config_file == "/custom/config.json"
            assert config.override_file == "/custom/override.json"

    def test_init_default_config_paths(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TDD_INSTALL_DIR", None)
            os.environ.pop("TDD_CONFIG_FILE", None)
            os.environ.pop("TDD_OVERRIDE_FILE", None)
            config = TDDConfig()
            assert "tdd-config.json" in config.config_file
            assert "tdd-override.json" in config.override_file


class TestDetectProfile:
    """Tests for detect_profile method."""

    def test_returns_cached_profile(self):
        config = TDDConfig()
        config._detected_profile = "cached-profile"
        result = config.detect_profile()
        assert result == "cached-profile"

    def test_uses_override_file(self):
        import profile_detector
        profile_detector.get_override = MagicMock(return_value="override-profile")
        profile_detector.detect_profile = MagicMock(return_value="")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{}")
            f.flush()
            config = TDDConfig()
            config.override_file = f.name

            result = config.detect_profile()
            assert result == "override-profile"

    def test_auto_detects_profile(self):
        import profile_detector
        profile_detector.get_override = MagicMock(return_value="")
        profile_detector.detect_profile = MagicMock(return_value="detected-profile")

        config = TDDConfig()
        config.override_file = "/nonexistent/file"
        result = config.detect_profile()
        assert result == "detected-profile"

    def test_uses_env_default(self):
        import profile_detector
        profile_detector.get_override = MagicMock(return_value="")
        profile_detector.detect_profile = MagicMock(return_value="")

        with patch.dict(os.environ, {"TDD_DEFAULT_PROFILE": "env-default"}):
            config = TDDConfig()
            config.override_file = "/nonexistent/file"
            config._detected_profile = None
            result = config.detect_profile()
            assert result == "env-default"

    def test_returns_none_when_no_profile(self):
        import profile_detector
        profile_detector.get_override = MagicMock(return_value="")
        profile_detector.detect_profile = MagicMock(return_value="")

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TDD_DEFAULT_PROFILE", None)
            config = TDDConfig()
            config.override_file = "/nonexistent/file"
            config._detected_profile = None
            result = config.detect_profile()
            assert result is None


class TestGetProfileName:
    """Tests for get_profile_name method."""

    def test_returns_name_from_config(self):
        import config_reader
        config_reader.get_config_value = MagicMock(return_value="Kotlin Maven")

        config = TDDConfig()
        config._detected_profile = "kotlin-maven"
        result = config.get_profile_name()
        assert result == "Kotlin Maven"

    def test_returns_profile_id_as_fallback(self):
        import config_reader
        config_reader.get_config_value = MagicMock(return_value=None)

        config = TDDConfig()
        config._detected_profile = "typescript-npm"
        result = config.get_profile_name()
        assert result == "typescript-npm"

    def test_returns_unknown_when_no_profile(self):
        config = TDDConfig()
        config._detected_profile = None
        # Force detect_profile to return None
        with patch.object(config, 'detect_profile', return_value=None):
            result = config.get_profile_name()
            assert result == "Unknown"


class TestGetCommand:
    """Tests for get_command method."""

    def test_returns_command(self):
        import config_reader
        config_reader.get_config_value = MagicMock(return_value="npm run build")

        config = TDDConfig()
        config._detected_profile = "typescript-npm"
        result = config.get_command("compile")
        assert result == "npm run build"

        config_reader.get_config_value.assert_called_with(
            "profiles.typescript-npm.commands.compile",
            config.config_file
        )

    def test_returns_none_when_no_profile(self):
        config = TDDConfig()
        with patch.object(config, 'detect_profile', return_value=None):
            result = config.get_command("compile")
            assert result is None


class TestGetSourcePattern:
    """Tests for get_source_pattern method."""

    def test_returns_pattern(self):
        import config_reader
        config_reader.get_config_value = MagicMock(return_value='["src/**/*.ts"]')

        config = TDDConfig()
        config._detected_profile = "typescript-npm"
        result = config.get_source_pattern("main")
        assert result == '["src/**/*.ts"]'

    def test_returns_none_when_no_profile(self):
        config = TDDConfig()
        with patch.object(config, 'detect_profile', return_value=None):
            result = config.get_source_pattern("main")
            assert result is None


class TestIsMainSource:
    """Tests for is_main_source method."""

    def test_returns_true_for_match(self):
        import pattern_matcher
        pattern_matcher.matches_any = MagicMock(return_value=True)

        config = TDDConfig()
        config._detected_profile = "typescript-npm"
        with patch.object(config, 'get_source_pattern', return_value='["src/**/*.ts"]'):
            result = config.is_main_source("src/main.ts")
            assert result is True

    def test_returns_false_for_no_match(self):
        import pattern_matcher
        pattern_matcher.matches_any = MagicMock(return_value=False)

        config = TDDConfig()
        config._detected_profile = "typescript-npm"
        with patch.object(config, 'get_source_pattern', return_value='["src/**/*.ts"]'):
            result = config.is_main_source("test/main.spec.ts")
            assert result is False

    def test_returns_false_when_no_pattern(self):
        config = TDDConfig()
        with patch.object(config, 'get_source_pattern', return_value=None):
            result = config.is_main_source("src/main.ts")
            assert result is False


class TestIsTestSource:
    """Tests for is_test_source method."""

    def test_returns_true_for_match(self):
        import pattern_matcher
        pattern_matcher.matches_any = MagicMock(return_value=True)

        config = TDDConfig()
        config._detected_profile = "typescript-npm"
        with patch.object(config, 'get_source_pattern', return_value='["**/*.spec.ts"]'):
            result = config.is_test_source("test/main.spec.ts")
            assert result is True

    def test_returns_false_when_no_pattern(self):
        config = TDDConfig()
        with patch.object(config, 'get_source_pattern', return_value=None):
            result = config.is_test_source("test/main.spec.ts")
            assert result is False


class TestIsConfigFile:
    """Tests for is_config_file method."""

    def test_returns_true_for_match(self):
        import pattern_matcher
        pattern_matcher.matches_any = MagicMock(return_value=True)

        config = TDDConfig()
        config._detected_profile = "typescript-npm"
        with patch.object(config, 'get_source_pattern', return_value='["package.json"]'):
            result = config.is_config_file("package.json")
            assert result is True

    def test_returns_false_when_no_pattern(self):
        config = TDDConfig()
        with patch.object(config, 'get_source_pattern', return_value=None):
            result = config.is_config_file("package.json")
            assert result is False


class TestGetTodoPlaceholder:
    """Tests for get_todo_placeholder method."""

    def test_returns_placeholder(self):
        import config_reader
        config_reader.get_config_value = MagicMock(return_value="// TODO")

        config = TDDConfig()
        config._detected_profile = "typescript-npm"
        result = config.get_todo_placeholder()
        assert result == "// TODO"

    def test_returns_none_when_no_profile(self):
        config = TDDConfig()
        with patch.object(config, 'detect_profile', return_value=None):
            result = config.get_todo_placeholder()
            assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
