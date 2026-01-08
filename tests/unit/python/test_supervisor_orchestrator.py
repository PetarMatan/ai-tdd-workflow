#!/usr/bin/env python3
"""
Unit tests for tdd_supervisor/orchestrator.py - TDDOrchestrator class

Note: These tests mock the claude-agent-sdk to test orchestrator logic
without requiring actual Claude API calls.
"""

import os
import sys
import tempfile
import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Mock claude_agent_sdk before importing orchestrator
mock_sdk = MagicMock()
mock_sdk.query = MagicMock()
mock_sdk.ClaudeAgentOptions = MagicMock()
sys.modules['claude_agent_sdk'] = mock_sdk

# Add tdd_supervisor to path
sys.path.insert(0, '.')
from tdd_supervisor.markers import SupervisorMarkers
from tdd_supervisor.context import ContextBuilder


# Helper to run async functions in tests
def run_async(coro):
    """Run an async function synchronously for testing."""
    return asyncio.run(coro)


class TestTDDOrchestratorInit:
    """Tests for TDDOrchestrator initialization."""

    def test_init_sets_working_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)
                assert orchestrator.working_dir == Path(tmpdir).resolve()

    def test_init_defaults_to_cwd(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                with patch('os.getcwd', return_value=tmpdir):
                    from tdd_supervisor.orchestrator import TDDOrchestrator
                    orchestrator = TDDOrchestrator()
                    assert orchestrator.working_dir == Path(tmpdir).resolve()

    def test_init_creates_markers_instance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)
                assert isinstance(orchestrator.markers, SupervisorMarkers)

    def test_init_creates_context_builder_instance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)
                assert isinstance(orchestrator.context_builder, ContextBuilder)

    def test_init_raises_for_invalid_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                with pytest.raises(ValueError) as exc_info:
                    TDDOrchestrator(working_dir="/nonexistent/path/xyz")
                assert "does not exist" in str(exc_info.value)

    def test_init_with_custom_workflow_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(
                    working_dir=tmpdir,
                    workflow_id="custom-123"
                )
                assert orchestrator.markers.workflow_id == "custom-123"

    def test_init_resolves_relative_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                # Use current directory which should exist
                orchestrator = TDDOrchestrator(working_dir=".")
                assert orchestrator.working_dir.is_absolute()


class TestPhaseHeader:
    """Tests for _phase_header method."""

    def test_phase_header_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)
                header = orchestrator._phase_header(1, "Requirements Gathering")

                assert "PHASE 1" in header
                assert "REQUIREMENTS GATHERING" in header
                assert "=" in header

    def test_phase_header_all_phases(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)

                phases = [
                    (1, "Requirements Gathering"),
                    (2, "Interface Design"),
                    (3, "Test Writing"),
                    (4, "Implementation"),
                ]

                for phase_num, phase_name in phases:
                    header = orchestrator._phase_header(phase_num, phase_name)
                    assert f"PHASE {phase_num}" in header
                    assert phase_name.upper() in header


class TestPhaseCompleteSignal:
    """Tests for PHASE_COMPLETE_SIGNAL constant."""

    def test_phase_complete_signal_exists(self):
        from tdd_supervisor.orchestrator import TDDOrchestrator
        assert hasattr(TDDOrchestrator, 'PHASE_COMPLETE_SIGNAL')
        assert TDDOrchestrator.PHASE_COMPLETE_SIGNAL == "PHASE_COMPLETE"


class TestRunPhase1:
    """Tests for _run_phase1 method."""

    def test_run_phase1_sets_phase_marker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)

                # Mock the async methods
                async def mock_run_session(*args, **kwargs):
                    pass

                async def mock_generate_summary(*args, **kwargs):
                    return "# Summary"

                orchestrator._run_phase_session = mock_run_session
                orchestrator._generate_summary = mock_generate_summary

                run_async(orchestrator._run_phase1("test task"))

                assert orchestrator.markers.get_phase() == 1

    def test_run_phase1_saves_requirements_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)

                async def mock_run_session(*args, **kwargs):
                    pass

                async def mock_generate_summary(*args, **kwargs):
                    return "# Requirements\n- Feature A"

                orchestrator._run_phase_session = mock_run_session
                orchestrator._generate_summary = mock_generate_summary

                run_async(orchestrator._run_phase1("test"))

                saved = orchestrator.markers.get_requirements_summary()
                assert "# Requirements" in saved


class TestRunPhase2:
    """Tests for _run_phase2 method."""

    def test_run_phase2_sets_phase_marker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)
                orchestrator.markers.save_requirements_summary("# Requirements")

                async def mock_run_session(*args, **kwargs):
                    pass

                async def mock_generate_summary(*args, **kwargs):
                    return "# Interfaces"

                orchestrator._run_phase_session = mock_run_session
                orchestrator._generate_summary = mock_generate_summary

                run_async(orchestrator._run_phase2())

                assert orchestrator.markers.get_phase() == 2

    def test_run_phase2_saves_interfaces_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)
                orchestrator.markers.save_requirements_summary("# Requirements")

                async def mock_run_session(*args, **kwargs):
                    pass

                async def mock_generate_summary(*args, **kwargs):
                    return "# Interfaces\n- ServiceA"

                orchestrator._run_phase_session = mock_run_session
                orchestrator._generate_summary = mock_generate_summary

                run_async(orchestrator._run_phase2())

                saved = orchestrator.markers.get_interfaces_list()
                assert "# Interfaces" in saved


class TestRunPhase3:
    """Tests for _run_phase3 method."""

    def test_run_phase3_sets_phase_marker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)
                orchestrator.markers.save_requirements_summary("# Requirements")
                orchestrator.markers.save_interfaces_list("# Interfaces")

                async def mock_run_session(*args, **kwargs):
                    pass

                async def mock_generate_summary(*args, **kwargs):
                    return "# Tests"

                orchestrator._run_phase_session = mock_run_session
                orchestrator._generate_summary = mock_generate_summary

                run_async(orchestrator._run_phase3())

                assert orchestrator.markers.get_phase() == 3

    def test_run_phase3_saves_tests_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)
                orchestrator.markers.save_requirements_summary("# Requirements")
                orchestrator.markers.save_interfaces_list("# Interfaces")

                async def mock_run_session(*args, **kwargs):
                    pass

                async def mock_generate_summary(*args, **kwargs):
                    return "# Tests\n- test_feature"

                orchestrator._run_phase_session = mock_run_session
                orchestrator._generate_summary = mock_generate_summary

                run_async(orchestrator._run_phase3())

                saved = orchestrator.markers.get_tests_list()
                assert "# Tests" in saved


class TestRunPhase4:
    """Tests for _run_phase4 method."""

    def test_run_phase4_sets_phase_marker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)
                orchestrator.markers.save_requirements_summary("# Requirements")
                orchestrator.markers.save_interfaces_list("# Interfaces")
                orchestrator.markers.save_tests_list("# Tests")

                phase_set_to = None

                async def mock_run_session(*args, **kwargs):
                    nonlocal phase_set_to
                    # Capture phase while session is running (before cleanup)
                    phase_set_to = orchestrator.markers.get_phase()

                orchestrator._run_phase_session = mock_run_session

                run_async(orchestrator._run_phase4())

                # Phase was set to 4 during the session
                assert phase_set_to == 4

    def test_run_phase4_cleans_up_markers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)
                orchestrator.markers.initialize()
                orchestrator.markers.save_requirements_summary("# Requirements")
                orchestrator.markers.save_interfaces_list("# Interfaces")
                orchestrator.markers.save_tests_list("# Tests")

                async def mock_run_session(*args, **kwargs):
                    pass

                orchestrator._run_phase_session = mock_run_session

                run_async(orchestrator._run_phase4())

                # Markers should be cleaned up after phase 4
                assert not orchestrator.markers.markers_dir.exists()


class TestGenerateSummary:
    """Tests for _generate_summary method."""

    def test_generate_summary_returns_empty_for_phase4(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)

                # Phase 4 has no summary prompt, should return empty
                result = run_async(orchestrator._generate_summary(4))
                assert result == ""


class TestRunSupervisor:
    """Tests for run_supervisor function."""

    def test_run_supervisor_function_exists(self):
        from tdd_supervisor.orchestrator import run_supervisor
        assert callable(run_supervisor)


class TestKeyboardInterruptHandling:
    """Tests for keyboard interrupt handling."""

    def test_keyboard_interrupt_preserves_markers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)
                orchestrator.markers.initialize()

                # Simulate keyboard interrupt during phase 1
                async def raise_interrupt(*args, **kwargs):
                    raise KeyboardInterrupt()

                orchestrator._run_phase1 = raise_interrupt

                # The orchestrator catches KeyboardInterrupt internally
                # and prints a message, so we just run it
                run_async(orchestrator.run())

                # Markers should still exist (not cleaned up on interrupt)
                assert orchestrator.markers.markers_dir.exists()


class TestConfirmPhaseCompletion:
    """Tests for _confirm_phase_completion method."""

    def test_confirm_phase_completion_accepts_y(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)

                with patch('builtins.input', return_value='y'):
                    # Should not raise
                    run_async(orchestrator._confirm_phase_completion(1))

    def test_confirm_phase_completion_accepts_yes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)

                with patch('builtins.input', return_value='yes'):
                    run_async(orchestrator._confirm_phase_completion(1))

    def test_confirm_phase_completion_rejects_n(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)

                with patch('builtins.input', return_value='n'):
                    with pytest.raises(Exception) as exc_info:
                        run_async(orchestrator._confirm_phase_completion(1))
                    assert "continue phase" in str(exc_info.value).lower()

    def test_confirm_phase_completion_retries_on_invalid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)

                # First invalid, then valid
                inputs = iter(['invalid', 'y'])
                with patch('builtins.input', lambda _: next(inputs)):
                    run_async(orchestrator._confirm_phase_completion(1))


class TestContextPassing:
    """Tests for context passing between phases."""

    def test_phase2_receives_requirements_context(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)
                orchestrator.markers.save_requirements_summary("# Saved Requirements")

                captured_context = None

                async def capture_context(context, phase):
                    nonlocal captured_context
                    captured_context = context

                async def mock_generate_summary(*args, **kwargs):
                    return "# Interfaces"

                orchestrator._run_phase_session = capture_context
                orchestrator._generate_summary = mock_generate_summary

                run_async(orchestrator._run_phase2())

                assert "# Saved Requirements" in captured_context

    def test_phase3_receives_requirements_and_interfaces(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)
                orchestrator.markers.save_requirements_summary("# Requirements Summary")
                orchestrator.markers.save_interfaces_list("# Interfaces List")

                captured_context = None

                async def capture_context(context, phase):
                    nonlocal captured_context
                    captured_context = context

                async def mock_generate_summary(*args, **kwargs):
                    return "# Tests"

                orchestrator._run_phase_session = capture_context
                orchestrator._generate_summary = mock_generate_summary

                run_async(orchestrator._run_phase3())

                assert "# Requirements Summary" in captured_context
                assert "# Interfaces List" in captured_context

    def test_phase4_receives_all_context(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)
                orchestrator.markers.save_requirements_summary("# Req Summary")
                orchestrator.markers.save_interfaces_list("# Int List")
                orchestrator.markers.save_tests_list("# Test List")

                captured_context = None

                async def capture_context(context, phase):
                    nonlocal captured_context
                    captured_context = context

                orchestrator._run_phase_session = capture_context

                run_async(orchestrator._run_phase4())

                assert "# Req Summary" in captured_context
                assert "# Int List" in captured_context
                assert "# Test List" in captured_context


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
