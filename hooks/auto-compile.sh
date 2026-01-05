#!/bin/bash
# Auto-Compile Hook - PostToolUse
# Runs compilation after source file changes (outside of Phase 4 TDD)
# Version: 1.0.0

set -e
set -o pipefail

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

# Check if file is a source file
cd "$project_dir" || exit 0

is_source=false
if is_main_source "$file_path" "$project_dir" || is_test_source "$file_path" "$project_dir"; then
    is_source=true
fi

# Skip non-source files
if [[ "$is_source" == false ]]; then
    exit 0
fi

# Skip if TDD Phase 4 is active (tdd-auto-test.sh handles compile+test)
if [[ -f "$TDD_MODE_MARKER" ]]; then
    tdd_phase=$(cat "$TDD_PHASE_FILE" 2>/dev/null || echo "0")
    if [[ "$tdd_phase" == "4" ]]; then
        exit 0
    fi
fi

# Get profile info and compile command
profile_name=$(get_profile_name "$project_dir")
compile_cmd=$(get_command "compile" "$project_dir")

echo ">>> Auto-compiling ($profile_name) after source file change..." >&2

# Run compilation
compile_output_file="/tmp/compile-output.txt"
set +e
eval "$compile_cmd" > "$compile_output_file" 2>&1
compile_exit_code=$?
set -e

if [[ $compile_exit_code -eq 0 ]]; then
    echo ">>> Compilation successful" >&2
    log_build "SUCCESS" "Compiled after $file_path change" "$session_id"
    exit 0
else
    echo ">>> Compilation failed - fix errors" >&2
    log_build "FAILED" "Compilation errors in $file_path" "$session_id"

    error_summary=$(cat "$compile_output_file" | head -20)

    # Build context message for approve-message
    context="## COMPILATION FAILED ($profile_name)

**File:** $file_path

**Errors:**
\`\`\`
$error_summary
\`\`\`

**Full output:** /tmp/compile-output.txt

Fix the compilation errors before proceeding."

    python3 "$SCRIPT_DIR/lib/hook_io.py" approve-message \
        "Compilation failed ($profile_name). Fix errors immediately." \
        "PostToolUse" \
        "$context"
    exit 0
fi
