#!/usr/bin/env python3
"""
Unit tests for tdd_supervisor/markers.py - SupervisorMarkers class
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime

# Add tdd_supervisor to path
sys.path.insert(0, '.')
from tdd_supervisor.markers import SupervisorMarkers


class TestSupervisorMarkersInit:
    """Tests for SupervisorMarkers initialization."""

    def test_init_creates_markers_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test-workflow")
                assert markers.markers_dir.exists()

    def test_init_with_custom_workflow_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("custom-id-123")
                assert markers.workflow_id == "custom-id-123"
                assert "tdd-supervisor-custom-id-123" in str(markers.markers_dir)

    def test_init_generates_workflow_id_when_none_provided(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers()
                assert markers.workflow_id is not None
                assert len(markers.workflow_id) > 0

    def test_init_sets_base_dir_to_claude_tmp(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                assert ".claude" in str(markers.base_dir)
                assert "tmp" in str(markers.base_dir)


class TestGenerateWorkflowId:
    """Tests for workflow ID generation."""

    def test_generate_workflow_id_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers()
                # Format should be YYYYMMDD-HHMMSS
                parts = markers.workflow_id.split("-")
                assert len(parts) == 2
                assert len(parts[0]) == 8  # YYYYMMDD
                assert len(parts[1]) == 6  # HHMMSS

    def test_generate_workflow_id_is_valid_timestamp(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers()
                # Should be parseable as datetime
                try:
                    datetime.strptime(markers.workflow_id, "%Y%m%d-%H%M%S")
                except ValueError:
                    pytest.fail("Workflow ID is not a valid timestamp format")


class TestMarkerProperties:
    """Tests for marker path properties."""

    def test_tdd_mode_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                assert markers.tdd_mode.name == "tdd-mode"
                assert markers.tdd_mode.parent == markers.markers_dir

    def test_tdd_phase_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                assert markers.tdd_phase.name == "tdd-phase"

    def test_supervisor_active_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                assert markers.supervisor_active.name == "tdd-supervisor-active"

    def test_requirements_summary_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                assert markers.requirements_summary.name == "tdd-requirements-summary.md"

    def test_interfaces_list_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                assert markers.interfaces_list.name == "tdd-interfaces-list.md"

    def test_tests_list_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                assert markers.tests_list.name == "tdd-tests-list.md"

    def test_completion_marker_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                assert markers.requirements_confirmed.name == "tdd-requirements-confirmed"
                assert markers.interfaces_designed.name == "tdd-interfaces-designed"
                assert markers.tests_approved.name == "tdd-tests-approved"
                assert markers.tests_passing.name == "tdd-tests-passing"


class TestInitialize:
    """Tests for initialize method."""

    def test_initialize_creates_tdd_mode_marker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                markers.initialize()
                assert markers.tdd_mode.exists()

    def test_initialize_creates_supervisor_active_marker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                markers.initialize()
                assert markers.supervisor_active.exists()

    def test_initialize_sets_phase_to_1(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                markers.initialize()
                assert markers.get_phase() == 1


class TestPhaseManagement:
    """Tests for phase get/set methods."""

    def test_get_phase_returns_1_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                assert markers.get_phase() == 1

    def test_get_phase_reads_correct_value(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                for phase in [1, 2, 3, 4]:
                    markers.set_phase(phase)
                    assert markers.get_phase() == phase

    def test_get_phase_handles_invalid_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                markers.tdd_phase.write_text("invalid")
                assert markers.get_phase() == 1

    def test_get_phase_handles_empty_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                markers.tdd_phase.write_text("")
                assert markers.get_phase() == 1

    def test_set_phase_writes_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                markers.set_phase(3)
                assert markers.tdd_phase.read_text() == "3"


class TestIsActive:
    """Tests for is_active method."""

    def test_is_active_false_when_no_markers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                assert markers.is_active() is False

    def test_is_active_false_when_only_tdd_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                markers.tdd_mode.touch()
                assert markers.is_active() is False

    def test_is_active_false_when_only_supervisor_active(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                markers.supervisor_active.touch()
                assert markers.is_active() is False

    def test_is_active_true_when_both_markers_exist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                markers.tdd_mode.touch()
                markers.supervisor_active.touch()
                assert markers.is_active() is True


class TestContextStorage:
    """Tests for context save/get methods."""

    def test_save_and_get_requirements_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                summary = "# Requirements\n- Feature A\n- Feature B"
                markers.save_requirements_summary(summary)
                assert markers.get_requirements_summary() == summary

    def test_get_requirements_summary_returns_empty_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                assert markers.get_requirements_summary() == ""

    def test_save_and_get_interfaces_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                interfaces = "# Interfaces\n- UserService\n- AuthHandler"
                markers.save_interfaces_list(interfaces)
                assert markers.get_interfaces_list() == interfaces

    def test_get_interfaces_list_returns_empty_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                assert markers.get_interfaces_list() == ""

    def test_save_and_get_tests_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                tests = "# Tests\n- test_user_creation\n- test_auth_flow"
                markers.save_tests_list(tests)
                assert markers.get_tests_list() == tests

    def test_get_tests_list_returns_empty_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                assert markers.get_tests_list() == ""

    def test_save_overwrites_existing_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                markers.save_requirements_summary("first")
                markers.save_requirements_summary("second")
                assert markers.get_requirements_summary() == "second"


class TestCleanup:
    """Tests for cleanup method."""

    def test_cleanup_removes_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                markers.initialize()
                markers.save_requirements_summary("test")

                markers.cleanup()

                assert not markers.markers_dir.exists()

    def test_cleanup_handles_nonexistent_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                # Remove directory manually first
                markers.markers_dir.rmdir()

                # Should not raise
                markers.cleanup()


class TestGetMarkerDir:
    """Tests for get_marker_dir method."""

    def test_get_marker_dir_returns_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test-id")
                path = markers.get_marker_dir()
                assert "tdd-supervisor-test-id" in path
                assert isinstance(path, str)


class TestGetEnvVars:
    """Tests for get_env_vars method."""

    def test_get_env_vars_contains_workflow_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test-workflow-id")
                env_vars = markers.get_env_vars()
                assert "TDD_SUPERVISOR_WORKFLOW_ID" in env_vars
                assert env_vars["TDD_SUPERVISOR_WORKFLOW_ID"] == "test-workflow-id"

    def test_get_env_vars_contains_markers_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                env_vars = markers.get_env_vars()
                assert "TDD_SUPERVISOR_MARKERS_DIR" in env_vars
                assert env_vars["TDD_SUPERVISOR_MARKERS_DIR"] == str(markers.markers_dir)

    def test_get_env_vars_contains_active_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                env_vars = markers.get_env_vars()
                assert "TDD_SUPERVISOR_ACTIVE" in env_vars
                assert env_vars["TDD_SUPERVISOR_ACTIVE"] == "1"

    def test_get_env_vars_returns_all_required_vars(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                markers = SupervisorMarkers("test")
                env_vars = markers.get_env_vars()
                required_keys = [
                    "TDD_SUPERVISOR_WORKFLOW_ID",
                    "TDD_SUPERVISOR_MARKERS_DIR",
                    "TDD_SUPERVISOR_ACTIVE",
                ]
                for key in required_keys:
                    assert key in env_vars


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
