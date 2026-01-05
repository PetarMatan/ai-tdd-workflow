#!/usr/bin/env python3
"""
Hook I/O - Input parsing and response generation for Claude Code hooks.

Usage from bash:
    # Parse input
    eval $(python3 hook_io.py parse < input.json)
    echo $HOOK_TOOL_NAME $HOOK_FILE_PATH $HOOK_CWD $HOOK_SESSION_ID

    # Generate block response
    python3 hook_io.py block "Reason message" ["agent content"]

    # Generate approve response (empty output = approve)
    python3 hook_io.py approve
"""

import json
import sys
from typing import Optional


def parse_input() -> None:
    """
    Parse hook input JSON from stdin and output bash variable assignments.

    Outputs bash-eval-safe variable assignments:
        HOOK_TOOL_NAME, HOOK_FILE_PATH, HOOK_CWD, HOOK_SESSION_ID,
        HOOK_STOP_ACTIVE, HOOK_EVENT_TYPE
    """
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        data = {}

    # Extract common fields with safe defaults
    tool_name = data.get('tool_name', '')
    tool_input = data.get('tool_input', {})
    file_path = tool_input.get('file_path', '') if isinstance(tool_input, dict) else ''
    cwd = data.get('cwd', '')
    session_id = data.get('session_id', 'unknown')
    stop_hook_active = str(data.get('stop_hook_active', False))
    event_type = data.get('event_type', '')
    hook_event_name = data.get('hook_event_name', '')

    # Output as bash variable assignments (safe for eval)
    # Using printf-style escaping for safety
    print(f'HOOK_TOOL_NAME="{_escape_bash(tool_name)}"')
    print(f'HOOK_FILE_PATH="{_escape_bash(file_path)}"')
    print(f'HOOK_CWD="{_escape_bash(cwd)}"')
    print(f'HOOK_SESSION_ID="{_escape_bash(session_id)}"')
    print(f'HOOK_STOP_ACTIVE="{stop_hook_active}"')
    print(f'HOOK_EVENT_TYPE="{_escape_bash(event_type)}"')
    print(f'HOOK_EVENT_NAME="{_escape_bash(hook_event_name)}"')


def _escape_bash(s: str) -> str:
    """Escape a string for safe use in bash double quotes."""
    if not s:
        return ''
    # Escape backslashes, double quotes, backticks, and dollar signs
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')


def block_response(reason: str, agent_content: Optional[str] = None) -> None:
    """
    Generate a block response JSON.

    Args:
        reason: The reason message to show the user
        agent_content: Optional additional agent content to append
    """
    full_reason = reason
    if agent_content:
        full_reason = reason + agent_content

    output = {"decision": "block", "reason": full_reason}
    print(json.dumps(output, indent=2))


def approve_response() -> None:
    """Generate an approve response (empty output means approve)."""
    # Empty output = approve in Claude Code hooks
    pass


def approve_with_message(reason: str, hook_event: str, context: str) -> None:
    """
    Generate an approve response with additional context message.
    Used for cases like compile errors where we approve but want to show info.

    Args:
        reason: Short reason for the message
        hook_event: The hook event name (e.g., "PostToolUse")
        context: Detailed context/message to show
    """
    output = {
        "decision": "approve",
        "reason": reason,
        "hookSpecificOutput": {
            "hookEventName": hook_event,
            "additionalContext": context
        }
    }
    print(json.dumps(output, indent=2))


def main():
    if len(sys.argv) < 2:
        print("Usage: hook_io.py <command> [args...]", file=sys.stderr)
        print("Commands: parse, block, approve, approve-message", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == 'parse':
        parse_input()
    elif command == 'block':
        reason = sys.argv[2] if len(sys.argv) > 2 else "Blocked"
        agent_content = sys.argv[3] if len(sys.argv) > 3 else None
        block_response(reason, agent_content)
    elif command == 'approve':
        approve_response()
    elif command == 'approve-message':
        reason = sys.argv[2] if len(sys.argv) > 2 else ""
        hook_event = sys.argv[3] if len(sys.argv) > 3 else "PostToolUse"
        context = sys.argv[4] if len(sys.argv) > 4 else ""
        approve_with_message(reason, hook_event, context)
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
