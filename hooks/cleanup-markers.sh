#!/bin/bash
set -e

# Cleanup Hook - SessionEnd
# Removes TDD marker files to ensure fresh state for next session
# Version: 1.0.0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/log.sh"

input=$(cat)
hook_event=$(echo "$input" | python3 -c "import sys, json; print(json.load(sys.stdin).get('hook_event_name', ''))")
session_id=$(echo "$input" | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_id', 'unknown'))")

if [[ "$hook_event" == "SessionEnd" ]]; then
    log_session "Session ending - cleaning up TDD markers" "$session_id"

    # Clean up TDD workflow markers
    rm -f ~/.claude/tmp/tdd-mode 2>/dev/null || true
    rm -f ~/.claude/tmp/tdd-phase 2>/dev/null || true
    rm -f ~/.claude/tmp/tdd-requirements-confirmed 2>/dev/null || true
    rm -f ~/.claude/tmp/tdd-interfaces-designed 2>/dev/null || true
    rm -f ~/.claude/tmp/tdd-tests-approved 2>/dev/null || true
    rm -f ~/.claude/tmp/tdd-tests-passing 2>/dev/null || true

    log_session "TDD markers cleanup complete" "$session_id"
fi

exit 0
