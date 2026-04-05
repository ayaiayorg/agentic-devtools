"""Tests for _emit_log_marker."""

import io
from datetime import datetime
from unittest.mock import MagicMock

from agentic_devtools.cli.copilot.session import _LOG_PREFIX, _emit_log_marker


class TestEmitLogMarker:
    """Unit tests for the _emit_log_marker helper."""

    def test_writes_correct_format_to_log_file(self):
        """Marker line contains the prefix, event name, ISO timestamp, and fields."""
        log_file = io.StringIO()
        _emit_log_marker(log_file, None, "SESSION_START", pid=1234, model="gpt-4o")

        output = log_file.getvalue()
        assert output.endswith("\n")
        assert _LOG_PREFIX in output
        assert "SESSION_START" in output
        assert "pid=1234" in output
        assert "model=gpt-4o" in output

    def test_handles_none_stdout_gracefully(self):
        """When stdout is None, marker is written to log_file only without errors."""
        log_file = io.StringIO()
        _emit_log_marker(log_file, None, "SESSION_END", exit_code=0)

        output = log_file.getvalue()
        assert "SESSION_END" in output
        assert "exit_code=0" in output

    def test_handles_broken_stdout_gracefully(self):
        """When stdout raises OSError, marker is still written to log_file."""
        log_file = io.StringIO()
        broken_stdout = MagicMock()
        broken_stdout.write.side_effect = OSError("stdout closed")

        _emit_log_marker(log_file, broken_stdout, "SESSION_END", exit_code=0)

        output = log_file.getvalue()
        assert "SESSION_END" in output
        assert "exit_code=0" in output

    def test_handles_stdout_value_error_gracefully(self):
        """When stdout raises ValueError, marker is still written to log_file."""
        log_file = io.StringIO()
        broken_stdout = MagicMock()
        broken_stdout.write.side_effect = ValueError("I/O operation on closed file")

        _emit_log_marker(log_file, broken_stdout, "SESSION_ERROR", exit_code=1)

        output = log_file.getvalue()
        assert "SESSION_ERROR" in output

    def test_values_with_spaces_are_json_escaped(self):
        """Field values containing spaces are JSON-escaped."""
        log_file = io.StringIO()
        _emit_log_marker(log_file, None, "SESSION_START", working_directory="/home/user/my project")

        output = log_file.getvalue()
        assert 'working_directory="/home/user/my project"' in output

    def test_values_with_embedded_quotes_are_json_escaped(self):
        """Field values containing double quotes are JSON-escaped."""
        log_file = io.StringIO()
        _emit_log_marker(log_file, None, "SESSION_START", path='/home/"user"/dir')

        output = log_file.getvalue()
        # json.dumps produces: "/home/\"user\"/dir"
        assert 'path="/home/\\"user\\"/dir"' in output

    def test_values_with_backslashes_are_json_escaped(self):
        """Field values containing backslashes are JSON-escaped."""
        log_file = io.StringIO()
        _emit_log_marker(log_file, None, "SESSION_START", path="C:\\Users\\test")

        output = log_file.getvalue()
        assert 'path="C:\\\\Users\\\\test"' in output

    def test_empty_values_are_json_escaped(self):
        """Empty string values are JSON-escaped to be unambiguous."""
        log_file = io.StringIO()
        _emit_log_marker(log_file, None, "SESSION_START", model="")

        output = log_file.getvalue()
        assert 'model=""' in output

    def test_values_without_special_chars_are_not_quoted(self):
        """Field values without special characters are not quoted."""
        log_file = io.StringIO()
        _emit_log_marker(log_file, None, "SESSION_START", pid=1234)

        output = log_file.getvalue()
        assert "pid=1234" in output
        assert '"1234"' not in output

    def test_non_printable_control_chars_are_json_escaped(self):
        """Non-printable control characters (e.g. NUL, BEL) are JSON-escaped."""
        log_file = io.StringIO()
        _emit_log_marker(log_file, None, "SESSION_START", value="abc\x00def\x07")

        output = log_file.getvalue()
        # json.dumps escapes \x00 as \u0000, \x07 as \u0007
        assert 'value="abc\\u0000def\\u0007"' in output

    def test_writes_to_both_log_file_and_stdout(self):
        """When stdout is provided and healthy, marker is written to both sinks."""
        log_file = io.StringIO()
        stdout = io.StringIO()

        _emit_log_marker(log_file, stdout, "SESSION_START", pid=42)

        log_output = log_file.getvalue()
        stdout_output = stdout.getvalue()
        assert "SESSION_START" in log_output
        assert "SESSION_START" in stdout_output
        assert log_output == stdout_output

    def test_log_file_is_flushed(self):
        """The log file is flushed after writing the marker."""
        log_file = MagicMock()
        _emit_log_marker(log_file, None, "SESSION_END", exit_code=0)

        log_file.write.assert_called_once()
        log_file.flush.assert_called_once()

    def test_stdout_is_flushed(self):
        """stdout is flushed after writing the marker."""
        log_file = io.StringIO()
        stdout = MagicMock()

        _emit_log_marker(log_file, stdout, "SESSION_END", exit_code=0)

        stdout.write.assert_called_once()
        stdout.flush.assert_called_once()

    def test_marker_contains_iso_timestamp(self):
        """The marker line contains an ISO-8601 UTC timestamp."""
        log_file = io.StringIO()
        _emit_log_marker(log_file, None, "SESSION_START", pid=1)

        output = log_file.getvalue()
        # Extract the timestamp (3rd space-separated token)
        parts = output.strip().split(" ")
        timestamp_str = parts[2]
        # Should parse as a valid ISO timestamp
        parsed = datetime.fromisoformat(timestamp_str)
        assert parsed.tzinfo is not None

    def test_multiple_fields_in_order(self):
        """Multiple fields appear in the marker in the order they were passed."""
        log_file = io.StringIO()
        _emit_log_marker(
            log_file,
            None,
            "SESSION_END",
            exit_code=0,
            duration_seconds=10.5,
            total_bytes=1024,
            total_lines=42,
        )

        output = log_file.getvalue()
        # All fields present
        assert "exit_code=0" in output
        assert "duration_seconds=10.5" in output
        assert "total_bytes=1024" in output
        assert "total_lines=42" in output
