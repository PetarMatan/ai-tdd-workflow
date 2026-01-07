#!/usr/bin/env python3
"""
Unit tests for hook_io.py

Tests the hook input parsing and response generation functions.
"""

import json
import sys
import io
import pytest
from unittest.mock import patch

# Add the hooks/lib directory to the path
sys.path.insert(0, 'hooks/lib')
from hook_io import (
    parse_input,
    block_response,
    approve_response,
    approve_with_message,
    _escape_bash,
)


class TestEscapeBash:
    """Tests for _escape_bash function."""

    def test_empty_string(self):
        assert _escape_bash('') == ''

    def test_none_returns_empty(self):
        assert _escape_bash(None) == ''

    def test_simple_string(self):
        assert _escape_bash('hello') == 'hello'

    def test_escapes_backslash(self):
        assert _escape_bash('path\\to\\file') == 'path\\\\to\\\\file'

    def test_escapes_double_quote(self):
        assert _escape_bash('say "hello"') == 'say \\"hello\\"'

    def test_escapes_backtick(self):
        assert _escape_bash('run `cmd`') == 'run \\`cmd\\`'

    def test_escapes_dollar_sign(self):
        assert _escape_bash('$HOME/path') == '\\$HOME/path'

    def test_escapes_multiple_special_chars(self):
        input_str = 'echo "$HOME" `pwd`'
        expected = 'echo \\"\\$HOME\\" \\`pwd\\`'
        assert _escape_bash(input_str) == expected

    def test_preserves_single_quotes(self):
        assert _escape_bash("it's fine") == "it's fine"

    def test_preserves_newlines(self):
        assert _escape_bash("line1\nline2") == "line1\nline2"


class TestParseInput:
    """Tests for parse_input function."""

    def test_parses_complete_input(self, capsys):
        input_data = {
            'tool_name': 'Write',
            'tool_input': {'file_path': '/path/to/file.py'},
            'cwd': '/project',
            'session_id': 'abc123',
            'stop_hook_active': False,
            'hook_event_name': 'PostToolUse'
        }

        with patch('sys.stdin', io.StringIO(json.dumps(input_data))):
            parse_input()

        captured = capsys.readouterr()
        assert 'HOOK_TOOL_NAME="Write"' in captured.out
        assert 'HOOK_FILE_PATH="/path/to/file.py"' in captured.out
        assert 'HOOK_CWD="/project"' in captured.out
        assert 'HOOK_SESSION_ID="abc123"' in captured.out
        assert 'HOOK_STOP_ACTIVE="False"' in captured.out
        assert 'HOOK_EVENT_NAME="PostToolUse"' in captured.out

    def test_handles_empty_json(self, capsys):
        with patch('sys.stdin', io.StringIO('{}')):
            parse_input()

        captured = capsys.readouterr()
        assert 'HOOK_TOOL_NAME=""' in captured.out
        assert 'HOOK_FILE_PATH=""' in captured.out
        assert 'HOOK_SESSION_ID="unknown"' in captured.out

    def test_handles_invalid_json(self, capsys):
        with patch('sys.stdin', io.StringIO('not valid json')):
            parse_input()

        captured = capsys.readouterr()
        assert 'HOOK_TOOL_NAME=""' in captured.out
        assert 'HOOK_SESSION_ID="unknown"' in captured.out

    def test_handles_missing_tool_input(self, capsys):
        input_data = {'tool_name': 'Read', 'cwd': '/project'}

        with patch('sys.stdin', io.StringIO(json.dumps(input_data))):
            parse_input()

        captured = capsys.readouterr()
        assert 'HOOK_TOOL_NAME="Read"' in captured.out
        assert 'HOOK_FILE_PATH=""' in captured.out

    def test_handles_tool_input_not_dict(self, capsys):
        input_data = {'tool_name': 'Bash', 'tool_input': 'ls -la'}

        with patch('sys.stdin', io.StringIO(json.dumps(input_data))):
            parse_input()

        captured = capsys.readouterr()
        assert 'HOOK_FILE_PATH=""' in captured.out

    def test_escapes_special_characters_in_path(self, capsys):
        input_data = {
            'tool_input': {'file_path': '/path/with spaces/$var/file.py'}
        }

        with patch('sys.stdin', io.StringIO(json.dumps(input_data))):
            parse_input()

        captured = capsys.readouterr()
        assert 'HOOK_FILE_PATH="/path/with spaces/\\$var/file.py"' in captured.out

    def test_stop_hook_active_true(self, capsys):
        input_data = {'stop_hook_active': True}

        with patch('sys.stdin', io.StringIO(json.dumps(input_data))):
            parse_input()

        captured = capsys.readouterr()
        assert 'HOOK_STOP_ACTIVE="True"' in captured.out


class TestBlockResponse:
    """Tests for block_response function."""

    def test_simple_block(self, capsys):
        block_response("Cannot proceed")

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output['decision'] == 'block'
        assert output['reason'] == 'Cannot proceed'

    def test_block_with_agent_content(self, capsys):
        block_response("Phase 1 blocked", "\n\n## Agent Instructions\nDo this...")

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output['decision'] == 'block'
        assert 'Phase 1 blocked' in output['reason']
        assert '## Agent Instructions' in output['reason']

    def test_block_with_empty_agent_content(self, capsys):
        block_response("Blocked", "")

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output['reason'] == 'Blocked'

    def test_block_with_none_agent_content(self, capsys):
        block_response("Blocked", None)

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output['reason'] == 'Blocked'

    def test_block_output_is_valid_json(self, capsys):
        block_response("Test with special chars: \"quotes\" and $vars")

        captured = capsys.readouterr()
        # Should not raise
        output = json.loads(captured.out)
        assert 'decision' in output


class TestApproveResponse:
    """Tests for approve_response function."""

    def test_approve_produces_no_output(self, capsys):
        approve_response()

        captured = capsys.readouterr()
        assert captured.out == ''


class TestApproveWithMessage:
    """Tests for approve_with_message function."""

    def test_approve_with_context(self, capsys):
        approve_with_message(
            "Compilation failed",
            "PostToolUse",
            "## Error Details\n\nFix the errors."
        )

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output['decision'] == 'approve'
        assert output['reason'] == 'Compilation failed'
        assert output['hookSpecificOutput']['hookEventName'] == 'PostToolUse'
        assert '## Error Details' in output['hookSpecificOutput']['additionalContext']

    def test_approve_with_empty_context(self, capsys):
        approve_with_message("Info", "PreToolUse", "")

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output['decision'] == 'approve'
        assert output['hookSpecificOutput']['additionalContext'] == ''

    def test_output_structure(self, capsys):
        approve_with_message("reason", "event", "context")

        captured = capsys.readouterr()
        output = json.loads(captured.out)

        # Verify complete structure
        assert set(output.keys()) == {'decision', 'reason', 'hookSpecificOutput'}
        assert set(output['hookSpecificOutput'].keys()) == {'hookEventName', 'additionalContext'}


class TestMainCLI:
    """Tests for the CLI interface."""

    def test_parse_command(self, capsys):
        input_data = {'tool_name': 'Edit', 'session_id': 'test'}

        with patch('sys.stdin', io.StringIO(json.dumps(input_data))):
            with patch('sys.argv', ['hook_io.py', 'parse']):
                from hook_io import main
                main()

        captured = capsys.readouterr()
        assert 'HOOK_TOOL_NAME="Edit"' in captured.out

    def test_block_command(self, capsys):
        with patch('sys.argv', ['hook_io.py', 'block', 'Test reason']):
            from hook_io import main
            main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output['decision'] == 'block'
        assert output['reason'] == 'Test reason'

    def test_block_command_with_agent_content(self, capsys):
        with patch('sys.argv', ['hook_io.py', 'block', 'Reason', 'Agent content']):
            from hook_io import main
            main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert 'Agent content' in output['reason']

    def test_approve_command(self, capsys):
        with patch('sys.argv', ['hook_io.py', 'approve']):
            from hook_io import main
            main()

        captured = capsys.readouterr()
        assert captured.out == ''

    def test_approve_message_command(self, capsys):
        with patch('sys.argv', ['hook_io.py', 'approve-message', 'reason', 'PostToolUse', 'context']):
            from hook_io import main
            main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output['decision'] == 'approve'

    def test_unknown_command_exits_with_error(self, capsys):
        with patch('sys.argv', ['hook_io.py', 'unknown']):
            with pytest.raises(SystemExit) as exc_info:
                from hook_io import main
                main()

        assert exc_info.value.code == 1

    def test_no_args_exits_with_error(self, capsys):
        with patch('sys.argv', ['hook_io.py']):
            with pytest.raises(SystemExit) as exc_info:
                from hook_io import main
                main()

        assert exc_info.value.code == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
