#!/usr/bin/env bats
# Integration tests for full TDD workflow

load '../test_helper'

setup() {
    setup_test_environment

    export PROJECT_DIR="$TEST_TMP/project"
    create_mock_project "kotlin-maven" "$PROJECT_DIR"

    export TDD_INSTALL_DIR="$PROJECT_ROOT"
    export TDD_CONFIG_FILE="$PROJECT_ROOT/config/tdd-config.json"

    set_mock_compile_result 0 "BUILD SUCCESS"
    set_mock_test_result 0 "Tests run: 10, Failures: 0"
}

teardown() {
    teardown_test_environment
}

# Helper to simulate the full workflow
run_orchestrator() {
    local input="$1"
    echo "$input" | bash "$HOOKS_DIR/tdd-orchestrator.sh"
}

run_phase_guard() {
    local input="$1"
    echo "$input" | bash "$HOOKS_DIR/tdd-phase-guard.sh"
}

# =============================================================================
# Full Workflow Integration Tests
# =============================================================================

@test "complete TDD workflow from phase 1 to completion" {
    # === PHASE 1: Requirements ===
    create_marker "tdd-mode"
    set_phase 1

    # Try to edit source - should be blocked
    local write_input=$(generate_hook_input "Write" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")
    run run_phase_guard "$write_input"
    assert_decision_block

    # Orchestrator should block without requirements marker
    local stop_input=$(generate_stop_hook_input "$PROJECT_DIR")
    run run_orchestrator "$stop_input"
    assert_decision_block
    assert_output_contains "Requirements"

    # Simulate user confirming requirements
    create_marker "tdd-requirements-confirmed"

    # Orchestrator should advance to phase 2
    run run_orchestrator "$stop_input"
    [ "$(get_phase)" = "2" ]

    # === PHASE 2: Interfaces ===

    # Should now allow main source edits
    run run_phase_guard "$write_input"
    assert_decision_allow

    # But block test edits
    local test_input=$(generate_hook_input "Write" "$PROJECT_DIR/src/test/kotlin/ServiceTest.kt" "$PROJECT_DIR")
    run run_phase_guard "$test_input"
    assert_decision_block

    # Orchestrator should block without interface marker
    run run_orchestrator "$stop_input"
    assert_decision_block
    assert_output_contains "approval"

    # Simulate user approving interfaces
    create_marker "tdd-interfaces-designed"

    # Orchestrator should advance to phase 3
    run run_orchestrator "$stop_input"
    [ "$(get_phase)" = "3" ]

    # === PHASE 3: Tests ===

    # Should block main source edits
    run run_phase_guard "$write_input"
    assert_decision_block

    # But allow test edits
    run run_phase_guard "$test_input"
    assert_decision_allow

    # Orchestrator should block without tests marker
    run run_orchestrator "$stop_input"
    assert_decision_block

    # Simulate user approving tests
    create_marker "tdd-tests-approved"

    # Set tests to fail initially so phase 4 doesn't complete immediately
    set_mock_test_result 1 "Tests failed: 5 of 10"

    # Orchestrator should advance to phase 4
    run run_orchestrator "$stop_input"
    [ "$(get_phase)" = "4" ]

    # === PHASE 4: Implementation ===

    # Should allow all edits
    run run_phase_guard "$write_input"
    assert_decision_allow

    run run_phase_guard "$test_input"
    assert_decision_allow

    # Now set tests to pass
    set_mock_test_result 0 "Tests run: 10, Failures: 0"

    # With passing tests, orchestrator should complete and cleanup
    run run_orchestrator "$stop_input"
    [ "$status" -eq 0 ]

    # Verify completion
    marker_exists "tdd-tests-passing"
    ! marker_exists "tdd-mode"
}

@test "workflow handles compile failures in phase 2" {
    create_marker "tdd-mode"
    set_phase 2

    set_mock_compile_result 1 "[ERROR] Cannot find symbol"

    local stop_input=$(generate_stop_hook_input "$PROJECT_DIR")
    run run_orchestrator "$stop_input"

    assert_decision_block
    assert_output_contains "Compilation FAILED"
    assert_output_contains "Cannot find symbol"

    # Should still be in phase 2
    [ "$(get_phase)" = "2" ]
}

@test "workflow handles test failures in phase 4" {
    create_marker "tdd-mode"
    set_phase 4

    set_mock_compile_result 0 "BUILD SUCCESS"
    set_mock_test_result 1 "Tests run: 5, Failures: 2"

    local stop_input=$(generate_stop_hook_input "$PROJECT_DIR")
    run run_orchestrator "$stop_input"

    assert_decision_block
    assert_output_contains "Tests FAILED"

    # Should still be in phase 4 (loop until pass)
    [ "$(get_phase)" = "4" ]
    marker_exists "tdd-mode"
}

# =============================================================================
# TypeScript Workflow Tests
# =============================================================================

@test "complete workflow with TypeScript project" {
    # Create TypeScript project
    local ts_project="$TEST_TMP/ts-project"
    create_mock_project "typescript-npm" "$ts_project"

    create_marker "tdd-mode"
    set_phase 1

    # Verify TypeScript file blocking works
    local ts_write=$(generate_hook_input "Write" "$ts_project/src/service.ts" "$ts_project")
    run run_phase_guard "$ts_write"
    assert_decision_block

    # Advance through phases
    create_marker "tdd-requirements-confirmed"
    local stop_input=$(generate_stop_hook_input "$ts_project")
    run run_orchestrator "$stop_input"
    [ "$(get_phase)" = "2" ]

    # Now TypeScript source should be allowed
    run run_phase_guard "$ts_write"
    assert_decision_allow

    # Test file should be blocked in phase 2
    local ts_test=$(generate_hook_input "Write" "$ts_project/src/service.test.ts" "$ts_project")
    run run_phase_guard "$ts_test"
    assert_decision_block
}

# =============================================================================
# Reset Workflow Tests
# =============================================================================

@test "reset clears all state and allows restart" {
    # Set up mid-workflow state
    create_marker "tdd-mode"
    set_phase 3
    create_marker "tdd-requirements-confirmed"
    create_marker "tdd-interfaces-designed"

    # Simulate reset by removing markers
    rm -f "$TEST_MARKERS_DIR/tdd-mode"
    rm -f "$TEST_MARKERS_DIR/tdd-phase"
    rm -f "$TEST_MARKERS_DIR/tdd-requirements-confirmed"
    rm -f "$TEST_MARKERS_DIR/tdd-interfaces-designed"

    # Orchestrator should do nothing now
    local stop_input=$(generate_stop_hook_input "$PROJECT_DIR")
    run run_orchestrator "$stop_input"
    [ "$status" -eq 0 ]
    [ -z "$output" ]

    # Phase guard should allow everything
    local write_input=$(generate_hook_input "Write" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")
    run run_phase_guard "$write_input"
    [ -z "$output" ]
}

# =============================================================================
# Session End Integration Tests
# =============================================================================

@test "session end cleans up mid-workflow state" {
    create_marker "tdd-mode"
    set_phase 2
    create_marker "tdd-requirements-confirmed"

    # Run session end cleanup (use same session_id as TEST_SESSION_ID)
    local cleanup_input='{"hook_event_name": "SessionEnd", "session_id": "test-session"}'
    echo "$cleanup_input" | bash "$HOOKS_DIR/cleanup-markers.sh"

    # All state should be gone
    ! marker_exists "tdd-mode"
    ! marker_exists "tdd-phase"
    ! marker_exists "tdd-requirements-confirmed"

    # New session should start fresh
    local stop_input=$(generate_stop_hook_input "$PROJECT_DIR")
    run run_orchestrator "$stop_input"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# =============================================================================
# Error Recovery Tests
# =============================================================================

@test "recovers from missing phase file" {
    create_marker "tdd-mode"
    # Don't create phase file

    local stop_input=$(generate_stop_hook_input "$PROJECT_DIR")
    run run_orchestrator "$stop_input"

    # Should initialize to phase 1 (session-scoped)
    [ -f "$TEST_MARKERS_DIR/tdd-phase" ]
    assert_decision_block
    assert_output_contains "Phase 1"
}

@test "handles corrupt phase number" {
    create_marker "tdd-mode"
    echo "invalid" > "$TEST_MARKERS_DIR/tdd-phase"

    local stop_input=$(generate_stop_hook_input "$PROJECT_DIR")
    run run_orchestrator "$stop_input"

    # Should reset to phase 1
    [ "$(get_phase)" = "1" ]
}
