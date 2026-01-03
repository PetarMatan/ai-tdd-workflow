#!/usr/bin/env bats
# Unit tests for lib/agents.sh

load '../test_helper'

setup() {
    setup_test_environment

    # Source the agents library
    source "$HOOKS_DIR/lib/agents.sh"

    # Create agents directory
    mkdir -p "$HOME/.claude/agents"
}

teardown() {
    teardown_test_environment
}

# =============================================================================
# get_agents_for_phase tests
# =============================================================================

@test "get_agents_for_phase returns agent with matching phase" {
    # Create agent with phases frontmatter
    cat > "$HOME/.claude/agents/test-agent.md" << 'EOF'
---
name: Test Agent
phases: [2, 3]
---

# Test Agent

This is a test agent.
EOF

    run get_agents_for_phase "2"
    [ "$status" -eq 0 ]
    [[ "$output" == *"test-agent.md"* ]]
}

@test "get_agents_for_phase returns empty for non-matching phase" {
    cat > "$HOME/.claude/agents/test-agent.md" << 'EOF'
---
name: Test Agent
phases: [2, 3]
---

# Test Agent
EOF

    run get_agents_for_phase "1"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "get_agents_for_phase returns multiple matching agents" {
    cat > "$HOME/.claude/agents/agent1.md" << 'EOF'
---
name: Agent One
phases: [2]
---
# Agent One
EOF

    cat > "$HOME/.claude/agents/agent2.md" << 'EOF'
---
name: Agent Two
phases: [2, 3]
---
# Agent Two
EOF

    cat > "$HOME/.claude/agents/agent3.md" << 'EOF'
---
name: Agent Three
phases: [4]
---
# Agent Three
EOF

    run get_agents_for_phase "2"
    [ "$status" -eq 0 ]
    [[ "$output" == *"agent1.md"* ]]
    [[ "$output" == *"agent2.md"* ]]
    [[ "$output" != *"agent3.md"* ]]
}

@test "get_agents_for_phase ignores agents without phases field" {
    cat > "$HOME/.claude/agents/no-phases.md" << 'EOF'
---
name: No Phases Agent
---
# No Phases Agent
EOF

    run get_agents_for_phase "1"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "get_agents_for_phase ignores agents without frontmatter" {
    cat > "$HOME/.claude/agents/no-frontmatter.md" << 'EOF'
# No Frontmatter Agent

This agent has no YAML frontmatter.
EOF

    run get_agents_for_phase "1"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "get_agents_for_phase handles empty agents directory" {
    rm -rf "$HOME/.claude/agents"
    mkdir -p "$HOME/.claude/agents"

    run get_agents_for_phase "1"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "get_agents_for_phase handles missing agents directory" {
    rm -rf "$HOME/.claude/agents"

    run get_agents_for_phase "1"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "get_agents_for_phase handles phases array with spaces" {
    cat > "$HOME/.claude/agents/spaced.md" << 'EOF'
---
name: Spaced Agent
phases: [ 1, 2, 3 ]
---
# Spaced Agent
EOF

    run get_agents_for_phase "2"
    [ "$status" -eq 0 ]
    [[ "$output" == *"spaced.md"* ]]
}

# =============================================================================
# load_agent_content tests
# =============================================================================

@test "load_agent_content returns content without frontmatter" {
    cat > "$HOME/.claude/agents/test-agent.md" << 'EOF'
---
name: Test Agent
phases: [2]
---

# Test Agent

This is the content.
EOF

    run load_agent_content "$HOME/.claude/agents/test-agent.md"
    [ "$status" -eq 0 ]
    [[ "$output" == *"# Test Agent"* ]]
    [[ "$output" == *"This is the content."* ]]
    [[ "$output" != *"phases:"* ]]
}

@test "load_agent_content returns full content when no frontmatter" {
    cat > "$HOME/.claude/agents/no-fm.md" << 'EOF'
# No Frontmatter Agent

All content here.
EOF

    run load_agent_content "$HOME/.claude/agents/no-fm.md"
    [ "$status" -eq 0 ]
    [[ "$output" == *"# No Frontmatter Agent"* ]]
    [[ "$output" == *"All content here."* ]]
}

@test "load_agent_content returns error for missing file" {
    run load_agent_content "$HOME/.claude/agents/nonexistent.md"
    [ "$status" -ne 0 ]
}

# =============================================================================
# get_agent_name tests
# =============================================================================

@test "get_agent_name returns name from frontmatter" {
    cat > "$HOME/.claude/agents/my-agent.md" << 'EOF'
---
name: My Custom Agent
phases: [1]
---
# Agent
EOF

    run get_agent_name "$HOME/.claude/agents/my-agent.md"
    [ "$status" -eq 0 ]
    [ "$output" = "My Custom Agent" ]
}

@test "get_agent_name derives name from filename when no frontmatter name" {
    cat > "$HOME/.claude/agents/api-designer.md" << 'EOF'
---
phases: [2]
---
# API Designer
EOF

    run get_agent_name "$HOME/.claude/agents/api-designer.md"
    [ "$status" -eq 0 ]
    [ "$output" = "Api Designer" ]
}

@test "get_agent_name derives name from filename when no frontmatter" {
    cat > "$HOME/.claude/agents/test-expert.md" << 'EOF'
# Test Expert

No frontmatter here.
EOF

    run get_agent_name "$HOME/.claude/agents/test-expert.md"
    [ "$status" -eq 0 ]
    [ "$output" = "Test Expert" ]
}

# =============================================================================
# list_phase_bound_agents tests
# =============================================================================

@test "list_phase_bound_agents returns JSON array" {
    cat > "$HOME/.claude/agents/agent1.md" << 'EOF'
---
name: Agent One
phases: [1, 2]
---
# Agent One
EOF

    run list_phase_bound_agents
    [ "$status" -eq 0 ]
    [[ "$output" == "["* ]]
    [[ "$output" == *"]" ]]
    [[ "$output" == *'"name": "Agent One"'* ]] || [[ "$output" == *'"name":"Agent One"'* ]]
}

@test "list_phase_bound_agents returns empty array when no agents" {
    rm -rf "$HOME/.claude/agents"
    mkdir -p "$HOME/.claude/agents"

    run list_phase_bound_agents
    [ "$status" -eq 0 ]
    [ "$output" = "[]" ]
}

@test "list_phase_bound_agents excludes agents without phases" {
    cat > "$HOME/.claude/agents/with-phases.md" << 'EOF'
---
name: With Phases
phases: [1]
---
# With Phases
EOF

    cat > "$HOME/.claude/agents/without-phases.md" << 'EOF'
---
name: Without Phases
---
# Without Phases
EOF

    run list_phase_bound_agents
    [ "$status" -eq 0 ]
    [[ "$output" == *"With Phases"* ]]
    [[ "$output" != *"Without Phases"* ]]
}

@test "list_phase_bound_agents includes phases array in output" {
    cat > "$HOME/.claude/agents/multi-phase.md" << 'EOF'
---
name: Multi Phase
phases: [2, 3, 4]
---
# Multi Phase
EOF

    run list_phase_bound_agents
    [ "$status" -eq 0 ]
    [[ "$output" == *'"phases"'* ]]
    [[ "$output" == *"2"* ]]
    [[ "$output" == *"3"* ]]
    [[ "$output" == *"4"* ]]
}
