"""Tests for _require_int_value helper."""

import pytest

from agentic_devtools.state import set_value


class TestRequireIntValue:
    """Tests for _require_int_value helper function."""

    def test_returns_int_when_value_is_numeric(self, temp_state_dir, clear_state_before):
        """Should return the integer when the value is a valid numeric string."""
        from agentic_devtools.cli.azure_devops.async_commands import _require_int_value

        set_value("pull_request_id", "12345")

        result = _require_int_value("pull_request_id", "agdt-approve-file --pull-request-id 12345")
        assert result == 12345

    def test_exits_when_value_missing(self, temp_state_dir, clear_state_before, capsys):
        """Should exit with error when value is not set."""
        from agentic_devtools.cli.azure_devops.async_commands import _require_int_value

        with pytest.raises(SystemExit) as exc_info:
            _require_int_value("missing_key", "agdt-approve-file --pull-request-id 12345")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "missing_key" in captured.err
        assert "required" in captured.err.lower()

    def test_exits_when_value_not_numeric(self, temp_state_dir, clear_state_before, capsys):
        """Should exit with a CLI-friendly error when value is present but not numeric."""
        from agentic_devtools.cli.azure_devops.async_commands import _require_int_value

        set_value("pull_request_id", "not-a-number")

        with pytest.raises(SystemExit) as exc_info:
            _require_int_value("pull_request_id", "agdt-approve-file --pull-request-id 12345")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "must be a numeric ID" in captured.err
        assert "not-a-number" in captured.err

    def test_returns_int_when_value_is_already_int(self, temp_state_dir, clear_state_before):
        """Should handle values that are already integers in state."""
        from agentic_devtools.cli.azure_devops.async_commands import _require_int_value

        set_value("pull_request_id", 99999)

        result = _require_int_value("pull_request_id", "agdt-approve-file --pull-request-id 99999")
        assert result == 99999
