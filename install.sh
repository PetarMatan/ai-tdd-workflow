#!/bin/bash
set -e

# TDD Workflow Installer for Claude Code
# Version: 1.0.0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${HOME}/.claude/tdd-workflow"
COMMANDS_DIR="${HOME}/.claude/commands"
SETTINGS_FILE="${HOME}/.claude/settings.json"

echo "=== TDD Workflow Installer ==="
echo ""

# Check for required tools
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not installed."
    exit 1
fi

# Create directories
echo "Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$COMMANDS_DIR"
mkdir -p "${HOME}/.claude/tmp"
mkdir -p "${HOME}/.claude/logs/sessions"

# Copy hook files
echo "Installing hooks..."
cp -r "$SCRIPT_DIR/hooks" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/hooks/"*.sh
chmod +x "$INSTALL_DIR/hooks/lib/"*.sh 2>/dev/null || true

# Copy config
echo "Installing configuration..."
cp -r "$SCRIPT_DIR/config" "$INSTALL_DIR/"

# Copy agents (optional - for reference)
echo "Installing agents..."
cp -r "$SCRIPT_DIR/agents" "$INSTALL_DIR/"

# Install skills as commands
echo "Installing skills..."
cp "$SCRIPT_DIR/skills/tdd.md" "$COMMANDS_DIR/tdd.md"
cp "$SCRIPT_DIR/skills/tdd-status.md" "$COMMANDS_DIR/tdd-status.md"
cp "$SCRIPT_DIR/skills/tdd-reset.md" "$COMMANDS_DIR/tdd-reset.md"

# Update settings.json
echo ""
echo "=== Settings Configuration ==="
echo ""

if [[ -f "$SETTINGS_FILE" ]]; then
    echo "Found existing settings.json"
    echo ""
    echo "The installer needs to add TDD hooks to your settings."
    echo "This will modify: $SETTINGS_FILE"
    echo ""
    read -p "Would you like to automatically update settings.json? (y/n): " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Backup existing settings
        cp "$SETTINGS_FILE" "${SETTINGS_FILE}.backup.$(date +%Y%m%d%H%M%S)"
        echo "Backup created."

        # Use Python to merge settings
        python3 - "$SETTINGS_FILE" "$INSTALL_DIR" <<'PYTHON'
import json
import sys

settings_file = sys.argv[1]
install_dir = sys.argv[2]

# Load existing settings
with open(settings_file, 'r') as f:
    settings = json.load(f)

# Ensure permissions exist
if 'permissions' not in settings:
    settings['permissions'] = {}
if 'allow' not in settings['permissions']:
    settings['permissions']['allow'] = []

# Add TDD permissions if not present
tdd_permissions = [
    "Bash(mkdir -p ~/.claude/tmp:*)",
    "Bash(mkdir -p ~/.claude/tmp &&:*)",
    "Bash(touch ~/.claude/tmp/:*)",
    "Bash(echo:*)",
    "Bash(rm -f ~/.claude/tmp/tdd-*:*)",
    "Bash(cat ~/.claude/tmp/:*)"
]

for perm in tdd_permissions:
    if perm not in settings['permissions']['allow']:
        settings['permissions']['allow'].append(perm)

# Ensure hooks exist
if 'hooks' not in settings:
    settings['hooks'] = {}

# TDD hook configurations
tdd_hooks = {
    "PreToolUse": [
        {
            "matcher": "Write|Edit",
            "hooks": [{
                "type": "command",
                "command": f"bash {install_dir}/hooks/tdd-phase-guard.sh",
                "timeout": 5000
            }]
        }
    ],
    "PostToolUse": [
        {
            "matcher": "Write|Edit",
            "hooks": [{
                "type": "command",
                "command": f"bash {install_dir}/hooks/auto-compile.sh",
                "timeout": 120000
            }]
        },
        {
            "matcher": "Write|Edit",
            "hooks": [{
                "type": "command",
                "command": f"bash {install_dir}/hooks/tdd-auto-test.sh",
                "timeout": 300000
            }]
        }
    ],
    "Stop": [
        {
            "hooks": [{
                "type": "command",
                "command": f"bash {install_dir}/hooks/tdd-orchestrator.sh",
                "timeout": 120000
            }]
        }
    ],
    "SessionEnd": [
        {
            "hooks": [{
                "type": "command",
                "command": f"bash {install_dir}/hooks/cleanup-markers.sh",
                "timeout": 5000
            }]
        }
    ]
}

# Merge hooks (add TDD hooks, don't replace existing)
for event, hooks in tdd_hooks.items():
    if event not in settings['hooks']:
        settings['hooks'][event] = []

    existing_commands = set()
    for hook_config in settings['hooks'][event]:
        for h in hook_config.get('hooks', []):
            existing_commands.add(h.get('command', ''))

    for hook in hooks:
        hook_cmd = hook['hooks'][0]['command']
        if hook_cmd not in existing_commands:
            settings['hooks'][event].append(hook)

# Write updated settings
with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

print("Settings updated successfully.")
PYTHON
    else
        echo ""
        echo "Please manually add the hooks from config/settings.example.json"
        echo "to your ~/.claude/settings.json"
    fi
else
    echo "No settings.json found. Creating new one..."
    cp "$SCRIPT_DIR/config/settings.example.json" "$SETTINGS_FILE"
    # Update paths in the new settings file
    sed -i.bak "s|~/.claude/tdd-workflow|$INSTALL_DIR|g" "$SETTINGS_FILE" 2>/dev/null || \
    sed -i '' "s|~/.claude/tdd-workflow|$INSTALL_DIR|g" "$SETTINGS_FILE"
    rm -f "${SETTINGS_FILE}.bak"
    echo "Created new settings.json with TDD hooks."
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Installed to: $INSTALL_DIR"
echo ""
echo "Available commands:"
echo "  /tdd        - Start TDD mode"
echo "  /tdd-status - Check current TDD status"
echo "  /tdd-reset  - Reset TDD state"
echo ""
echo "Restart Claude Code to apply changes."
