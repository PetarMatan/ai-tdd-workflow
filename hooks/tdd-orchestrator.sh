#!/bin/bash
set -e

# TDD Workflow Orchestrator - Stop Hook
# Enforces TDD phase progression: Requirements -> Interfaces -> Tests -> Implementation
# Version: 1.0.0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/log.sh"
source "$SCRIPT_DIR/lib/config.sh"
source "$SCRIPT_DIR/lib/agents.sh"
source "$SCRIPT_DIR/lib/markers.sh"

# Load agents configured for a specific phase and return their content
# Usage: load_phase_agents <phase_number> <session_id>
# Returns: Combined agent content for injection into context
load_phase_agents() {
    local phase="$1"
    local session_id="$2"
    local agent_content=""

    local agents
    agents=$(get_agents_for_phase "$phase")

    if [[ -z "$agents" ]]; then
        return 0
    fi

    while IFS= read -r agent_file; do
        if [[ -n "$agent_file" ]]; then
            local agent_name
            agent_name=$(get_agent_name "$agent_file")
            log_tdd "Loading agent '$agent_name' for phase $phase" "$session_id"
            echo ">>> TDD: Loaded agent: $agent_name" >&2

            local content
            content=$(load_agent_content "$agent_file")
            if [[ -n "$content" ]]; then
                agent_content="${agent_content}

---

## Agent: ${agent_name}

${content}"
            fi
        fi
    done <<< "$agents"

    echo "$agent_content"
}

# Parse hook input
input=$(cat)
eval "$(echo "$input" | python3 "$SCRIPT_DIR/lib/hook_io.py" parse)"
stop_hook_active="$HOOK_STOP_ACTIVE"
project_dir="$HOOK_CWD"
session_id="$HOOK_SESSION_ID"

# Initialize session-scoped markers
setup_markers "$session_id"

# Prevent infinite loops
if [[ "$stop_hook_active" == "True" ]]; then
    exit 0
fi

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

        # Load agents configured for phase 1
        phase1_agents=$(load_phase_agents "1" "$session_id")

        marker_dir="~/.claude/tmp/tdd-$session_id"
        reason="## TDD Phase 1: Requirements Gathering

You cannot proceed until requirements are fully gathered and confirmed.

**Required Actions:**

1. **Review the user's feature request** - understand what they want
2. **Identify any gaps or ambiguities** in the requirements
3. **Ask clarifying questions** using AskUserQuestion tool:
   - Edge cases to handle
   - Error scenarios
   - Expected behavior details
4. **When requirements are complete**, ask user to confirm:
   - Use AskUserQuestion: \"Are these requirements complete and accurate?\"
   - Options: \"Yes, requirements are complete\" / \"No, I have more details\"

5. **When user confirms**, create the marker:
   \`\`\`bash
   mkdir -p $marker_dir && touch $marker_dir/tdd-requirements-confirmed
   \`\`\`

**Only after creating the marker can you proceed to Phase 2 (Interface Design).**"

        python3 "$SCRIPT_DIR/lib/hook_io.py" block "$reason" "$phase1_agents"
        exit 0
    fi
fi

# Phase 2: Interfaces
if [[ "$current_phase" == "2" ]]; then
    # Check if interfaces compile (capture output on first run)
    set +e
    compile_output=$(eval "$compile_cmd" 2>&1)
    compile_exit_code=$?
    set -e
    if [[ $compile_exit_code -ne 0 ]]; then
        # Load agents only when blocking
        phase2_agents=$(load_phase_agents "2" "$session_id")
        compile_errors=$(echo "$compile_output" | head -20)
        reason="## TDD Phase 2: Interface Design ($profile_name)

**Compilation FAILED** - fix errors before proceeding.

**Compilation Errors:**
\`\`\`
$compile_errors
\`\`\`

**Required Actions:**

1. **Design class structure** based on requirements from Phase 1
2. **Create empty classes** with proper package organization
3. **Define method signatures** (parameters, return types)
4. **Method bodies should throw** NOT_IMPLEMENTED or TODO

5. **Ensure code compiles**: \`$compile_cmd\`

**After code compiles, present interfaces to user for approval.**"

        python3 "$SCRIPT_DIR/lib/hook_io.py" block "$reason" "$phase2_agents"
        exit 0
    fi

    # Code compiles, check for marker
    if [[ -f "$INTERFACES_MARKER" ]]; then
        echo "3" > "$TDD_PHASE_FILE"
        current_phase="3"
        log_tdd "Phase 2 -> 3: Interfaces approved, advancing to Tests" "$session_id"
        echo ">>> TDD: Phase 2 complete, advancing to Phase 3 (Tests)" >&2
    else
        # Load agents only when blocking
        phase2_agents=$(load_phase_agents "2" "$session_id")
        log_tdd "Phase 2: Blocked - awaiting interface approval" "$session_id"
        marker_dir="~/.claude/tmp/tdd-$session_id"
        reason="## TDD Phase 2: Interface Design ($profile_name)

**Compilation PASSED** - now get user approval for interfaces.

**Required Actions:**

1. **Present interfaces to user for review**:
   - Use AskUserQuestion: \"I've designed the following interfaces. Please review and approve.\"
   - List the classes/methods you created
   - Options: \"Interfaces look good, approved\" / \"Need changes\"

2. **When user approves**, create the marker:
   \`\`\`bash
   mkdir -p $marker_dir && touch $marker_dir/tdd-interfaces-designed
   \`\`\`

**Only after creating the marker can you proceed to Phase 3 (Test Writing).**"

        python3 "$SCRIPT_DIR/lib/hook_io.py" block "$reason" "$phase2_agents"
        exit 0
    fi
fi

# Phase 3: Tests
if [[ "$current_phase" == "3" ]]; then
    # Check if tests compile (capture output on first run)
    set +e
    compile_output=$(eval "$test_compile_cmd" 2>&1)
    compile_exit_code=$?
    set -e
    if [[ $compile_exit_code -ne 0 ]]; then
        # Load agents only when blocking
        phase3_agents=$(load_phase_agents "3" "$session_id")
        compile_errors=$(echo "$compile_output" | head -20)
        reason="## TDD Phase 3: Test Writing ($profile_name)

**Test Compilation FAILED** - fix errors before proceeding.

**Compilation Errors:**
\`\`\`
$compile_errors
\`\`\`

**Required Actions:**

1. **Write tests** that compile correctly
2. **Tests WILL FAIL** when run - that's expected (Red phase of TDD)
3. **Ensure tests compile**: \`$test_compile_cmd\`

**After tests compile, present them to user for approval.**"

        python3 "$SCRIPT_DIR/lib/hook_io.py" block "$reason" "$phase3_agents"
        exit 0
    fi

    if [[ -f "$TESTS_MARKER" ]]; then
        echo "4" > "$TDD_PHASE_FILE"
        current_phase="4"
        log_tdd "Phase 3 -> 4: Tests approved, advancing to Implementation" "$session_id"
        echo ">>> TDD: Phase 3 complete, advancing to Phase 4 (Implementation)" >&2
    else
        # Load agents only when blocking
        phase3_agents=$(load_phase_agents "3" "$session_id")
        log_tdd "Phase 3: Blocked - awaiting test approval" "$session_id"
        marker_dir="~/.claude/tmp/tdd-$session_id"
        reason="## TDD Phase 3: Test Writing ($profile_name)

**Tests compile successfully** - now get user approval.

**Required Actions:**

1. **Write unit/integration tests** based on requirements:
   - Happy path tests (main success scenarios)
   - Edge case tests
   - Error handling tests

2. **Tests WILL FAIL** - that's expected (Red phase of TDD)

3. **Present tests to user for review**:
   - Use AskUserQuestion: \"I've written the following tests. Please review and approve.\"
   - List the test cases you've written
   - Options: \"Tests look good, approved\" / \"Need changes\"

4. **When user approves**, create the marker:
   \`\`\`bash
   mkdir -p $marker_dir && touch $marker_dir/tdd-tests-approved
   \`\`\`

**Only after creating the marker can you proceed to Phase 4 (Implementation).**"

        python3 "$SCRIPT_DIR/lib/hook_io.py" block "$reason" "$phase3_agents"
        exit 0
    fi
fi

# Phase 4: Implementation
if [[ "$current_phase" == "4" ]]; then
    # Check if compile passes (capture output on first run)
    set +e
    compile_output=$(eval "$compile_cmd" 2>&1)
    compile_exit_code=$?
    set -e
    if [[ $compile_exit_code -ne 0 ]]; then
        # Load agents only when blocking
        phase4_agents=$(load_phase_agents "4" "$session_id")
        compile_errors=$(echo "$compile_output" | head -20)
        reason="## TDD Phase 4: Implementation Loop ($profile_name)

**Compilation FAILED** - fix errors and continue.

**Compilation Errors:**
\`\`\`
$compile_errors
\`\`\`

**Continue the loop:** Implement -> Compile -> Test -> Fix -> Repeat

Fix the compilation errors, then try again."

        python3 "$SCRIPT_DIR/lib/hook_io.py" block "$reason" "$phase4_agents"
        exit 0
    fi

    # Compile passes, check if tests pass (capture output on first run)
    set +e
    test_full_output=$(eval "$test_cmd" 2>&1)
    test_exit_code=$?
    set -e
    if [[ $test_exit_code -ne 0 ]]; then
        # Load agents only when blocking
        phase4_agents=$(load_phase_agents "4" "$session_id")
        test_output=$(echo "$test_full_output" | tail -30)
        reason="## TDD Phase 4: Implementation Loop ($profile_name)

**Compilation PASSED** but **Tests FAILED** - continue implementing.

**Test Results:**
\`\`\`
$test_output
\`\`\`

**Continue the loop:** Implement -> Compile -> Test -> Fix -> Repeat

Review the failing tests, implement the missing logic, and try again."

        python3 "$SCRIPT_DIR/lib/hook_io.py" block "$reason" "$phase4_agents"
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
