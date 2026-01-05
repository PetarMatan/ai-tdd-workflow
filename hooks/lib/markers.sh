#!/bin/bash
# TDD Workflow - Marker Paths
# Centralized marker file path definitions with session isolation
#
# Source this in any hook: source "$(dirname "$0")/lib/markers.sh"
# Then call: setup_markers "$session_id"

# Base directory for all TDD markers
TDD_MARKERS_BASE="${HOME}/.claude/tmp"

# Session-scoped directory (set by setup_markers)
TDD_MARKERS_DIR=""

# Core TDD state markers (set by setup_markers)
TDD_MODE_MARKER=""
TDD_PHASE_FILE=""

# Phase progression markers (set by setup_markers)
REQUIREMENTS_MARKER=""
INTERFACES_MARKER=""
TESTS_MARKER=""
TESTS_PASSING_MARKER=""

# Initialize markers with session-specific paths
# Usage: setup_markers "$session_id"
# Must be called after parsing session_id from hook input
setup_markers() {
    local session_id="${1:-unknown}"

    # Create session-scoped directory
    TDD_MARKERS_DIR="${TDD_MARKERS_BASE}/tdd-${session_id}"

    # Ensure directory exists
    mkdir -p "$TDD_MARKERS_DIR" 2>/dev/null || true

    # Set all marker paths
    TDD_MODE_MARKER="${TDD_MARKERS_DIR}/tdd-mode"
    TDD_PHASE_FILE="${TDD_MARKERS_DIR}/tdd-phase"
    REQUIREMENTS_MARKER="${TDD_MARKERS_DIR}/tdd-requirements-confirmed"
    INTERFACES_MARKER="${TDD_MARKERS_DIR}/tdd-interfaces-designed"
    TESTS_MARKER="${TDD_MARKERS_DIR}/tdd-tests-approved"
    TESTS_PASSING_MARKER="${TDD_MARKERS_DIR}/tdd-tests-passing"
}

# Helper function to clean up all TDD markers for current session
cleanup_all_markers() {
    if [[ -n "$TDD_MARKERS_DIR" && -d "$TDD_MARKERS_DIR" ]]; then
        rm -rf "$TDD_MARKERS_DIR" 2>/dev/null || true
    fi
}

# Clean up markers for a specific session (used by cleanup hook)
# Usage: cleanup_session_markers "$session_id"
cleanup_session_markers() {
    local session_id="${1:-}"
    if [[ -n "$session_id" ]]; then
        local session_dir="${TDD_MARKERS_BASE}/tdd-${session_id}"
        if [[ -d "$session_dir" ]]; then
            rm -rf "$session_dir" 2>/dev/null || true
        fi
    fi
}
