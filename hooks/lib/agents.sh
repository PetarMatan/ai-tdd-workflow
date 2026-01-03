#!/bin/bash
# Agent Discovery Library
# Discovers and loads agents based on TDD phase configuration
# Version: 1.0.0

# Get agents configured for a specific phase
# Usage: get_agents_for_phase <phase_number>
# Returns: newline-separated list of agent file paths
get_agents_for_phase() {
    local phase="$1"
    local agents_dir="${HOME}/.claude/agents"

    if [[ ! -d "$agents_dir" ]]; then
        return 0
    fi

    python3 - "$agents_dir" "$phase" <<'PYTHON'
import sys
import os
import re

agents_dir = sys.argv[1]
target_phase = int(sys.argv[2])

def parse_frontmatter(filepath):
    """Parse YAML frontmatter from markdown file."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        # Check for frontmatter delimiters
        if not content.startswith('---'):
            return None

        # Find end of frontmatter
        end_match = re.search(r'\n---\s*\n', content[3:])
        if not end_match:
            return None

        frontmatter = content[3:end_match.start() + 3]

        # Simple YAML parsing for phases field
        # Look for: phases: [1, 2, 3] or phases: [1,2,3]
        phases_match = re.search(r'phases:\s*\[([^\]]*)\]', frontmatter)
        if phases_match:
            phases_str = phases_match.group(1)
            phases = [int(p.strip()) for p in phases_str.split(',') if p.strip().isdigit()]
            return {'phases': phases}

        return None
    except Exception:
        return None

# Scan agents directory
for filename in os.listdir(agents_dir):
    if not filename.endswith('.md'):
        continue

    filepath = os.path.join(agents_dir, filename)
    if not os.path.isfile(filepath):
        continue

    frontmatter = parse_frontmatter(filepath)
    if frontmatter and 'phases' in frontmatter:
        if target_phase in frontmatter['phases']:
            print(filepath)
PYTHON
}

# Load agent content (returns the markdown content without frontmatter)
# Usage: load_agent_content <agent_file_path>
load_agent_content() {
    local agent_file="$1"

    if [[ ! -f "$agent_file" ]]; then
        return 1
    fi

    python3 - "$agent_file" <<'PYTHON'
import sys
import re

filepath = sys.argv[1]

try:
    with open(filepath, 'r') as f:
        content = f.read()

    # Remove frontmatter if present
    if content.startswith('---'):
        end_match = re.search(r'\n---\s*\n', content[3:])
        if end_match:
            content = content[end_match.end() + 3:]

    print(content)
except Exception as e:
    sys.exit(1)
PYTHON
}

# Get agent name from frontmatter or filename
# Usage: get_agent_name <agent_file_path>
get_agent_name() {
    local agent_file="$1"

    python3 - "$agent_file" <<'PYTHON'
import sys
import os
import re

filepath = sys.argv[1]
filename = os.path.basename(filepath)

try:
    with open(filepath, 'r') as f:
        content = f.read()

    # Try to get name from frontmatter
    if content.startswith('---'):
        end_match = re.search(r'\n---\s*\n', content[3:])
        if end_match:
            frontmatter = content[3:end_match.start() + 3]
            name_match = re.search(r'name:\s*(.+)', frontmatter)
            if name_match:
                print(name_match.group(1).strip())
                sys.exit(0)

    # Fallback: derive from filename
    name = filename.replace('.md', '').replace('-', ' ').title()
    print(name)
except Exception:
    # Ultimate fallback
    print(filename.replace('.md', ''))
PYTHON
}

# Get all agents with their phase bindings (for status display)
# Usage: list_phase_bound_agents
# Returns: JSON array of {name, file, phases}
list_phase_bound_agents() {
    local agents_dir="${HOME}/.claude/agents"

    if [[ ! -d "$agents_dir" ]]; then
        echo "[]"
        return 0
    fi

    python3 - "$agents_dir" <<'PYTHON'
import sys
import os
import re
import json

agents_dir = sys.argv[1]
result = []

def parse_frontmatter(filepath):
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        if not content.startswith('---'):
            return None

        end_match = re.search(r'\n---\s*\n', content[3:])
        if not end_match:
            return None

        frontmatter = content[3:end_match.start() + 3]

        data = {}

        # Parse name
        name_match = re.search(r'name:\s*(.+)', frontmatter)
        if name_match:
            data['name'] = name_match.group(1).strip()

        # Parse phases
        phases_match = re.search(r'phases:\s*\[([^\]]*)\]', frontmatter)
        if phases_match:
            phases_str = phases_match.group(1)
            data['phases'] = [int(p.strip()) for p in phases_str.split(',') if p.strip().isdigit()]

        return data if data else None
    except Exception:
        return None

for filename in os.listdir(agents_dir):
    if not filename.endswith('.md'):
        continue

    filepath = os.path.join(agents_dir, filename)
    if not os.path.isfile(filepath):
        continue

    frontmatter = parse_frontmatter(filepath)
    if frontmatter and 'phases' in frontmatter:
        name = frontmatter.get('name', filename.replace('.md', '').replace('-', ' ').title())
        result.append({
            'name': name,
            'file': filepath,
            'phases': frontmatter['phases']
        })

print(json.dumps(result))
PYTHON
}
