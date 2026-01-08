#!/usr/bin/env python3
"""
TDD Supervisor - Marker Management

Manages TDD markers for supervisor mode. Uses a workflow ID that persists
across multiple Claude sessions within a single TDD workflow run.
"""

import os
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime


class SupervisorMarkers:
    """Manages TDD markers for supervisor-controlled workflows."""

    def __init__(self, workflow_id: Optional[str] = None):
        """
        Initialize marker manager for supervisor mode.

        Args:
            workflow_id: Unique identifier for this workflow run.
                        If not provided, generates one from timestamp.
        """
        self.base_dir = Path.home() / ".claude" / "tmp"
        self.workflow_id = workflow_id or self._generate_workflow_id()
        self.markers_dir = self.base_dir / f"tdd-supervisor-{self.workflow_id}"

        # Ensure directory exists
        self.markers_dir.mkdir(parents=True, exist_ok=True)

    def _generate_workflow_id(self) -> str:
        """Generate a unique workflow ID."""
        return datetime.now().strftime("%Y%m%d-%H%M%S")

    # Marker paths
    @property
    def tdd_mode(self) -> Path:
        return self.markers_dir / "tdd-mode"

    @property
    def tdd_phase(self) -> Path:
        return self.markers_dir / "tdd-phase"

    @property
    def supervisor_active(self) -> Path:
        return self.markers_dir / "tdd-supervisor-active"

    @property
    def requirements_summary(self) -> Path:
        return self.markers_dir / "tdd-requirements-summary.md"

    @property
    def interfaces_list(self) -> Path:
        return self.markers_dir / "tdd-interfaces-list.md"

    @property
    def tests_list(self) -> Path:
        return self.markers_dir / "tdd-tests-list.md"

    # Completion markers (still used for hook compatibility)
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

    # State management
    def initialize(self) -> None:
        """Initialize markers for a new TDD workflow."""
        self.tdd_mode.touch()
        self.supervisor_active.touch()
        self.set_phase(1)

    def get_phase(self) -> int:
        """Get current TDD phase (1-4)."""
        if not self.tdd_phase.exists():
            return 1
        try:
            return int(self.tdd_phase.read_text().strip())
        except (ValueError, OSError):
            return 1

    def set_phase(self, phase: int) -> None:
        """Set the current TDD phase."""
        self.tdd_phase.write_text(str(phase))

    def is_active(self) -> bool:
        """Check if TDD supervisor mode is active."""
        return self.tdd_mode.exists() and self.supervisor_active.exists()

    # Context storage
    def save_requirements_summary(self, summary: str) -> None:
        """Save requirements summary for passing to later phases."""
        self.requirements_summary.write_text(summary)

    def get_requirements_summary(self) -> str:
        """Get saved requirements summary."""
        if self.requirements_summary.exists():
            return self.requirements_summary.read_text()
        return ""

    def save_interfaces_list(self, interfaces: str) -> None:
        """Save list of created interfaces."""
        self.interfaces_list.write_text(interfaces)

    def get_interfaces_list(self) -> str:
        """Get saved interfaces list."""
        if self.interfaces_list.exists():
            return self.interfaces_list.read_text()
        return ""

    def save_tests_list(self, tests: str) -> None:
        """Save list of created tests."""
        self.tests_list.write_text(tests)

    def get_tests_list(self) -> str:
        """Get saved tests list."""
        if self.tests_list.exists():
            return self.tests_list.read_text()
        return ""

    # Cleanup
    def cleanup(self) -> None:
        """Remove all markers for this workflow."""
        if self.markers_dir.exists():
            shutil.rmtree(self.markers_dir, ignore_errors=True)

    def get_marker_dir(self) -> str:
        """Get the marker directory path."""
        return str(self.markers_dir)

    def get_env_vars(self) -> dict:
        """
        Get environment variables to pass to Claude sessions.

        These allow hooks to find the correct marker directory.
        """
        return {
            "TDD_SUPERVISOR_WORKFLOW_ID": self.workflow_id,
            "TDD_SUPERVISOR_MARKERS_DIR": str(self.markers_dir),
            "TDD_SUPERVISOR_ACTIVE": "1",
        }
