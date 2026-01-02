#!/usr/bin/env bats
# Unit tests for lib/log.sh

load '../test_helper'

setup() {
    setup_test_environment

    # Source the log library
    export TDD_INSTALL_DIR="$TEST_TMP"
    export TDD_LOG_DIR="$TEST_TMP/logs"
    export TDD_SESSION_LOG_DIR="$TEST_TMP/logs/sessions"
    mkdir -p "$TDD_LOG_DIR" "$TDD_SESSION_LOG_DIR"

    source "$HOOKS_DIR/lib/log.sh"
}

teardown() {
    teardown_test_environment
}

# =============================================================================
# get_timestamp tests
# =============================================================================

@test "get_timestamp returns valid format" {
    run get_timestamp
    [ "$status" -eq 0 ]
    # Should match YYYY-MM-DD HH:MM:SS format
    [[ "$output" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2}:[0-9]{2}$ ]]
}

# =============================================================================
# get_log_date tests
# =============================================================================

@test "get_log_date returns valid date format" {
    run get_log_date
    [ "$status" -eq 0 ]
    # Should match YYYY-MM-DD format
    [[ "$output" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]
}

# =============================================================================
# log_event tests
# =============================================================================

@test "log_event writes to session log" {
    log_event "TEST" "Test message" "test-session-123"

    local log_date=$(get_log_date)
    local session_log="$TDD_SESSION_LOG_DIR/${log_date}-test-session-123.log"

    [ -f "$session_log" ]
    grep -q "\[TEST\] Test message" "$session_log"
}

@test "log_event writes to daily log" {
    log_event "TEST" "Daily log test" "test-session-456"

    local log_date=$(get_log_date)
    local daily_log="$TDD_LOG_DIR/${log_date}.log"

    [ -f "$daily_log" ]
    grep -q "\[test-session-456\]" "$daily_log"
    grep -q "\[TEST\] Daily log test" "$daily_log"
}

@test "log_event creates current.log symlink" {
    log_event "TEST" "Symlink test" "test-session-789"

    [ -L "$TDD_LOG_DIR/current.log" ]
}

# =============================================================================
# log_tdd tests
# =============================================================================

@test "log_tdd logs with TDD category" {
    log_tdd "Phase transition" "tdd-session"

    local log_date=$(get_log_date)
    local session_log="$TDD_SESSION_LOG_DIR/${log_date}-tdd-session.log"

    [ -f "$session_log" ]
    grep -q "\[TDD\] Phase transition" "$session_log"
}

# =============================================================================
# log_build tests
# =============================================================================

@test "log_build logs success with details" {
    log_build "SUCCESS" "Compiled Main.kt" "build-session"

    local log_date=$(get_log_date)
    local session_log="$TDD_SESSION_LOG_DIR/${log_date}-build-session.log"

    [ -f "$session_log" ]
    grep -q "\[BUILD\] SUCCESS - Compiled Main.kt" "$session_log"
}

@test "log_build logs failure" {
    log_build "FAILED" "Compilation errors" "build-session-2"

    local log_date=$(get_log_date)
    local session_log="$TDD_SESSION_LOG_DIR/${log_date}-build-session-2.log"

    [ -f "$session_log" ]
    grep -q "\[BUILD\] FAILED - Compilation errors" "$session_log"
}

# =============================================================================
# log_hook tests
# =============================================================================

@test "log_hook logs hook events" {
    log_hook "phase-guard" "STARTED" "checking file" "hook-session"

    local log_date=$(get_log_date)
    local session_log="$TDD_SESSION_LOG_DIR/${log_date}-hook-session.log"

    [ -f "$session_log" ]
    grep -q "\[HOOK:phase-guard\] STARTED - checking file" "$session_log"
}

# =============================================================================
# log_error tests
# =============================================================================

@test "log_error logs with ERROR category" {
    log_error "Something went wrong" "error-session"

    local log_date=$(get_log_date)
    local session_log="$TDD_SESSION_LOG_DIR/${log_date}-error-session.log"

    [ -f "$session_log" ]
    grep -q "\[ERROR\] Something went wrong" "$session_log"
}

# =============================================================================
# log_session tests
# =============================================================================

@test "log_session logs session events" {
    log_session "Session started" "session-test"

    local log_date=$(get_log_date)
    local session_log="$TDD_SESSION_LOG_DIR/${log_date}-session-test.log"

    [ -f "$session_log" ]
    grep -q "\[SESSION\] Session started" "$session_log"
}

# =============================================================================
# view_logs tests
# =============================================================================

@test "view_logs returns log content" {
    log_event "TEST" "Line 1" "view-session"
    log_event "TEST" "Line 2" "view-session"
    log_event "TEST" "Line 3" "view-session"

    run view_logs 2
    [ "$status" -eq 0 ]
    [[ "$output" == *"Line 2"* ]] || [[ "$output" == *"Line 3"* ]]
}

@test "view_logs handles missing log gracefully" {
    rm -f "$TDD_LOG_DIR/current.log"

    run view_logs
    [ "$status" -eq 0 ]
    [[ "$output" == *"No current session log found"* ]]
}
