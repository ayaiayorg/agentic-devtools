"""Tests for start_copilot_session."""

import warnings
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.copilot import session as session_module
from agentic_devtools.cli.copilot.session import CopilotSessionResult, start_copilot_session


@pytest.fixture
def temp_state(tmp_path):
    """Redirect state storage to a temp directory.

    Patches both the state module's get_state_dir (used by set_value/load_state)
    and the session module's imported get_state_dir reference (used by
    _get_prompt_file_path and _get_log_file_path), so no real filesystem
    or git subprocess calls occur.
    """
    with patch.object(state, "get_state_dir", return_value=tmp_path):
        with patch.object(session_module, "get_state_dir", return_value=tmp_path):
            state.clear_state()
            yield tmp_path


@pytest.fixture
def mock_available():
    """Patch is_gh_copilot_available to return True."""
    with patch.object(session_module, "is_gh_copilot_available", return_value=True):
        yield


@pytest.fixture
def mock_unavailable():
    """Patch is_gh_copilot_available to return False."""
    with patch.object(session_module, "is_gh_copilot_available", return_value=False):
        yield


@pytest.fixture
def mock_popen_interactive():
    """Return a mock Popen that simulates an interactive session ending immediately.

    Patches subprocess.Popen only within the session module's namespace so
    that other subprocess.run calls (e.g. in the state module) are unaffected.
    """
    mock_proc = MagicMock()
    mock_proc.pid = 9999
    mock_proc.wait.return_value = 0
    with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc) as mock_popen:
        yield mock_popen, mock_proc


@pytest.fixture
def mock_popen_noninteractive():
    """Return a mock Popen for a non-interactive session."""
    mock_proc = MagicMock()
    mock_proc.pid = 8888
    with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc) as mock_popen:
        yield mock_popen, mock_proc


class TestStartCopilotSessionInteractive:
    """Tests for start_copilot_session in interactive mode."""

    def test_returns_copilot_session_result(self, temp_state, mock_available, mock_popen_interactive):
        """Returns a CopilotSessionResult instance."""
        result = start_copilot_session(
            prompt="Do something",
            working_directory=str(temp_state),
            interactive=True,
        )
        assert isinstance(result, CopilotSessionResult)

    def test_mode_is_interactive(self, temp_state, mock_available, mock_popen_interactive):
        """Mode is set to 'interactive'."""
        result = start_copilot_session(
            prompt="Do something",
            working_directory=str(temp_state),
            interactive=True,
        )
        assert result.mode == "interactive"

    def test_session_id_is_generated(self, temp_state, mock_available, mock_popen_interactive):
        """A session_id is generated when not provided."""
        result = start_copilot_session(
            prompt="Do something",
            working_directory=str(temp_state),
            interactive=True,
        )
        assert result.session_id
        assert len(result.session_id) == 32  # UUID4 hex

    def test_custom_session_id_is_used(self, temp_state, mock_available, mock_popen_interactive):
        """A caller-supplied session_id is used without generating a new one."""
        result = start_copilot_session(
            prompt="Do something",
            working_directory=str(temp_state),
            interactive=True,
            session_id="custom-id-123",
        )
        assert result.session_id == "custom-id-123"

    def test_prompt_file_is_written(self, temp_state, mock_available, mock_popen_interactive):
        """The prompt is written to a file on disk."""
        result = start_copilot_session(
            prompt="Hello copilot",
            working_directory=str(temp_state),
            interactive=True,
        )
        from pathlib import Path

        assert Path(result.prompt_file).read_text(encoding="utf-8") == "Hello copilot"

    def test_start_time_is_set(self, temp_state, mock_available, mock_popen_interactive):
        """start_time is a non-empty ISO-8601 timestamp string."""
        result = start_copilot_session(
            prompt="Do something",
            working_directory=str(temp_state),
            interactive=True,
        )
        assert result.start_time
        assert "T" in result.start_time  # ISO-8601 datetime contains 'T'

    def test_pid_is_none_for_interactive(self, temp_state, mock_available, mock_popen_interactive):
        """pid is None for interactive sessions (process has exited when result is returned)."""
        result = start_copilot_session(
            prompt="Do something",
            working_directory=str(temp_state),
            interactive=True,
        )
        assert result.pid is None

    def test_popen_called_with_shell_false(self, temp_state, mock_available, mock_popen_interactive):
        """Popen is called with shell=False to prevent env-var expansion on Windows."""
        mock_popen, _ = mock_popen_interactive
        start_copilot_session(
            prompt="Do something",
            working_directory=str(temp_state),
            interactive=True,
        )
        call_kwargs = mock_popen.call_args[1]
        assert call_kwargs.get("shell") is False

    def test_popen_called_with_correct_args(self, temp_state, mock_available, mock_popen_interactive):
        """Popen is called with the gh copilot suggest --file <prompt_file> args."""
        mock_popen, _ = mock_popen_interactive
        result = start_copilot_session(
            prompt="Do something",
            working_directory=str(temp_state),
            interactive=True,
        )
        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        assert cmd[:4] == ["gh", "copilot", "suggest", "--file"]
        assert cmd[4] == result.prompt_file

    def test_wait_is_called(self, temp_state, mock_available, mock_popen_interactive):
        """process.wait() is called for interactive mode."""
        _, mock_proc = mock_popen_interactive
        start_copilot_session(
            prompt="Do something",
            working_directory=str(temp_state),
            interactive=True,
        )
        mock_proc.wait.assert_called_once()

    def test_state_is_persisted(self, temp_state, mock_available, mock_popen_interactive):
        """Session metadata is written to agdt-state.json."""
        result = start_copilot_session(
            prompt="Do something",
            working_directory=str(temp_state),
            interactive=True,
        )
        assert state.get_value("copilot.session_id") == result.session_id
        assert state.get_value("copilot.mode") == "interactive"
        assert state.get_value("copilot.prompt_file") == result.prompt_file
        assert state.get_value("copilot.start_time") == result.start_time


class TestStartCopilotSessionNonInteractive:
    """Tests for start_copilot_session in non-interactive mode."""

    def test_popen_called_with_shell_false(self, temp_state, mock_available, mock_popen_noninteractive):
        """Popen is called with shell=False in non-interactive mode."""
        mock_popen, _ = mock_popen_noninteractive
        start_copilot_session(
            prompt="Review the PR",
            working_directory=str(temp_state),
            interactive=False,
        )
        call_kwargs = mock_popen.call_args[1]
        assert call_kwargs.get("shell") is False

    def test_mode_is_non_interactive(self, temp_state, mock_available, mock_popen_noninteractive):
        """Mode is set to 'non-interactive'."""
        result = start_copilot_session(
            prompt="Review the PR",
            working_directory=str(temp_state),
            interactive=False,
        )
        assert result.mode == "non-interactive"

    def test_returns_pid(self, temp_state, mock_available, mock_popen_noninteractive):
        """Result contains the PID of the background process."""
        _, mock_proc = mock_popen_noninteractive
        result = start_copilot_session(
            prompt="Review the PR",
            working_directory=str(temp_state),
            interactive=False,
        )
        assert result.pid == mock_proc.pid

    def test_process_is_stored(self, temp_state, mock_available, mock_popen_noninteractive):
        """The Popen process handle is stored in the result."""
        _, mock_proc = mock_popen_noninteractive
        result = start_copilot_session(
            prompt="Review the PR",
            working_directory=str(temp_state),
            interactive=False,
        )
        assert result.process is mock_proc

    def test_wait_is_not_called(self, temp_state, mock_available, mock_popen_noninteractive):
        """process.wait() is NOT called for non-interactive mode."""
        _, mock_proc = mock_popen_noninteractive
        start_copilot_session(
            prompt="Review the PR",
            working_directory=str(temp_state),
            interactive=False,
        )
        mock_proc.wait.assert_not_called()

    def test_state_mode_persisted(self, temp_state, mock_available, mock_popen_noninteractive):
        """Non-interactive mode is stored in state."""
        start_copilot_session(
            prompt="Review the PR",
            working_directory=str(temp_state),
            interactive=False,
        )
        assert state.get_value("copilot.mode") == "non-interactive"

    def test_pid_persisted_in_state(self, temp_state, mock_available, mock_popen_noninteractive):
        """PID is stored in state for non-interactive sessions."""
        _, mock_proc = mock_popen_noninteractive
        start_copilot_session(
            prompt="Review the PR",
            working_directory=str(temp_state),
            interactive=False,
        )
        assert state.get_value("copilot.pid") == mock_proc.pid


class TestStartCopilotSessionFallback:
    """Tests for start_copilot_session fallback when gh copilot is unavailable."""

    def test_returns_result_without_process(self, temp_state, mock_unavailable):
        """Returns a CopilotSessionResult with no process when gh copilot unavailable."""
        with warnings.catch_warnings(record=True):
            result = start_copilot_session(
                prompt="Do something",
                working_directory=str(temp_state),
            )
        assert isinstance(result, CopilotSessionResult)
        assert result.process is None
        assert result.pid is None

    def test_issues_warning(self, temp_state, mock_unavailable):
        """Issues a UserWarning when gh copilot is unavailable."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            start_copilot_session(
                prompt="Do something",
                working_directory=str(temp_state),
            )
        assert any("gh copilot is not available" in str(warning.message) for warning in w)

    def test_prints_prompt_to_stdout(self, temp_state, mock_unavailable, capsys):
        """Prints the prompt to stdout as fallback."""
        with warnings.catch_warnings(record=True):
            start_copilot_session(
                prompt="My fallback prompt",
                working_directory=str(temp_state),
            )
        captured = capsys.readouterr()
        assert "My fallback prompt" in captured.out

    def test_state_is_persisted_in_fallback(self, temp_state, mock_unavailable):
        """Session state is still persisted even in fallback mode."""
        with warnings.catch_warnings(record=True):
            result = start_copilot_session(
                prompt="Do something",
                working_directory=str(temp_state),
            )
        assert state.get_value("copilot.session_id") == result.session_id
        assert state.get_value("copilot.mode") in ("interactive", "non-interactive")

    def test_prompt_file_is_written_in_fallback(self, temp_state, mock_unavailable):
        """Prompt file is written even when gh copilot is unavailable."""
        from pathlib import Path

        with warnings.catch_warnings(record=True):
            result = start_copilot_session(
                prompt="Fallback prompt text",
                working_directory=str(temp_state),
            )
        assert Path(result.prompt_file).read_text(encoding="utf-8") == "Fallback prompt text"


class TestStartCopilotSessionWithStandaloneBinary:
    """Tests for start_copilot_session when the standalone copilot binary is available."""

    def test_uses_standalone_binary_in_popen_args(self, temp_state, mock_available, mock_popen_interactive):
        """When standalone copilot binary is found, Popen is called with it directly."""
        mock_popen, _ = mock_popen_interactive
        with patch.object(session_module, "_get_copilot_binary", return_value="/usr/local/bin/copilot"):
            result = start_copilot_session(
                prompt="Use standalone",
                working_directory=str(temp_state),
                interactive=True,
            )
        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        assert cmd[0] == "/usr/local/bin/copilot"
        assert cmd[1] == "suggest"
        assert cmd[2] == "--file"
        assert cmd[3] == result.prompt_file
