#!/usr/bin/env python3
"""
TDD Workflow - Configuration Reader
Reads values from JSON configuration files using dot-notation paths.

Usage:
    python3 config_reader.py get <path> <config_file>

Examples:
    python3 config_reader.py get "profiles.kotlin-maven.name" config.json
    python3 config_reader.py get "profiles.typescript-npm.commands.compile" config.json
"""

import json
import sys


def config_get(path: str, config_file: str) -> None:
    """Read a value from JSON config using dot-notation path."""
    parts = path.split('.')

    try:
        with open(config_file, 'r') as f:
            data = json.load(f)

        for part in parts:
            if isinstance(data, dict):
                data = data.get(part)
            else:
                data = None
                break

        if data is not None:
            if isinstance(data, (dict, list)):
                print(json.dumps(data))
            else:
                print(data)
    except Exception:
        sys.exit(1)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: config_reader.py <command> [args...]", file=sys.stderr)
        print("Commands:", file=sys.stderr)
        print("  get <path> <config_file>  - Read value at path", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "get":
        if len(sys.argv) < 4:
            print("Usage: config_reader.py get <path> <config_file>", file=sys.stderr)
            sys.exit(1)
        config_get(sys.argv[2], sys.argv[3])
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
