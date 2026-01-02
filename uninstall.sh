#!/bin/bash
set -e

# TDD Workflow Uninstaller for Claude Code
# Version: 1.0.0

INSTALL_DIR="${HOME}/.claude/tdd-workflow"
COMMANDS_DIR="${HOME}/.claude/commands"
SETTINGS_FILE="${HOME}/.claude/settings.json"

echo "=== TDD Workflow Uninstaller ==="
echo ""

# Remove TDD markers
echo "Cleaning up TDD markers..."
rm -f ~/.claude/tmp/tdd-mode 2>/dev/null || true
rm -f ~/.claude/tmp/tdd-phase 2>/dev/null || true
rm -f ~/.claude/tmp/tdd-requirements-confirmed 2>/dev/null || true
rm -f ~/.claude/tmp/tdd-interfaces-designed 2>/dev/null || true
rm -f ~/.claude/tmp/tdd-tests-approved 2>/dev/null || true
rm -f ~/.claude/tmp/tdd-tests-passing 2>/dev/null || true

# Remove skills
echo "Removing skills..."
rm -f "$COMMANDS_DIR/tdd.md" 2>/dev/null || true
rm -f "$COMMANDS_DIR/tdd-status.md" 2>/dev/null || true
rm -f "$COMMANDS_DIR/tdd-reset.md" 2>/dev/null || true

# Remove installation directory
if [[ -d "$INSTALL_DIR" ]]; then
    echo "Removing installation directory..."
    rm -rf "$INSTALL_DIR"
fi

# Update settings.json
echo ""
echo "=== Settings Cleanup ==="
echo ""

if [[ -f "$SETTINGS_FILE" ]]; then
    read -p "Would you like to remove TDD hooks from settings.json? (y/n): " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Backup existing settings
        cp "$SETTINGS_FILE" "${SETTINGS_FILE}.backup.$(date +%Y%m%d%H%M%S)"
        echo "Backup created."

        # Use Python to remove TDD hooks
        python3 - "$SETTINGS_FILE" <<'PYTHON'
import json
import sys

settings_file = sys.argv[1]

with open(settings_file, 'r') as f:
    settings = json.load(f)

# Remove TDD-related permissions
if 'permissions' in settings and 'allow' in settings['permissions']:
    tdd_patterns = ['tdd-', 'tdd_']
    settings['permissions']['allow'] = [
        p for p in settings['permissions']['allow']
        if not any(pattern in p for pattern in tdd_patterns)
    ]

# Remove TDD hooks
if 'hooks' in settings:
    for event in list(settings['hooks'].keys()):
        if event in settings['hooks']:
            settings['hooks'][event] = [
                hook_config for hook_config in settings['hooks'][event]
                if not any(
                    'tdd-' in h.get('command', '')
                    for h in hook_config.get('hooks', [])
                )
            ]
            # Remove empty event lists
            if not settings['hooks'][event]:
                del settings['hooks'][event]

with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

print("TDD hooks removed from settings.")
PYTHON
    else
        echo "Skipping settings cleanup. You may need to manually remove TDD hooks."
    fi
fi

echo ""
echo "=== Uninstall Complete ==="
echo ""
echo "TDD Workflow has been removed."
echo "Restart Claude Code to apply changes."
