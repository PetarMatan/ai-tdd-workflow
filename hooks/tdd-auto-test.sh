#!/bin/bash
# Note: We intentionally do NOT use set -e here because we need to
# capture compile/test failures and report them, not exit early

# TDD Auto-Test Hook - PostToolUse
# Runs compile + test cycle after file changes in Phase 4
# Version: 1.0.0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/log.sh"
source "$SCRIPT_DIR/lib/config.sh"
source "$SCRIPT_DIR/lib/markers.sh"

# Parse hook input
input=$(cat)
eval "$(echo "$input" | python3 "$SCRIPT_DIR/lib/hook_io.py" parse)"
tool_name="$HOOK_TOOL_NAME"
file_path="$HOOK_FILE_PATH"
project_dir="$HOOK_CWD"
session_id="$HOOK_SESSION_ID"

# Initialize session-scoped markers
setup_markers "$session_id"

# Only process Write|Edit operations
if [[ ! "$tool_name" =~ ^(Write|Edit)$ ]]; then
    exit 0
fi

# Check if TDD mode is active
if [[ ! -f "$TDD_MODE_MARKER" ]]; then
    exit 0
fi

# Check if we're in Phase 4
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

    # Build context message
    context="## TDD Phase 4: Compilation FAILED ($profile_name)

**File:** $file_path

**Errors:**
\`\`\`
$error_summary
\`\`\`

Fix these compilation errors and continue implementing."

    python3 "$SCRIPT_DIR/lib/hook_io.py" approve-message \
        "TDD Phase 4 ($profile_name): Compilation failed, fix immediately" \
        "PostToolUse" \
        "$context"
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

    # Build context message
    context="## TDD Phase 4: Compilation PASSED, Tests FAILED ($profile_name)

**File:** $file_path

**Test Results:**
\`\`\`
$test_summary
\`\`\`

Review the failing tests and continue implementing the business logic.

**Full output:** /tmp/tdd-test-output.txt"

    python3 "$SCRIPT_DIR/lib/hook_io.py" approve-message \
        "TDD Phase 4 ($profile_name): Tests failing, continue implementing" \
        "PostToolUse" \
        "$context"
    exit 0
fi

# Both passed!
log_tdd "Phase 4: All tests passing!" "$session_id"
echo ">>> TDD: All tests passing!" >&2
exit 0
