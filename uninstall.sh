#!/bin/bash
set -e

# TDD Workflow Uninstaller for Claude Code
# Version: 1.0.0

INSTALL_DIR="${HOME}/.claude/tdd-workflow"
COMMANDS_DIR="${HOME}/.claude/commands"
SETTINGS_FILE="${HOME}/.claude/settings.json"

echo "=== TDD Workflow Uninstaller ==="
echo ""

# Remove TDD markers (both old flat files and new session-scoped directories)
echo "Cleaning up TDD markers..."
rm -f ~/.claude/tmp/tdd-mode 2>/dev/null || true
rm -f ~/.claude/tmp/tdd-phase 2>/dev/null || true
rm -f ~/.claude/tmp/tdd-requirements-confirmed 2>/dev/null || true
rm -f ~/.claude/tmp/tdd-interfaces-designed 2>/dev/null || true
rm -f ~/.claude/tmp/tdd-tests-approved 2>/dev/null || true
rm -f ~/.claude/tmp/tdd-tests-passing 2>/dev/null || true
rm -rf ~/.claude/tmp/tdd-* 2>/dev/null || true

# Remove skills
echo "Removing skills..."
rm -f "$COMMANDS_DIR/tdd.md" 2>/dev/null || true
rm -f "$COMMANDS_DIR/tdd-status.md" 2>/dev/null || true
rm -f "$COMMANDS_DIR/tdd-reset.md" 2>/dev/null || true
rm -f "$COMMANDS_DIR/tdd-create-agent.md" 2>/dev/null || true

# Update settings.json (before removing install dir since we need settings_manager.py)
echo ""
echo "=== Settings Cleanup ==="
echo ""

if [[ -f "$SETTINGS_FILE" && -d "$INSTALL_DIR" ]]; then
    # Check if running interactively
    if [[ -t 0 ]]; then
        read -p "Would you like to remove TDD hooks from settings.json? (y/n): " -n 1 -r
        echo ""
    else
        # Non-interactive (piped) - default to yes
        echo "Running non-interactively, automatically removing hooks from settings..."
        REPLY="y"
    fi

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Backup existing settings
        cp "$SETTINGS_FILE" "${SETTINGS_FILE}.backup.$(date +%Y%m%d%H%M%S)"
        echo "Backup created."

        # Use settings_manager to remove TDD hooks
        python3 "$INSTALL_DIR/hooks/lib/settings_manager.py" remove "$SETTINGS_FILE"
    else
        echo "Skipping settings cleanup. You may need to manually remove TDD hooks."
    fi
elif [[ -f "$SETTINGS_FILE" ]]; then
    echo "Installation directory not found. Skipping settings cleanup."
    echo "You may need to manually remove TDD hooks from settings.json."
fi

# Remove installation directory (after settings cleanup)
if [[ -d "$INSTALL_DIR" ]]; then
    echo ""
    echo "Removing installation directory..."
    rm -rf "$INSTALL_DIR"
fi

echo ""
echo "=== Uninstall Complete ==="
echo ""
echo "TDD Workflow has been removed."
echo "Restart Claude Code to apply changes."
