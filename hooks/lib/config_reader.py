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


def get_config_value(path: str, config_file: str):
    """Read a value from JSON config using dot-notation path. Returns the value or None."""
    parts = path.split('.')

    try:
        with open(config_file, 'r') as f:
            data = json.load(f)

        for part in parts:
            if isinstance(data, dict):
                data = data.get(part)
            else:
                return None

        return data
    except Exception:
        return None


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
        result = get_config_value(sys.argv[2], sys.argv[3])
        if result is not None:
            if isinstance(result, (dict, list)):
                print(json.dumps(result))
            else:
                print(result)
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
