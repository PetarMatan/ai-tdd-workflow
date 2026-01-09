#!/usr/bin/env python3
"""
TDD Supervisor - Main Orchestrator

Orchestrates TDD workflow across multiple Claude sessions,
managing context transfer between phases.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, List

try:
    from claude_agent_sdk import query, ClaudeAgentOptions
    from claude_agent_sdk.types import AssistantMessage, ResultMessage
except ImportError:
    print("Error: claude-agent-sdk not installed.", file=sys.stderr)
    print("Install with: pip install claude-agent-sdk", file=sys.stderr)
    sys.exit(1)

from .markers import SupervisorMarkers
from .context import ContextBuilder
from .templates import (
    format_phase_header,
    format_workflow_header,
    format_phase_complete_banner,
    format_workflow_complete,
)


def read_user_input(prompt: str = "") -> str:
    """
    Read user input, supporting both direct text and file paths.

    For complex features, users can write structured requirements in a file
    and provide the path. The file content will be read and returned.

    File input methods:
    - @/path/to/file.md  - Explicit file prefix
    - /absolute/path.md  - Auto-detected absolute path
    - ./relative/path.md - Auto-detected relative path
    - ~/home/path.md     - Auto-detected home path

    Args:
        prompt: The prompt to display

    Returns:
        User input text or file contents
    """
    try:
        user_input = input(prompt)
    except (EOFError, KeyboardInterrupt):
        return ""

    # Check if input is a file reference
    file_path = None

    if user_input.startswith('@'):
        # Explicit file reference: @/path/to/file
        file_path = user_input[1:].strip()
    elif user_input.startswith(('/', './', '../', '~/')):
        # Potential file path - check if it exists
        expanded = os.path.expanduser(user_input.strip())
        if os.path.isfile(expanded):
            file_path = expanded

    if file_path:
        expanded_path = os.path.expanduser(file_path)
        try:
            with open(expanded_path, 'r') as f:
                content = f.read()
            print(f"[Loaded {len(content)} chars from {file_path}]")
            return content
        except FileNotFoundError:
            print(f"[File not found: {file_path}]")
            return ""
        except PermissionError:
            print(f"[Permission denied: {file_path}]")
            return ""
        except Exception as e:
            print(f"[Error reading file: {e}]")
            return ""

    return user_input


class TDDOrchestrator:
    """
    Orchestrates TDD workflow across multiple Claude sessions.

    Each phase runs in its own session with clean context.
    Context is passed between phases via summaries.
    """

    # Signals must be on their own line to avoid false positives
    PHASE_COMPLETE_SIGNAL = "---PHASE_COMPLETE---"
    SUMMARY_VERIFIED_SIGNAL = "SUMMARY_VERIFIED"
    GAPS_FOUND_SIGNAL = "GAPS_FOUND"

    PHASE_NAMES = {
        1: "Requirements Gathering",
        2: "Interface Design",
        3: "Test Writing",
        4: "Implementation",
    }

    def __init__(self, working_dir: Optional[str] = None):
        """
        Initialize the TDD orchestrator.

        Args:
            working_dir: Project working directory (defaults to cwd)
        """
        self.working_dir = Path(working_dir or os.getcwd()).resolve()
        self.markers = SupervisorMarkers()

        # Validate working directory
        if not self.working_dir.is_dir():
            raise ValueError(f"Working directory does not exist: {self.working_dir}")

    async def run(self, initial_task: Optional[str] = None) -> None:
        """
        Run the complete TDD workflow.

        Args:
            initial_task: Optional initial task description
        """
        print(format_workflow_header(
            working_dir=str(self.working_dir),
            workflow_id=self.markers.workflow_id,
            markers_dir=str(self.markers.get_marker_dir())
        ))

        try:
            # Initialize markers
            self.markers.initialize()

            # Run all 4 TDD phases
            await self._run_phase(1, initial_task)
            await self._run_phase(2)
            await self._run_phase(3)
            await self._run_phase(4)

            print(format_workflow_complete())

        except KeyboardInterrupt:
            print("\n\nWorkflow interrupted by user.")
            self.markers.cleanup()
            print("Markers cleaned up.")
        except Exception as e:
            print(f"\n\nWorkflow error: {e}", file=sys.stderr)
            self.markers.cleanup()
            raise

    def _build_phase_context(self, phase: int, initial_task: Optional[str] = None) -> str:
        """Build context for a specific phase."""
        if phase == 1:
            return ContextBuilder.build_phase1_context(initial_task)
        elif phase == 2:
            return ContextBuilder.build_phase2_context(
                self.markers.get_requirements_summary()
            )
        elif phase == 3:
            return ContextBuilder.build_phase3_context(
                self.markers.get_requirements_summary(),
                self.markers.get_interfaces_list()
            )
        elif phase == 4:
            return ContextBuilder.build_phase4_context(
                self.markers.get_requirements_summary(),
                self.markers.get_interfaces_list(),
                self.markers.get_tests_list()
            )
        else:
            raise ValueError(f"Invalid phase: {phase}")

    def _save_phase_summary(self, phase: int, summary: str) -> None:
        """Save summary for a specific phase."""
        if phase == 1:
            self.markers.save_requirements_summary(summary)
        elif phase == 2:
            self.markers.save_interfaces_list(summary)
        elif phase == 3:
            self.markers.save_tests_list(summary)

    async def _run_phase(self, phase: int, initial_task: Optional[str] = None) -> None:
        """
        Run a single TDD phase.

        Args:
            phase: Phase number (1-4)
            initial_task: Initial task description (phase 1 only)
        """
        print(format_phase_header(phase, self.PHASE_NAMES[phase]))
        self.markers.set_phase(phase)

        context = self._build_phase_context(phase, initial_task)
        session_id = await self._run_phase_session(context, phase)

        if phase < 4:
            summary = await self._generate_and_verify_summary(phase, session_id)
            self._save_phase_summary(phase, summary)
            print(f"\n[Supervisor] {self.PHASE_NAMES[phase]} summary saved.")
        else:
            print(f"\n[Supervisor] Implementation complete - all tests passing!")
            self.markers.cleanup()

    async def _run_phase_session(self, initial_context: str, phase: int) -> Optional[str]:
        """
        Run an interactive Claude session for a phase.

        Args:
            initial_context: Initial context/prompt for the phase
            phase: Current phase number

        Returns:
            Session ID for resuming conversation (e.g., for summary generation)
        """
        env_vars = self.markers.get_env_vars()

        # First message to Claude with phase context
        print(f"\n[Starting Phase {phase} session...]\n")

        session_id = None
        phase_complete = False
        working_indicator_shown = False

        # Initial query with context
        async for message in query(
            prompt=initial_context,
            options=ClaudeAgentOptions(
                cwd=str(self.working_dir),
                env=env_vars,
                permission_mode="bypassPermissions",
            )
        ):
            # Capture session ID
            if hasattr(message, 'session_id') and message.session_id:
                session_id = message.session_id

            # Print AssistantMessage content (text and tool usage)
            if isinstance(message, AssistantMessage) and message.content:
                for block in message.content:
                    if hasattr(block, 'text'):
                        if working_indicator_shown:
                            print("\n", end='')  # New line after dots
                            working_indicator_shown = False
                        print(block.text, end='', flush=True)
                        if self.PHASE_COMPLETE_SIGNAL in block.text:
                            phase_complete = True
                    elif hasattr(block, 'name'):
                        # Tool use - show dot as progress indicator
                        print(".", end='', flush=True)
                        working_indicator_shown = True

        # If phase not complete, continue interactive loop
        first_input = True
        while not phase_complete:
            # Show hint on first input prompt
            if first_input:
                print("\n[Tip: For structured input, provide a file path: @/path/to/file.md]")
                first_input = False

            user_input = read_user_input("\nYou: ").strip()

            if not user_input:
                continue

            # Check for user commands
            if user_input.lower() in ['/done', '/complete', '/next']:
                phase_complete = True
                break

            if user_input.lower() in ['/quit', '/exit', '/abort']:
                raise KeyboardInterrupt("User requested abort")

            # Continue conversation
            print("\n", end='', flush=True)
            working_indicator_shown = False
            async for message in query(
                prompt=user_input,
                options=ClaudeAgentOptions(
                    cwd=str(self.working_dir),
                    env=env_vars,
                    resume=session_id,
                    permission_mode="bypassPermissions",
                )
            ):
                # Print AssistantMessage content (text and tool usage)
                if isinstance(message, AssistantMessage) and message.content:
                    for block in message.content:
                        if hasattr(block, 'text'):
                            if working_indicator_shown:
                                print("\n", end='')  # New line after progress dots
                                working_indicator_shown = False
                            print(block.text, end='', flush=True)
                            if self.PHASE_COMPLETE_SIGNAL in block.text:
                                phase_complete = True
                        elif hasattr(block, 'name'):
                            # Tool use - show dot as progress indicator
                            print(".", end='', flush=True)

        # Ask for user confirmation before proceeding
        if phase < 4:
            await self._confirm_phase_completion(phase)

        return session_id

    async def _confirm_phase_completion(self, phase: int) -> None:
        """Ask user to confirm phase completion."""
        name = self.PHASE_NAMES.get(phase, f"Phase {phase}")

        print(format_phase_complete_banner(phase, name))

        while True:
            response = input("\nProceed to next phase? [y to continue, Ctrl+C to abort]: ").strip().lower()
            if response in ['y', 'yes', '']:
                return
            else:
                print("Press 'y' or Enter to continue, or Ctrl+C to abort.")

    async def _generate_and_verify_summary(self, phase: int, session_id: Optional[str] = None) -> str:
        """
        Generate a summary for the phase with self-review verification.

        This is a two-step process:
        1. Generate initial summary
        2. Ask Claude to self-review and fill any gaps

        Args:
            phase: Phase number to summarize
            session_id: Session ID to resume (uses same context as phase session)

        Returns:
            Verified summary text
        """
        # Step 1: Generate initial summary
        summary_prompt = ContextBuilder.get_summary_prompt(phase)
        if not summary_prompt:
            return ""

        print(f"\n[Supervisor] Generating phase {phase} summary...")

        initial_summary = await self._query_for_text(summary_prompt, session_id=session_id)

        # Step 2: Self-review
        review_prompt = ContextBuilder.get_review_prompt(phase)
        if not review_prompt:
            return initial_summary

        print(f"[Supervisor] Verifying summary completeness...")

        review_response = await self._query_for_text(review_prompt, session_id=session_id)

        # Parse review response
        if review_response.startswith(self.GAPS_FOUND_SIGNAL):
            # Extract updated summary (everything after the signal line)
            lines = review_response.split('\n', 1)
            if len(lines) > 1:
                updated_summary = lines[1].strip()
                print(f"[Supervisor] Summary updated with missing items.")
                return updated_summary
            else:
                # Fallback to initial if parsing fails
                return initial_summary
        elif review_response.startswith(self.SUMMARY_VERIFIED_SIGNAL):
            # Extract verified summary
            lines = review_response.split('\n', 1)
            if len(lines) > 1:
                print(f"[Supervisor] Summary verified complete.")
                return lines[1].strip()
            else:
                return initial_summary
        else:
            # If response doesn't follow format, use as-is
            # (Claude might have just output the summary directly)
            print(f"[Supervisor] Summary captured.")
            return review_response if review_response else initial_summary

    async def _query_for_text(
        self,
        prompt: str,
        timeout: float = 300.0,
        session_id: Optional[str] = None
    ) -> str:
        """
        Send a query and collect the text response.

        Args:
            prompt: The prompt to send
            timeout: Maximum time to wait in seconds (default 5 minutes)
            session_id: Optional session ID to resume conversation

        Returns:
            Collected text response
        """
        text_parts: List[str] = []
        env_vars = self.markers.get_env_vars()

        async def collect_response() -> None:
            async for message in query(
                prompt=prompt,
                options=ClaudeAgentOptions(
                    cwd=str(self.working_dir),
                    env=env_vars,
                    resume=session_id,
                    permission_mode="bypassPermissions",
                )
            ):
                if isinstance(message, AssistantMessage) and message.content:
                    for block in message.content:
                        if hasattr(block, 'text'):
                            text_parts.append(block.text)

        try:
            await asyncio.wait_for(collect_response(), timeout=timeout)
        except asyncio.TimeoutError:
            print(f"\n[Supervisor] Query timed out after {timeout}s", file=sys.stderr)

        return ''.join(text_parts)


async def run_supervisor(
    working_dir: Optional[str] = None,
    task: Optional[str] = None,
) -> None:
    """
    Run the TDD supervisor.

    Args:
        working_dir: Project working directory
        task: Initial task description
    """
    orchestrator = TDDOrchestrator(working_dir=working_dir)
    await orchestrator.run(initial_task=task)
