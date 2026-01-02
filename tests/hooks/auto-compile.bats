#!/usr/bin/env bats
# Hook tests for auto-compile.sh

load '../test_helper'

setup() {
    setup_test_environment

    export PROJECT_DIR="$TEST_TMP/project"
    create_mock_project "kotlin-maven" "$PROJECT_DIR"

    export TDD_INSTALL_DIR="$PROJECT_ROOT"
    export TDD_CONFIG_FILE="$PROJECT_ROOT/config/tdd-config.json"

    set_mock_compile_result 0 "BUILD SUCCESS"
}

teardown() {
    teardown_test_environment
}

run_auto_compile() {
    local input="$1"
    echo "$input" | bash "$HOOKS_DIR/auto-compile.sh"
}

# =============================================================================
# Basic Functionality Tests
# =============================================================================

@test "compiles after kotlin source file change" {
    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_auto_compile "$input"
    [ "$status" -eq 0 ]
}

@test "skips non-source files" {
    local input=$(generate_hook_input "Write" "$PROJECT_DIR/README.md" "$PROJECT_DIR")

    run run_auto_compile "$input"
    [ "$status" -eq 0 ]
    # Should exit early without compile message
}

@test "skips non-Write/Edit tools" {
    local input=$(generate_hook_input "Read" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_auto_compile "$input"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

# =============================================================================
# Compile Result Tests
# =============================================================================

@test "reports successful compilation" {
    set_mock_compile_result 0 "BUILD SUCCESS"

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_auto_compile "$input"
    [ "$status" -eq 0 ]
}

@test "reports compilation errors with details" {
    set_mock_compile_result 1 "[ERROR] Cannot resolve symbol: unknownMethod"

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_auto_compile "$input"
    [ "$status" -eq 0 ]
    assert_output_contains "COMPILATION FAILED"
    assert_output_contains "Cannot resolve symbol"
}

# =============================================================================
# TDD Phase 4 Skip Tests
# =============================================================================

@test "skips when TDD phase 4 is active" {
    create_marker "tdd-mode"
    set_phase 4

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_auto_compile "$input"
    [ "$status" -eq 0 ]
    # Should exit without compile (tdd-auto-test handles it)
    assert_output_not_contains "COMPILATION"
}

@test "runs when TDD phase is not 4" {
    create_marker "tdd-mode"
    set_phase 2

    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_auto_compile "$input"
    [ "$status" -eq 0 ]
    # Should run compilation
}

@test "runs when TDD mode is inactive" {
    local input=$(generate_hook_input "Write" "$PROJECT_DIR/src/main/kotlin/Service.kt" "$PROJECT_DIR")

    run run_auto_compile "$input"
    [ "$status" -eq 0 ]
}
