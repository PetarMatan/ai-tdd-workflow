#!/usr/bin/env python3
"""
Pattern Matcher Library for TDD Workflow
Provides glob-to-regex conversion and file pattern matching.

Usage:
    python3 pattern_matcher.py match <file_path> <patterns_json>
    python3 pattern_matcher.py to_regex <pattern>

Exit codes:
    0 - Match found (for 'match' command)
    1 - No match (for 'match' command)
"""

import re
import json
import sys


def glob_to_regex(pattern):
    """
    Convert a glob pattern to a regex pattern.

    Supports:
    - ** matches zero or more directories
    - * matches anything except /
    - ? matches single character except /
    """
    # Escape special regex chars except * and ?
    regex = re.escape(pattern)

    # Unescape the glob special chars we want to handle
    regex = regex.replace(r'\*\*', '__DOUBLE_STAR__')
    regex = regex.replace(r'\*', '__SINGLE_STAR__')
    regex = regex.replace(r'\?', '__QUESTION__')

    # Convert glob patterns to regex
    regex = regex.replace('__DOUBLE_STAR__/', '(?:.*/)?')  # **/ matches zero or more directories
    regex = regex.replace('__DOUBLE_STAR__', '.*')         # ** at end matches anything
    regex = regex.replace('__SINGLE_STAR__', '[^/]*')      # * matches anything except /
    regex = regex.replace('__QUESTION__', '[^/]')          # ? matches single char except /

    # Pattern should match the end of the path (with optional leading directories)
    return f'^(?:.*/)?{regex}$'


def matches_pattern(file_path, pattern):
    """Check if a file path matches a single glob pattern."""
    regex = glob_to_regex(pattern)
    return bool(re.match(regex, file_path))


def matches_any(file_path, patterns):
    """
    Check if a file path matches any of the given patterns.

    Args:
        file_path: The file path to check
        patterns: A single pattern string, JSON array string, or list of patterns

    Returns:
        True if file matches any pattern, False otherwise
    """
    # Handle different input formats
    if isinstance(patterns, str):
        if patterns.startswith('['):
            patterns = json.loads(patterns)
        else:
            patterns = [patterns]

    for pattern in patterns:
        if matches_pattern(file_path, pattern):
            return True
    return False


def main():
    if len(sys.argv) < 2:
        print("Usage: pattern_matcher.py <command> [args...]", file=sys.stderr)
        print("Commands:", file=sys.stderr)
        print("  match <file_path> <patterns>  - Check if file matches patterns", file=sys.stderr)
        print("  to_regex <pattern>            - Convert glob to regex", file=sys.stderr)
        sys.exit(2)

    command = sys.argv[1]

    if command == 'match':
        if len(sys.argv) < 4:
            print("Usage: pattern_matcher.py match <file_path> <patterns>", file=sys.stderr)
            sys.exit(2)

        file_path = sys.argv[2]
        patterns = sys.argv[3]

        if matches_any(file_path, patterns):
            sys.exit(0)
        else:
            sys.exit(1)

    elif command == 'to_regex':
        if len(sys.argv) < 3:
            print("Usage: pattern_matcher.py to_regex <pattern>", file=sys.stderr)
            sys.exit(2)

        pattern = sys.argv[2]
        print(glob_to_regex(pattern))
        sys.exit(0)

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
