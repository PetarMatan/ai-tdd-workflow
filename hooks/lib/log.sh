#!/bin/bash
# TDD Workflow - Logging Library
# Source this in any hook: source "$(dirname "$0")/lib/log.sh"

# Determine install directory (handles both installed and development scenarios)
if [[ -n "$TDD_INSTALL_DIR" ]]; then
    TDD_LOG_DIR="$TDD_INSTALL_DIR/logs"
else
    TDD_LOG_DIR="${HOME}/.claude/logs"
fi

TDD_SESSION_LOG_DIR="${TDD_LOG_DIR}/sessions"

# Ensure log directories exist
mkdir -p "$TDD_LOG_DIR" "$TDD_SESSION_LOG_DIR" 2>/dev/null || true

# Get timestamp for log entries
get_timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# Get today's date for log file naming
get_log_date() {
    date '+%Y-%m-%d'
}

# Main logging function
# Usage: log_event "CATEGORY" "message" ["session_id"]
log_event() {
    local category="$1"
    local message="$2"
    local session_id="${3:-${CLAUDE_SESSION_ID:-unknown}}"
    local timestamp
    timestamp=$(get_timestamp)
    local log_date
    log_date=$(get_log_date)

    # Sanitize message: replace newlines with \n to prevent log injection
    local safe_message="${message//$'\n'/\\n}"

    # Format: [timestamp] [CATEGORY] message
    local log_line="[$timestamp] [$category] $safe_message"

    # Write to session-specific log
    local session_log="$TDD_SESSION_LOG_DIR/${log_date}-${session_id}.log"
    echo "$log_line" >> "$session_log" 2>/dev/null || true

    # Also write to daily rolling log
    local daily_log="$TDD_LOG_DIR/${log_date}.log"
    echo "[$session_id] $log_line" >> "$daily_log" 2>/dev/null || true

    # Update current.log symlink
    ln -sf "$session_log" "$TDD_LOG_DIR/current.log" 2>/dev/null || true
}

# TDD-specific logging
log_tdd() {
    local message="$1"
    local session_id="$2"
    log_event "TDD" "$message" "$session_id"
}

# Build/compile logging
log_build() {
    local result="$1"
    local details="$2"
    local session_id="$3"
    log_event "BUILD" "$result${details:+ - $details}" "$session_id"
}

# Hook logging
log_hook() {
    local hook_name="$1"
    local event="$2"
    local details="$3"
    local session_id="$4"
    log_event "HOOK:$hook_name" "$event${details:+ - $details}" "$session_id"
}

# Error logging
log_error() {
    local message="$1"
    local session_id="$2"
    log_event "ERROR" "$message" "$session_id"
}

# Session logging
log_session() {
    local event="$1"
    local session_id="$2"
    log_event "SESSION" "$event" "$session_id"
}

# View recent logs helper
view_logs() {
    local lines="${1:-50}"
    if [[ -f "$TDD_LOG_DIR/current.log" ]]; then
        tail -n "$lines" "$TDD_LOG_DIR/current.log"
    else
        echo "No current session log found"
    fi
}
