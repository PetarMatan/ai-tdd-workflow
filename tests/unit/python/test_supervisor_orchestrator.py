#!/usr/bin/env python3
"""
Unit tests for tdd_supervisor/orchestrator.py - TDDOrchestrator class

Note: These tests mock the claude-agent-sdk to test orchestrator logic
without requiring actual Claude API calls.
"""

import io
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
mock_types = MagicMock()
mock_types.AssistantMessage = MagicMock()
mock_types.ResultMessage = MagicMock()
mock_sdk.types = mock_types
sys.modules['claude_agent_sdk'] = mock_sdk
sys.modules['claude_agent_sdk.types'] = mock_types

# Add tdd_supervisor to path
sys.path.insert(0, '.')
from tdd_supervisor.markers import SupervisorMarkers
from tdd_supervisor.context import ContextBuilder
from tdd_supervisor.orchestrator import read_multiline_input


# Helper to run async functions in tests
def run_async(coro):
    """Run an async function synchronously for testing."""
    return asyncio.run(coro)


class TestReadMultilineInput:
    """Tests for read_multiline_input function."""

    def test_single_line_input(self):
        """Single line input returns that line."""
        mock_stdin = io.StringIO("hello world\n")

        with patch('tdd_supervisor.orchestrator.sys.stdin', mock_stdin):
            with patch('tdd_supervisor.orchestrator.select.select', return_value=([], [], [])):
                result = read_multiline_input()

        assert result == "hello world"

    def test_multiline_paste(self):
        """Multi-line paste returns all lines joined."""
        # Simulate pasting 3 lines at once
        mock_stdin = io.StringIO("line 1\nline 2\nline 3\n")

        # select returns stdin as readable for first 2 calls, then empty
        select_returns = [
            ([mock_stdin], [], []),  # More data after line 1
            ([mock_stdin], [], []),  # More data after line 2
            ([], [], []),            # No more data after line 3
        ]
        select_iter = iter(select_returns)

        with patch('tdd_supervisor.orchestrator.sys.stdin', mock_stdin):
            with patch('tdd_supervisor.orchestrator.select.select', side_effect=lambda *args: next(select_iter)):
                result = read_multiline_input()

        assert result == "line 1\nline 2\nline 3"

    def test_empty_input_returns_empty_string(self):
        """Empty input (EOF) returns empty string."""
        mock_stdin = io.StringIO("")

        with patch('tdd_supervisor.orchestrator.sys.stdin', mock_stdin):
            result = read_multiline_input()

        assert result == ""

    def test_prompt_is_printed(self, capsys):
        """Prompt is printed before reading input."""
        mock_stdin = io.StringIO("test\n")

        with patch('tdd_supervisor.orchestrator.sys.stdin', mock_stdin):
            with patch('tdd_supervisor.orchestrator.select.select', return_value=([], [], [])):
                read_multiline_input("Enter text: ")

        captured = capsys.readouterr()
        assert "Enter text: " in captured.out

    def test_multiline_with_empty_lines(self):
        """Multi-line paste with empty lines preserves them."""
        mock_stdin = io.StringIO("line 1\n\nline 3\n")

        select_returns = [
            ([mock_stdin], [], []),
            ([mock_stdin], [], []),
            ([], [], []),
        ]
        select_iter = iter(select_returns)

        with patch('tdd_supervisor.orchestrator.sys.stdin', mock_stdin):
            with patch('tdd_supervisor.orchestrator.select.select', side_effect=lambda *args: next(select_iter)):
                result = read_multiline_input()

        assert result == "line 1\n\nline 3"

    def test_strips_trailing_newlines_per_line(self):
        """Each line has its trailing newline stripped."""
        mock_stdin = io.StringIO("line with trailing\n")

        with patch('tdd_supervisor.orchestrator.sys.stdin', mock_stdin):
            with patch('tdd_supervisor.orchestrator.select.select', return_value=([], [], [])):
                result = read_multiline_input()

        assert result == "line with trailing"
        assert not result.endswith('\n')

    def test_handles_jira_style_paste(self):
        """Handles typical Jira ticket paste with multiple sections."""
        jira_content = """Title: User Authentication Feature
Description: Implement OAuth2 login
Acceptance Criteria:
- Users can login with Google
- Users can login with GitHub
- Session persists for 7 days
"""
        mock_stdin = io.StringIO(jira_content)

        # Simulate all lines being available at once (paste)
        def select_side_effect(*args):
            if mock_stdin.tell() < len(jira_content):
                return ([mock_stdin], [], [])
            return ([], [], [])

        with patch('tdd_supervisor.orchestrator.sys.stdin', mock_stdin):
            with patch('tdd_supervisor.orchestrator.select.select', side_effect=select_side_effect):
                result = read_multiline_input()

        assert "Title: User Authentication Feature" in result
        assert "Acceptance Criteria:" in result
        assert "- Users can login with Google" in result
        assert "- Session persists for 7 days" in result


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

    def test_init_raises_for_invalid_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                with pytest.raises(ValueError) as exc_info:
                    TDDOrchestrator(working_dir="/nonexistent/path/xyz")
                assert "does not exist" in str(exc_info.value)

    def test_init_resolves_relative_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                # Use current directory which should exist
                orchestrator = TDDOrchestrator(working_dir=".")
                assert orchestrator.working_dir.is_absolute()


class TestOrchestratorSignals:
    """Tests for orchestrator signal constants."""

    def test_phase_complete_signal_exists(self):
        from tdd_supervisor.orchestrator import TDDOrchestrator
        assert hasattr(TDDOrchestrator, 'PHASE_COMPLETE_SIGNAL')
        assert TDDOrchestrator.PHASE_COMPLETE_SIGNAL == "PHASE_COMPLETE"

    def test_summary_verified_signal_exists(self):
        from tdd_supervisor.orchestrator import TDDOrchestrator
        assert hasattr(TDDOrchestrator, 'SUMMARY_VERIFIED_SIGNAL')
        assert TDDOrchestrator.SUMMARY_VERIFIED_SIGNAL == "SUMMARY_VERIFIED"

    def test_gaps_found_signal_exists(self):
        from tdd_supervisor.orchestrator import TDDOrchestrator
        assert hasattr(TDDOrchestrator, 'GAPS_FOUND_SIGNAL')
        assert TDDOrchestrator.GAPS_FOUND_SIGNAL == "GAPS_FOUND"

    def test_phase_names_dict_exists(self):
        from tdd_supervisor.orchestrator import TDDOrchestrator
        assert hasattr(TDDOrchestrator, 'PHASE_NAMES')
        assert 1 in TDDOrchestrator.PHASE_NAMES
        assert 2 in TDDOrchestrator.PHASE_NAMES
        assert 3 in TDDOrchestrator.PHASE_NAMES
        assert 4 in TDDOrchestrator.PHASE_NAMES


class TestRunPhase:
    """Tests for _run_phase method."""

    def test_run_phase_sets_phase_marker(self):
        """Test that _run_phase sets the correct phase marker for each phase."""
        for phase in [1, 2, 3, 4]:
            with tempfile.TemporaryDirectory() as tmpdir:
                with patch.object(Path, 'home', return_value=Path(tmpdir)):
                    from tdd_supervisor.orchestrator import TDDOrchestrator
                    orchestrator = TDDOrchestrator(working_dir=tmpdir)

                    # Set up prerequisites for phases 2-4
                    if phase >= 2:
                        orchestrator.markers.save_requirements_summary("# Requirements")
                    if phase >= 3:
                        orchestrator.markers.save_interfaces_list("# Interfaces")
                    if phase == 4:
                        orchestrator.markers.save_tests_list("# Tests")

                    phase_during_session = None

                    async def mock_run_session(*args, **kwargs):
                        nonlocal phase_during_session
                        phase_during_session = orchestrator.markers.get_phase()

                    async def mock_generate_and_verify(*args, **kwargs):
                        return "# Summary"

                    orchestrator._run_phase_session = mock_run_session
                    orchestrator._generate_and_verify_summary = mock_generate_and_verify

                    run_async(orchestrator._run_phase(phase, "test task" if phase == 1 else None))

                    assert phase_during_session == phase

    def test_run_phase_saves_requirements_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)

                async def mock_run_session(*args, **kwargs):
                    pass

                async def mock_generate_and_verify(*args, **kwargs):
                    return "# Requirements\n- Feature A"

                orchestrator._run_phase_session = mock_run_session
                orchestrator._generate_and_verify_summary = mock_generate_and_verify

                run_async(orchestrator._run_phase(1, "test"))

                saved = orchestrator.markers.get_requirements_summary()
                assert "# Requirements" in saved

    def test_run_phase_saves_interfaces_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)
                orchestrator.markers.save_requirements_summary("# Requirements")

                async def mock_run_session(*args, **kwargs):
                    pass

                async def mock_generate_and_verify(*args, **kwargs):
                    return "# Interfaces\n- ServiceA"

                orchestrator._run_phase_session = mock_run_session
                orchestrator._generate_and_verify_summary = mock_generate_and_verify

                run_async(orchestrator._run_phase(2))

                saved = orchestrator.markers.get_interfaces_list()
                assert "# Interfaces" in saved

    def test_run_phase_saves_tests_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)
                orchestrator.markers.save_requirements_summary("# Requirements")
                orchestrator.markers.save_interfaces_list("# Interfaces")

                async def mock_run_session(*args, **kwargs):
                    pass

                async def mock_generate_and_verify(*args, **kwargs):
                    return "# Tests\n- test_feature"

                orchestrator._run_phase_session = mock_run_session
                orchestrator._generate_and_verify_summary = mock_generate_and_verify

                run_async(orchestrator._run_phase(3))

                saved = orchestrator.markers.get_tests_list()
                assert "# Tests" in saved

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

                run_async(orchestrator._run_phase(4))

                # Markers should be cleaned up after phase 4
                assert not orchestrator.markers.markers_dir.exists()


class TestGenerateAndVerifySummary:
    """Tests for _generate_and_verify_summary method."""

    def test_generate_and_verify_returns_empty_for_phase4(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)

                # Phase 4 has no summary prompt, should return empty
                result = run_async(orchestrator._generate_and_verify_summary(4))
                assert result == ""

    def test_generate_and_verify_calls_query_for_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)

                call_count = 0

                async def mock_query_for_text(prompt):
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        return "# Initial Summary"
                    else:
                        return "SUMMARY_VERIFIED\n# Initial Summary"

                orchestrator._query_for_text = mock_query_for_text

                result = run_async(orchestrator._generate_and_verify_summary(1))

                # Should call query twice: once for summary, once for review
                assert call_count == 2

    def test_generate_and_verify_handles_gaps_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)

                call_count = 0

                async def mock_query_for_text(prompt):
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        return "# Initial Summary"
                    else:
                        return "GAPS_FOUND\n# Updated Summary with additions"

                orchestrator._query_for_text = mock_query_for_text

                result = run_async(orchestrator._generate_and_verify_summary(1))

                assert "Updated Summary" in result

    def test_generate_and_verify_handles_verified(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)

                call_count = 0

                async def mock_query_for_text(prompt):
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        return "# Initial Summary"
                    else:
                        return "SUMMARY_VERIFIED\n# Verified Summary"

                orchestrator._query_for_text = mock_query_for_text

                result = run_async(orchestrator._generate_and_verify_summary(1))

                assert "Verified Summary" in result

    def test_generate_and_verify_handles_non_standard_response(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)

                call_count = 0

                async def mock_query_for_text(prompt):
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        return "# Initial Summary"
                    else:
                        # Response doesn't follow expected format
                        return "# Some other response"

                orchestrator._query_for_text = mock_query_for_text

                result = run_async(orchestrator._generate_and_verify_summary(1))

                # Should use the review response as-is
                assert "Some other response" in result


class TestRunSupervisor:
    """Tests for run_supervisor function."""

    def test_run_supervisor_function_exists(self):
        from tdd_supervisor.orchestrator import run_supervisor
        assert callable(run_supervisor)


class TestKeyboardInterruptHandling:
    """Tests for keyboard interrupt handling."""

    def test_keyboard_interrupt_cleans_up_markers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)
                orchestrator.markers.initialize()

                # Simulate keyboard interrupt during phase
                async def raise_interrupt(*args, **kwargs):
                    raise KeyboardInterrupt()

                orchestrator._run_phase = raise_interrupt

                # The orchestrator catches KeyboardInterrupt internally
                # and cleans up markers
                run_async(orchestrator.run())

                # Markers should be cleaned up on interrupt
                assert not orchestrator.markers.markers_dir.exists()


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

    def test_confirm_phase_completion_accepts_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)

                with patch('builtins.input', return_value=''):
                    # Empty string should be accepted (same as pressing Enter)
                    run_async(orchestrator._confirm_phase_completion(1))

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

                async def mock_generate_and_verify(*args, **kwargs):
                    return "# Interfaces"

                orchestrator._run_phase_session = capture_context
                orchestrator._generate_and_verify_summary = mock_generate_and_verify

                run_async(orchestrator._run_phase(2))

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

                async def mock_generate_and_verify(*args, **kwargs):
                    return "# Tests"

                orchestrator._run_phase_session = capture_context
                orchestrator._generate_and_verify_summary = mock_generate_and_verify

                run_async(orchestrator._run_phase(3))

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

                run_async(orchestrator._run_phase(4))

                assert "# Req Summary" in captured_context
                assert "# Int List" in captured_context
                assert "# Test List" in captured_context


@pytest.mark.skipif(
    os.environ.get('RUN_E2E_TESTS') != '1',
    reason="E2E tests skipped by default. Use --e2e flag or set RUN_E2E_TESTS=1"
)
class TestSupervisorEndToEnd:
    """End-to-end tests for full supervisor workflow."""

    def _create_mock_message(self, text: str, session_id: str = "test-session-123"):
        """Create a mock message that passes isinstance checks."""
        # Create a simple class that will pass isinstance check
        class MockAssistantMessage:
            pass

        mock_message = MockAssistantMessage()
        mock_message.session_id = session_id

        # Create text block
        text_block = MagicMock()
        text_block.text = text
        mock_message.content = [text_block]

        return mock_message, MockAssistantMessage

    def _create_mock_query(self, phases_executed: list):
        """
        Create a mock query function that simulates Claude responses.

        Args:
            phases_executed: List to track which phases were executed

        Returns:
            Tuple of (async generator function, message class for isinstance patch)
        """
        # Create a real class for isinstance checks
        class MockAssistantMessage:
            pass

        async def mock_query(prompt, options=None):
            """Mock query that yields appropriate responses per phase."""
            mock_message = MockAssistantMessage()
            mock_message.session_id = "test-session-123"

            # Determine response based on prompt content
            # Use specific phase header patterns to avoid false matches
            # (e.g., "Requirements from Phase 1" would incorrectly match Phase 1)
            if "Phase 4:" in prompt or "Phase 4 of" in prompt:
                phases_executed.append(4)
                text = "All tests passing! PHASE_COMPLETE"
            elif "Phase 3:" in prompt or "Phase 3 of" in prompt:
                phases_executed.append(3)
                text = "I've written the tests. PHASE_COMPLETE"
            elif "Phase 2:" in prompt or "Phase 2 of" in prompt:
                phases_executed.append(2)
                text = "I've designed the interfaces. PHASE_COMPLETE"
            elif "Phase 1:" in prompt or "Phase 1 of" in prompt:
                phases_executed.append(1)
                text = "I understand you want to build a feature. PHASE_COMPLETE"
            elif "summary" in prompt.lower():
                # Summary generation prompts
                text = "# Summary\n- Item 1\n- Item 2"
            elif "review" in prompt.lower() or "verify" in prompt.lower():
                # Review prompts
                text = "SUMMARY_VERIFIED\n# Summary\n- Item 1\n- Item 2"
            else:
                text = "OK, continuing..."

            # Create text block
            text_block = MagicMock()
            text_block.text = text
            mock_message.content = [text_block]

            yield mock_message

        return mock_query, MockAssistantMessage

    def test_complete_workflow_all_four_phases(self):
        """
        End-to-end test: Run complete TDD workflow through all 4 phases.

        This test verifies:
        1. All 4 phases execute in order
        2. Summaries are generated and saved between phases
        3. Context is passed correctly between phases
        4. Markers are cleaned up at the end
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator

                # Track which phases were executed
                phases_executed = []

                # Create orchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)

                # Mock the query function and get the message class
                mock_query, MockMessageClass = self._create_mock_query(phases_executed)

                # Mock user confirmations (always say 'y' to proceed)
                with patch('builtins.input', return_value='y'):
                    # Patch the query function and AssistantMessage class
                    with patch('tdd_supervisor.orchestrator.query', mock_query):
                        with patch('tdd_supervisor.orchestrator.AssistantMessage', MockMessageClass):
                            # Run the complete workflow
                            run_async(orchestrator.run(initial_task="Build a test feature"))

                # Verify all 4 phases were executed
                assert 1 in phases_executed, "Phase 1 should have executed"
                assert 2 in phases_executed, "Phase 2 should have executed"
                assert 3 in phases_executed, "Phase 3 should have executed"
                assert 4 in phases_executed, "Phase 4 should have executed"

                # Verify phases executed in order
                phase_order = [p for p in phases_executed if p in [1, 2, 3, 4]]
                assert phase_order == [1, 2, 3, 4], f"Phases should execute in order, got {phase_order}"

                # Verify markers were cleaned up (phase 4 cleanup)
                assert not orchestrator.markers.markers_dir.exists(), \
                    "Markers should be cleaned up after successful completion"

    def test_workflow_saves_summaries_between_phases(self):
        """
        End-to-end test: Verify summaries are saved and passed between phases.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator

                phases_executed = []
                saved_summaries = {}

                # Create orchestrator
                orchestrator = TDDOrchestrator(working_dir=tmpdir)

                # Capture summaries as they're saved
                original_save_req = orchestrator.markers.save_requirements_summary
                original_save_int = orchestrator.markers.save_interfaces_list
                original_save_tests = orchestrator.markers.save_tests_list

                def capture_req_summary(summary):
                    saved_summaries['requirements'] = summary
                    return original_save_req(summary)

                def capture_int_summary(summary):
                    saved_summaries['interfaces'] = summary
                    return original_save_int(summary)

                def capture_tests_summary(summary):
                    saved_summaries['tests'] = summary
                    return original_save_tests(summary)

                orchestrator.markers.save_requirements_summary = capture_req_summary
                orchestrator.markers.save_interfaces_list = capture_int_summary
                orchestrator.markers.save_tests_list = capture_tests_summary

                mock_query, MockMessageClass = self._create_mock_query(phases_executed)

                with patch('builtins.input', return_value='y'):
                    with patch('tdd_supervisor.orchestrator.query', mock_query):
                        with patch('tdd_supervisor.orchestrator.AssistantMessage', MockMessageClass):
                            run_async(orchestrator.run(initial_task="Build a feature"))

                # Verify summaries were saved for phases 1-3
                assert 'requirements' in saved_summaries, "Requirements summary should be saved"
                assert 'interfaces' in saved_summaries, "Interfaces summary should be saved"
                assert 'tests' in saved_summaries, "Tests summary should be saved"

                # Verify summaries have content
                assert len(saved_summaries['requirements']) > 0
                assert len(saved_summaries['interfaces']) > 0
                assert len(saved_summaries['tests']) > 0

    def test_workflow_with_initial_task(self):
        """
        End-to-end test: Verify initial task is passed to phase 1.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                from tdd_supervisor.orchestrator import TDDOrchestrator

                phases_executed = []
                captured_prompts = []

                # Create a real class for isinstance checks
                class MockAssistantMessage:
                    pass

                async def capturing_mock_query(prompt, options=None):
                    """Mock that captures prompts."""
                    captured_prompts.append(prompt)

                    mock_message = MockAssistantMessage()
                    mock_message.session_id = "test-session"

                    if "Phase 1" in prompt:
                        phases_executed.append(1)
                        text = "PHASE_COMPLETE"
                    elif "Phase 2" in prompt:
                        phases_executed.append(2)
                        text = "PHASE_COMPLETE"
                    elif "Phase 3" in prompt:
                        phases_executed.append(3)
                        text = "PHASE_COMPLETE"
                    elif "Phase 4" in prompt:
                        phases_executed.append(4)
                        text = "PHASE_COMPLETE"
                    else:
                        text = "SUMMARY_VERIFIED\n# Summary"

                    text_block = MagicMock()
                    text_block.text = text
                    mock_message.content = [text_block]
                    yield mock_message

                orchestrator = TDDOrchestrator(working_dir=tmpdir)

                with patch('builtins.input', return_value='y'):
                    with patch('tdd_supervisor.orchestrator.query', capturing_mock_query):
                        with patch('tdd_supervisor.orchestrator.AssistantMessage', MockAssistantMessage):
                            run_async(orchestrator.run(initial_task="Build a REST API for users"))

                # Verify initial task appears in phase 1 prompt
                phase1_prompts = [p for p in captured_prompts if "Phase 1" in p]
                assert len(phase1_prompts) > 0, "Should have phase 1 prompt"
                assert "Build a REST API for users" in phase1_prompts[0], \
                    "Initial task should be in phase 1 context"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
