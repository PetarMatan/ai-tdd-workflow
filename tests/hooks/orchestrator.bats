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

    # Phase file should be created (session-scoped)
    [ -f "$TEST_MARKERS_DIR/tdd-phase" ]
}

@test "resets unknown phase to 1" {
    create_marker "tdd-mode"
    echo "99" > "$TEST_MARKERS_DIR/tdd-phase"

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"

    [ "$(get_phase)" = "1" ]
}

# =============================================================================
# Agent Loading Tests
# =============================================================================

@test "phase 1 loads agents configured for phase 1" {
    create_marker "tdd-mode"
    set_phase 1

    # Create an agent bound to phase 1
    mkdir -p "$TDD_AGENTS_DIR"
    cat > "$TDD_AGENTS_DIR/requirements-expert.md" << 'EOF'
---
name: Requirements Expert
phases: [1]
---

# Requirements Expert

Help gather complete requirements.
EOF

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]
    assert_decision_block
    assert_output_contains "Requirements Expert"
    assert_output_contains "Help gather complete requirements"
}

@test "phase 2 loads agents configured for phase 2" {
    create_marker "tdd-mode"
    set_phase 2

    set_mock_compile_result 0 "BUILD SUCCESS"

    # Create an agent bound to phase 2
    mkdir -p "$TDD_AGENTS_DIR"
    cat > "$TDD_AGENTS_DIR/api-designer.md" << 'EOF'
---
name: API Designer
phases: [2]
---

# API Designer

Design clean REST APIs.
EOF

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]
    assert_decision_block
    assert_output_contains "API Designer"
    assert_output_contains "Design clean REST APIs"
}

@test "phase 3 loads agents configured for phase 3" {
    create_marker "tdd-mode"
    set_phase 3

    set_mock_compile_result 0 "BUILD SUCCESS"

    # Create an agent bound to phase 3
    mkdir -p "$TDD_AGENTS_DIR"
    cat > "$TDD_AGENTS_DIR/test-expert.md" << 'EOF'
---
name: Test Expert
phases: [3]
---

# Test Expert

Write comprehensive tests.
EOF

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]
    assert_decision_block
    assert_output_contains "Test Expert"
    assert_output_contains "Write comprehensive tests"
}

@test "phase 4 loads agents configured for phase 4" {
    create_marker "tdd-mode"
    set_phase 4

    set_mock_compile_result 0 "BUILD SUCCESS"
    set_mock_test_result 1 "Tests failed"

    # Create an agent bound to phase 4
    mkdir -p "$TDD_AGENTS_DIR"
    cat > "$TDD_AGENTS_DIR/implementation-expert.md" << 'EOF'
---
name: Implementation Expert
phases: [4]
---

# Implementation Expert

Implement clean code.
EOF

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]
    assert_decision_block
    assert_output_contains "Implementation Expert"
    assert_output_contains "Implement clean code"
}

@test "loads multiple agents for same phase" {
    create_marker "tdd-mode"
    set_phase 2

    set_mock_compile_result 0 "BUILD SUCCESS"

    # Create multiple agents bound to phase 2
    mkdir -p "$TDD_AGENTS_DIR"
    cat > "$TDD_AGENTS_DIR/agent-one.md" << 'EOF'
---
name: Agent One
phases: [2]
---
First agent content.
EOF

    cat > "$TDD_AGENTS_DIR/agent-two.md" << 'EOF'
---
name: Agent Two
phases: [2, 3]
---
Second agent content.
EOF

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]
    assert_decision_block
    assert_output_contains "Agent One"
    assert_output_contains "First agent content"
    assert_output_contains "Agent Two"
    assert_output_contains "Second agent content"
}

@test "does not load agents configured for different phase" {
    create_marker "tdd-mode"
    set_phase 1

    # Create an agent bound to phase 3 only
    mkdir -p "$TDD_AGENTS_DIR"
    cat > "$TDD_AGENTS_DIR/phase3-only.md" << 'EOF'
---
name: Phase 3 Only
phases: [3]
---
Should not appear in phase 1.
EOF

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]
    assert_output_not_contains "Phase 3 Only"
    assert_output_not_contains "Should not appear in phase 1"
}

@test "handles no agents gracefully" {
    create_marker "tdd-mode"
    set_phase 1

    # Ensure no agents exist
    rm -rf "$TDD_AGENTS_DIR"

    local input=$(generate_stop_hook_input "$PROJECT_DIR")

    run run_orchestrator "$input"
    [ "$status" -eq 0 ]
    assert_decision_block
    # Should still show phase 1 guidance
    assert_output_contains "Phase 1"
}

@test "agent with multiple phases loads in each phase" {
    mkdir -p "$TDD_AGENTS_DIR"
    cat > "$TDD_AGENTS_DIR/multi-phase.md" << 'EOF'
---
name: Multi Phase Agent
phases: [2, 3]
---
Available in phases 2 and 3.
EOF

    # Test in phase 2
    create_marker "tdd-mode"
    set_phase 2
    set_mock_compile_result 0 "BUILD SUCCESS"

    local input=$(generate_stop_hook_input "$PROJECT_DIR")
    run run_orchestrator "$input"
    assert_output_contains "Multi Phase Agent"

    # Test in phase 3
    set_phase 3
    run run_orchestrator "$input"
    assert_output_contains "Multi Phase Agent"
}
