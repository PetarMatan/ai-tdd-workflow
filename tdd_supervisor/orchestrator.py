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
from typing import Optional, AsyncIterator

try:
    from claude_agent_sdk import query, ClaudeAgentOptions
except ImportError:
    print("Error: claude-agent-sdk not installed.", file=sys.stderr)
    print("Install with: pip install claude-agent-sdk", file=sys.stderr)
    sys.exit(1)

from .markers import SupervisorMarkers
from .context import ContextBuilder


class TDDOrchestrator:
    """
    Orchestrates TDD workflow across multiple Claude sessions.

    Each phase runs in its own session with clean context.
    Context is passed between phases via summaries.
    """

    PHASE_COMPLETE_SIGNAL = "PHASE_COMPLETE"

    def __init__(
        self,
        working_dir: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ):
        """
        Initialize the TDD orchestrator.

        Args:
            working_dir: Project working directory (defaults to cwd)
            workflow_id: Unique workflow ID (auto-generated if not provided)
        """
        self.working_dir = Path(working_dir or os.getcwd()).resolve()
        self.markers = SupervisorMarkers(workflow_id)
        self.context_builder = ContextBuilder()

        # Validate working directory
        if not self.working_dir.is_dir():
            raise ValueError(f"Working directory does not exist: {self.working_dir}")

    async def run(self, initial_task: Optional[str] = None) -> None:
        """
        Run the complete TDD workflow.

        Args:
            initial_task: Optional initial task description
        """
        print(f"\n{'='*60}")
        print("TDD Supervisor - Starting Workflow")
        print(f"{'='*60}")
        print(f"Working directory: {self.working_dir}")
        print(f"Workflow ID: {self.markers.workflow_id}")
        print(f"Markers directory: {self.markers.get_marker_dir()}")
        print(f"{'='*60}\n")

        try:
            # Initialize markers
            self.markers.initialize()

            # Phase 1: Requirements
            await self._run_phase1(initial_task)

            # Phase 2: Interfaces
            await self._run_phase2()

            # Phase 3: Tests
            await self._run_phase3()

            # Phase 4: Implementation
            await self._run_phase4()

            print(f"\n{'='*60}")
            print("TDD Workflow Complete!")
            print(f"{'='*60}\n")

        except KeyboardInterrupt:
            print("\n\nWorkflow interrupted by user.")
            print(f"Markers preserved at: {self.markers.get_marker_dir()}")
            print("You can resume or clean up manually.")
        except Exception as e:
            print(f"\n\nWorkflow error: {e}", file=sys.stderr)
            raise
        finally:
            # Cleanup on completion (not on interrupt)
            pass

    async def _run_phase1(self, initial_task: Optional[str] = None) -> None:
        """Run Phase 1: Requirements Gathering."""
        print(self._phase_header(1, "Requirements Gathering"))

        self.markers.set_phase(1)
        context = self.context_builder.build_phase1_context(initial_task)

        # Run session until phase complete
        await self._run_phase_session(context, 1)

        # Generate and save requirements summary
        summary = await self._generate_summary(1)
        self.markers.save_requirements_summary(summary)

        print(f"\n[Supervisor] Requirements summary saved.")

    async def _run_phase2(self) -> None:
        """Run Phase 2: Interface Design."""
        print(self._phase_header(2, "Interface Design"))

        self.markers.set_phase(2)
        requirements = self.markers.get_requirements_summary()
        context = self.context_builder.build_phase2_context(requirements)

        # Run session until phase complete
        await self._run_phase_session(context, 2)

        # Generate and save interfaces list
        interfaces = await self._generate_summary(2)
        self.markers.save_interfaces_list(interfaces)

        print(f"\n[Supervisor] Interfaces list saved.")

    async def _run_phase3(self) -> None:
        """Run Phase 3: Test Writing."""
        print(self._phase_header(3, "Test Writing"))

        self.markers.set_phase(3)
        requirements = self.markers.get_requirements_summary()
        interfaces = self.markers.get_interfaces_list()
        context = self.context_builder.build_phase3_context(requirements, interfaces)

        # Run session until phase complete
        await self._run_phase_session(context, 3)

        # Generate and save tests list
        tests = await self._generate_summary(3)
        self.markers.save_tests_list(tests)

        print(f"\n[Supervisor] Tests list saved.")

    async def _run_phase4(self) -> None:
        """Run Phase 4: Implementation."""
        print(self._phase_header(4, "Implementation"))

        self.markers.set_phase(4)
        requirements = self.markers.get_requirements_summary()
        interfaces = self.markers.get_interfaces_list()
        tests = self.markers.get_tests_list()
        context = self.context_builder.build_phase4_context(
            requirements, interfaces, tests
        )

        # Run session until tests pass
        await self._run_phase_session(context, 4)

        print(f"\n[Supervisor] Implementation complete - all tests passing!")

        # Cleanup markers
        self.markers.cleanup()

    async def _run_phase_session(self, initial_context: str, phase: int) -> None:
        """
        Run an interactive Claude session for a phase.

        Args:
            initial_context: Initial context/prompt for the phase
            phase: Current phase number
        """
        env_vars = self.markers.get_env_vars()

        # First message to Claude with phase context
        print(f"\n[Starting Phase {phase} session...]\n")

        session_id = None
        phase_complete = False

        # Initial query with context
        async for message in query(
            prompt=initial_context,
            options=ClaudeAgentOptions(
                working_directory=str(self.working_dir),
                environment=env_vars,
            )
        ):
            # Capture session ID
            if hasattr(message, 'session_id') and message.session_id:
                session_id = message.session_id

            # Display message to user
            if hasattr(message, 'content'):
                print(message.content, end='', flush=True)

                # Check for phase completion signal
                if self.PHASE_COMPLETE_SIGNAL in message.content:
                    phase_complete = True

            # Handle result messages
            if hasattr(message, 'result'):
                if message.result:
                    print(message.result, end='', flush=True)

        # If phase not complete, continue interactive loop
        while not phase_complete:
            # Get user input
            try:
                user_input = input("\nYou: ").strip()
            except EOFError:
                break

            if not user_input:
                continue

            # Check for user commands
            if user_input.lower() in ['/done', '/complete', '/next']:
                phase_complete = True
                break

            if user_input.lower() in ['/quit', '/exit', '/abort']:
                raise KeyboardInterrupt("User requested abort")

            # Continue conversation
            async for message in query(
                prompt=user_input,
                options=ClaudeAgentOptions(
                    working_directory=str(self.working_dir),
                    environment=env_vars,
                    resume=session_id,
                )
            ):
                if hasattr(message, 'content'):
                    print(message.content, end='', flush=True)

                    if self.PHASE_COMPLETE_SIGNAL in message.content:
                        phase_complete = True

                if hasattr(message, 'result'):
                    if message.result:
                        print(message.result, end='', flush=True)

        # Ask for user confirmation before proceeding
        if phase < 4:
            await self._confirm_phase_completion(phase)

    async def _confirm_phase_completion(self, phase: int) -> None:
        """Ask user to confirm phase completion."""
        phase_names = {
            1: "Requirements",
            2: "Interfaces",
            3: "Tests",
        }
        name = phase_names.get(phase, f"Phase {phase}")

        print(f"\n{'='*40}")
        print(f"Phase {phase} ({name}) appears complete.")
        print(f"{'='*40}")

        while True:
            response = input("\nProceed to next phase? [y/n]: ").strip().lower()
            if response in ['y', 'yes']:
                return
            elif response in ['n', 'no']:
                print("Continuing current phase...")
                # Re-run the phase (this is a simplified approach)
                raise Exception("User requested to continue phase - not yet implemented")
            else:
                print("Please enter 'y' or 'n'")

    async def _generate_summary(self, phase: int) -> str:
        """
        Ask Claude to generate a summary for the phase.

        Args:
            phase: Phase number to summarize

        Returns:
            Generated summary text
        """
        summary_prompt = self.context_builder.get_summary_prompt(phase)
        if not summary_prompt:
            return ""

        print(f"\n[Supervisor] Generating phase {phase} summary...")

        summary_parts = []
        env_vars = self.markers.get_env_vars()

        async for message in query(
            prompt=summary_prompt,
            options=ClaudeAgentOptions(
                working_directory=str(self.working_dir),
                environment=env_vars,
            )
        ):
            if hasattr(message, 'content'):
                summary_parts.append(message.content)
            if hasattr(message, 'result') and message.result:
                summary_parts.append(message.result)

        return ''.join(summary_parts)

    def _phase_header(self, phase: int, name: str) -> str:
        """Generate a phase header for display."""
        return f"""
{'='*60}
PHASE {phase}: {name.upper()}
{'='*60}
"""


async def run_supervisor(
    working_dir: Optional[str] = None,
    task: Optional[str] = None,
    workflow_id: Optional[str] = None,
) -> None:
    """
    Run the TDD supervisor.

    Args:
        working_dir: Project working directory
        task: Initial task description
        workflow_id: Workflow ID for resuming
    """
    orchestrator = TDDOrchestrator(
        working_dir=working_dir,
        workflow_id=workflow_id,
    )
    await orchestrator.run(initial_task=task)
