#!/usr/bin/env python3
"""
Unit tests for config_reader.py
"""

import json
import sys
import tempfile
import pytest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

# Add hooks/lib to path
sys.path.insert(0, 'hooks/lib')
from config_reader import get_config_value, main


class TestGetConfigValue:
    """Tests for get_config_value function."""

    def test_reads_simple_value(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"name": "test"}, f)
            f.flush()
            result = get_config_value("name", f.name)
            assert result == "test"

    def test_reads_nested_value(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"profiles": {"kotlin": {"name": "Kotlin"}}}, f)
            f.flush()
            result = get_config_value("profiles.kotlin.name", f.name)
            assert result == "Kotlin"

    def test_reads_deeply_nested_value(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "profiles": {
                    "typescript-npm": {
                        "commands": {
                            "compile": "npm run build"
                        }
                    }
                }
            }, f)
            f.flush()
            result = get_config_value("profiles.typescript-npm.commands.compile", f.name)
            assert result == "npm run build"

    def test_returns_dict_for_object_path(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"profiles": {"kotlin": {"name": "Kotlin", "version": "1.9"}}}, f)
            f.flush()
            result = get_config_value("profiles.kotlin", f.name)
            assert result == {"name": "Kotlin", "version": "1.9"}

    def test_returns_list_for_array_path(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"patterns": ["*.py", "*.ts"]}, f)
            f.flush()
            result = get_config_value("patterns", f.name)
            assert result == ["*.py", "*.ts"]

    def test_returns_none_for_missing_path(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"name": "test"}, f)
            f.flush()
            result = get_config_value("nonexistent.path", f.name)
            assert result is None

    def test_returns_none_for_partial_path(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"profiles": {"kotlin": {"name": "Kotlin"}}}, f)
            f.flush()
            result = get_config_value("profiles.kotlin.commands.compile", f.name)
            assert result is None

    def test_returns_none_for_missing_file(self):
        result = get_config_value("name", "/nonexistent/file.json")
        assert result is None

    def test_returns_none_for_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json {")
            f.flush()
            result = get_config_value("name", f.name)
            assert result is None

    def test_returns_none_when_traversing_non_dict(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"name": "test"}, f)
            f.flush()
            result = get_config_value("name.subkey", f.name)
            assert result is None


class TestMainCLI:
    """Tests for main() CLI function."""

    def test_no_args_prints_usage(self):
        with patch.object(sys, 'argv', ['config_reader.py']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_get_command_missing_args(self):
        with patch.object(sys, 'argv', ['config_reader.py', 'get']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_get_command_prints_simple_value(self, capsys):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"name": "test"}, f)
            f.flush()
            with patch.object(sys, 'argv', ['config_reader.py', 'get', 'name', f.name]):
                main()
            captured = capsys.readouterr()
            assert captured.out.strip() == "test"

    def test_get_command_prints_json_for_dict(self, capsys):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"data": {"key": "value"}}, f)
            f.flush()
            with patch.object(sys, 'argv', ['config_reader.py', 'get', 'data', f.name]):
                main()
            captured = capsys.readouterr()
            assert json.loads(captured.out.strip()) == {"key": "value"}

    def test_get_command_prints_json_for_list(self, capsys):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"items": [1, 2, 3]}, f)
            f.flush()
            with patch.object(sys, 'argv', ['config_reader.py', 'get', 'items', f.name]):
                main()
            captured = capsys.readouterr()
            assert json.loads(captured.out.strip()) == [1, 2, 3]

    def test_unknown_command_prints_error(self):
        with patch.object(sys, 'argv', ['config_reader.py', 'unknown']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
