#!/usr/bin/env python3
"""
Unit tests for markers.py
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

# Add hooks/lib to path
sys.path.insert(0, 'hooks/lib')
from markers import MarkerManager


class TestMarkerManager:
    """Tests for MarkerManager class."""

    def test_init_creates_markers_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                manager = MarkerManager("test-session")
                assert manager.markers_dir.exists()
                assert "tdd-test-session" in str(manager.markers_dir)

    def test_is_tdd_active_false_when_no_marker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                manager = MarkerManager("test-session")
                assert manager.is_tdd_active() is False

    def test_is_tdd_active_true_when_marker_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                manager = MarkerManager("test-session")
                manager.tdd_mode.touch()
                assert manager.is_tdd_active() is True

    def test_get_phase_defaults_to_1(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                manager = MarkerManager("test-session")
                assert manager.get_phase() == 1

    def test_get_phase_reads_from_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                manager = MarkerManager("test-session")
                manager.tdd_phase.write_text("3")
                assert manager.get_phase() == 3

    def test_get_phase_handles_invalid_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                manager = MarkerManager("test-session")
                manager.tdd_phase.write_text("invalid")
                assert manager.get_phase() == 1

    def test_set_phase(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                manager = MarkerManager("test-session")
                manager.set_phase(4)
                assert manager.tdd_phase.read_text() == "4"

    def test_marker_properties(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                manager = MarkerManager("test-session")

                assert "tdd-mode" in str(manager.tdd_mode)
                assert "tdd-phase" in str(manager.tdd_phase)
                assert "tdd-requirements-confirmed" in str(manager.requirements_confirmed)
                assert "tdd-interfaces-designed" in str(manager.interfaces_designed)
                assert "tdd-tests-approved" in str(manager.tests_approved)
                assert "tdd-tests-passing" in str(manager.tests_passing)

    def test_create_and_remove_marker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                manager = MarkerManager("test-session")

                # Create marker
                manager.create_marker(manager.requirements_confirmed)
                assert manager.requirements_confirmed.exists()

                # Remove marker
                manager.remove_marker(manager.requirements_confirmed)
                assert not manager.requirements_confirmed.exists()

    def test_cleanup_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                manager = MarkerManager("test-session")

                # Create some markers
                manager.tdd_mode.touch()
                manager.set_phase(2)
                manager.requirements_confirmed.touch()

                # Cleanup
                manager.cleanup_session()

                # Directory should be gone
                assert not manager.markers_dir.exists()

    def test_cleanup_all_markers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                manager = MarkerManager("test-session")

                # Create all markers
                manager.tdd_mode.touch()
                manager.set_phase(3)
                manager.requirements_confirmed.touch()
                manager.interfaces_designed.touch()

                # Cleanup markers (not directory)
                manager.cleanup_all_markers()

                # Directory should still exist
                assert manager.markers_dir.exists()
                # But markers should be gone
                assert not manager.tdd_mode.exists()
                assert not manager.tdd_phase.exists()

    def test_get_marker_dir_display(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                manager = MarkerManager("abc123")
                display = manager.get_marker_dir_display()
                assert display == "~/.claude/tmp/tdd-abc123"


class TestSupervisorMode:
    """Tests for supervisor mode functionality."""

    def test_is_supervisor_mode_false_by_default(self):
        """Supervisor mode should be false when no env vars set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                # Ensure env vars are not set
                env = os.environ.copy()
                env.pop("TDD_SUPERVISOR_ACTIVE", None)
                env.pop("TDD_SUPERVISOR_MARKERS_DIR", None)

                with patch.dict(os.environ, env, clear=True):
                    manager = MarkerManager("test-session")
                    assert manager.is_supervisor_mode() is False

    def test_is_supervisor_mode_true_with_active_env_var(self):
        """Supervisor mode should be true when TDD_SUPERVISOR_ACTIVE=1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                with patch.dict(os.environ, {"TDD_SUPERVISOR_ACTIVE": "1"}):
                    manager = MarkerManager("test-session")
                    assert manager.is_supervisor_mode() is True

    def test_is_supervisor_mode_true_with_markers_dir_env_var(self):
        """Supervisor mode should be true when TDD_SUPERVISOR_MARKERS_DIR is set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                supervisor_dir = Path(tmpdir) / "supervisor-markers"
                supervisor_dir.mkdir(parents=True)

                with patch.dict(os.environ, {"TDD_SUPERVISOR_MARKERS_DIR": str(supervisor_dir)}, clear=False):
                    manager = MarkerManager("test-session")
                    assert manager.is_supervisor_mode() is True

    def test_init_uses_supervisor_dir_when_env_set(self):
        """MarkerManager should use supervisor's marker directory when env var set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                supervisor_dir = Path(tmpdir) / "custom-supervisor-dir"
                supervisor_dir.mkdir(parents=True)

                with patch.dict(os.environ, {"TDD_SUPERVISOR_MARKERS_DIR": str(supervisor_dir)}, clear=False):
                    manager = MarkerManager("test-session")
                    assert manager.markers_dir == supervisor_dir

    def test_init_uses_session_dir_when_no_supervisor_env(self):
        """MarkerManager should use session-based directory when not in supervisor mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                # Clear supervisor env vars
                env = os.environ.copy()
                env.pop("TDD_SUPERVISOR_MARKERS_DIR", None)
                env.pop("TDD_SUPERVISOR_ACTIVE", None)

                with patch.dict(os.environ, env, clear=True):
                    manager = MarkerManager("my-session")
                    assert "tdd-my-session" in str(manager.markers_dir)

    def test_supervisor_mode_markers_shared(self):
        """Multiple MarkerManagers in supervisor mode should share the same directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                supervisor_dir = Path(tmpdir) / "shared-supervisor-dir"
                supervisor_dir.mkdir(parents=True)

                with patch.dict(os.environ, {"TDD_SUPERVISOR_MARKERS_DIR": str(supervisor_dir)}, clear=False):
                    manager1 = MarkerManager("session-1")
                    manager2 = MarkerManager("session-2")

                    # Both should use the same supervisor directory
                    assert manager1.markers_dir == manager2.markers_dir
                    assert manager1.markers_dir == supervisor_dir


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
