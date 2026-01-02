#!/bin/bash
set -e

# TDD Workflow Orchestrator - Stop Hook
# Enforces TDD phase progression: Requirements -> Interfaces -> Tests -> Implementation
# Version: 1.0.0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/log.sh"
source "$SCRIPT_DIR/lib/config.sh"

# Read hook input
input=$(cat)
stop_hook_active=$(echo "$input" | python3 -c "import sys, json; print(json.load(sys.stdin).get('stop_hook_active', False))")
project_dir=$(echo "$input" | python3 -c "import sys, json; print(json.load(sys.stdin).get('cwd', ''))")
session_id=$(echo "$input" | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_id', 'unknown'))")

# Prevent infinite loops
if [[ "$stop_hook_active" == "True" ]]; then
    exit 0
fi

# Marker file paths
TDD_MODE_MARKER="${HOME}/.claude/tmp/tdd-mode"
TDD_PHASE_FILE="${HOME}/.claude/tmp/tdd-phase"
REQUIREMENTS_MARKER="${HOME}/.claude/tmp/tdd-requirements-confirmed"
INTERFACES_MARKER="${HOME}/.claude/tmp/tdd-interfaces-designed"
TESTS_MARKER="${HOME}/.claude/tmp/tdd-tests-approved"
TESTS_PASSING_MARKER="${HOME}/.claude/tmp/tdd-tests-passing"

# Check if TDD mode is active
if [[ ! -f "$TDD_MODE_MARKER" ]]; then
    exit 0
fi

# Initialize phase if not set
if [[ ! -f "$TDD_PHASE_FILE" ]]; then
    echo "1" > "$TDD_PHASE_FILE"
fi
current_phase=$(cat "$TDD_PHASE_FILE")

cd "$project_dir" || exit 0

# Detect technology profile
profile=$(detect_profile "$project_dir")
profile_name=$(get_profile_name "$project_dir")
compile_cmd=$(get_command "compile" "$project_dir")
test_compile_cmd=$(get_command "testCompile" "$project_dir")
test_cmd=$(get_command "test" "$project_dir")

# Phase 1: Requirements
if [[ "$current_phase" == "1" ]]; then
    if [[ -f "$REQUIREMENTS_MARKER" ]]; then
        echo "2" > "$TDD_PHASE_FILE"
        current_phase="2"
        log_tdd "Phase 1 -> 2: Requirements confirmed, advancing to Interfaces" "$session_id"
        echo ">>> TDD: Phase 1 complete, advancing to Phase 2 (Interfaces)" >&2
    else
        log_tdd "Phase 1: Blocked - requirements not confirmed" "$session_id"
        python3 <<'PYTHON'
import json

reason = """## TDD Phase 1: Requirements Gathering

You cannot proceed until requirements are fully gathered and confirmed.

**Required Actions:**

1. **Review the user's feature request** - understand what they want
2. **Identify any gaps or ambiguities** in the requirements
3. **Ask clarifying questions** using AskUserQuestion tool:
   - Edge cases to handle
   - Error scenarios
   - Expected behavior details
4. **When requirements are complete**, ask user to confirm:
   - Use AskUserQuestion: "Are these requirements complete and accurate?"
   - Options: "Yes, requirements are complete" / "No, I have more details"

5. **When user confirms**, create the marker:
   ```bash
   touch ~/.claude/tmp/tdd-requirements-confirmed
   ```

**Only after creating the marker can you proceed to Phase 2 (Interface Design).**"""

output = {"decision": "block", "reason": reason}
print(json.dumps(output, indent=2))
PYTHON
        exit 0
    fi
fi

# Phase 2: Interfaces
if [[ "$current_phase" == "2" ]]; then
    # Check if interfaces compile
    if ! eval "$compile_cmd" 2>/dev/null; then
        compile_errors=$(eval "$compile_cmd" 2>&1 | head -20)
        python3 - "$compile_errors" "$profile_name" "$compile_cmd" <<'PYTHON'
import sys
import json

errors = sys.argv[1] if len(sys.argv) > 1 else "Unknown compilation error"
profile = sys.argv[2] if len(sys.argv) > 2 else "Unknown"
compile_cmd = sys.argv[3] if len(sys.argv) > 3 else "compile command"

reason = f"""## TDD Phase 2: Interface Design ({profile})

**Compilation FAILED** - fix errors before proceeding.

**Compilation Errors:**
```
{errors}
```

**Required Actions:**

1. **Design class structure** based on requirements from Phase 1
2. **Create empty classes** with proper package organization
3. **Define method signatures** (parameters, return types)
4. **Method bodies should throw** NOT_IMPLEMENTED or TODO

5. **Ensure code compiles**: `{compile_cmd}`

**After code compiles, present interfaces to user for approval.**"""

output = {"decision": "block", "reason": reason}
print(json.dumps(output, indent=2))
PYTHON
        exit 0
    fi

    # Code compiles, check for marker
    if [[ -f "$INTERFACES_MARKER" ]]; then
        echo "3" > "$TDD_PHASE_FILE"
        current_phase="3"
        log_tdd "Phase 2 -> 3: Interfaces approved, advancing to Tests" "$session_id"
        echo ">>> TDD: Phase 2 complete, advancing to Phase 3 (Tests)" >&2
    else
        log_tdd "Phase 2: Blocked - awaiting interface approval" "$session_id"
        python3 - "$profile_name" <<'PYTHON'
import sys
import json

profile = sys.argv[1] if len(sys.argv) > 1 else "Unknown"

reason = f"""## TDD Phase 2: Interface Design ({profile})

**Compilation PASSED** - now get user approval for interfaces.

**Required Actions:**

1. **Present interfaces to user for review**:
   - Use AskUserQuestion: "I've designed the following interfaces. Please review and approve."
   - List the classes/methods you created
   - Options: "Interfaces look good, approved" / "Need changes"

2. **When user approves**, create the marker:
   ```bash
   touch ~/.claude/tmp/tdd-interfaces-designed
   ```

**Only after creating the marker can you proceed to Phase 3 (Test Writing).**"""

output = {"decision": "block", "reason": reason}
print(json.dumps(output, indent=2))
PYTHON
        exit 0
    fi
fi

# Phase 3: Tests
if [[ "$current_phase" == "3" ]]; then
    # Check if tests compile (new gate!)
    if ! eval "$test_compile_cmd" 2>/dev/null; then
        compile_errors=$(eval "$test_compile_cmd" 2>&1 | head -20)
        python3 - "$compile_errors" "$profile_name" "$test_compile_cmd" <<'PYTHON'
import sys
import json

errors = sys.argv[1] if len(sys.argv) > 1 else "Unknown compilation error"
profile = sys.argv[2] if len(sys.argv) > 2 else "Unknown"
test_compile_cmd = sys.argv[3] if len(sys.argv) > 3 else "test compile command"

reason = f"""## TDD Phase 3: Test Writing ({profile})

**Test Compilation FAILED** - fix errors before proceeding.

**Compilation Errors:**
```
{errors}
```

**Required Actions:**

1. **Write tests** that compile correctly
2. **Tests WILL FAIL** when run - that's expected (Red phase of TDD)
3. **Ensure tests compile**: `{test_compile_cmd}`

**After tests compile, present them to user for approval.**"""

output = {"decision": "block", "reason": reason}
print(json.dumps(output, indent=2))
PYTHON
        exit 0
    fi

    if [[ -f "$TESTS_MARKER" ]]; then
        echo "4" > "$TDD_PHASE_FILE"
        current_phase="4"
        log_tdd "Phase 3 -> 4: Tests approved, advancing to Implementation" "$session_id"
        echo ">>> TDD: Phase 3 complete, advancing to Phase 4 (Implementation)" >&2
    else
        log_tdd "Phase 3: Blocked - awaiting test approval" "$session_id"

        # Load tester agent content if available
        TESTER_AGENT="${HOME}/.claude/agents/tester-v2.md"
        TESTER_CONTENT=""
        if [[ -f "$TESTER_AGENT" ]]; then
            TESTER_CONTENT=$(cat "$TESTER_AGENT")
        fi

        python3 - "$TESTER_CONTENT" "$profile_name" <<'PYTHON'
import sys
import json

tester_content = sys.argv[1] if len(sys.argv) > 1 else ""
profile = sys.argv[2] if len(sys.argv) > 2 else "Unknown"

base_context = f"""## TDD Phase 3: Test Writing ({profile})

**Tests compile successfully** - now get user approval.

**Required Actions:**

1. **Write unit/integration tests** based on requirements:
   - Happy path tests (main success scenarios)
   - Edge case tests
   - Error handling tests

2. **Tests WILL FAIL** - that's expected (Red phase of TDD)

3. **Present tests to user for review**:
   - Use AskUserQuestion: "I've written the following tests. Please review and approve."
   - List the test cases you've written
   - Options: "Tests look good, approved" / "Need changes"

4. **When user approves**, create the marker:
   ```bash
   touch ~/.claude/tmp/tdd-tests-approved
   ```

**Only after creating the marker can you proceed to Phase 4 (Implementation).**"""

if tester_content:
    full_context = base_context + "\n\n---\n\n## Testing Guidelines\n\n" + tester_content
else:
    full_context = base_context

output = {"decision": "block", "reason": full_context}
print(json.dumps(output, indent=2))
PYTHON
        exit 0
    fi
fi

# Phase 4: Implementation
if [[ "$current_phase" == "4" ]]; then
    # Check if compile passes
    if ! eval "$compile_cmd" 2>/dev/null; then
        compile_errors=$(eval "$compile_cmd" 2>&1 | head -20)
        python3 - "$compile_errors" "$profile_name" <<'PYTHON'
import sys
import json

errors = sys.argv[1] if len(sys.argv) > 1 else "Unknown compilation error"
profile = sys.argv[2] if len(sys.argv) > 2 else "Unknown"

reason = f"""## TDD Phase 4: Implementation Loop ({profile})

**Compilation FAILED** - fix errors and continue.

**Compilation Errors:**
```
{errors}
```

**Continue the loop:** Implement -> Compile -> Test -> Fix -> Repeat

Fix the compilation errors, then try again."""

output = {"decision": "block", "reason": reason}
print(json.dumps(output, indent=2))
PYTHON
        exit 0
    fi

    # Compile passes, check if tests pass
    if ! eval "$test_cmd" 2>/dev/null; then
        test_output=$(eval "$test_cmd" 2>&1 | tail -30)
        python3 - "$test_output" "$profile_name" <<'PYTHON'
import sys
import json

test_output = sys.argv[1] if len(sys.argv) > 1 else ""
profile = sys.argv[2] if len(sys.argv) > 2 else "Unknown"

reason = f"""## TDD Phase 4: Implementation Loop ({profile})

**Compilation PASSED** but **Tests FAILED** - continue implementing.

**Test Results:**
```
{test_output}
```

**Continue the loop:** Implement -> Compile -> Test -> Fix -> Repeat

Review the failing tests, implement the missing logic, and try again."""

output = {"decision": "block", "reason": reason}
print(json.dumps(output, indent=2))
PYTHON
        exit 0
    fi

    # Both compile and tests pass - TDD complete!
    log_tdd "Phase 4 COMPLETE: All tests passing - TDD workflow finished" "$session_id"
    echo ">>> TDD: Phase 4 complete! All tests passing." >&2

    # Create passing marker
    touch "$TESTS_PASSING_MARKER"

    # Clean up TDD markers
    rm -f "$TDD_MODE_MARKER"
    rm -f "$TDD_PHASE_FILE"
    rm -f "$REQUIREMENTS_MARKER"
    rm -f "$INTERFACES_MARKER"
    rm -f "$TESTS_MARKER"
    exit 0
fi

# Unknown phase, reset to 1
echo "1" > "$TDD_PHASE_FILE"
exit 0
