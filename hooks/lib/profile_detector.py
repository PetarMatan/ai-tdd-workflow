#!/usr/bin/env python3
"""
TDD Workflow - Profile Detector
Detects technology profile based on project files and configuration.

Usage:
    python3 profile_detector.py override <override_file>
    python3 profile_detector.py detect <project_dir> <config_file>

Examples:
    python3 profile_detector.py override ~/.claude/tdd-override.json
    python3 profile_detector.py detect /path/to/project config.json
"""

import json
import os
import sys
from pathlib import Path


def get_override(override_file: str) -> str:
    """Read activeProfile from override file. Returns profile name or empty string."""
    try:
        with open(override_file, 'r') as f:
            profile = json.load(f).get('activeProfile', '')
            return profile or ''
    except Exception:
        return ''


def detect_profile(project_dir: str, config_file: str) -> str:
    """Auto-detect profile based on project files. Returns profile name or empty string."""
    project_path = Path(project_dir).resolve()

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)

        profiles = config.get('profiles', {})

        # Score each profile based on detection criteria
        scores = {}
        for profile_name, profile in profiles.items():
            detection = profile.get('detection', {})
            files = detection.get('files', [])
            patterns = detection.get('patterns', [])

            score = 0

            # Check for detection files
            for f in files:
                if (project_path / f).exists():
                    score += 10

            # Check for source patterns (simplified glob check)
            for pattern in patterns:
                # Convert glob to simple check
                ext = pattern.split('*')[-1] if '*' in pattern else pattern
                pattern_matched = False
                for root, dirs, filenames in os.walk(project_path):
                    for filename in filenames:
                        if filename.endswith(ext):
                            score += 1
                            pattern_matched = True
                            break
                    if pattern_matched:
                        break

            if score > 0:
                scores[profile_name] = score

        # Return highest scoring profile
        if scores:
            return max(scores, key=scores.get)
        return ''
    except Exception:
        return ''


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: profile_detector.py <command> [args...]", file=sys.stderr)
        print("Commands:", file=sys.stderr)
        print("  override <override_file>           - Read override profile", file=sys.stderr)
        print("  detect <project_dir> <config_file> - Auto-detect profile", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "override":
        if len(sys.argv) < 3:
            print("Usage: profile_detector.py override <override_file>", file=sys.stderr)
            sys.exit(1)
        result = get_override(sys.argv[2])
        if result:
            print(result)
    elif command == "detect":
        if len(sys.argv) < 4:
            print("Usage: profile_detector.py detect <project_dir> <config_file>", file=sys.stderr)
            sys.exit(1)
        result = detect_profile(sys.argv[2], sys.argv[3])
        if result:
            print(result)
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
