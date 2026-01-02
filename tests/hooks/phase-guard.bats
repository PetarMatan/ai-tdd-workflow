#!/usr/bin/env bats
# Hook tests for tdd-phase-guard.sh

load '../test_helper'

setup() {
    setup_test_environment

    # Create a mock kotlin-maven project
    export PROJECT_DIR="$TEST_TMP/project"
    create_mock_project "kotlin-maven" "$PROJECT_DIR"

    # Set up the hook environment
    export TDD_INSTALL_DIR="$PROJECT_ROOT"
    export TDD_CONFIG_FILE="$PROJECT_ROOT/config/tdd-config.json"
}

teardown() {
    teardown_test_environment
}

# Helper to run the phase guard hook
run_phase_guard() {
    local input="$1"
    echo "$input" | bash "$HOOKS_DIR/tdd-phase-guard.sh"
}

# =============================================================================
# TDD Mode Inactive Tests
# =============================================================================

@test "allows all edits when TDD mode is inactive" {
    # No TDD markers created
    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_phase_guard "$input"
    [ "$status" -eq 0 ]
    [ -z "$output" ]  # No output means allowed
}

@test "allows test edits when TDD mode is inactive" {
    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/test/kotlin/ServiceTest.kt" "$PROJECT_DIR")

    run run_phase_guard "$input"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# =============================================================================
# Phase 1 Tests (Requirements)
# =============================================================================

@test "phase 1 blocks main source edits" {
    create_marker "tdd-mode"
    set_phase 1

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_phase_guard "$input"
    [ "$status" -eq 0 ]
    assert_decision_block
    assert_output_contains "Phase 1"
    assert_output_contains "Requirements"
}

@test "phase 1 blocks test source edits" {
    create_marker "tdd-mode"
    set_phase 1

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/test/kotlin/ServiceTest.kt" "$PROJECT_DIR")

    run run_phase_guard "$input"
    [ "$status" -eq 0 ]
    assert_decision_block
}

@test "phase 1 allows config file edits" {
    create_marker "tdd-mode"
    set_phase 1

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/pom.xml" "$PROJECT_DIR")

    run run_phase_guard "$input"
    [ "$status" -eq 0 ]
    # Should not block config files
    assert_output_not_contains '"decision": "block"'
}

# =============================================================================
# Phase 2 Tests (Interfaces)
# =============================================================================

@test "phase 2 allows main source edits" {
    create_marker "tdd-mode"
    set_phase 2

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_phase_guard "$input"
    [ "$status" -eq 0 ]
    assert_decision_allow
}

@test "phase 2 blocks test source edits" {
    create_marker "tdd-mode"
    set_phase 2

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/test/kotlin/ServiceTest.kt" "$PROJECT_DIR")

    run run_phase_guard "$input"
    [ "$status" -eq 0 ]
    assert_decision_block
    assert_output_contains "Phase 2"
    assert_output_contains "Interface"
}

@test "phase 2 allows config file edits" {
    create_marker "tdd-mode"
    set_phase 2

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/pom.xml" "$PROJECT_DIR")

    run run_phase_guard "$input"
    [ "$status" -eq 0 ]
    assert_decision_allow
}

# =============================================================================
# Phase 3 Tests (Tests)
# =============================================================================

@test "phase 3 blocks main source edits" {
    create_marker "tdd-mode"
    set_phase 3

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_phase_guard "$input"
    [ "$status" -eq 0 ]
    assert_decision_block
    assert_output_contains "Phase 3"
    assert_output_contains "Test"
}

@test "phase 3 allows test source edits" {
    create_marker "tdd-mode"
    set_phase 3

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/test/kotlin/ServiceTest.kt" "$PROJECT_DIR")

    run run_phase_guard "$input"
    [ "$status" -eq 0 ]
    assert_decision_allow
}

@test "phase 3 allows config file edits" {
    create_marker "tdd-mode"
    set_phase 3

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/application.yaml" "$PROJECT_DIR")

    run run_phase_guard "$input"
    [ "$status" -eq 0 ]
    assert_decision_allow
}

# =============================================================================
# Phase 4 Tests (Implementation)
# =============================================================================

@test "phase 4 allows main source edits" {
    create_marker "tdd-mode"
    set_phase 4

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_phase_guard "$input"
    [ "$status" -eq 0 ]
    assert_decision_allow
}

@test "phase 4 allows test source edits" {
    create_marker "tdd-mode"
    set_phase 4

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/test/kotlin/ServiceTest.kt" "$PROJECT_DIR")

    run run_phase_guard "$input"
    [ "$status" -eq 0 ]
    assert_decision_allow
}

@test "phase 4 allows config file edits" {
    create_marker "tdd-mode"
    set_phase 4

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/pom.xml" "$PROJECT_DIR")

    run run_phase_guard "$input"
    [ "$status" -eq 0 ]
    assert_decision_allow
}

# =============================================================================
# Tool Type Tests
# =============================================================================

@test "ignores non-Write/Edit tools" {
    create_marker "tdd-mode"
    set_phase 1

    local input=$(generate_hook_input "Read" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_phase_guard "$input"
    [ "$status" -eq 0 ]
    [ -z "$output" ]  # Should pass through without output
}

@test "handles Edit tool same as Write" {
    create_marker "tdd-mode"
    set_phase 1

    local input=$(generate_hook_input "Edit" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_phase_guard "$input"
    [ "$status" -eq 0 ]
    assert_decision_block
}

# =============================================================================
# TypeScript Project Tests
# =============================================================================

@test "phase 2 blocks test files for typescript project" {
    # Create TypeScript project
    local ts_project="$TEST_TMP/ts-project"
    create_mock_project "typescript-npm" "$ts_project"

    create_marker "tdd-mode"
    set_phase 2

    local input=$(generate_hook_input "Write" "$ts_project/src/service.test.ts" "$ts_project")

    run run_phase_guard "$input"
    [ "$status" -eq 0 ]
    assert_decision_block
}

@test "phase 3 allows test files for typescript project" {
    local ts_project="$TEST_TMP/ts-project"
    create_mock_project "typescript-npm" "$ts_project"

    create_marker "tdd-mode"
    set_phase 3

    local input=$(generate_hook_input "Write" "$ts_project/src/service.test.ts" "$ts_project")

    run run_phase_guard "$input"
    [ "$status" -eq 0 ]
    assert_decision_allow
}
