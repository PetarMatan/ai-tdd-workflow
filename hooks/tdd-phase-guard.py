#!/usr/bin/env python3
"""
TDD Phase Guard - PreToolUse Hook

Blocks file edits that don't match the current TDD phase.
"""

import json
import os
import sys

# Add lib directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from hook_io import HookInput
from markers import MarkerManager
from tdd_logging import TDDLogger
from tdd_config import TDDConfig
from formatters import (
    format_phase_guard_phase1_block,
    format_phase_guard_phase2_block,
    format_phase_guard_phase3_block,
)


def block_response(reason: str, context: str) -> None:
    """Output a block response with context."""
    output = {
        "decision": "block",
        "reason": reason,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": context
        }
    }
    print(json.dumps(output, indent=2))


def main():
    # Parse hook input
    hook = HookInput.from_stdin()

    # Initialize components
    markers = MarkerManager(hook.session_id)
    logger = TDDLogger(hook.session_id)

    # Check if TDD mode is active
    if not markers.is_tdd_active():
        return

    # Only guard Write and Edit tools
    if hook.tool_name not in ("Write", "Edit"):
        return

    # If no file path, allow
    if not hook.file_path:
        return

    # Get current phase
    current_phase = markers.get_phase()

    # Initialize config for pattern matching
    config = TDDConfig(hook.cwd)
    profile_name = config.get_profile_name()

    # Check file type
    is_main = config.is_main_source(hook.file_path)
    is_test = config.is_test_source(hook.file_path)
    is_config = config.is_config_file(hook.file_path)

    # Phase-specific rules
    if current_phase == 1:
        # Phase 1: Requirements - Block all source file edits
        if is_main or is_test:
            logger.log_tdd(f"Phase 1: Blocked edit to {hook.file_path} - requirements gathering")
            block_response(
                "TDD Phase 1: Cannot edit source files during requirements gathering",
                format_phase_guard_phase1_block(hook.file_path, profile_name)
            )
            return

    elif current_phase == 2:
        # Phase 2: Interfaces - Allow main source only (config files also ok)
        if is_test:
            logger.log_tdd(f"Phase 2: Blocked edit to {hook.file_path} - no tests during interface design")
            block_response(
                "TDD Phase 2: Cannot write tests during interface design",
                format_phase_guard_phase2_block(hook.file_path, profile_name)
            )
            return

    elif current_phase == 3:
        # Phase 3: Tests - Allow test source only
        # Note: A test file might match both main and test patterns
        # so we only block if it's main AND NOT test AND NOT config
        if is_main and not is_test and not is_config:
            logger.log_tdd(f"Phase 3: Blocked edit to {hook.file_path} - no implementation during test writing")
            block_response(
                "TDD Phase 3: Cannot edit implementation during test writing",
                format_phase_guard_phase3_block(hook.file_path, profile_name)
            )
            return

    # Phase 4 or allowed operation - no output means approve


if __name__ == '__main__':
    main()
