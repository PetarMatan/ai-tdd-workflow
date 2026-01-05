#!/bin/bash
# TDD Phase Guard - PreToolUse Hook
# Blocks file edits that don't match the current TDD phase
# Version: 1.0.0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/log.sh"
source "$SCRIPT_DIR/lib/config.sh"
source "$SCRIPT_DIR/lib/markers.sh"

# Parse hook input
input=$(cat)
eval "$(echo "$input" | python3 "$SCRIPT_DIR/lib/hook_io.py" parse)"
session_id="$HOOK_SESSION_ID"
tool_name="$HOOK_TOOL_NAME"
file_path="$HOOK_FILE_PATH"
project_dir="$HOOK_CWD"

# Initialize markers
setup_markers "$session_id"

# Check if TDD mode is active
if [[ ! -f "$TDD_MODE_MARKER" ]]; then
    exit 0
fi

# Only guard Write and Edit tools
if [[ "$tool_name" != "Write" && "$tool_name" != "Edit" ]]; then
    exit 0
fi

# If no file path, allow
if [[ -z "$file_path" ]]; then
    exit 0
fi

# Read current phase
current_phase="1"
if [[ -f "$TDD_PHASE_FILE" ]]; then
    current_phase=$(cat "$TDD_PHASE_FILE")
fi

# Get profile info
profile_name=$(get_profile_name "$project_dir")

# Check file type using config-based patterns
is_main=false
is_test=false
is_config=false

if is_main_source "$file_path" "$project_dir"; then
    is_main=true
fi
if is_test_source "$file_path" "$project_dir"; then
    is_test=true
fi
if is_config_file "$file_path" "$project_dir"; then
    is_config=true
fi

# Phase-specific rules
case "$current_phase" in
    "1")
        # Phase 1: Requirements - Block all source file edits
        if [[ "$is_main" == true || "$is_test" == true ]]; then
            log_tdd "Phase 1: Blocked edit to $file_path - requirements gathering" "$session_id"
            cat <<EOF
{
  "decision": "block",
  "reason": "TDD Phase 1: Cannot edit source files during requirements gathering",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "## TDD Phase 1: Requirements Gathering ($profile_name)

**Blocked:** Cannot edit \`$file_path\`

You are in **Phase 1 (Requirements)**. No source code changes are allowed yet.

**Complete Phase 1 first:**
1. Gather all requirements from user
2. Ask clarifying questions
3. Get user confirmation
4. Create marker: \`touch ~/.claude/tmp/tdd-requirements-confirmed\`

Then you can proceed to Phase 2 (Interface Design)."
  }
}
EOF
            exit 0
        fi
        ;;
    "2")
        # Phase 2: Interfaces - Allow main source only (config files also ok)
        if [[ "$is_test" == true ]]; then
            log_tdd "Phase 2: Blocked edit to $file_path - no tests during interface design" "$session_id"
            cat <<EOF
{
  "decision": "block",
  "reason": "TDD Phase 2: Cannot write tests during interface design",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "## TDD Phase 2: Interface Design ($profile_name)

**Blocked:** Cannot edit \`$file_path\`

You are in **Phase 2 (Interfaces)**. Test files cannot be edited yet.

**In Phase 2, you should:**
1. Create class skeletons in main source
2. Define method signatures with TODO bodies
3. Ensure code compiles
4. Present interfaces to user for approval
5. Create marker: \`touch ~/.claude/tmp/tdd-interfaces-designed\`

**After marker is created**, you'll advance to Phase 3 (Tests)."
  }
}
EOF
            exit 0
        fi
        ;;
    "3")
        # Phase 3: Tests - Allow test source only
        # Note: A test file might match both main and test patterns (e.g., src/service.test.ts)
        # so we only block if it's main AND NOT test AND NOT config
        if [[ "$is_main" == true && "$is_test" == false && "$is_config" == false ]]; then
            log_tdd "Phase 3: Blocked edit to $file_path - no implementation during test writing" "$session_id"
            cat <<EOF
{
  "decision": "block",
  "reason": "TDD Phase 3: Cannot edit implementation during test writing",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "## TDD Phase 3: Test Writing ($profile_name)

**Blocked:** Cannot edit \`$file_path\`

You are in **Phase 3 (Tests)**. Implementation files cannot be edited yet.

**In Phase 3, you should:**
1. Write tests in test source directories
2. Tests WILL fail (Red phase) - that's expected
3. Present tests to user for approval
4. Create marker: \`touch ~/.claude/tmp/tdd-tests-approved\`

**After tests are approved**, you'll advance to Phase 4 (Implementation)."
  }
}
EOF
            exit 0
        fi
        ;;
    "4")
        # Phase 4: Implementation - Allow everything
        ;;
esac

# Allow the operation
exit 0
