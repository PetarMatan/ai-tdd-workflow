#!/usr/bin/env bats
# Hook tests for tdd-orchestrator.sh

load '../test_helper'

setup() {
    setup_test_environment

    # Create a mock kotlin-maven project
    export PROJECT_DIR="$TEST_TMP/project"
    create_mock_project "kotlin-maven" "$PROJECT_DIR"

    # Set up the hook environment
    export TDD_INSTALL_DIR="$PROJECT_ROOT"
    export TDD_CONFIG_FILE="$PROJECT_ROOT/config/tdd-config.json"

    # Default to successful compile/test
    set_mock_compile_result 0 "BUILD SUCCESS"
    set_mock_test_result 0 "Tests run: 10, Failures: 0"
}

teardown() {
    teardown_test_environment
}

# Helper to run the orchestrator hook
run_orchestrator() {
    local input="$1"
    echo "$input" | bash "$HOOKS_DIR/tdd-orchestrator.sh"
}

# =============================================================================
# TDD Mode Inactive Tests
# =============================================================================

@test "exits silently when TDD mode is inactive" {
    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "exits when stop_hook_active is true (prevent loops)" {
    create_marker "tdd-mode"
    set_phase 1

    local input='{"cwd": "/project", "stop_hook_active": true}'

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# =============================================================================
# Phase 1 Tests (Requirements)
# =============================================================================

@test "phase 1 blocks without requirements marker" {
    create_marker "tdd-mode"
    set_phase 1

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]
    assert_decision_block
    assert_output_contains "Phase 1"
    assert_output_contains "Requirements"
}

@test "phase 1 advances to phase 2 with marker" {
    create_marker "tdd-mode"
    set_phase 1
    create_marker "tdd-requirements-confirmed"

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]

    # Should now be in phase 2
    [ "$(get_phase)" = "2" ]
}

# =============================================================================
# Phase 2 Tests (Interfaces)
# =============================================================================

@test "phase 2 blocks when compile fails" {
    create_marker "tdd-mode"
    set_phase 2

    set_mock_compile_result 1 "[ERROR] Compilation failed"

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]
    assert_decision_block
    assert_output_contains "Compilation FAILED"
}

@test "phase 2 blocks without interface marker when compile passes" {
    create_marker "tdd-mode"
    set_phase 2

    set_mock_compile_result 0 "BUILD SUCCESS"

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]
    assert_decision_block
    assert_output_contains "Compilation PASSED"
    assert_output_contains "approval"
}

@test "phase 2 advances to phase 3 with marker and passing compile" {
    create_marker "tdd-mode"
    set_phase 2
    create_marker "tdd-interfaces-designed"

    set_mock_compile_result 0 "BUILD SUCCESS"

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]

    [ "$(get_phase)" = "3" ]
}

# =============================================================================
# Phase 3 Tests (Tests)
# =============================================================================

@test "phase 3 blocks when test compile fails" {
    create_marker "tdd-mode"
    set_phase 3

    set_mock_compile_result 1 "[ERROR] Test compilation failed"

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]
    assert_decision_block
    assert_output_contains "Test Compilation FAILED"
}

@test "phase 3 blocks without tests marker" {
    create_marker "tdd-mode"
    set_phase 3

    set_mock_compile_result 0 "BUILD SUCCESS"

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]
    assert_decision_block
    assert_output_contains "Phase 3"
}

@test "phase 3 advances to phase 4 with marker and passing test compile" {
    create_marker "tdd-mode"
    set_phase 3
    create_marker "tdd-tests-approved"

    # Set compile to pass but tests to fail, so phase 4 doesn't complete
    set_mock_compile_result 0 "BUILD SUCCESS"
    set_mock_test_result 1 "Tests failed: 1 of 10"

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]

    # Phase should be 4 (tests are failing, so it doesn't complete)
    [ "$(get_phase)" = "4" ]
}

# =============================================================================
# Phase 4 Tests (Implementation)
# =============================================================================

@test "phase 4 blocks when compile fails" {
    create_marker "tdd-mode"
    set_phase 4

    set_mock_compile_result 1 "[ERROR] Compilation failed"

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]
    assert_decision_block
    assert_output_contains "Compilation FAILED"
}

@test "phase 4 blocks when tests fail" {
    create_marker "tdd-mode"
    set_phase 4

    set_mock_compile_result 0 "BUILD SUCCESS"
    set_mock_test_result 1 "Tests run: 10, Failures: 3"

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]
    assert_decision_block
    assert_output_contains "Tests FAILED"
}

@test "phase 4 completes and cleans up when all tests pass" {
    create_marker "tdd-mode"
    set_phase 4
    create_marker "tdd-requirements-confirmed"
    create_marker "tdd-interfaces-designed"
    create_marker "tdd-tests-approved"

    set_mock_compile_result 0 "BUILD SUCCESS"
    set_mock_test_result 0 "Tests run: 10, Failures: 0"

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]

    # Should have created tests-passing marker
    marker_exists "tdd-tests-passing"

    # Should have cleaned up other markers
    ! marker_exists "tdd-mode"
    ! marker_exists "tdd-phase"
    ! marker_exists "tdd-requirements-confirmed"
    ! marker_exists "tdd-interfaces-designed"
    ! marker_exists "tdd-tests-approved"
}

# =============================================================================
# Error Message Quality Tests
# =============================================================================

@test "phase 2 compile error shows actual errors" {
    create_marker "tdd-mode"
    set_phase 2

    set_mock_compile_result 1 "[ERROR] Cannot find symbol: class Foo"

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]
    assert_output_contains "Cannot find symbol"
}

@test "phase 4 test failure shows test output" {
    create_marker "tdd-mode"
    set_phase 4

    set_mock_compile_result 0 "BUILD SUCCESS"
    set_mock_test_result 1 "FAILURE: should calculate total correctly"

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]
    assert_output_contains "should calculate total correctly"
}

# =============================================================================
# Phase Initialization Tests
# =============================================================================

@test "initializes phase to 1 if phase file missing" {
    create_marker "tdd-mode"
    # Don't set phase file

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]

    # Phase file should be created
    [ -f "$HOME/.claude/tmp/tdd-phase" ]
}

@test "resets unknown phase to 1" {
    create_marker "tdd-mode"
    echo "99" > "$HOME/.claude/tmp/tdd-phase"

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"

    [ "$(get_phase)" = "1" ]
}
