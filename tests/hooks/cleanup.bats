#!/usr/bin/env bats
# Hook tests for cleanup-markers.sh

load '../test_helper'

setup() {
    setup_test_environment

    export TDD_INSTALL_DIR="$PROJECT_ROOT"
}

teardown() {
    teardown_test_environment
}

run_cleanup() {
    local input="$1"
    echo "$input" | bash "$HOOKS_DIR/cleanup-markers.sh"
}

# =============================================================================
# SessionEnd Cleanup Tests
# =============================================================================

@test "cleans up all TDD markers on SessionEnd" {
    # Create all markers
    create_marker "tdd-mode"
    set_phase 3
    create_marker "tdd-requirements-confirmed"
    create_marker "tdd-interfaces-designed"
    create_marker "tdd-tests-approved"
    create_marker "tdd-tests-passing"

    # Verify they exist
    marker_exists "tdd-mode"
    marker_exists "tdd-phase"
    marker_exists "tdd-requirements-confirmed"
    marker_exists "tdd-interfaces-designed"
    marker_exists "tdd-tests-approved"
    marker_exists "tdd-tests-passing"

    # Run cleanup with SessionEnd event
    local input='{"hook_event_name": "SessionEnd", "session_id": "test-session"}'

    run run_cleanup "$input"
    [ "$status" -eq 0 ]

    # Verify all markers are gone
    ! marker_exists "tdd-mode"
    ! marker_exists "tdd-phase"
    ! marker_exists "tdd-requirements-confirmed"
    ! marker_exists "tdd-interfaces-designed"
    ! marker_exists "tdd-tests-approved"
    ! marker_exists "tdd-tests-passing"
}

@test "does nothing for non-SessionEnd events" {
    create_marker "tdd-mode"
    set_phase 2

    local input='{"hook_event_name": "SomeOtherEvent", "session_id": "test-session"}'

    run run_cleanup "$input"
    [ "$status" -eq 0 ]

    # Markers should still exist
    marker_exists "tdd-mode"
    marker_exists "tdd-phase"
}

@test "handles missing markers gracefully" {
    # Don't create any markers

    local input='{"hook_event_name": "SessionEnd", "session_id": "test-session"}'

    run run_cleanup "$input"
    [ "$status" -eq 0 ]
}

@test "handles partial markers" {
    # Create only some markers
    create_marker "tdd-mode"
    create_marker "tdd-requirements-confirmed"
    # Don't create others

    local input='{"hook_event_name": "SessionEnd", "session_id": "test-session"}'

    run run_cleanup "$input"
    [ "$status" -eq 0 ]

    # All should be gone
    ! marker_exists "tdd-mode"
    ! marker_exists "tdd-requirements-confirmed"
}
