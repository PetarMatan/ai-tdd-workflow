#!/bin/bash
set -e

# Cleanup Hook - SessionEnd
# Removes TDD marker files to ensure fresh state for next session
# Version: 1.0.0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/log.sh"
source "$SCRIPT_DIR/lib/markers.sh"

# Parse hook input
input=$(cat)
eval "$(echo "$input" | python3 "$SCRIPT_DIR/lib/hook_io.py" parse)"
hook_event="$HOOK_EVENT_NAME"
session_id="$HOOK_SESSION_ID"

if [[ "$hook_event" == "SessionEnd" ]]; then
    log_session "Session ending - cleaning up TDD markers" "$session_id"

    # Clean up TDD workflow markers for this session
    cleanup_session_markers "$session_id"

    log_session "TDD markers cleanup complete" "$session_id"
fi

exit 0
