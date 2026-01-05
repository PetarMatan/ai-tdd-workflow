#!/bin/bash
# Agent Discovery Library
# Discovers and loads agents based on TDD phase configuration
# Version: 1.0.0

# Python library path and agents directory (relative to this agents.sh file)
_AGENTS_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_PARSER="${_AGENTS_LIB_DIR}/agent_parser.py"
# TDD_AGENTS_DIR can be overridden for testing
TDD_AGENTS_DIR="${TDD_AGENTS_DIR:-${_AGENTS_LIB_DIR}/../../agents}"

# Get agents configured for a specific phase
# Usage: get_agents_for_phase <phase_number>
# Returns: newline-separated list of agent file paths
get_agents_for_phase() {
    local phase="$1"
    local agents_dir="$TDD_AGENTS_DIR"

    if [[ ! -d "$agents_dir" ]]; then
        return 0
    fi

    python3 "$AGENT_PARSER" agents-for-phase "$agents_dir" "$phase"
}

# Load agent content (returns the markdown content without frontmatter)
# Usage: load_agent_content <agent_file_path>
load_agent_content() {
    local agent_file="$1"

    if [[ ! -f "$agent_file" ]]; then
        return 1
    fi

    python3 "$AGENT_PARSER" get-content "$agent_file"
}

# Get agent name from frontmatter or filename
# Usage: get_agent_name <agent_file_path>
get_agent_name() {
    local agent_file="$1"

    python3 "$AGENT_PARSER" get-name "$agent_file"
}

# Get all agents with their phase bindings (for status display)
# Usage: list_phase_bound_agents
# Returns: JSON array of {name, file, phases}
list_phase_bound_agents() {
    local agents_dir="$TDD_AGENTS_DIR"

    if [[ ! -d "$agents_dir" ]]; then
        echo "[]"
        return 0
    fi

    python3 "$AGENT_PARSER" list-agents "$agents_dir"
}
