#!/usr/bin/env python3
"""
TDD Workflow Orchestrator - Stop Hook

Enforces TDD phase progression: Requirements -> Interfaces -> Tests -> Implementation
"""

import json
import os
import subprocess
import sys

# Add lib directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from hook_io import HookInput
from markers import MarkerManager
from tdd_logging import TDDLogger
from tdd_config import TDDConfig
from tdd_agents import AgentLoader
from formatters import (
    format_phase1_block,
    format_phase2_compile_error,
    format_phase2_awaiting_approval,
    format_phase3_compile_error,
    format_phase3_awaiting_approval,
    format_phase4_orchestrator_compile_error,
    format_phase4_orchestrator_test_failure,
)


def block_response(reason: str, agent_content: str = "") -> None:
    """Output a block response."""
    full_reason = reason + agent_content if agent_content else reason
    output = {"decision": "block", "reason": full_reason}
    print(json.dumps(output, indent=2))


def run_command(cmd: str, timeout: int = 120) -> tuple:
    """Run a shell command and return (exit_code, output)."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return 1, f"Command timed out after {timeout} seconds"
    except Exception as e:
        return 1, f"Command error: {e}"


def main():
    # Parse hook input
    hook = HookInput.from_stdin()

    # Initialize components
    markers = MarkerManager(hook.session_id)
    logger = TDDLogger(hook.session_id)
    agents = AgentLoader()

    # Prevent infinite loops
    if hook.stop_hook_active:
        return

    # Check if TDD mode is active
    if not markers.is_tdd_active():
        return

    # In supervisor mode, skip phase transition logic
    # Supervisor handles phase transitions; hooks only load agents
    if markers.is_supervisor_mode():
        logger.log_tdd("Supervisor mode: skipping orchestrator phase transitions")
        current_phase = markers.get_phase()
        phase_agents = agents.load_phase_agents(current_phase, logger)
        if phase_agents:
            # Just provide agents, don't block or manage transitions
            print(json.dumps({
                "decision": "approve",
                "hookSpecificOutput": {
                    "hookEventName": "Stop",
                    "additionalContext": phase_agents
                }
            }, indent=2))
        return

    # Initialize phase if not set
    current_phase = markers.get_phase()
    if not markers.tdd_phase.exists():
        markers.set_phase(1)
        current_phase = 1
        # Clear any stale tests_passing from previous TDD round
        markers.remove_marker(markers.tests_passing)

    # Change to project directory
    if not hook.cwd or not os.path.isdir(hook.cwd):
        return

    os.chdir(hook.cwd)

    # Initialize config
    config = TDDConfig(hook.cwd)
    profile_name = config.get_profile_name()

    # Get commands
    compile_cmd = config.get_command("compile")
    test_compile_cmd = config.get_command("testCompile")
    test_cmd = config.get_command("test")

    marker_dir = markers.get_marker_dir_display()

    # Phase 1: Requirements
    if current_phase == 1:
        if markers.requirements_confirmed.exists():
            markers.set_phase(2)
            current_phase = 2
            logger.log_tdd("Phase 1 -> 2: Requirements confirmed, advancing to Interfaces")
            print(">>> TDD: Phase 1 complete, advancing to Phase 2 (Interfaces)", file=sys.stderr)
        else:
            logger.log_tdd("Phase 1: Blocked - requirements not confirmed")
            phase_agents = agents.load_phase_agents(1, logger)
            reason = format_phase1_block(marker_dir)
            block_response(reason, phase_agents)
            return

    # Phase 2: Interfaces
    if current_phase == 2:
        # Check if interfaces compile
        if compile_cmd:
            compile_exit_code, compile_output = run_command(compile_cmd)
            if compile_exit_code != 0:
                phase_agents = agents.load_phase_agents(2, logger)
                reason = format_phase2_compile_error(compile_output, profile_name, compile_cmd)
                block_response(reason, phase_agents)
                return

        # Code compiles, check for marker
        if markers.interfaces_designed.exists():
            markers.set_phase(3)
            current_phase = 3
            logger.log_tdd("Phase 2 -> 3: Interfaces approved, advancing to Tests")
            print(">>> TDD: Phase 2 complete, advancing to Phase 3 (Tests)", file=sys.stderr)
        else:
            phase_agents = agents.load_phase_agents(2, logger)
            logger.log_tdd("Phase 2: Blocked - awaiting interface approval")
            reason = format_phase2_awaiting_approval(marker_dir, profile_name)
            block_response(reason, phase_agents)
            return

    # Phase 3: Tests
    if current_phase == 3:
        # Check if tests compile
        test_compile = test_compile_cmd or compile_cmd
        if test_compile:
            compile_exit_code, compile_output = run_command(test_compile)
            if compile_exit_code != 0:
                phase_agents = agents.load_phase_agents(3, logger)
                reason = format_phase3_compile_error(compile_output, profile_name, test_compile)
                block_response(reason, phase_agents)
                return

        if markers.tests_approved.exists():
            markers.set_phase(4)
            current_phase = 4
            logger.log_tdd("Phase 3 -> 4: Tests approved, advancing to Implementation")
            print(">>> TDD: Phase 3 complete, advancing to Phase 4 (Implementation)", file=sys.stderr)
        else:
            phase_agents = agents.load_phase_agents(3, logger)
            logger.log_tdd("Phase 3: Blocked - awaiting test approval")
            reason = format_phase3_awaiting_approval(marker_dir, profile_name)
            block_response(reason, phase_agents)
            return

    # Phase 4: Implementation
    if current_phase == 4:
        # Check if compile passes
        if compile_cmd:
            compile_exit_code, compile_output = run_command(compile_cmd)
            if compile_exit_code != 0:
                phase_agents = agents.load_phase_agents(4, logger)
                reason = format_phase4_orchestrator_compile_error(compile_output, profile_name)
                block_response(reason, phase_agents)
                return

        # Compile passes, check if tests pass
        if test_cmd:
            test_exit_code, test_output = run_command(test_cmd, timeout=300)
            if test_exit_code != 0:
                phase_agents = agents.load_phase_agents(4, logger)
                reason = format_phase4_orchestrator_test_failure(test_output, profile_name)
                block_response(reason, phase_agents)
                return

        # Both compile and tests pass - TDD complete!
        logger.log_tdd("Phase 4 COMPLETE: All tests passing - TDD workflow finished")
        print(">>> TDD: Phase 4 complete! All tests passing.", file=sys.stderr)

        # Create passing marker
        markers.create_marker(markers.tests_passing)

        # Clean up TDD markers
        markers.cleanup_all_markers()
        return

    # Unknown phase, reset to 1
    markers.set_phase(1)


if __name__ == '__main__':
    main()
