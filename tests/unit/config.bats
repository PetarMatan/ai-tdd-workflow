#!/usr/bin/env bats
# Unit tests for lib/config.sh

load '../test_helper'

setup() {
    setup_test_environment

    # Source the config library
    export TDD_INSTALL_DIR="$PROJECT_ROOT"
    export TDD_CONFIG_FILE="$PROJECT_ROOT/config/tdd-config.json"
    source "$HOOKS_DIR/lib/config.sh"
}

teardown() {
    teardown_test_environment
}

# =============================================================================
# config_get tests
# =============================================================================

@test "config_get returns profile name" {
    run config_get "profiles.kotlin-maven.name"
    [ "$status" -eq 0 ]
    [ "$output" = "Kotlin/Maven" ]
}

@test "config_get returns compile command" {
    run config_get "profiles.kotlin-maven.commands.compile"
    [ "$status" -eq 0 ]
    [ "$output" = "mvn clean compile -q" ]
}

@test "config_get returns test command" {
    run config_get "profiles.typescript-npm.commands.test"
    [ "$status" -eq 0 ]
    [ "$output" = "npm test" ]
}

@test "config_get returns empty for nonexistent path" {
    run config_get "profiles.nonexistent.commands.compile"
    [ "$status" -eq 1 ] || [ -z "$output" ]
}

# =============================================================================
# detect_profile tests
# =============================================================================

@test "detect_profile returns kotlin-maven for pom.xml + .kt files" {
    local project_dir="$TEST_TMP/kotlin-project"
    create_mock_project "kotlin-maven" "$project_dir"

    run detect_profile "$project_dir"
    [ "$status" -eq 0 ]
    [ "$output" = "kotlin-maven" ]
}

@test "detect_profile returns typescript-npm for package.json + tsconfig.json" {
    local project_dir="$TEST_TMP/ts-project"
    create_mock_project "typescript-npm" "$project_dir"

    run detect_profile "$project_dir"
    [ "$status" -eq 0 ]
    [ "$output" = "typescript-npm" ]
}

@test "detect_profile returns python-pytest for pyproject.toml + .py files" {
    local project_dir="$TEST_TMP/python-project"
    create_mock_project "python-pytest" "$project_dir"

    run detect_profile "$project_dir"
    [ "$status" -eq 0 ]
    [ "$output" = "python-pytest" ]
}

@test "detect_profile returns go for go.mod" {
    local project_dir="$TEST_TMP/go-project"
    create_mock_project "go" "$project_dir"

    run detect_profile "$project_dir"
    [ "$status" -eq 0 ]
    [ "$output" = "go" ]
}

@test "detect_profile respects override file" {
    local project_dir="$TEST_TMP/kotlin-project"
    create_mock_project "kotlin-maven" "$project_dir"

    # Create override file
    export TDD_OVERRIDE_FILE="$TEST_TMP/override.json"
    echo '{"activeProfile": "typescript-npm"}' > "$TDD_OVERRIDE_FILE"

    # Clear cache
    _TDD_DETECTED_PROFILE=""

    run detect_profile "$project_dir"
    [ "$status" -eq 0 ]
    [ "$output" = "typescript-npm" ]
}

@test "detect_profile respects TDD_DEFAULT_PROFILE env var" {
    local project_dir="$TEST_TMP/empty-project"
    mkdir -p "$project_dir"

    export TDD_DEFAULT_PROFILE="python-pytest"
    _TDD_DETECTED_PROFILE=""

    run detect_profile "$project_dir"
    [ "$status" -eq 0 ]
    [ "$output" = "python-pytest" ]
}

@test "detect_profile returns empty for unknown project" {
    local project_dir="$TEST_TMP/unknown-project"
    mkdir -p "$project_dir"
    touch "$project_dir/unknown.xyz"

    unset TDD_DEFAULT_PROFILE
    _TDD_DETECTED_PROFILE=""

    run detect_profile "$project_dir"
    [ "$status" -eq 1 ] || [ -z "$output" ]
}

# =============================================================================
# get_command tests
# =============================================================================

@test "get_command returns correct compile command for kotlin-maven" {
    local project_dir="$TEST_TMP/kotlin-project"
    create_mock_project "kotlin-maven" "$project_dir"
    _TDD_DETECTED_PROFILE=""

    run get_command "compile" "$project_dir"
    [ "$status" -eq 0 ]
    [ "$output" = "mvn clean compile -q" ]
}

@test "get_command returns correct test command for typescript-npm" {
    local project_dir="$TEST_TMP/ts-project"
    create_mock_project "typescript-npm" "$project_dir"
    _TDD_DETECTED_PROFILE=""

    run get_command "test" "$project_dir"
    [ "$status" -eq 0 ]
    [ "$output" = "npm test" ]
}

# =============================================================================
# is_main_source tests
# =============================================================================

@test "is_main_source returns true for kotlin main file" {
    local project_dir="$TEST_TMP/kotlin-project"
    create_mock_project "kotlin-maven" "$project_dir"
    _TDD_DETECTED_PROFILE=""

    run is_main_source "$project_dir/src/main/kotlin/Service.kt" "$project_dir"
    [ "$status" -eq 0 ]
}

@test "is_main_source returns false for kotlin test file" {
    local project_dir="$TEST_TMP/kotlin-project"
    create_mock_project "kotlin-maven" "$project_dir"
    _TDD_DETECTED_PROFILE=""

    run is_main_source "$project_dir/src/test/kotlin/ServiceTest.kt" "$project_dir"
    [ "$status" -eq 1 ]
}

@test "is_main_source returns true for typescript src file" {
    local project_dir="$TEST_TMP/ts-project"
    create_mock_project "typescript-npm" "$project_dir"
    _TDD_DETECTED_PROFILE=""

    run is_main_source "$project_dir/src/service.ts" "$project_dir"
    [ "$status" -eq 0 ]
}

# =============================================================================
# is_test_source tests
# =============================================================================

@test "is_test_source returns true for kotlin test file" {
    local project_dir="$TEST_TMP/kotlin-project"
    create_mock_project "kotlin-maven" "$project_dir"
    _TDD_DETECTED_PROFILE=""

    run is_test_source "$project_dir/src/test/kotlin/ServiceTest.kt" "$project_dir"
    [ "$status" -eq 0 ]
}

@test "is_test_source returns false for kotlin main file" {
    local project_dir="$TEST_TMP/kotlin-project"
    create_mock_project "kotlin-maven" "$project_dir"
    _TDD_DETECTED_PROFILE=""

    run is_test_source "$project_dir/src/main/kotlin/Service.kt" "$project_dir"
    [ "$status" -eq 1 ]
}

@test "is_test_source returns true for typescript test file" {
    local project_dir="$TEST_TMP/ts-project"
    create_mock_project "typescript-npm" "$project_dir"
    _TDD_DETECTED_PROFILE=""

    run is_test_source "$project_dir/src/service.test.ts" "$project_dir"
    [ "$status" -eq 0 ]
}

# =============================================================================
# get_profile_name tests
# =============================================================================

@test "get_profile_name returns human-readable name" {
    local project_dir="$TEST_TMP/kotlin-project"
    create_mock_project "kotlin-maven" "$project_dir"
    _TDD_DETECTED_PROFILE=""

    run get_profile_name "$project_dir"
    [ "$status" -eq 0 ]
    [ "$output" = "Kotlin/Maven" ]
}

# =============================================================================
# get_todo_placeholder tests
# =============================================================================

@test "get_todo_placeholder returns kotlin TODO" {
    local project_dir="$TEST_TMP/kotlin-project"
    create_mock_project "kotlin-maven" "$project_dir"
    _TDD_DETECTED_PROFILE=""

    run get_todo_placeholder "$project_dir"
    [ "$status" -eq 0 ]
    [[ "$output" == *'TODO("Implementation pending'* ]]
}
