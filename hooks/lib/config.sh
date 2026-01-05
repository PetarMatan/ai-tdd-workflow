#!/bin/bash
# TDD Workflow - Configuration Library
# Handles technology profile detection and configuration loading
#
# Source this in any hook: source "$(dirname "$0")/lib/config.sh"

# Determine install directory
TDD_INSTALL_DIR="${TDD_INSTALL_DIR:-$HOME/.claude/tdd-workflow}"
TDD_CONFIG_FILE="${TDD_CONFIG_FILE:-$TDD_INSTALL_DIR/config/tdd-config.json}"
TDD_OVERRIDE_FILE="${TDD_OVERRIDE_FILE:-$HOME/.claude/tdd-override.json}"

# Cache for detected profile (avoid re-detection)
_TDD_DETECTED_PROFILE=""

# Python library paths (relative to this config.sh file)
_CONFIG_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_READER="${_CONFIG_LIB_DIR}/config_reader.py"
PROFILE_DETECTOR="${_CONFIG_LIB_DIR}/profile_detector.py"
PATTERN_MATCHER="${_CONFIG_LIB_DIR}/pattern_matcher.py"

# Read a value from JSON config using Python
# Usage: config_get "profiles.kotlin-maven.commands.compile"
config_get() {
    local path="$1"
    local config_file="${2:-$TDD_CONFIG_FILE}"

    if [[ ! -f "$config_file" ]]; then
        return 1
    fi

    python3 "$CONFIG_READER" get "$path" "$config_file"
}

# Detect technology profile based on project files
# Usage: detect_profile "/path/to/project"
detect_profile() {
    local project_dir="${1:-.}"

    # Return cached result if available
    if [[ -n "$_TDD_DETECTED_PROFILE" ]]; then
        echo "$_TDD_DETECTED_PROFILE"
        return 0
    fi

    # Check for override file first
    if [[ -f "$TDD_OVERRIDE_FILE" ]]; then
        local override
        override=$(python3 "$PROFILE_DETECTOR" override "$TDD_OVERRIDE_FILE")
        if [[ -n "$override" ]]; then
            _TDD_DETECTED_PROFILE="$override"
            echo "$override"
            return 0
        fi
    fi

    # Auto-detect based on project files
    local detected
    detected=$(python3 "$PROFILE_DETECTOR" detect "$project_dir" "$TDD_CONFIG_FILE")

    if [[ -n "$detected" ]]; then
        _TDD_DETECTED_PROFILE="$detected"
        echo "$detected"
        return 0
    fi

    # No profile detected - return empty (caller should handle)
    # User can set TDD_DEFAULT_PROFILE env var or use override file
    local default_profile="${TDD_DEFAULT_PROFILE:-}"
    if [[ -n "$default_profile" ]]; then
        echo "$default_profile"
        return 0
    fi

    # Return empty - hooks will skip if no profile detected
    echo ""
    return 1
}

# Get command for current profile
# Usage: get_command "compile" "/path/to/project"
get_command() {
    local command_name="$1"
    local project_dir="${2:-.}"

    local profile
    profile=$(detect_profile "$project_dir")

    config_get "profiles.${profile}.commands.${command_name}"
}

# Get source pattern for current profile
# Usage: get_source_pattern "main" "/path/to/project"
get_source_pattern() {
    local pattern_type="$1"
    local project_dir="${2:-.}"

    local profile
    profile=$(detect_profile "$project_dir")

    config_get "profiles.${profile}.sourcePatterns.${pattern_type}"
}

# Check if a file matches a glob pattern with proper ** support
# Usage: _matches_glob "/path/to/file.kt" "**/*.kt"
_matches_glob() {
    local file_path="$1"
    local pattern="$2"
    python3 "$PATTERN_MATCHER" match "$file_path" "$pattern" 2>/dev/null
}

# Check if a file matches main source pattern
# Usage: is_main_source "/path/to/file.kt" "/path/to/project"
is_main_source() {
    local file_path="$1"
    local project_dir="${2:-.}"

    local pattern
    pattern=$(get_source_pattern "main" "$project_dir")

    python3 "$PATTERN_MATCHER" match "$file_path" "$pattern" 2>/dev/null
}

# Check if a file matches test source pattern
# Usage: is_test_source "/path/to/file.kt" "/path/to/project"
is_test_source() {
    local file_path="$1"
    local project_dir="${2:-.}"

    local pattern
    pattern=$(get_source_pattern "test" "$project_dir")

    python3 "$PATTERN_MATCHER" match "$file_path" "$pattern" 2>/dev/null
}

# Check if a file matches config pattern
# Usage: is_config_file "/path/to/pom.xml" "/path/to/project"
is_config_file() {
    local file_path="$1"
    local project_dir="${2:-.}"

    local patterns
    patterns=$(get_source_pattern "config" "$project_dir")

    python3 "$PATTERN_MATCHER" match "$file_path" "$patterns" 2>/dev/null
}

# Get profile name for display
# Usage: get_profile_name "/path/to/project"
get_profile_name() {
    local project_dir="${1:-.}"
    local profile
    profile=$(detect_profile "$project_dir")
    config_get "profiles.${profile}.name"
}

# Get TODO placeholder for current profile
# Usage: get_todo_placeholder "/path/to/project"
get_todo_placeholder() {
    local project_dir="${1:-.}"
    local profile
    profile=$(detect_profile "$project_dir")
    config_get "profiles.${profile}.todoPlaceholder"
}
