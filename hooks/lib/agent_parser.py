#!/usr/bin/env python3
"""
TDD Workflow - Agent Parser
Parses agent markdown files with YAML frontmatter.

Usage:
    python3 agent_parser.py get-phases <agent_file>
    python3 agent_parser.py get-name <agent_file>
    python3 agent_parser.py get-content <agent_file>
    python3 agent_parser.py list-agents <agents_dir>
    python3 agent_parser.py agents-for-phase <agents_dir> <phase>

Examples:
    python3 agent_parser.py get-phases ~/.claude/agents/tester.md
    python3 agent_parser.py list-agents ~/.claude/agents
    python3 agent_parser.py agents-for-phase ~/.claude/agents 3
"""

import json
import os
import re
import sys
from typing import Optional


def parse_frontmatter(filepath: str) -> Optional[dict]:
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
        data = {}

        # Parse name
        name_match = re.search(r'name:\s*(.+)', frontmatter)
        if name_match:
            data['name'] = name_match.group(1).strip()

        # Parse phases: [1, 2, 3] or phases: [1,2,3]
        phases_match = re.search(r'phases:\s*\[([^\]]*)\]', frontmatter)
        if phases_match:
            phases_str = phases_match.group(1)
            data['phases'] = [int(p.strip()) for p in phases_str.split(',') if p.strip().isdigit()]

        return data if data else None
    except Exception:
        return None


def get_content_without_frontmatter(filepath: str) -> str:
    """Get markdown content without frontmatter."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()

        # Remove frontmatter if present
        if content.startswith('---'):
            end_match = re.search(r'\n---\s*\n', content[3:])
            if end_match:
                content = content[end_match.end() + 3:]

        return content
    except Exception:
        return ""


def get_phases(agent_file: str) -> None:
    """Print phases array as JSON."""
    frontmatter = parse_frontmatter(agent_file)
    if frontmatter and 'phases' in frontmatter:
        print(json.dumps(frontmatter['phases']))
    else:
        print("[]")


def get_name(agent_file: str) -> None:
    """Print agent name."""
    frontmatter = parse_frontmatter(agent_file)

    if frontmatter and 'name' in frontmatter:
        print(frontmatter['name'])
    else:
        # Fallback: derive from filename
        filename = os.path.basename(agent_file)
        name = filename.replace('.md', '').replace('-', ' ').title()
        print(name)


def get_content(agent_file: str) -> None:
    """Print agent content without frontmatter."""
    content = get_content_without_frontmatter(agent_file)
    if content:
        print(content)
    else:
        sys.exit(1)


def list_agents(agents_dir: str) -> None:
    """List all agents with phase bindings as JSON."""
    result = []

    if not os.path.isdir(agents_dir):
        print("[]")
        return

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


def agents_for_phase(agents_dir: str, phase: int) -> None:
    """Print agent file paths that match the given phase."""
    if not os.path.isdir(agents_dir):
        return

    for filename in os.listdir(agents_dir):
        if not filename.endswith('.md'):
            continue

        filepath = os.path.join(agents_dir, filename)
        if not os.path.isfile(filepath):
            continue

        frontmatter = parse_frontmatter(filepath)
        if frontmatter and 'phases' in frontmatter:
            if phase in frontmatter['phases']:
                print(filepath)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: agent_parser.py <command> [args...]", file=sys.stderr)
        print("Commands:", file=sys.stderr)
        print("  get-phases <agent_file>              - Get phases array as JSON", file=sys.stderr)
        print("  get-name <agent_file>                - Get agent name", file=sys.stderr)
        print("  get-content <agent_file>             - Get content without frontmatter", file=sys.stderr)
        print("  list-agents <agents_dir>             - List all phase-bound agents as JSON", file=sys.stderr)
        print("  agents-for-phase <agents_dir> <phase> - List agents for a phase", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "get-phases":
        if len(sys.argv) < 3:
            print("Usage: agent_parser.py get-phases <agent_file>", file=sys.stderr)
            sys.exit(1)
        get_phases(sys.argv[2])

    elif command == "get-name":
        if len(sys.argv) < 3:
            print("Usage: agent_parser.py get-name <agent_file>", file=sys.stderr)
            sys.exit(1)
        get_name(sys.argv[2])

    elif command == "get-content":
        if len(sys.argv) < 3:
            print("Usage: agent_parser.py get-content <agent_file>", file=sys.stderr)
            sys.exit(1)
        get_content(sys.argv[2])

    elif command == "list-agents":
        if len(sys.argv) < 3:
            print("Usage: agent_parser.py list-agents <agents_dir>", file=sys.stderr)
            sys.exit(1)
        list_agents(sys.argv[2])

    elif command == "agents-for-phase":
        if len(sys.argv) < 4:
            print("Usage: agent_parser.py agents-for-phase <agents_dir> <phase>", file=sys.stderr)
            sys.exit(1)
        agents_for_phase(sys.argv[2], int(sys.argv[3]))

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
