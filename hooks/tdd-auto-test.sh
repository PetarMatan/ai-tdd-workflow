#!/bin/bash
# Note: We intentionally do NOT use set -e here because we need to
# capture compile/test failures and report them, not exit early

# TDD Auto-Test Hook - PostToolUse
# Runs compile + test cycle after file changes in Phase 4
# Version: 1.0.0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/log.sh"
source "$SCRIPT_DIR/lib/config.sh"

input=$(cat)
tool_name=$(echo "$input" | python3 -c "import sys, json; print(json.load(sys.stdin).get('tool_name', ''))")
file_path=$(echo "$input" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('tool_input', {}).get('file_path', ''))")
project_dir=$(echo "$input" | python3 -c "import sys, json; print(json.load(sys.stdin).get('cwd', ''))")
session_id=$(echo "$input" | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_id', 'unknown'))")

# Only process Write|Edit operations
if [[ ! "$tool_name" =~ ^(Write|Edit)$ ]]; then
    exit 0
fi

# Check if TDD mode is active
TDD_MODE_MARKER="${HOME}/.claude/tmp/tdd-mode"
if [[ ! -f "$TDD_MODE_MARKER" ]]; then
    exit 0
fi

# Check if we're in Phase 4
TDD_PHASE_FILE="${HOME}/.claude/tmp/tdd-phase"
if [[ ! -f "$TDD_PHASE_FILE" ]]; then
    exit 0
fi

current_phase=$(cat "$TDD_PHASE_FILE")
if [[ "$current_phase" != "4" ]]; then
    exit 0
fi

cd "$project_dir" || exit 0

# Detect profile and get commands
profile_name=$(get_profile_name "$project_dir")
compile_cmd=$(get_command "compile" "$project_dir")
test_cmd=$(get_command "test" "$project_dir")

# Check if the file matches source patterns for this profile
is_source=false
if is_main_source "$file_path" "$project_dir" || is_test_source "$file_path" "$project_dir"; then
    is_source=true
fi

# Skip non-source files
if [[ "$is_source" == false ]]; then
    exit 0
fi

log_tdd "Phase 4: Running compile + test cycle for $file_path" "$session_id"
echo ">>> TDD Phase 4 ($profile_name): Running compile + test cycle..." >&2

# Run compilation
compile_output_file="/tmp/tdd-compile-output.txt"
eval "$compile_cmd" > "$compile_output_file" 2>&1
compile_exit_code=$?

if [[ $compile_exit_code -ne 0 ]]; then
    log_build "FAILED" "TDD Phase 4 compilation failed" "$session_id"
    echo ">>> TDD: Compilation failed" >&2
    error_summary=$(cat "$compile_output_file" | head -20)

    python3 - "$file_path" "$error_summary" "$profile_name" <<'PYTHON'
import sys
import json

file_path = sys.argv[1]
error_summary = sys.argv[2]
profile = sys.argv[3]

output = {
    "decision": "approve",
    "reason": f"TDD Phase 4 ({profile}): Compilation failed, fix immediately",
    "hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": f"""## TDD Phase 4: Compilation FAILED ({profile})

**File:** {file_path}

**Errors:**
```
{error_summary}
```

Fix these compilation errors and continue implementing."""
    }
}
print(json.dumps(output, indent=2))
PYTHON
    exit 0
fi

log_build "SUCCESS" "TDD Phase 4 compilation passed" "$session_id"
echo ">>> TDD: Compilation passed, running tests..." >&2

# Run tests
test_output_file="/tmp/tdd-test-output.txt"
eval "$test_cmd" > "$test_output_file" 2>&1
test_exit_code=$?

if [[ $test_exit_code -ne 0 ]]; then
    log_tdd "Phase 4: Tests failed - continuing implementation" "$session_id"
    echo ">>> TDD: Tests failed" >&2
    test_summary=$(cat "$test_output_file" | tail -30)

    python3 - "$file_path" "$test_summary" "$profile_name" <<'PYTHON'
import sys
import json

file_path = sys.argv[1]
test_summary = sys.argv[2]
profile = sys.argv[3]

output = {
    "decision": "approve",
    "reason": f"TDD Phase 4 ({profile}): Tests failing, continue implementing",
    "hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": f"""## TDD Phase 4: Compilation PASSED, Tests FAILED ({profile})

**File:** {file_path}

**Test Results:**
```
{test_summary}
```

Review the failing tests and continue implementing the business logic.

**Full output:** /tmp/tdd-test-output.txt"""
    }
}
print(json.dumps(output, indent=2))
PYTHON
    exit 0
fi

# Both passed!
log_tdd "Phase 4: All tests passing!" "$session_id"
echo ">>> TDD: All tests passing!" >&2
exit 0
