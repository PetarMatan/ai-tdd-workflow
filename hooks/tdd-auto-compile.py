#!/usr/bin/env python3
"""
TDD Auto-Compile Hook - PostToolUse

Runs compilation after source file changes (outside of Phase 4 TDD).
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
from formatters import format_compile_error


def approve_with_message(reason: str, context: str) -> None:
    """Output an approve response with additional context message."""
    output = {
        "decision": "approve",
        "reason": reason,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
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

    # Only process Write|Edit operations
    if hook.tool_name not in ("Write", "Edit"):
        return

    # Change to project directory
    if not hook.cwd or not os.path.isdir(hook.cwd):
        return

    os.chdir(hook.cwd)

    # Initialize config
    config = TDDConfig(hook.cwd)

    # Check if file is a source file
    is_source = config.is_main_source(hook.file_path) or config.is_test_source(hook.file_path)
    if not is_source:
        return

    # Skip if TDD Phase 4 is active (tdd-auto-test handles compile+test)
    if markers.is_tdd_active():
        tdd_phase = markers.get_phase()
        if tdd_phase == 4:
            return

    # Get profile info and compile command
    profile_name = config.get_profile_name()
    compile_cmd = config.get_command("compile")

    if not compile_cmd:
        return

    print(f">>> Auto-compiling ({profile_name}) after source file change...", file=sys.stderr)

    # Run compilation
    try:
        result = subprocess.run(
            compile_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )
        compile_output = result.stdout + result.stderr
        compile_exit_code = result.returncode
    except subprocess.TimeoutExpired:
        compile_output = "Compilation timed out after 120 seconds"
        compile_exit_code = 1
    except Exception as e:
        compile_output = f"Compilation error: {e}"
        compile_exit_code = 1

    if compile_exit_code == 0:
        print(">>> Compilation successful", file=sys.stderr)
        logger.log_build("SUCCESS", f"Compiled after {hook.file_path} change")
        return
    else:
        print(">>> Compilation failed - fix errors", file=sys.stderr)
        logger.log_build("FAILED", f"Compilation errors in {hook.file_path}")

        context = format_compile_error(compile_output, hook.file_path, profile_name)

        approve_with_message(
            f"Compilation failed ({profile_name}). Fix errors immediately.",
            context
        )


if __name__ == '__main__':
    main()
