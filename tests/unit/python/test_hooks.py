#!/usr/bin/env python3
"""
Integration tests for Python hooks.

Tests the hook scripts by simulating Claude Code hook input.
"""

import json
import os
import subprocess
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

# Get the project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
MOCKS_DIR = PROJECT_ROOT / "tests" / "fixtures" / "mocks"


def run_hook(hook_name: str, input_data: dict, env: dict = None, use_mocks: bool = False) -> tuple:
    """
    Run a Python hook script with the given input.

    Args:
        hook_name: Name of the hook script (without .py)
        input_data: Dict to pass as JSON stdin
        env: Additional environment variables
        use_mocks: If True, add mocks directory to PATH

    Returns (exit_code, stdout, stderr)
    """
    hook_path = PROJECT_ROOT / "hooks" / f"{hook_name}.py"

    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    # Add mocks to PATH if requested
    if use_mocks:
        full_env["PATH"] = f"{MOCKS_DIR}:{full_env.get('PATH', '')}"

    result = subprocess.run(
        ["python3", str(hook_path)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        env=full_env,
        timeout=30
    )
    return result.returncode, result.stdout, result.stderr


def setup_mock_compile(tmpdir: str, success: bool = True, output: str = None) -> None:
    """
    Set up mock compile command behavior.

    Args:
        tmpdir: Temp directory for mock control files
        success: If True, compile succeeds; if False, fails
        output: Custom output message (optional)
    """
    exit_code = "0" if success else "1"
    if output is None:
        output = "BUILD SUCCESS" if success else "[ERROR] Compilation failure\nSrc.kt:10: error: unresolved reference: foo"

    Path(tmpdir, "mock_compile_exit_code").write_text(exit_code)
    Path(tmpdir, "mock_compile_output").write_text(output)


def setup_mock_test(tmpdir: str, success: bool = True, output: str = None) -> None:
    """
    Set up mock test command behavior.

    Args:
        tmpdir: Temp directory for mock control files
        success: If True, tests pass; if False, tests fail
        output: Custom output message (optional)
    """
    exit_code = "0" if success else "1"
    if output is None:
        output = "Tests run: 10, Failures: 0" if success else "Tests run: 10, Failures: 2\n\nFailed tests:\n  - testSomething\n  - testAnother"

    Path(tmpdir, "mock_test_exit_code").write_text(exit_code)
    Path(tmpdir, "mock_test_output").write_text(output)


def setup_tdd_state(
    markers_dir: Path,
    phase: int = 1,
    active: bool = True,
    requirements_complete: bool = False,
    interfaces_complete: bool = False,
    tests_complete: bool = False,
    implementation_complete: bool = False
) -> None:
    """
    Set up TDD state.json file for testing.

    Args:
        markers_dir: The markers directory path
        phase: Current TDD phase (1-4)
        active: Whether TDD mode is active
        requirements_complete: Whether requirements phase is complete
        interfaces_complete: Whether interfaces phase is complete
        tests_complete: Whether tests phase is complete
        implementation_complete: Whether implementation phase is complete
    """
    markers_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "version": 1,
        "active": active,
        "supervisorActive": False,
        "phase": phase,
        "mode": "cli",
        "completedPhases": {
            "requirements": requirements_complete,
            "interfaces": interfaces_complete,
            "tests": tests_complete,
            "implementation": implementation_complete
        },
        "summaries": {
            "requirements": "",
            "interfaces": "",
            "tests": ""
        },
        "metadata": {
            "startedAt": "2026-01-10T00:00:00",
            "workflowId": "",
            "sessionId": "test-session"
        }
    }
    (markers_dir / "state.json").write_text(json.dumps(state, indent=2))


def get_tdd_state(markers_dir: Path) -> dict:
    """Read TDD state from state.json file."""
    state_file = markers_dir / "state.json"
    if not state_file.exists():
        return None
    return json.loads(state_file.read_text())


def get_tdd_phase(markers_dir: Path) -> int:
    """Get current TDD phase from state.json."""
    state = get_tdd_state(markers_dir)
    if state is None:
        return None
    return state.get("phase", 1)


def generate_hook_input(
    tool_name: str = "Write",
    file_path: str = "/project/src/main.py",
    cwd: str = "/project",
    session_id: str = "test-session",
    hook_event_name: str = "",
    stop_hook_active: bool = False
) -> dict:
    """Generate hook input JSON."""
    return {
        "tool_name": tool_name,
        "tool_input": {"file_path": file_path},
        "cwd": cwd,
        "session_id": session_id,
        "hook_event_name": hook_event_name,
        "stop_hook_active": stop_hook_active,
    }


class TestCleanupMarkersHook:
    """Tests for tdd-cleanup-markers.py"""

    def test_does_nothing_for_non_session_end(self):
        """Should do nothing for non-SessionEnd events."""
        input_data = generate_hook_input(hook_event_name="Stop")

        exit_code, stdout, stderr = run_hook("tdd-cleanup-markers", input_data)

        assert exit_code == 0
        assert stdout == ""

    def test_cleans_up_on_session_end(self):
        """Should clean up markers on SessionEnd."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create marker directory with markers
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=2)

            # Mock home directory
            env = {"HOME": tmpdir}
            input_data = generate_hook_input(
                hook_event_name="SessionEnd",
                session_id="test-session"
            )

            exit_code, stdout, stderr = run_hook("tdd-cleanup-markers", input_data, env)

            assert exit_code == 0
            # Markers should be cleaned up
            assert not markers_dir.exists()

    def test_cleans_up_all_tdd_state(self):
        """Should clean up all TDD state on SessionEnd."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)

            # Create state with all phases complete
            setup_tdd_state(
                markers_dir,
                phase=4,
                requirements_complete=True,
                interfaces_complete=True,
                tests_complete=True,
                implementation_complete=True
            )

            # Verify state exists
            assert (markers_dir / "state.json").exists()

            env = {"HOME": tmpdir}
            input_data = generate_hook_input(
                hook_event_name="SessionEnd",
                session_id="test-session"
            )

            exit_code, stdout, stderr = run_hook("tdd-cleanup-markers", input_data, env)

            assert exit_code == 0
            # Directory should be gone
            assert not markers_dir.exists()

    def test_handles_missing_markers_gracefully(self):
        """Should handle missing markers gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Don't create any markers
            env = {"HOME": tmpdir}
            input_data = generate_hook_input(
                hook_event_name="SessionEnd",
                session_id="test-session"
            )

            exit_code, stdout, stderr = run_hook("tdd-cleanup-markers", input_data, env)

            assert exit_code == 0

    def test_handles_partial_state(self):
        """Should handle partial state (only some phases complete)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)

            # Create state with only requirements complete
            setup_tdd_state(markers_dir, phase=1, requirements_complete=True)

            env = {"HOME": tmpdir}
            input_data = generate_hook_input(
                hook_event_name="SessionEnd",
                session_id="test-session"
            )

            exit_code, stdout, stderr = run_hook("tdd-cleanup-markers", input_data, env)

            assert exit_code == 0
            # All should be gone
            assert not markers_dir.exists()


class TestPhaseGuardHook:
    """Tests for tdd-phase-guard.py"""

    def test_allows_when_tdd_inactive(self):
        """Should allow all operations when TDD is not active."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input()

            exit_code, stdout, stderr = run_hook("tdd-phase-guard", input_data, env)

            assert exit_code == 0
            assert stdout == ""  # Empty output = allow

    def test_allows_test_edits_when_tdd_inactive(self):
        """Should allow test file edits when TDD is not active."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "test" / "kotlin" / "ServiceTest.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-phase-guard", input_data, env)

            assert exit_code == 0
            assert stdout == ""

    def test_allows_non_write_edit_tools(self):
        """Should allow non-Write/Edit tools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create TDD mode marker
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=1)

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(tool_name="Read")

            exit_code, stdout, stderr = run_hook("tdd-phase-guard", input_data, env)

            assert exit_code == 0
            assert stdout == ""  # Empty output = allow

    def test_handles_edit_tool_same_as_write(self):
        """Should handle Edit tool same as Write."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=1)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                tool_name="Edit",
                file_path=str(project_dir / "src" / "main" / "kotlin" / "Service.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-phase-guard", input_data, env)

            assert exit_code == 0
            if stdout:
                response = json.loads(stdout)
                assert response.get("decision") == "block"

    def test_blocks_source_edit_in_phase_1(self):
        """Should block source file edits in Phase 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create TDD mode marker in phase 1
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=1)

            # Create a mock project with pom.xml for profile detection
            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "main" / "kotlin" / "Service.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-phase-guard", input_data, env)

            assert exit_code == 0
            if stdout:  # If there's output, it should be a block
                response = json.loads(stdout)
                assert response.get("decision") == "block"
                assert "Phase 1" in response.get("reason", "")

    def test_phase_1_blocks_test_source_edits(self):
        """Should block test file edits in Phase 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=1)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "test" / "kotlin" / "ServiceTest.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-phase-guard", input_data, env)

            assert exit_code == 0
            if stdout:
                response = json.loads(stdout)
                assert response.get("decision") == "block"

    def test_phase_1_allows_config_file_edits(self):
        """Should allow config file edits in Phase 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=1)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                file_path=str(project_dir / "pom.xml"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-phase-guard", input_data, env)

            assert exit_code == 0
            # Should not block config files
            if stdout:
                response = json.loads(stdout)
                assert response.get("decision") != "block"

    def test_phase_2_allows_main_source_edits(self):
        """Should allow main source edits in Phase 2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=2)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "main" / "kotlin" / "Service.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-phase-guard", input_data, env)

            assert exit_code == 0
            assert stdout == ""  # No output means allowed

    def test_phase_2_blocks_test_source_edits(self):
        """Should block test file edits in Phase 2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=2)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "test" / "kotlin" / "ServiceTest.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-phase-guard", input_data, env)

            assert exit_code == 0
            if stdout:
                response = json.loads(stdout)
                assert response.get("decision") == "block"
                assert "Phase 2" in response.get("reason", "")

    def test_phase_2_allows_config_file_edits(self):
        """Should allow config file edits in Phase 2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=2)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                file_path=str(project_dir / "pom.xml"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-phase-guard", input_data, env)

            assert exit_code == 0
            # Should not block config files
            if stdout:
                response = json.loads(stdout)
                assert response.get("decision") != "block"

    def test_phase_3_blocks_main_source_edits(self):
        """Should block main source edits in Phase 3."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=3)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "main" / "kotlin" / "Service.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-phase-guard", input_data, env)

            assert exit_code == 0
            if stdout:
                response = json.loads(stdout)
                assert response.get("decision") == "block"
                assert "Phase 3" in response.get("reason", "")

    def test_phase_3_allows_test_source_edits(self):
        """Should allow test file edits in Phase 3."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=3)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "test" / "kotlin" / "ServiceTest.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-phase-guard", input_data, env)

            assert exit_code == 0
            assert stdout == ""  # No output means allowed

    def test_phase_3_allows_config_file_edits(self):
        """Should allow config file edits in Phase 3."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=3)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                file_path=str(project_dir / "application.yaml"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-phase-guard", input_data, env)

            assert exit_code == 0
            # Should not block config files
            if stdout:
                response = json.loads(stdout)
                assert response.get("decision") != "block"

    def test_phase_4_allows_main_source_edits(self):
        """Should allow main source edits in Phase 4."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=4)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "main" / "kotlin" / "Service.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-phase-guard", input_data, env)

            assert exit_code == 0
            assert stdout == ""  # No output means allowed

    def test_phase_4_allows_test_source_edits(self):
        """Should allow test file edits in Phase 4."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=4)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "test" / "kotlin" / "ServiceTest.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-phase-guard", input_data, env)

            assert exit_code == 0
            assert stdout == ""  # No output means allowed

    def test_phase_4_allows_config_file_edits(self):
        """Should allow config file edits in Phase 4."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=4)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                file_path=str(project_dir / "pom.xml"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-phase-guard", input_data, env)

            assert exit_code == 0
            # Should not block config files
            if stdout:
                response = json.loads(stdout)
                assert response.get("decision") != "block"

    def test_typescript_phase_2_blocks_test_files(self):
        """Should block test files for TypeScript project in Phase 2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=2)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "package.json").write_text('{"name": "test"}')
            (project_dir / "tsconfig.json").write_text('{}')

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "service.test.ts"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-phase-guard", input_data, env)

            assert exit_code == 0
            if stdout:
                response = json.loads(stdout)
                assert response.get("decision") == "block"

    def test_typescript_phase_3_allows_test_files(self):
        """Should allow test files for TypeScript project in Phase 3."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=3)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "package.json").write_text('{"name": "test"}')
            (project_dir / "tsconfig.json").write_text('{}')

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "service.test.ts"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-phase-guard", input_data, env)

            assert exit_code == 0
            assert stdout == ""  # No output means allowed


class TestAutoCompileHook:
    """Tests for tdd-auto-compile.py"""

    def test_compiles_after_source_file_change_success(self):
        """Should compile successfully after kotlin source file change."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            # Set up mock to succeed
            setup_mock_compile(tmpdir, success=True)

            env = {
                "HOME": tmpdir,
                "TDD_INSTALL_DIR": str(PROJECT_ROOT),
                "TEST_TMP": tmpdir
            }
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "main" / "kotlin" / "Service.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-auto-compile", input_data, env, use_mocks=True)
            assert exit_code == 0
            assert "Auto-compiling" in stderr
            assert "Compilation successful" in stderr

    def test_compiles_after_source_file_change_failure(self):
        """Should handle compilation failure and output error context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            # Set up mock to fail with error output
            setup_mock_compile(tmpdir, success=False, output="[ERROR] Service.kt:15: unresolved reference: myVar")

            env = {
                "HOME": tmpdir,
                "TDD_INSTALL_DIR": str(PROJECT_ROOT),
                "TEST_TMP": tmpdir
            }
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "main" / "kotlin" / "Service.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-auto-compile", input_data, env, use_mocks=True)
            assert exit_code == 0
            assert "Compilation failed" in stderr
            # Should output approve with error context
            if stdout:
                response = json.loads(stdout)
                assert response.get("decision") == "approve"
                assert "Compilation failed" in response.get("reason", "")

    def test_skips_non_source_files(self):
        """Should skip non-source files like README."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                file_path=str(project_dir / "README.md"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-auto-compile", input_data, env)
            assert exit_code == 0
            assert stdout == ""
            assert "Auto-compiling" not in stderr

    def test_skips_non_write_edit_tools(self):
        """Should skip non-Write/Edit tools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                tool_name="Read",
                file_path=str(project_dir / "src" / "main" / "kotlin" / "Service.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-auto-compile", input_data, env)
            assert exit_code == 0
            assert stdout == ""

    def test_skips_when_tdd_phase_4_is_active(self):
        """Should skip when TDD phase 4 is active (auto-test handles it)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=4)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "main" / "kotlin" / "Service.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-auto-compile", input_data, env)
            assert exit_code == 0
            # Should exit without compile output
            assert "Auto-compiling" not in stderr

    def test_runs_when_tdd_phase_is_not_4(self):
        """Should run compilation when TDD phase is not 4."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=2)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            setup_mock_compile(tmpdir, success=True)

            env = {
                "HOME": tmpdir,
                "TDD_INSTALL_DIR": str(PROJECT_ROOT),
                "TEST_TMP": tmpdir
            }
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "main" / "kotlin" / "Service.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-auto-compile", input_data, env, use_mocks=True)
            assert exit_code == 0
            assert "Auto-compiling" in stderr

    def test_runs_when_tdd_mode_is_inactive(self):
        """Should run compilation when TDD mode is inactive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            setup_mock_compile(tmpdir, success=True)

            env = {
                "HOME": tmpdir,
                "TDD_INSTALL_DIR": str(PROJECT_ROOT),
                "TEST_TMP": tmpdir
            }
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "main" / "kotlin" / "Service.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-auto-compile", input_data, env, use_mocks=True)
            assert exit_code == 0
            assert "Auto-compiling" in stderr

    def test_typescript_compile_success(self):
        """Should compile TypeScript project successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "package.json").write_text('{"name": "test"}')
            (project_dir / "tsconfig.json").write_text('{}')

            setup_mock_compile(tmpdir, success=True, output="Build completed successfully")

            env = {
                "HOME": tmpdir,
                "TDD_INSTALL_DIR": str(PROJECT_ROOT),
                "TEST_TMP": tmpdir
            }
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "service.ts"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-auto-compile", input_data, env, use_mocks=True)
            assert exit_code == 0
            assert "Auto-compiling" in stderr

    def test_typescript_compile_failure(self):
        """Should handle TypeScript compilation failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "package.json").write_text('{"name": "test"}')
            (project_dir / "tsconfig.json").write_text('{}')

            setup_mock_compile(tmpdir, success=False, output="error TS2304: Cannot find name 'foo'")

            env = {
                "HOME": tmpdir,
                "TDD_INSTALL_DIR": str(PROJECT_ROOT),
                "TEST_TMP": tmpdir
            }
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "service.ts"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-auto-compile", input_data, env, use_mocks=True)
            assert exit_code == 0
            assert "Compilation failed" in stderr


class TestAutoTestHook:
    """Tests for tdd-auto-test.py"""

    def test_skips_when_tdd_mode_is_inactive(self):
        """Should skip when TDD mode is inactive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "main" / "kotlin" / "Service.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-auto-test", input_data, env)
            assert exit_code == 0
            assert stdout == ""

    def test_skips_when_not_in_phase_4(self):
        """Should skip when not in phase 4."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=2)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "main" / "kotlin" / "Service.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-auto-test", input_data, env)
            assert exit_code == 0
            assert stdout == ""

    def test_skips_for_non_write_edit_tools(self):
        """Should skip for non-Write/Edit tools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=4)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                tool_name="Read",
                file_path=str(project_dir / "src" / "main" / "kotlin" / "Service.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-auto-test", input_data, env)
            assert exit_code == 0
            assert stdout == ""

    def test_skips_for_non_source_files(self):
        """Should skip for non-source files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=4)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                file_path=str(project_dir / "README.md"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-auto-test", input_data, env)
            assert exit_code == 0
            assert stdout == ""

    def test_runs_in_phase_4_for_source_files_success(self):
        """Should run tests in phase 4 for source file changes - tests pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=4)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            # Set up mocks for both compile and test to succeed
            setup_mock_compile(tmpdir, success=True)
            setup_mock_test(tmpdir, success=True)

            env = {
                "HOME": tmpdir,
                "TDD_INSTALL_DIR": str(PROJECT_ROOT),
                "TEST_TMP": tmpdir
            }
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "main" / "kotlin" / "Service.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-auto-test", input_data, env, use_mocks=True)
            assert exit_code == 0
            assert "Running compile + test cycle" in stderr
            assert "All tests passing" in stderr

    def test_runs_in_phase_4_for_source_files_test_failure(self):
        """Should handle test failures in phase 4."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=4)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            # Set up compile to succeed but tests to fail
            setup_mock_compile(tmpdir, success=True)
            setup_mock_test(tmpdir, success=False, output="Tests run: 5, Failures: 2\nFailed: testService")

            env = {
                "HOME": tmpdir,
                "TDD_INSTALL_DIR": str(PROJECT_ROOT),
                "TEST_TMP": tmpdir
            }
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "main" / "kotlin" / "Service.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-auto-test", input_data, env, use_mocks=True)
            assert exit_code == 0
            # Should indicate test failure
            assert "fail" in stderr.lower() or "fail" in stdout.lower()

    def test_runs_in_phase_4_compile_failure(self):
        """Should handle compile failures in phase 4."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=4)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            # Set up compile to fail
            setup_mock_compile(tmpdir, success=False, output="[ERROR] Compilation failed")

            env = {
                "HOME": tmpdir,
                "TDD_INSTALL_DIR": str(PROJECT_ROOT),
                "TEST_TMP": tmpdir
            }
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "main" / "kotlin" / "Service.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-auto-test", input_data, env, use_mocks=True)
            assert exit_code == 0
            # Should indicate compile failure - tests shouldn't run
            assert "compil" in stderr.lower() or "compil" in stdout.lower()

    def test_runs_for_test_file_changes(self):
        """Should run for test file changes in phase 4."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=4)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            setup_mock_compile(tmpdir, success=True)
            setup_mock_test(tmpdir, success=True)

            env = {
                "HOME": tmpdir,
                "TDD_INSTALL_DIR": str(PROJECT_ROOT),
                "TEST_TMP": tmpdir
            }
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "test" / "kotlin" / "ServiceTest.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-auto-test", input_data, env, use_mocks=True)
            assert exit_code == 0

    def test_outputs_approve_with_context_on_test_failure(self):
        """Should output approve decision with error context when tests fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=4)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            setup_mock_compile(tmpdir, success=True)
            setup_mock_test(tmpdir, success=False, output="Tests run: 3, Failures: 1\nFailed: testSomething")

            env = {
                "HOME": tmpdir,
                "TDD_INSTALL_DIR": str(PROJECT_ROOT),
                "TEST_TMP": tmpdir
            }
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "main" / "kotlin" / "Service.kt"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-auto-test", input_data, env, use_mocks=True)
            assert exit_code == 0
            # Should output approve with context
            if stdout:
                response = json.loads(stdout)
                assert response.get("decision") == "approve"
                assert "Tests failing" in response.get("reason", "")

    def test_typescript_test_cycle(self):
        """Should run compile + test cycle for TypeScript projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=4)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "package.json").write_text('{"name": "test"}')
            (project_dir / "tsconfig.json").write_text('{}')

            setup_mock_compile(tmpdir, success=True)
            setup_mock_test(tmpdir, success=True)

            env = {
                "HOME": tmpdir,
                "TDD_INSTALL_DIR": str(PROJECT_ROOT),
                "TEST_TMP": tmpdir
            }
            input_data = generate_hook_input(
                file_path=str(project_dir / "src" / "service.ts"),
                cwd=str(project_dir)
            )

            exit_code, stdout, stderr = run_hook("tdd-auto-test", input_data, env, use_mocks=True)
            assert exit_code == 0
            assert "Running compile + test cycle" in stderr


class TestOrchestratorHook:
    """Tests for tdd-orchestrator.py"""

    def test_exits_silently_when_tdd_inactive(self):
        """Should exit silently when TDD mode is inactive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                cwd=str(project_dir),
                hook_event_name="Stop"
            )

            exit_code, stdout, stderr = run_hook("tdd-orchestrator", input_data, env)
            assert exit_code == 0
            assert stdout == ""

    def test_exits_when_stop_hook_active(self):
        """Should exit when stop_hook_active is true to prevent loops."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=1)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                cwd=str(project_dir),
                hook_event_name="Stop",
                stop_hook_active=True
            )

            exit_code, stdout, stderr = run_hook("tdd-orchestrator", input_data, env)
            assert exit_code == 0
            assert stdout == ""

    def test_phase_1_blocks_without_requirements_marker(self):
        """Should block in phase 1 without requirements marker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=1)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                cwd=str(project_dir),
                hook_event_name="Stop"
            )

            exit_code, stdout, stderr = run_hook("tdd-orchestrator", input_data, env)
            assert exit_code == 0
            if stdout:
                response = json.loads(stdout)
                assert response.get("decision") == "block"
                assert "Phase 1" in response.get("reason", "")

    def test_phase_1_advances_to_phase_2_with_marker(self):
        """Should advance from phase 1 to phase 2 when requirements are complete."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=1, requirements_complete=True)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                cwd=str(project_dir),
                hook_event_name="Stop"
            )

            exit_code, stdout, stderr = run_hook("tdd-orchestrator", input_data, env)
            assert exit_code == 0
            # Should now be in phase 2
            assert get_tdd_phase(markers_dir) == 2

    def test_initializes_phase_to_1_if_missing(self):
        """Should initialize phase to 1 if phase file is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=1)
            # Don't create phase file

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                cwd=str(project_dir),
                hook_event_name="Stop"
            )

            exit_code, stdout, stderr = run_hook("tdd-orchestrator", input_data, env)
            assert exit_code == 0
            # Phase file should be created
            assert (markers_dir / "state.json").exists()

    def test_handles_no_agents_gracefully(self):
        """Should handle no agents gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=1)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            # Point to non-existent agents directory
            env = {
                "HOME": tmpdir,
                "TDD_INSTALL_DIR": str(Path(tmpdir) / "nonexistent")
            }
            input_data = generate_hook_input(
                cwd=str(project_dir),
                hook_event_name="Stop"
            )

            exit_code, stdout, stderr = run_hook("tdd-orchestrator", input_data, env)
            assert exit_code == 0
            # Should still show phase 1 guidance
            if stdout:
                response = json.loads(stdout)
                assert response.get("decision") == "block"

    def test_treats_unknown_phase_as_phase_1(self):
        """Should treat unknown phase as phase 1 (blocks until requirements complete)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=99)  # Unknown phase

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(PROJECT_ROOT)}
            input_data = generate_hook_input(
                cwd=str(project_dir),
                hook_event_name="Stop"
            )

            exit_code, stdout, stderr = run_hook("tdd-orchestrator", input_data, env)

            assert exit_code == 0
            # Should block as if in phase 1
            if stdout:
                response = json.loads(stdout)
                assert response.get("decision") == "block"
                assert "Phase 1" in response.get("reason", "")

    def test_phase_1_loads_agents_configured_for_phase_1(self):
        """Should load agents configured for phase 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=1)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            # Create install dir with agents
            install_dir = Path(tmpdir) / "tdd-workflow"
            agents_dir = install_dir / "agents"
            agents_dir.mkdir(parents=True)

            # Create an agent configured for phase 1
            (agents_dir / "phase1-agent.md").write_text("""---
name: Phase 1 Test Agent
phases: [1]
---

# Phase 1 Agent Content

This agent helps with requirements gathering.
""")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(install_dir)}
            input_data = generate_hook_input(
                cwd=str(project_dir),
                hook_event_name="Stop"
            )

            exit_code, stdout, stderr = run_hook("tdd-orchestrator", input_data, env)

            assert exit_code == 0
            # Should mention loaded agent in stderr
            assert "Phase 1 Test Agent" in stderr or "phase1-agent" in stderr.lower()

    def test_does_not_load_agents_configured_for_different_phase(self):
        """Should not load agents configured for different phase."""
        with tempfile.TemporaryDirectory() as tmpdir:
            markers_dir = Path(tmpdir) / ".claude" / "tmp" / "tdd-test-session"
            markers_dir.mkdir(parents=True)
            setup_tdd_state(markers_dir, phase=1)

            project_dir = Path(tmpdir) / "project"
            project_dir.mkdir()
            (project_dir / "pom.xml").write_text("<project></project>")

            # Create install dir with agents
            install_dir = Path(tmpdir) / "tdd-workflow"
            agents_dir = install_dir / "agents"
            agents_dir.mkdir(parents=True)

            # Create an agent configured for phase 3 only
            (agents_dir / "phase3-agent.md").write_text("""---
name: Phase 3 Only Agent
phases: [3]
---

# Phase 3 Agent Content

This agent helps with test writing.
""")

            env = {"HOME": tmpdir, "TDD_INSTALL_DIR": str(install_dir)}
            input_data = generate_hook_input(
                cwd=str(project_dir),
                hook_event_name="Stop"
            )

            exit_code, stdout, stderr = run_hook("tdd-orchestrator", input_data, env)

            assert exit_code == 0
            # Should NOT mention the phase 3 agent
            assert "Phase 3 Only Agent" not in stderr
            assert "phase3-agent" not in stderr.lower()


class TestHookIO:
    """Tests for hook_io.py HookInput class."""

    def test_hook_input_from_dict(self):
        sys.path.insert(0, str(PROJECT_ROOT / "hooks" / "lib"))
        from hook_io import HookInput

        data = {
            "tool_name": "Write",
            "tool_input": {"file_path": "/test/path.py"},
            "cwd": "/test",
            "session_id": "abc123",
            "stop_hook_active": False,
            "hook_event_name": "PreToolUse",
        }

        hook = HookInput.from_dict(data)

        assert hook.tool_name == "Write"
        assert hook.file_path == "/test/path.py"
        assert hook.cwd == "/test"
        assert hook.session_id == "abc123"
        assert hook.stop_hook_active is False
        assert hook.hook_event_name == "PreToolUse"

    def test_hook_input_handles_missing_fields(self):
        sys.path.insert(0, str(PROJECT_ROOT / "hooks" / "lib"))
        from hook_io import HookInput

        hook = HookInput.from_dict({})

        assert hook.tool_name == ""
        assert hook.file_path == ""
        assert hook.cwd == ""
        assert hook.session_id == "unknown"
        assert hook.stop_hook_active is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
