#!/usr/bin/env bats
# Hook tests for tdd-auto-test.sh

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

run_auto_test() {
    local input="$1"
    echo "$input" | bash "$HOOKS_DIR/tdd-auto-test.sh"
}

# =============================================================================
# Skip Conditions Tests
# =============================================================================

@test "skips when TDD mode is inactive" {
    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_auto_test "$input"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "skips when not in phase 4" {
    create_marker "tdd-mode"
    set_phase 2

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_auto_test "$input"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "skips for non-Write/Edit tools" {
    create_marker "tdd-mode"
    set_phase 4

    local input=$(generate_hook_input "Read" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_auto_test "$input"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "skips for non-source files" {
    create_marker "tdd-mode"
    set_phase 4

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/README.md" "$PROJECT_DIR")

    run run_auto_test "$input"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# =============================================================================
# Phase 4 Compile+Test Cycle Tests
# =============================================================================

@test "runs compile and test in phase 4" {
    create_marker "tdd-mode"
    set_phase 4

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_auto_test "$input"
    [ "$status" -eq 0 ]
}

@test "reports compilation failure in phase 4" {
    create_marker "tdd-mode"
    set_phase 4

    set_mock_compile_result 1 "[ERROR] Syntax error in Service.kt"

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_auto_test "$input"
    [ "$status" -eq 0 ]
    assert_output_contains "Compilation FAILED"
    assert_output_contains "Syntax error"
}

@test "reports test failure in phase 4" {
    create_marker "tdd-mode"
    set_phase 4

    set_mock_compile_result 0 "BUILD SUCCESS"
    set_mock_test_result 1 "Tests run: 10, Failures: 2
FAILURE: testCalculateTotal"

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_auto_test "$input"
    [ "$status" -eq 0 ]
    assert_output_contains "Tests FAILED"
    assert_output_contains "Failures: 2"
}

@test "reports success when compile and tests pass" {
    create_marker "tdd-mode"
    set_phase 4

    set_mock_compile_result 0 "BUILD SUCCESS"
    set_mock_test_result 0 "Tests run: 10, Failures: 0"

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_auto_test "$input"
    [ "$status" -eq 0 ]
}

# =============================================================================
# Test File Changes Tests
# =============================================================================

@test "runs cycle for test file changes" {
    create_marker "tdd-mode"
    set_phase 4

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/test/kotlin/ServiceTest.kt" "$PROJECT_DIR")

    run run_auto_test "$input"
    [ "$status" -eq 0 ]
}
