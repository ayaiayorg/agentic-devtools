"""
Tests for Jira async commands and write_async_status function.
"""

from unittest.mock import MagicMock, patch

import pytest

from agdt_ai_helpers.cli import jira
from agdt_ai_helpers.cli.jira import async_status


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create a temporary directory for state files."""
    # Patch where get_state_dir is used (in async_status module)
    with patch.object(async_status, "get_state_dir", return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def mock_background_and_state(tmp_path):
    """Mock both background task infrastructure and Jira state."""
    # Need to patch get_state_dir in both modules since task_state imports it directly
    with patch("agdt_ai_helpers.state.get_state_dir", return_value=tmp_path):
        with patch("agdt_ai_helpers.task_state.get_state_dir", return_value=tmp_path):
            # Patch subprocess.Popen only in the background_tasks module, not globally
            # This prevents interference with subprocess.run usage in state.py
            with patch("agdt_ai_helpers.background_tasks.subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.pid = 12345
                mock_popen.return_value = mock_process
                yield {
                    "state_dir": tmp_path,
                    "mock_popen": mock_popen,
                }


def _get_script_from_call(mock_popen):
    """Extract the Python script from the Popen call args."""
    call_args = mock_popen.call_args[0][0]  # First positional arg is the command list
    # Script is the third element: [python, -c, <script>]
    return call_args[2] if len(call_args) > 2 else ""


def _assert_function_in_script(script, module_path, function_name):
    """Assert the script calls the expected function from the expected module."""
    assert f"module_path = '{module_path}'" in script, f"Expected module_path = '{module_path}' in script"
    assert f"function_name = '{function_name}'" in script, f"Expected function_name = '{function_name}' in script"


class TestWriteAsyncStatus:
    """Tests for write_async_status function."""

    def test_write_async_status_creates_file(self, temp_state_dir):
        """Test async status file is created."""
        status = {"state": "running", "progress": 50}
        result_path = jira.write_async_status("test-op-123", status)

        assert result_path.exists()
        assert result_path.name == "test-op-123.json"

    def test_write_async_status_creates_directory(self, temp_state_dir):
        """Test async directory is created if not exists."""
        status = {"state": "complete"}
        result_path = jira.write_async_status("op-456", status)

        assert result_path.parent.name == "async"
        assert result_path.parent.exists()

    def test_write_async_status_content(self, temp_state_dir):
        """Test async status file contains correct JSON."""
        import json

        status = {"state": "running", "message": "Processing"}
        result_path = jira.write_async_status("op-789", status)

        content = json.loads(result_path.read_text(encoding="utf-8"))
        assert content == status

    def test_write_async_status_overwrites(self, temp_state_dir):
        """Test writing to same operation ID overwrites."""
        import json

        jira.write_async_status("op-same", {"state": "first"})
        jira.write_async_status("op-same", {"state": "second"})

        result_path = temp_state_dir / "async" / "op-same.json"
        content = json.loads(result_path.read_text(encoding="utf-8"))
        assert content["state"] == "second"

    def test_write_async_status_unicode(self, temp_state_dir):
        """Test async status handles unicode content."""
        import json

        status = {"message": "Größe Übung Äpfel and 日本語"}
        result_path = jira.write_async_status("unicode-op", status)

        content = json.loads(result_path.read_text(encoding="utf-8"))
        assert content["message"] == "Größe Übung Äpfel and 日本語"

