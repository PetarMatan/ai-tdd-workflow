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

# Read a value from JSON config using Python
# Usage: config_get "profiles.kotlin-maven.commands.compile"
config_get() {
    local path="$1"
    local config_file="${2:-$TDD_CONFIG_FILE}"

    if [[ ! -f "$config_file" ]]; then
        return 1
    fi

    python3 -c "
import json
import sys

path = '$path'
parts = path.split('.')

try:
    with open('$config_file', 'r') as f:
        data = json.load(f)

    for part in parts:
        if isinstance(data, dict):
            data = data.get(part)
        else:
            data = None
            break

    if data is not None:
        if isinstance(data, (dict, list)):
            print(json.dumps(data))
        else:
            print(data)
except Exception as e:
    sys.exit(1)
" 2>/dev/null
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
        override=$(python3 -c "
import json
with open('$TDD_OVERRIDE_FILE', 'r') as f:
    print(json.load(f).get('activeProfile', ''))
" 2>/dev/null)
        if [[ -n "$override" ]]; then
            _TDD_DETECTED_PROFILE="$override"
            echo "$override"
            return 0
        fi
    fi

    # Auto-detect based on project files
    local detected
    detected=$(python3 -c "
import json
import os
from pathlib import Path

project_dir = Path('$project_dir').resolve()

with open('$TDD_CONFIG_FILE', 'r') as f:
    config = json.load(f)

profiles = config.get('profiles', {})

# Score each profile based on detection criteria
scores = {}
for profile_name, profile in profiles.items():
    detection = profile.get('detection', {})
    files = detection.get('files', [])
    patterns = detection.get('patterns', [])

    score = 0

    # Check for detection files
    for f in files:
        if (project_dir / f).exists():
            score += 10

    # Check for source patterns (simplified glob check)
    for pattern in patterns:
        # Convert glob to simple check
        ext = pattern.split('*')[-1] if '*' in pattern else pattern
        pattern_matched = False
        for root, dirs, filenames in os.walk(project_dir):
            for filename in filenames:
                if filename.endswith(ext):
                    score += 1
                    pattern_matched = True
                    break
            if pattern_matched:
                break

    if score > 0:
        scores[profile_name] = score

# Return highest scoring profile
if scores:
    best = max(scores, key=scores.get)
    print(best)
" 2>/dev/null)

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

# Convert glob pattern to regex with proper ** support
# Usage: glob_to_regex "**/*.ts"
_glob_to_regex() {
    local pattern="$1"
    python3 -c "
import re
import sys

pattern = '''$pattern'''

# Convert glob to regex
# First, escape special regex chars except * and ?
regex = re.escape(pattern)
# Unescape the glob special chars we want to handle
regex = regex.replace(r'\*\*', '__DOUBLE_STAR__')
regex = regex.replace(r'\*', '__SINGLE_STAR__')
regex = regex.replace(r'\?', '__QUESTION__')

# Convert glob patterns to regex
regex = regex.replace('__DOUBLE_STAR__/', '(?:.*/)?')  # **/ matches zero or more directories
regex = regex.replace('__DOUBLE_STAR__', '.*')         # ** at end matches anything
regex = regex.replace('__SINGLE_STAR__', '[^/]*')      # * matches anything except /
regex = regex.replace('__QUESTION__', '[^/]')          # ? matches single char except /

print(f'^(?:.*/)?{regex}\$')
"
}

# Check if a file matches a glob pattern with proper ** support
# Usage: _matches_glob "/path/to/file.kt" "**/*.kt"
_matches_glob() {
    local file_path="$1"
    local pattern="$2"

    python3 -c "
import re
import sys

file_path = '''$file_path'''
pattern = '''$pattern'''

# Convert glob to regex
# First, escape special regex chars except * and ?
regex = re.escape(pattern)
# Unescape the glob special chars we want to handle
regex = regex.replace(r'\*\*', '__DOUBLE_STAR__')
regex = regex.replace(r'\*', '__SINGLE_STAR__')
regex = regex.replace(r'\?', '__QUESTION__')

# Convert glob patterns to regex
regex = regex.replace('__DOUBLE_STAR__/', '(?:.*/)?')  # **/ matches zero or more directories
regex = regex.replace('__DOUBLE_STAR__', '.*')         # ** at end matches anything
regex = regex.replace('__SINGLE_STAR__', '[^/]*')      # * matches anything except /
regex = regex.replace('__QUESTION__', '[^/]')          # ? matches single char except /

# Pattern should match the end of the path (with optional leading directories)
regex = f'^(?:.*/)?{regex}\$'

if re.match(regex, file_path):
    sys.exit(0)
sys.exit(1)
" 2>/dev/null
}

# Check if a file matches main source pattern
# Usage: is_main_source "/path/to/file.kt" "/path/to/project"
is_main_source() {
    local file_path="$1"
    local project_dir="${2:-.}"

    local pattern
    pattern=$(get_source_pattern "main" "$project_dir")

    python3 -c "
import re
import sys
import json

pattern_raw = '''$pattern'''
file_path = '''$file_path'''

# Handle JSON array patterns
if pattern_raw.startswith('['):
    patterns = json.loads(pattern_raw)
else:
    patterns = [pattern_raw]

def glob_to_regex(pattern):
    # Escape special regex chars except * and ?
    regex = re.escape(pattern)
    # Unescape the glob special chars we want to handle
    regex = regex.replace(r'\*\*', '__DOUBLE_STAR__')
    regex = regex.replace(r'\*', '__SINGLE_STAR__')
    regex = regex.replace(r'\?', '__QUESTION__')

    # Convert glob patterns to regex
    regex = regex.replace('__DOUBLE_STAR__/', '(?:.*/)?')  # **/ matches zero or more directories
    regex = regex.replace('__DOUBLE_STAR__', '.*')         # ** at end matches anything
    regex = regex.replace('__SINGLE_STAR__', '[^/]*')      # * matches anything except /
    regex = regex.replace('__QUESTION__', '[^/]')          # ? matches single char except /

    # Pattern should match the end of the path (with optional leading directories)
    return f'^(?:.*/)?{regex}\$'

for p in patterns:
    regex = glob_to_regex(p)
    if re.match(regex, file_path):
        sys.exit(0)
sys.exit(1)
" 2>/dev/null
}

# Check if a file matches test source pattern
# Usage: is_test_source "/path/to/file.kt" "/path/to/project"
is_test_source() {
    local file_path="$1"
    local project_dir="${2:-.}"

    local pattern
    pattern=$(get_source_pattern "test" "$project_dir")

    python3 -c "
import re
import sys
import json

pattern_raw = '''$pattern'''
file_path = '''$file_path'''

# Handle JSON array patterns
if pattern_raw.startswith('['):
    patterns = json.loads(pattern_raw)
else:
    patterns = [pattern_raw]

def glob_to_regex(pattern):
    # Escape special regex chars except * and ?
    regex = re.escape(pattern)
    # Unescape the glob special chars we want to handle
    regex = regex.replace(r'\*\*', '__DOUBLE_STAR__')
    regex = regex.replace(r'\*', '__SINGLE_STAR__')
    regex = regex.replace(r'\?', '__QUESTION__')

    # Convert glob patterns to regex
    regex = regex.replace('__DOUBLE_STAR__/', '(?:.*/)?')  # **/ matches zero or more directories
    regex = regex.replace('__DOUBLE_STAR__', '.*')         # ** at end matches anything
    regex = regex.replace('__SINGLE_STAR__', '[^/]*')      # * matches anything except /
    regex = regex.replace('__QUESTION__', '[^/]')          # ? matches single char except /

    # Pattern should match the end of the path (with optional leading directories)
    return f'^(?:.*/)?{regex}\$'

for p in patterns:
    regex = glob_to_regex(p)
    if re.match(regex, file_path):
        sys.exit(0)
sys.exit(1)
" 2>/dev/null
}

# Check if a file matches config pattern
# Usage: is_config_file "/path/to/pom.xml" "/path/to/project"
is_config_file() {
    local file_path="$1"
    local project_dir="${2:-.}"

    local patterns
    patterns=$(get_source_pattern "config" "$project_dir")

    python3 -c "
import re
import json
import sys

patterns_raw = '''$patterns'''
file_path = '''$file_path'''

# Parse patterns
if patterns_raw.startswith('['):
    patterns = json.loads(patterns_raw)
else:
    patterns = [patterns_raw]

def glob_to_regex(pattern):
    # Escape special regex chars except * and ?
    regex = re.escape(pattern)
    # Unescape the glob special chars we want to handle
    regex = regex.replace(r'\*\*', '__DOUBLE_STAR__')
    regex = regex.replace(r'\*', '__SINGLE_STAR__')
    regex = regex.replace(r'\?', '__QUESTION__')

    # Convert glob patterns to regex
    regex = regex.replace('__DOUBLE_STAR__/', '(?:.*/)?')  # **/ matches zero or more directories
    regex = regex.replace('__DOUBLE_STAR__', '.*')         # ** at end matches anything
    regex = regex.replace('__SINGLE_STAR__', '[^/]*')      # * matches anything except /
    regex = regex.replace('__QUESTION__', '[^/]')          # ? matches single char except /

    # Pattern should match the end of the path (with optional leading directories)
    return f'^(?:.*/)?{regex}\$'

for p in patterns:
    regex = glob_to_regex(p)
    if re.match(regex, file_path):
        sys.exit(0)
sys.exit(1)
" 2>/dev/null
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
