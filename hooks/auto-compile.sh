#!/bin/bash
# Auto-Compile Hook - PostToolUse
# Runs compilation after source file changes (outside of Phase 4 TDD)
# Version: 1.0.0

set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/log.sh"
source "$SCRIPT_DIR/lib/config.sh"

# Read hook input
input=$(cat)
tool_name=$(echo "$input" | python3 -c "import sys, json; print(json.load(sys.stdin).get('tool_name', ''))")
file_path=$(echo "$input" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('tool_input', {}).get('file_path', ''))")
project_dir=$(echo "$input" | python3 -c "import sys, json; print(json.load(sys.stdin).get('cwd', ''))")
session_id=$(echo "$input" | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_id', 'unknown'))")

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
TDD_MODE_MARKER="${HOME}/.claude/tmp/tdd-mode"
TDD_PHASE_FILE="${HOME}/.claude/tmp/tdd-phase"

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

    python3 - "$file_path" "$error_summary" "$profile_name" <<'PYTHON'
import sys
import json

file_path = sys.argv[1]
error_summary = sys.argv[2]
profile = sys.argv[3]

output = {
    "decision": "approve",
    "reason": f"Compilation failed ({profile}). Fix errors immediately.",
    "hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": f"""## COMPILATION FAILED ({profile})

**File:** {file_path}

**Errors:**
```
{error_summary}
```

**Full output:** /tmp/compile-output.txt

Fix the compilation errors before proceeding."""
    }
}
print(json.dumps(output, indent=2))
PYTHON
    exit 0
fi
