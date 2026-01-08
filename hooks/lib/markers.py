#!/usr/bin/env python3
"""
TDD Workflow - Marker Management

Handles session-scoped marker files for TDD phase tracking.
Supports both standalone session mode and supervisor mode.
"""

import os
import shutil
from pathlib import Path
from typing import Optional


class MarkerManager:
    """Manages TDD marker files with session isolation."""

    def __init__(self, session_id: str = "unknown"):
        """
        Initialize marker manager with session ID.

        In supervisor mode (TDD_SUPERVISOR_MARKERS_DIR set), uses the
        supervisor's marker directory instead of session-based one.
        """
        self.base_dir = Path.home() / ".claude" / "tmp"
        self.session_id = session_id

        # Check for supervisor mode - use supervisor's marker directory
        supervisor_markers_dir = os.environ.get("TDD_SUPERVISOR_MARKERS_DIR")
        if supervisor_markers_dir:
            self.markers_dir = Path(supervisor_markers_dir)
            self._supervisor_mode = True
        else:
            self.markers_dir = self.base_dir / f"tdd-{session_id}"
            self._supervisor_mode = False

        # Ensure directory exists
        self.markers_dir.mkdir(parents=True, exist_ok=True)

    def is_supervisor_mode(self) -> bool:
        """Check if running under supervisor control."""
        return self._supervisor_mode or os.environ.get("TDD_SUPERVISOR_ACTIVE") == "1"

    @property
    def tdd_mode(self) -> Path:
        return self.markers_dir / "tdd-mode"

    @property
    def tdd_phase(self) -> Path:
        return self.markers_dir / "tdd-phase"

    @property
    def requirements_confirmed(self) -> Path:
        return self.markers_dir / "tdd-requirements-confirmed"

    @property
    def interfaces_designed(self) -> Path:
        return self.markers_dir / "tdd-interfaces-designed"

    @property
    def tests_approved(self) -> Path:
        return self.markers_dir / "tdd-tests-approved"

    @property
    def tests_passing(self) -> Path:
        return self.markers_dir / "tdd-tests-passing"

    def is_tdd_active(self) -> bool:
        """Check if TDD mode is active."""
        return self.tdd_mode.exists()

    def get_phase(self) -> int:
        """Get current TDD phase (1-4), defaults to 1. Resets invalid values."""
        if not self.tdd_phase.exists():
            return 1
        try:
            phase = int(self.tdd_phase.read_text().strip())
            if phase < 1 or phase > 4:
                raise ValueError("Phase out of range")
            return phase
        except (ValueError, OSError):
            # Reset invalid phase to 1
            self.set_phase(1)
            return 1

    def set_phase(self, phase: int) -> None:
        """Set the current TDD phase."""
        self.tdd_phase.write_text(str(phase))

    def marker_exists(self, marker: Path) -> bool:
        """Check if a specific marker exists."""
        return marker.exists()

    def create_marker(self, marker: Path) -> None:
        """Create a marker file."""
        marker.touch()

    def remove_marker(self, marker: Path) -> None:
        """Remove a marker file if it exists."""
        if marker.exists():
            marker.unlink()

    def cleanup_session(self) -> None:
        """Remove all markers for this session."""
        if self.markers_dir.exists():
            shutil.rmtree(self.markers_dir, ignore_errors=True)

    def cleanup_all_markers(self) -> None:
        """Remove workflow marker files (keeps tests_passing as success indicator)."""
        markers = [
            self.tdd_mode,
            self.tdd_phase,
            self.requirements_confirmed,
            self.interfaces_designed,
            self.tests_approved,
            # Note: tests_passing kept - cleared on next TDD start instead
        ]
        for marker in markers:
            self.remove_marker(marker)

    def get_marker_dir_display(self) -> str:
        """Get displayable marker directory path (with ~)."""
        return f"~/.claude/tmp/tdd-{self.session_id}"
