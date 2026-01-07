#!/usr/bin/env python3
"""
TDD Workflow - Agent Discovery Library

Discovers and loads agents based on TDD phase configuration.
Wraps agent_parser.py for easy use.
"""

import os
from pathlib import Path
from typing import List, Optional

# Absolute import for subprocess compatibility
import agent_parser


class AgentLoader:
    """Loads and manages phase-bound agents."""

    def __init__(self, agents_dir: Optional[str] = None):
        """Initialize agent loader."""
        if agents_dir:
            self.agents_dir = agents_dir
        else:
            install_dir = os.environ.get(
                "TDD_INSTALL_DIR",
                str(Path.home() / ".claude" / "tdd-workflow")
            )
            self.agents_dir = os.path.join(install_dir, "agents")

    def get_agents_for_phase(self, phase: int) -> List[str]:
        """Get list of agent file paths configured for a specific phase."""
        if not os.path.isdir(self.agents_dir):
            return []

        return agent_parser.get_agents_for_phase(self.agents_dir, phase)

    def get_agent_name(self, agent_file: str) -> str:
        """Get agent name from frontmatter or filename."""
        return agent_parser.get_agent_name(agent_file)

    def get_agent_content(self, agent_file: str) -> Optional[str]:
        """Get agent content (markdown without frontmatter)."""
        return agent_parser.get_agent_content(agent_file)

    def load_phase_agents(self, phase: int, logger=None) -> str:
        """
        Load all agents configured for a phase and return combined content.

        Args:
            phase: The TDD phase number (1-4)
            logger: Optional TDDLogger for logging agent loads

        Returns:
            Combined agent content string for injection into context
        """
        agent_files = self.get_agents_for_phase(phase)
        if not agent_files:
            return ""

        agent_content = ""
        for agent_file in agent_files:
            agent_name = self.get_agent_name(agent_file)
            if logger:
                logger.log_tdd(f"Loading agent '{agent_name}' for phase {phase}")
            print(f">>> TDD: Loaded agent: {agent_name}", file=__import__('sys').stderr)

            content = self.get_agent_content(agent_file)
            if content:
                agent_content += f"\n\n---\n\n## Agent: {agent_name}\n\n{content}"

        return agent_content

    def list_agents(self) -> str:
        """List all agents with their phase bindings (JSON)."""
        if not os.path.isdir(self.agents_dir):
            return "[]"
        return agent_parser.list_agents(self.agents_dir)
