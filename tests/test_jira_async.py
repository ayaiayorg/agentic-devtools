"""
Tests for Jira async commands and write_async_status function.
"""

from unittest.mock import MagicMock, patch

import pytest

from dfly_ai_helpers.cli import jira
from dfly_ai_helpers.cli.jira import async_status
from dfly_ai_helpers.cli.jira.async_commands import (
    add_comment_async,
    add_users_to_project_role_async,
    add_users_to_project_role_batch_async,
    check_user_exists_async,
    check_users_exist_async,
    create_epic_async,
    create_issue_async,
    create_subtask_async,
    find_role_id_by_name_async,
    get_issue_async,
    get_project_role_details_async,
    list_project_roles_async,
    update_issue_async,
)


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
    with patch("dfly_ai_helpers.state.get_state_dir", return_value=tmp_path):
        with patch("dfly_ai_helpers.task_state.get_state_dir", return_value=tmp_path):
            # Patch subprocess.Popen only in the background_tasks module, not globally
            # This prevents interference with subprocess.run usage in state.py
            with patch("dfly_ai_helpers.background_tasks.subprocess.Popen") as mock_popen:
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


class TestAddCommentAsync:
    """Tests for add_comment_async command."""

    def test_requires_issue_key(self, mock_background_and_state):
        """Test add_comment_async requires issue_key."""
        with patch("dfly_ai_helpers.cli.jira.async_commands.get_jira_value", return_value=None):
            with pytest.raises(SystemExit):
                add_comment_async()

    def test_requires_comment(self, mock_background_and_state):
        """Test add_comment_async requires comment."""
        with patch(
            "dfly_ai_helpers.cli.jira.async_commands.get_jira_value",
            side_effect=lambda k: "DFLY-123" if k == "issue_key" else None,
        ):
            with pytest.raises(SystemExit):
                add_comment_async()

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test add_comment_async spawns a background task calling the correct function."""
        with patch(
            "dfly_ai_helpers.cli.jira.async_commands.get_jira_value",
            side_effect=lambda k: {"issue_key": "DFLY-123", "comment": "Test comment"}.get(k),
        ):
            add_comment_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

        # Verify the generated script calls the correct function
        script = _get_script_from_call(mock_background_and_state["mock_popen"])
        _assert_function_in_script(script, "dfly_ai_helpers.cli.jira.comment_commands", "add_comment")


class TestCreateEpicAsync:
    """Tests for create_epic_async command."""

    def test_requires_project_key(self, mock_background_and_state):
        """Test create_epic_async requires project_key."""
        with patch("dfly_ai_helpers.cli.jira.async_commands.get_jira_value", return_value=None):
            with pytest.raises(SystemExit):
                create_epic_async()

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test create_epic_async spawns a background task."""
        with patch(
            "dfly_ai_helpers.cli.jira.async_commands.get_jira_value",
            side_effect=lambda k: {"project_key": "DFLY", "summary": "Epic", "epic_name": "Name"}.get(k),
        ):
            create_epic_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out


class TestCreateIssueAsync:
    """Tests for create_issue_async command."""

    def test_requires_project_key(self, mock_background_and_state):
        """Test create_issue_async requires project_key."""
        with patch("dfly_ai_helpers.cli.jira.async_commands.get_jira_value", return_value=None):
            with pytest.raises(SystemExit):
                create_issue_async()

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test create_issue_async spawns a background task."""
        with patch(
            "dfly_ai_helpers.cli.jira.async_commands.get_jira_value",
            side_effect=lambda k: {"project_key": "DFLY", "summary": "Issue"}.get(k),
        ):
            create_issue_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out


class TestCreateSubtaskAsync:
    """Tests for create_subtask_async command."""

    def test_requires_parent_key(self, mock_background_and_state):
        """Test create_subtask_async requires parent_key."""
        with patch("dfly_ai_helpers.cli.jira.async_commands.get_jira_value", return_value=None):
            with pytest.raises(SystemExit):
                create_subtask_async()

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test create_subtask_async spawns a background task."""
        with patch(
            "dfly_ai_helpers.cli.jira.async_commands.get_jira_value",
            side_effect=lambda k: {"parent_key": "DFLY-123", "summary": "Subtask"}.get(k),
        ):
            create_subtask_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        assert "DFLY-123" in captured.out


class TestGetIssueAsync:
    """Tests for get_issue_async command."""

    def test_requires_issue_key(self, mock_background_and_state):
        """Test get_issue_async requires issue_key."""
        with patch("dfly_ai_helpers.cli.jira.async_commands.get_jira_value", return_value=None):
            with pytest.raises(SystemExit):
                get_issue_async()

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test get_issue_async spawns a background task."""
        with patch("dfly_ai_helpers.cli.jira.async_commands.get_jira_value", return_value="DFLY-456"):
            get_issue_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        assert "DFLY-456" in captured.out


class TestUpdateIssueAsync:
    """Tests for update_issue_async command."""

    def test_requires_issue_key(self, mock_background_and_state):
        """Test update_issue_async requires issue_key."""
        with patch("dfly_ai_helpers.cli.jira.async_commands.get_jira_value", return_value=None):
            with pytest.raises(SystemExit):
                update_issue_async()

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Test update_issue_async spawns a background task."""
        with patch("dfly_ai_helpers.cli.jira.async_commands.get_jira_value", return_value="DFLY-789"):
            update_issue_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        assert "DFLY-789" in captured.out


class TestRoleCommandsAsync:
    """Tests for role management async commands."""

    def test_list_project_roles_requires_project_key(self, mock_background_and_state):
        """Test list_project_roles_async requires project_key."""
        with patch("dfly_ai_helpers.cli.jira.async_commands.get_jira_value", return_value=None):
            with pytest.raises(SystemExit):
                list_project_roles_async()

    def test_list_project_roles_spawns_task(self, mock_background_and_state, capsys):
        """Test list_project_roles_async spawns background task."""
        with patch("dfly_ai_helpers.cli.jira.async_commands.get_jira_value", return_value="DFLY"):
            list_project_roles_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

    def test_get_project_role_details_requires_keys(self, mock_background_and_state):
        """Test get_project_role_details_async requires both keys."""
        with patch("dfly_ai_helpers.cli.jira.async_commands.get_jira_value", return_value=None):
            with pytest.raises(SystemExit):
                get_project_role_details_async()

    def test_add_users_to_role_spawns_task(self, mock_background_and_state, capsys):
        """Test add_users_to_project_role_async spawns background task."""
        with patch(
            "dfly_ai_helpers.cli.jira.async_commands.get_jira_value",
            side_effect=lambda k: {"project_key": "DFLY", "role_id": "10002", "users": "user1"}.get(k),
        ):
            add_users_to_project_role_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

    def test_add_users_batch_spawns_task(self, mock_background_and_state, capsys):
        """Test add_users_to_project_role_batch_async spawns background task."""
        with patch(
            "dfly_ai_helpers.cli.jira.async_commands.get_jira_value",
            side_effect=lambda k: {"project_key": "DFLY", "role_id": "10002", "users": "u1,u2"}.get(k),
        ):
            add_users_to_project_role_batch_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

    def test_find_role_id_spawns_task(self, mock_background_and_state, capsys):
        """Test find_role_id_by_name_async spawns background task."""
        with patch(
            "dfly_ai_helpers.cli.jira.async_commands.get_jira_value",
            side_effect=lambda k: {"project_key": "DFLY", "role_name": "Developers"}.get(k),
        ):
            find_role_id_by_name_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

    def test_check_user_exists_spawns_task(self, mock_background_and_state, capsys):
        """Test check_user_exists_async spawns background task."""
        with patch("dfly_ai_helpers.cli.jira.async_commands.get_jira_value", return_value="testuser"):
            check_user_exists_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

    def test_check_users_exist_spawns_task(self, mock_background_and_state, capsys):
        """Test check_users_exist_async spawns background task."""
        with patch("dfly_ai_helpers.cli.jira.async_commands.get_jira_value", return_value="u1,u2,u3"):
            check_users_exist_async()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
