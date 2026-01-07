#!/usr/bin/env python3
"""
Unit tests for tdd_agents.py
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add hooks/lib to path
sys.path.insert(0, 'hooks/lib')
from tdd_agents import AgentLoader


class TestAgentLoader:
    """Tests for AgentLoader class."""

    def test_init_uses_provided_dir(self):
        loader = AgentLoader("/custom/agents/dir")
        assert loader.agents_dir == "/custom/agents/dir"

    def test_init_uses_env_var(self):
        with patch.dict(os.environ, {"TDD_INSTALL_DIR": "/from/env"}):
            loader = AgentLoader()
            assert loader.agents_dir == "/from/env/agents"

    def test_init_uses_default_path(self):
        with patch.dict(os.environ, {}, clear=True):
            # Clear TDD_INSTALL_DIR if set
            os.environ.pop("TDD_INSTALL_DIR", None)
            loader = AgentLoader()
            assert "tdd-workflow/agents" in loader.agents_dir

    def test_get_agents_for_phase(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create agent for phase 2
            with open(os.path.join(tmpdir, "tester.md"), 'w') as f:
                f.write("""---
name: Tester
phases: [2, 3]
---
Test content
""")
            loader = AgentLoader(tmpdir)
            result = loader.get_agents_for_phase(2)
            assert len(result) == 1
            assert "tester.md" in result[0]

    def test_get_agents_for_phase_empty_dir(self):
        loader = AgentLoader("/nonexistent/dir")
        result = loader.get_agents_for_phase(1)
        assert result == []

    def test_get_agent_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = os.path.join(tmpdir, "my-agent.md")
            with open(agent_file, 'w') as f:
                f.write("""---
name: Custom Agent Name
---
Content
""")
            loader = AgentLoader(tmpdir)
            result = loader.get_agent_name(agent_file)
            assert result == "Custom Agent Name"

    def test_get_agent_name_from_filename(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = os.path.join(tmpdir, "tdd-tester.md")
            with open(agent_file, 'w') as f:
                f.write("# No frontmatter")
            loader = AgentLoader(tmpdir)
            result = loader.get_agent_name(agent_file)
            assert result == "Tdd Tester"

    def test_get_agent_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = os.path.join(tmpdir, "agent.md")
            with open(agent_file, 'w') as f:
                f.write("""---
name: Test
---

# Instructions
Do these things.
""")
            loader = AgentLoader(tmpdir)
            result = loader.get_agent_content(agent_file)
            assert "# Instructions" in result
            assert "name: Test" not in result

    def test_get_agent_content_returns_none_for_missing(self):
        loader = AgentLoader("/tmp")
        result = loader.get_agent_content("/nonexistent/agent.md")
        assert result is None

    def test_load_phase_agents_returns_combined_content(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "agent1.md"), 'w') as f:
                f.write("""---
name: Agent One
phases: [1]
---

First agent content.
""")
            with open(os.path.join(tmpdir, "agent2.md"), 'w') as f:
                f.write("""---
name: Agent Two
phases: [1]
---

Second agent content.
""")
            loader = AgentLoader(tmpdir)
            result = loader.load_phase_agents(1)

            assert "## Agent: Agent One" in result
            assert "First agent content" in result
            assert "## Agent: Agent Two" in result
            assert "Second agent content" in result

    def test_load_phase_agents_returns_empty_for_no_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "agent.md"), 'w') as f:
                f.write("""---
phases: [3]
---
Content
""")
            loader = AgentLoader(tmpdir)
            result = loader.load_phase_agents(1)
            assert result == ""

    def test_load_phase_agents_with_logger(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "agent.md"), 'w') as f:
                f.write("""---
name: Test Agent
phases: [2]
---
Content
""")
            mock_logger = MagicMock()
            loader = AgentLoader(tmpdir)
            loader.load_phase_agents(2, logger=mock_logger)

            mock_logger.log_tdd.assert_called_once()
            call_args = mock_logger.log_tdd.call_args[0][0]
            assert "Test Agent" in call_args
            assert "phase 2" in call_args

    def test_load_phase_agents_prints_to_stderr(self, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "agent.md"), 'w') as f:
                f.write("""---
name: Visible Agent
phases: [1]
---
Content
""")
            loader = AgentLoader(tmpdir)
            loader.load_phase_agents(1)

            captured = capsys.readouterr()
            assert "Loaded agent: Visible Agent" in captured.err

    def test_list_agents(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "agent1.md"), 'w') as f:
                f.write("""---
name: First
phases: [1, 2]
---
""")
            with open(os.path.join(tmpdir, "agent2.md"), 'w') as f:
                f.write("""---
name: Second
phases: [3]
---
""")
            loader = AgentLoader(tmpdir)
            result = loader.list_agents()

            import json
            data = json.loads(result)
            assert len(data) == 2
            names = [a['name'] for a in data]
            assert "First" in names
            assert "Second" in names

    def test_list_agents_empty_dir(self):
        loader = AgentLoader("/nonexistent/dir")
        result = loader.list_agents()
        assert result == "[]"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
