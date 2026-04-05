"""Tests for start_copilot_session."""

import io
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
            autopilot=False,
        )
        assert isinstance(result, CopilotSessionResult)

    def test_mode_is_interactive(self, temp_state, mock_available, mock_popen_interactive):
        """Mode is set to 'interactive'."""
        result = start_copilot_session(
            prompt="Do something",
            working_directory=str(temp_state),
            interactive=True,
            autopilot=False,
        )
        assert result.mode == "interactive"

    def test_session_id_is_generated(self, temp_state, mock_available, mock_popen_interactive):
        """A session_id is generated when not provided."""
        result = start_copilot_session(
            prompt="Do something",
            working_directory=str(temp_state),
            interactive=True,
            autopilot=False,
        )
        assert result.session_id
        assert len(result.session_id) == 32  # UUID4 hex

    def test_custom_session_id_is_used(self, temp_state, mock_available, mock_popen_interactive):
        """A caller-supplied session_id is used without generating a new one."""
        result = start_copilot_session(
            prompt="Do something",
            working_directory=str(temp_state),
            interactive=True,
            autopilot=False,
            session_id="custom-id-123",
        )
        assert result.session_id == "custom-id-123"

    def test_prompt_file_is_written(self, temp_state, mock_available, mock_popen_interactive):
        """The prompt is written to a file on disk."""
        result = start_copilot_session(
            prompt="Hello copilot",
            working_directory=str(temp_state),
            interactive=True,
            autopilot=False,
        )
        from pathlib import Path

        assert Path(result.prompt_file).read_text(encoding="utf-8") == "Hello copilot"

    def test_start_time_is_set(self, temp_state, mock_available, mock_popen_interactive):
        """start_time is a non-empty ISO-8601 timestamp string."""
        result = start_copilot_session(
            prompt="Do something",
            working_directory=str(temp_state),
            interactive=True,
            autopilot=False,
        )
        assert result.start_time
        assert "T" in result.start_time  # ISO-8601 datetime contains 'T'

    def test_pid_is_none_for_interactive(self, temp_state, mock_available, mock_popen_interactive):
        """pid is None for interactive sessions (process has exited when result is returned)."""
        result = start_copilot_session(
            prompt="Do something",
            working_directory=str(temp_state),
            interactive=True,
            autopilot=False,
        )
        assert result.pid is None

    def test_popen_called_with_shell_false(self, temp_state, mock_available, mock_popen_interactive):
        """Popen is called with shell=False to prevent env-var expansion on Windows."""
        mock_popen, _ = mock_popen_interactive
        start_copilot_session(
            prompt="Do something",
            working_directory=str(temp_state),
            interactive=True,
            autopilot=False,
        )
        call_kwargs = mock_popen.call_args[1]
        assert call_kwargs.get("shell") is False

    def test_popen_called_with_correct_args_gh_fallback(self, temp_state, mock_available, mock_popen_interactive):
        """Popen is called with gh copilot suggest <inlined_prompt> args when no standalone binary is available."""
        mock_popen, _ = mock_popen_interactive
        with patch.object(session_module, "_get_copilot_binary", return_value=None):
            start_copilot_session(
                prompt="Do something",
                working_directory=str(temp_state),
                interactive=True,
                autopilot=False,
            )
        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        assert cmd[:3] == ["gh", "copilot", "suggest"]
        # The prompt is inlined with <br> replacements
        assert "Do something" in cmd[3]
        assert "The full prompt is also saved at:" in cmd[3]

    def test_popen_called_with_standalone_binary(self, temp_state, mock_available, mock_popen_interactive):
        """Popen uses the standalone copilot binary with -i flag when available."""
        mock_popen, _ = mock_popen_interactive
        with patch.object(session_module, "_get_copilot_binary", return_value="/usr/bin/copilot"):
            start_copilot_session(
                prompt="Do something",
                working_directory=str(temp_state),
                interactive=True,
            )
        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        assert cmd[0] == "/usr/bin/copilot"
        assert "-i" in cmd
        assert "Do something" in cmd[-1]

    def test_wait_is_called(self, temp_state, mock_available, mock_popen_interactive):
        """process.wait() is called for interactive mode."""
        _, mock_proc = mock_popen_interactive
        start_copilot_session(
            prompt="Do something",
            working_directory=str(temp_state),
            interactive=True,
            autopilot=False,
        )
        mock_proc.wait.assert_called_once()

    def test_state_is_persisted(self, temp_state, mock_available, mock_popen_interactive):
        """Session metadata is written to agdt-state.json."""
        result = start_copilot_session(
            prompt="Do something",
            working_directory=str(temp_state),
            interactive=True,
            autopilot=False,
        )
        assert state.get_value("copilot.session_id") == result.session_id
        assert state.get_value("copilot.mode") == "interactive"
        assert state.get_value("copilot.prompt_file") == result.prompt_file
        assert state.get_value("copilot.start_time") == result.start_time

    def test_interactive_strips_node_options_from_env(self, temp_state, mock_available, mock_popen_interactive):
        """NODE_OPTIONS is excluded from the subprocess environment for interactive sessions."""
        mock_popen, _ = mock_popen_interactive
        with patch.dict("os.environ", {"NODE_OPTIONS": "--no-warnings"}, clear=False):
            start_copilot_session(
                prompt="Do something",
                working_directory=str(temp_state),
                interactive=True,
                autopilot=False,
            )

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs.get("env", {})
        assert "NODE_OPTIONS" not in env

    def test_interactive_preserves_other_env_vars(self, temp_state, mock_available, mock_popen_interactive):
        """Other environment variables are preserved in the interactive subprocess environment."""
        mock_popen, _ = mock_popen_interactive
        with patch.dict("os.environ", {"MY_CUSTOM_VAR": "my_value"}, clear=False):
            start_copilot_session(
                prompt="Do something",
                working_directory=str(temp_state),
                interactive=True,
                autopilot=False,
            )

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs.get("env", {})
        assert env.get("MY_CUSTOM_VAR") == "my_value"


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

    def test_wait_is_not_called_by_start_function(self, temp_state, mock_available, mock_popen_noninteractive):
        """process.wait() is NOT called by start_copilot_session directly for non-interactive mode.

        The _tee background thread calls process.wait() to collect the exit code
        for lifecycle markers, but start_copilot_session itself returns immediately
        without blocking on wait(). The thread is mocked here (not run
        synchronously), so wait() must not have been called at all.
        """
        _, mock_proc = mock_popen_noninteractive
        with patch("agentic_devtools.cli.copilot.session.threading.Thread") as mock_thread_cls:
            mock_thread_cls.return_value = MagicMock()
            result = start_copilot_session(
                prompt="Review the PR",
                working_directory=str(temp_state),
                interactive=False,
            )
        # The process handle is stored in the result (not waited on by the main function)
        assert result.process is mock_proc
        # Thread is mocked — wait() should not have been called yet
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
        with pytest.warns(UserWarning, match="gh copilot is not available"):
            result = start_copilot_session(
                prompt="Do something",
                working_directory=str(temp_state),
            )
        assert isinstance(result, CopilotSessionResult)
        assert result.process is None
        assert result.pid is None

    def test_issues_warning(self, temp_state, mock_unavailable):
        """Issues a UserWarning when gh copilot is unavailable."""
        with pytest.warns(UserWarning, match="gh copilot is not available"):
            start_copilot_session(
                prompt="Do something",
                working_directory=str(temp_state),
            )

    def test_prints_prompt_to_stdout(self, temp_state, mock_unavailable, capsys):
        """Prints the prompt to stdout as fallback."""
        with pytest.warns(UserWarning, match="gh copilot is not available"):
            start_copilot_session(
                prompt="My fallback prompt",
                working_directory=str(temp_state),
            )
        captured = capsys.readouterr()
        assert "My fallback prompt" in captured.out

    def test_state_is_persisted_in_fallback(self, temp_state, mock_unavailable):
        """Session state is still persisted even in fallback mode."""
        with pytest.warns(UserWarning, match="gh copilot is not available"):
            result = start_copilot_session(
                prompt="Do something",
                working_directory=str(temp_state),
            )
        assert state.get_value("copilot.session_id") == result.session_id
        assert state.get_value("copilot.mode") in ("interactive", "non-interactive")

    def test_prompt_file_is_written_in_fallback(self, temp_state, mock_unavailable):
        """Prompt file is written even when gh copilot is unavailable."""
        from pathlib import Path

        with pytest.warns(UserWarning, match="gh copilot is not available"):
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
        assert "suggest" not in cmd
        assert "--file" not in cmd
        assert "--autopilot" in cmd
        assert cmd.index("--autopilot") < cmd.index("-i")
        # The prompt is inlined with <br> and backup reference
        assert "Use standalone" in cmd[-1]
        assert "The full prompt is also saved at:" in cmd[-1]
        assert result.prompt_file  # prompt file is still written to disk

    def test_standalone_interactive_autopilot_false_excludes_flag(
        self, temp_state, mock_available, mock_popen_interactive
    ):
        """When autopilot=False, --autopilot is NOT included for standalone interactive sessions."""
        mock_popen, _ = mock_popen_interactive
        with patch.object(session_module, "_get_copilot_binary", return_value="/usr/local/bin/copilot"):
            start_copilot_session(
                prompt="Use standalone",
                working_directory=str(temp_state),
                interactive=True,
                autopilot=False,
            )
        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        assert cmd[0] == "/usr/local/bin/copilot"
        assert "--autopilot" not in cmd
        assert "-i" in cmd

    def test_standalone_binary_uses_prompt_flag_for_noninteractive(
        self, temp_state, mock_available, mock_popen_noninteractive
    ):
        """When standalone copilot binary is used non-interactively, -p flag and --allow-all are passed."""
        mock_popen, _ = mock_popen_noninteractive
        with patch.object(session_module, "_get_copilot_binary", return_value="/usr/local/bin/copilot"):
            result = start_copilot_session(
                prompt="Review PR",
                working_directory=str(temp_state),
                interactive=False,
            )

        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        assert cmd[0] == "/usr/local/bin/copilot"
        assert "suggest" not in cmd
        # --allow-all must come before -p so argument parsers that stop
        # processing flags after the first positional argument still see it.
        assert cmd[1] == "--allow-all"
        assert cmd[2] == "-p"
        assert "--allow-all-tools" not in cmd
        assert result.prompt_file

    def test_standalone_binary_includes_allow_all_only_for_noninteractive(
        self, temp_state, mock_available, mock_popen_interactive
    ):
        """--allow-all is NOT included when the standalone binary runs interactively."""
        mock_popen, _ = mock_popen_interactive
        with patch.object(session_module, "_get_copilot_binary", return_value="/usr/local/bin/copilot"):
            start_copilot_session(
                prompt="Use standalone",
                working_directory=str(temp_state),
                interactive=True,
            )
        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        assert "--allow-all" not in cmd
        assert "--allow-all-tools" not in cmd

    def test_noninteractive_passes_inlined_prompt_not_file_reference(
        self, temp_state, mock_available, mock_popen_noninteractive
    ):
        """Non-interactive mode passes the inlined prompt with <br> replacements, not a file reference."""
        mock_popen, _ = mock_popen_noninteractive
        original_prompt = "Detailed multi-line\nprompt with special chars: $PATH & more"
        with patch.object(session_module, "_get_copilot_binary", return_value="/usr/local/bin/copilot"):
            start_copilot_session(
                prompt=original_prompt,
                working_directory=str(temp_state),
                interactive=False,
            )

        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        # The -p argument must contain the inlined prompt with <br> replacements.
        # With --allow-all before -p, the layout is:
        #   cmd[0]=binary, cmd[1]=--allow-all, cmd[2]=-p, cmd[3]=<inlined prompt>
        argv_p = cmd[3]
        assert "   <br>   " in argv_p
        assert "Detailed multi-line" in argv_p
        assert "prompt with special chars: $PATH & more" in argv_p
        assert "The full prompt is also saved at:" in argv_p

    def test_noninteractive_strips_node_options_from_env(self, temp_state, mock_available, mock_popen_noninteractive):
        """NODE_OPTIONS is excluded from the subprocess environment for non-interactive sessions."""
        mock_popen, _ = mock_popen_noninteractive
        with patch.object(session_module, "_get_copilot_binary", return_value="/usr/local/bin/copilot"):
            with patch.dict("os.environ", {"NODE_OPTIONS": "--no-warnings"}, clear=False):
                start_copilot_session(
                    prompt="Review PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs.get("env", {})
        assert "NODE_OPTIONS" not in env

    def test_noninteractive_preserves_other_env_vars(self, temp_state, mock_available, mock_popen_noninteractive):
        """Other environment variables are preserved in the subprocess environment."""
        mock_popen, _ = mock_popen_noninteractive
        with patch.object(session_module, "_get_copilot_binary", return_value="/usr/local/bin/copilot"):
            with patch.dict("os.environ", {"MY_CUSTOM_VAR": "my_value"}, clear=False):
                start_copilot_session(
                    prompt="Review PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )

        call_kwargs = mock_popen.call_args[1]
        env = call_kwargs.get("env", {})
        assert env.get("MY_CUSTOM_VAR") == "my_value"


class TestStartCopilotSessionLargePromptFallback:
    """Tests for start_copilot_session with prompts that exceed safe argv limits.

    With the _inline_prompt mechanism, large prompts without a Focus Areas
    section fall back to a short file-reference-only prompt.  The stdout
    fallback path is only triggered when gh copilot is unavailable or
    _build_copilot_args returns None for other reasons.
    """

    def test_truncates_large_prompt_with_warning(self, temp_state, mock_available, mock_popen_interactive):
        """Large prompts fall back to a file-reference-only prompt with a warning."""
        mock_popen, _ = mock_popen_interactive
        large_prompt = "x" * (session_module._MAX_GH_COPILOT_ARGV_LENGTH + 1)

        with pytest.warns(UserWarning, match="too large for inline"):
            result = start_copilot_session(
                prompt=large_prompt,
                working_directory=str(temp_state),
                autopilot=False,
            )

        # Popen IS called (prompt was replaced with a short file-reference)
        mock_popen.assert_called_once()
        assert result.session_id
        # Verify the file-reference prompt preserves the backup path
        cmd = mock_popen.call_args[0][0]
        argv_prompt = cmd[-1]  # The prompt is the last argument
        assert "The full prompt is also saved at:" in argv_prompt
        assert len(argv_prompt) <= session_module._SAFE_ARGV_LENGTH

    def test_prompt_file_still_written_on_large_prompt(self, temp_state, mock_available, mock_popen_interactive):
        """Prompt file is written with full original content even for large prompts."""
        from pathlib import Path

        mock_popen, _ = mock_popen_interactive
        large_prompt = "x" * (session_module._MAX_GH_COPILOT_ARGV_LENGTH + 1)

        with pytest.warns(UserWarning, match="too large for inline"):
            result = start_copilot_session(
                prompt=large_prompt,
                working_directory=str(temp_state),
                autopilot=False,
            )

        assert Path(result.prompt_file).read_text(encoding="utf-8") == large_prompt

    def test_standalone_binary_truncates_large_prompt(self, temp_state, mock_available, mock_popen_interactive):
        """Standalone binary also falls back to file-reference for large prompts."""
        mock_popen, _ = mock_popen_interactive
        large_prompt = "x" * (session_module._MAX_GH_COPILOT_ARGV_LENGTH + 1)

        with patch.object(session_module, "_get_copilot_binary", return_value="/usr/local/bin/copilot"):
            with pytest.warns(UserWarning, match="too large for inline"):
                result = start_copilot_session(
                    prompt=large_prompt,
                    working_directory=str(temp_state),
                    interactive=True,
                )

        mock_popen.assert_called_once()
        assert result.session_id


class TestStartCopilotSessionNonInteractiveTee:
    """Tests for the non-interactive tee behavior: output goes to log file AND stdout."""

    def _make_mock_process(self, output_bytes: bytes, exit_code: int = 0) -> MagicMock:
        """Return a mock Popen whose stdout yields the given bytes."""
        proc = MagicMock()
        proc.pid = 7777
        proc.stdout = io.BytesIO(output_bytes)
        proc.wait.return_value = exit_code
        return proc

    def _sync_thread_side_effect(self, **kwargs):
        """Return a thread substitute that runs *target* synchronously on start().

        Accepts ``**kwargs`` because ``threading.Thread(...)`` is called with
        keyword arguments (``target=``, ``args=``, ``daemon=``).
        """
        target = kwargs.get("target")
        thread_args = kwargs.get("args", ())

        class _SyncThread:
            def start(self):
                if target is not None:
                    target(*thread_args)

        return _SyncThread()

    def test_output_teed_to_stdout(self, temp_state, mock_available, capsys):
        """Non-interactive output is written to stdout (pipeline visibility)."""
        output = b"copilot line one\ncopilot line two\n"
        mock_proc = self._make_mock_process(output)
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch(
                "agentic_devtools.cli.copilot.session.threading.Thread",
                side_effect=self._sync_thread_side_effect,
            ):
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        captured = capsys.readouterr()
        assert "copilot line one" in captured.out
        assert "copilot line two" in captured.out

    def test_output_written_to_log_file(self, temp_state, mock_available):
        """Non-interactive output is written to the log file."""
        output = b"log entry alpha\nlog entry beta\n"
        mock_proc = self._make_mock_process(output)
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch(
                "agentic_devtools.cli.copilot.session.threading.Thread",
                side_effect=self._sync_thread_side_effect,
            ):
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        log_dir = temp_state / "background-tasks" / "logs"
        log_files = list(log_dir.glob("*.log"))
        assert len(log_files) == 1
        log_content = log_files[0].read_text(encoding="utf-8")
        assert "log entry alpha" in log_content
        assert "log entry beta" in log_content

    def test_tee_runs_in_non_daemon_thread(self, temp_state, mock_available):
        """The tee thread is non-daemon so the parent waits for the subprocess to finish."""
        mock_proc = self._make_mock_process(b"")
        captured_thread_kwargs: list = []
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch("agentic_devtools.cli.copilot.session.threading.Thread") as mock_thread_cls:
                mock_thread_instance = MagicMock()
                mock_thread_cls.return_value = mock_thread_instance
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
                captured_thread_kwargs.extend(mock_thread_cls.call_args_list)

        assert len(captured_thread_kwargs) == 1
        call_kwargs = captured_thread_kwargs[0][1]
        assert call_kwargs.get("daemon") is False
        mock_thread_instance.start.assert_called_once()

    def test_log_file_directory_created(self, temp_state, mock_available):
        """The log file parent directory is created when it does not exist."""
        mock_proc = self._make_mock_process(b"")
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch("agentic_devtools.cli.copilot.session.threading.Thread") as mock_thread_cls:
                mock_thread_cls.return_value = MagicMock()
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        log_dir = temp_state / "background-tasks" / "logs"
        assert log_dir.is_dir()

    def test_popen_uses_pipe_for_stdout(self, temp_state, mock_available):
        """Popen is called with stdout=PIPE in non-interactive mode for tee support."""
        import subprocess

        mock_proc = self._make_mock_process(b"")
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc) as mock_popen:
            with patch("agentic_devtools.cli.copilot.session.threading.Thread") as mock_thread_cls:
                mock_thread_cls.return_value = MagicMock()
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        call_kwargs = mock_popen.call_args[1]
        assert call_kwargs.get("stdout") == subprocess.PIPE

    def test_tee_continues_logging_when_stdout_fails(self, temp_state, mock_available):
        """Log file still receives all output when stdout raises OSError mid-stream."""
        output = b"line before error\nline after error\n"
        mock_proc = self._make_mock_process(output)

        broken_stdout = MagicMock()
        broken_stdout.write.side_effect = OSError("stdout closed")

        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch("agentic_devtools.cli.copilot.session.sys.stdout", broken_stdout):
                with patch(
                    "agentic_devtools.cli.copilot.session.threading.Thread",
                    side_effect=self._sync_thread_side_effect,
                ):
                    start_copilot_session(
                        prompt="Review the PR",
                        working_directory=str(temp_state),
                        interactive=False,
                    )

        log_dir = temp_state / "background-tasks" / "logs"
        log_files = list(log_dir.glob("*.log"))
        assert len(log_files) == 1
        log_content = log_files[0].read_text(encoding="utf-8")
        assert "line before error" in log_content
        assert "line after error" in log_content

    def test_tee_handles_none_pipe_gracefully(self, temp_state, mock_available):
        """When process.stdout is None, the tee thread emits SESSION_START + SESSION_END and closes the log."""
        mock_proc = MagicMock()
        mock_proc.pid = 7777
        mock_proc.stdout = None  # Simulate None stdout pipe
        mock_proc.wait.return_value = 0
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch(
                "agentic_devtools.cli.copilot.session.threading.Thread",
                side_effect=self._sync_thread_side_effect,
            ):
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        log_dir = temp_state / "background-tasks" / "logs"
        log_files = list(log_dir.glob("*.log"))
        assert len(log_files) == 1
        log_content = log_files[0].read_text(encoding="utf-8")
        assert "[agdt-copilot-session] SESSION_START" in log_content
        assert "[agdt-copilot-session] SESSION_END" in log_content
        assert "total_lines=0" in log_content
        assert "total_bytes=0" in log_content

    def test_none_pipe_emits_session_error_on_nonzero_exit(self, temp_state, mock_available):
        """When process.stdout is None and exit code != 0, SESSION_ERROR is emitted."""
        mock_proc = MagicMock()
        mock_proc.pid = 7777
        mock_proc.stdout = None
        mock_proc.wait.return_value = 2
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch(
                "agentic_devtools.cli.copilot.session.threading.Thread",
                side_effect=self._sync_thread_side_effect,
            ):
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        log_dir = temp_state / "background-tasks" / "logs"
        log_content = list(log_dir.glob("*.log"))[0].read_text(encoding="utf-8")
        assert "[agdt-copilot-session] SESSION_ERROR" in log_content
        assert "exit_code=2" in log_content
        assert "[agdt-copilot-session] SESSION_END" in log_content

    def test_session_start_marker_in_log(self, temp_state, mock_available):
        """SESSION_START marker appears in the log file with expected fields."""
        output = b"some output\n"
        mock_proc = self._make_mock_process(output)
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch(
                "agentic_devtools.cli.copilot.session.threading.Thread",
                side_effect=self._sync_thread_side_effect,
            ):
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        log_dir = temp_state / "background-tasks" / "logs"
        log_files = list(log_dir.glob("*.log"))
        assert len(log_files) == 1
        log_content = log_files[0].read_text(encoding="utf-8")
        assert "[agdt-copilot-session] SESSION_START" in log_content
        assert "pid=7777" in log_content
        assert "model=default" in log_content
        assert "prompt_length=" in log_content

    def test_session_end_marker_in_log(self, temp_state, mock_available):
        """SESSION_END marker appears after all output lines."""
        output = b"line one\nline two\n"
        mock_proc = self._make_mock_process(output)
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch(
                "agentic_devtools.cli.copilot.session.threading.Thread",
                side_effect=self._sync_thread_side_effect,
            ):
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        log_dir = temp_state / "background-tasks" / "logs"
        log_content = list(log_dir.glob("*.log"))[0].read_text(encoding="utf-8")
        assert "[agdt-copilot-session] SESSION_END" in log_content
        assert "exit_code=0" in log_content
        assert "total_lines=2" in log_content
        # SESSION_END must appear after the output lines
        end_pos = log_content.index("[agdt-copilot-session] SESSION_END")
        assert log_content.index("line two") < end_pos

    def test_session_error_marker_on_nonzero_exit(self, temp_state, mock_available):
        """SESSION_ERROR marker appears when exit code != 0."""
        output = b"error output\n"
        mock_proc = self._make_mock_process(output, exit_code=1)
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch(
                "agentic_devtools.cli.copilot.session.threading.Thread",
                side_effect=self._sync_thread_side_effect,
            ):
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        log_dir = temp_state / "background-tasks" / "logs"
        log_content = list(log_dir.glob("*.log"))[0].read_text(encoding="utf-8")
        assert "[agdt-copilot-session] SESSION_ERROR" in log_content
        assert "exit_code=1" in log_content
        # SESSION_ERROR must appear before SESSION_END
        error_pos = log_content.index("[agdt-copilot-session] SESSION_ERROR")
        end_pos = log_content.index("[agdt-copilot-session] SESSION_END")
        assert error_pos < end_pos

    def test_no_session_error_on_zero_exit(self, temp_state, mock_available):
        """SESSION_ERROR marker is NOT emitted when exit code is 0."""
        output = b"ok\n"
        mock_proc = self._make_mock_process(output, exit_code=0)
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch(
                "agentic_devtools.cli.copilot.session.threading.Thread",
                side_effect=self._sync_thread_side_effect,
            ):
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        log_dir = temp_state / "background-tasks" / "logs"
        log_content = list(log_dir.glob("*.log"))[0].read_text(encoding="utf-8")
        assert "SESSION_ERROR" not in log_content

    def test_heartbeat_marker_emitted_after_interval(self, temp_state, mock_available):
        """SESSION_HEARTBEAT is emitted when enough time has passed."""
        output = b"line1\nline2\nline3\n"
        mock_proc = self._make_mock_process(output)

        # Calls to time.monotonic():
        # 1: tee_start (initial)
        # 2: now_mono for line1 (0.0s elapsed, no heartbeat)
        # 3: now_mono for line2 (61.0s elapsed, heartbeat fires)
        # 4: now_mono for line3 (62.0s since start, 1.0s since last heartbeat)
        # 5: elapsed_total after loop (for SESSION_END)
        # 6: JSONL summary total_duration_ms
        monotonic_values = iter([0.0, 0.0, 61.0, 62.0, 62.0, 62.0])

        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch("agentic_devtools.cli.copilot.session.time.monotonic", side_effect=monotonic_values):
                with patch(
                    "agentic_devtools.cli.copilot.session.threading.Thread",
                    side_effect=self._sync_thread_side_effect,
                ):
                    start_copilot_session(
                        prompt="Review the PR",
                        working_directory=str(temp_state),
                        interactive=False,
                    )
        log_dir = temp_state / "background-tasks" / "logs"
        log_content = list(log_dir.glob("*.log"))[0].read_text(encoding="utf-8")
        assert "[agdt-copilot-session] SESSION_HEARTBEAT" in log_content
        assert "elapsed_seconds=" in log_content
        assert "bytes_read=" in log_content
        assert "lines_read=" in log_content

    def test_no_heartbeat_for_short_sessions(self, temp_state, mock_available):
        """No heartbeat for sessions < 60s."""
        output = b"line1\nline2\n"
        mock_proc = self._make_mock_process(output)

        # Simulate time: all within 60 seconds
        # Calls to time.monotonic():
        # 1: tee_start (initial)
        # 2: now_mono for line1 (0.0s elapsed, no heartbeat)
        # 3: now_mono for line2 (1.0s elapsed, no heartbeat)
        # 4: elapsed_total after loop (for SESSION_END)
        # 5: JSONL summary total_duration_ms
        monotonic_values = iter([0.0, 0.0, 1.0, 2.0, 2.0])

        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch("agentic_devtools.cli.copilot.session.time.monotonic", side_effect=monotonic_values):
                with patch(
                    "agentic_devtools.cli.copilot.session.threading.Thread",
                    side_effect=self._sync_thread_side_effect,
                ):
                    start_copilot_session(
                        prompt="Review the PR",
                        working_directory=str(temp_state),
                        interactive=False,
                    )
        log_dir = temp_state / "background-tasks" / "logs"
        log_content = list(log_dir.glob("*.log"))[0].read_text(encoding="utf-8")
        assert "SESSION_HEARTBEAT" not in log_content


class TestStartCopilotSessionNonInteractiveJsonl:
    """Tests for the structured JSONL logging in non-interactive mode."""

    def _make_mock_process(self, output_bytes: bytes) -> MagicMock:
        """Return a mock Popen whose stdout yields the given bytes."""
        import io as _io

        proc = MagicMock()
        proc.pid = 7777
        proc.stdout = _io.BytesIO(output_bytes)
        proc.wait.return_value = 0
        return proc

    def _sync_thread_side_effect(self, **kwargs):
        """Run the thread target synchronously for deterministic testing."""
        target = kwargs.get("target")
        thread_args = kwargs.get("args", ())

        class _SyncThread:
            def start(self):
                if target is not None:
                    target(*thread_args)

        return _SyncThread()

    def test_jsonl_file_created_alongside_log(self, temp_state, mock_available):
        """A .jsonl file is created in the same directory as the .log file."""
        mock_proc = self._make_mock_process(b"some output\n")
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch(
                "agentic_devtools.cli.copilot.session.threading.Thread",
                side_effect=self._sync_thread_side_effect,
            ):
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        log_dir = temp_state / "background-tasks" / "logs"
        jsonl_files = list(log_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1

    def test_jsonl_file_has_same_stem_as_log(self, temp_state, mock_available):
        """The .jsonl file shares the same filename stem as the .log file."""
        mock_proc = self._make_mock_process(b"output\n")
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch(
                "agentic_devtools.cli.copilot.session.threading.Thread",
                side_effect=self._sync_thread_side_effect,
            ):
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        log_dir = temp_state / "background-tasks" / "logs"
        log_stems = {f.stem for f in log_dir.glob("*.log")}
        jsonl_stems = {f.stem for f in log_dir.glob("*.jsonl")}
        assert log_stems == jsonl_stems

    def test_each_output_line_produces_jsonl_entry(self, temp_state, mock_available):
        """Each line from subprocess output produces a JSON object in the .jsonl file."""
        import json

        output = b"alpha\nbeta\ngamma\n"
        mock_proc = self._make_mock_process(output)
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch(
                "agentic_devtools.cli.copilot.session.threading.Thread",
                side_effect=self._sync_thread_side_effect,
            ):
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        log_dir = temp_state / "background-tasks" / "logs"
        jsonl_file = list(log_dir.glob("*.jsonl"))[0]
        lines = jsonl_file.read_text(encoding="utf-8").strip().split("\n")
        entries = [json.loads(line) for line in lines]
        # 3 output entries + 1 summary entry
        assert len(entries) == 4
        output_entries = [e for e in entries if e["event_type"] == "output"]
        assert len(output_entries) == 3
        assert output_entries[0]["content"] == "alpha"
        assert output_entries[1]["content"] == "beta"
        assert output_entries[2]["content"] == "gamma"

    def test_jsonl_entries_include_timestamp(self, temp_state, mock_available):
        """Each JSONL entry contains a timestamp field."""
        import json

        mock_proc = self._make_mock_process(b"test line\n")
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch(
                "agentic_devtools.cli.copilot.session.threading.Thread",
                side_effect=self._sync_thread_side_effect,
            ):
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        log_dir = temp_state / "background-tasks" / "logs"
        jsonl_file = list(log_dir.glob("*.jsonl"))[0]
        lines = jsonl_file.read_text(encoding="utf-8").strip().split("\n")
        for line in lines:
            entry = json.loads(line)
            assert "timestamp" in entry

    def test_jsonl_entries_include_event_type(self, temp_state, mock_available):
        """Each JSONL entry contains an event_type field."""
        import json

        mock_proc = self._make_mock_process(b"hello\n")
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch(
                "agentic_devtools.cli.copilot.session.threading.Thread",
                side_effect=self._sync_thread_side_effect,
            ):
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        log_dir = temp_state / "background-tasks" / "logs"
        jsonl_file = list(log_dir.glob("*.jsonl"))[0]
        lines = jsonl_file.read_text(encoding="utf-8").strip().split("\n")
        entries = [json.loads(line) for line in lines]
        assert entries[0]["event_type"] == "output"
        assert entries[-1]["event_type"] == "summary"

    def test_jsonl_entries_include_duration_ms(self, temp_state, mock_available):
        """Each JSONL entry contains a duration_ms field."""
        import json

        mock_proc = self._make_mock_process(b"data\n")
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch(
                "agentic_devtools.cli.copilot.session.threading.Thread",
                side_effect=self._sync_thread_side_effect,
            ):
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        log_dir = temp_state / "background-tasks" / "logs"
        jsonl_file = list(log_dir.glob("*.jsonl"))[0]
        lines = jsonl_file.read_text(encoding="utf-8").strip().split("\n")
        for line in lines:
            entry = json.loads(line)
            assert "duration_ms" in entry
            assert isinstance(entry["duration_ms"], int)

    def test_summary_entry_written_at_session_end(self, temp_state, mock_available):
        """A summary entry with event_type='summary' is the last entry in the .jsonl file."""
        import json

        output = b"line one\nline two\n"
        mock_proc = self._make_mock_process(output)
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch(
                "agentic_devtools.cli.copilot.session.threading.Thread",
                side_effect=self._sync_thread_side_effect,
            ):
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        log_dir = temp_state / "background-tasks" / "logs"
        jsonl_file = list(log_dir.glob("*.jsonl"))[0]
        lines = jsonl_file.read_text(encoding="utf-8").strip().split("\n")
        summary = json.loads(lines[-1])
        assert summary["event_type"] == "summary"
        assert summary["content"] == "session_end"
        assert summary["total_lines"] == 2

    def test_existing_log_format_preserved(self, temp_state, mock_available):
        """The .log file format is unchanged by the addition of JSONL logging."""
        output = b"log entry alpha\nlog entry beta\n"
        mock_proc = self._make_mock_process(output)
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch(
                "agentic_devtools.cli.copilot.session.threading.Thread",
                side_effect=self._sync_thread_side_effect,
            ):
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        log_dir = temp_state / "background-tasks" / "logs"
        log_files = list(log_dir.glob("*.log"))
        assert len(log_files) == 1
        log_content = log_files[0].read_text(encoding="utf-8")
        assert "log entry alpha" in log_content
        assert "log entry beta" in log_content

    def test_jsonl_content_strips_trailing_newline(self, temp_state, mock_available):
        """The content field in JSONL entries has trailing newlines stripped."""
        import json

        mock_proc = self._make_mock_process(b"hello world\n")
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch(
                "agentic_devtools.cli.copilot.session.threading.Thread",
                side_effect=self._sync_thread_side_effect,
            ):
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        log_dir = temp_state / "background-tasks" / "logs"
        jsonl_file = list(log_dir.glob("*.jsonl"))[0]
        lines = jsonl_file.read_text(encoding="utf-8").strip().split("\n")
        output_entry = json.loads(lines[0])
        assert output_entry["content"] == "hello world"

    def test_jsonl_with_none_pipe_produces_empty_file(self, temp_state, mock_available):
        """When process.stdout is None, the .jsonl file is created but empty."""
        mock_proc = MagicMock()
        mock_proc.pid = 7777
        mock_proc.stdout = None
        mock_proc.wait.return_value = 0
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch(
                "agentic_devtools.cli.copilot.session.threading.Thread",
                side_effect=self._sync_thread_side_effect,
            ):
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        log_dir = temp_state / "background-tasks" / "logs"
        jsonl_files = list(log_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1
        jsonl_content = jsonl_files[0].read_text(encoding="utf-8")
        assert jsonl_content == ""

    def test_tee_continues_logging_when_jsonl_write_fails(self, temp_state, mock_available):
        """Log file and stdout still receive all output when JSONL write raises OSError."""
        output = b"line before jsonl error\nline after jsonl error\n"
        mock_proc = self._make_mock_process(output)

        # Intercept the jsonl file open to inject a broken file handle.
        broken_jsonl = MagicMock()
        broken_jsonl.write.side_effect = OSError("disk full")

        original_open = open  # noqa: WPS125

        def _patched_open(path, *args, **kwargs):
            if str(path).endswith(".jsonl"):
                return broken_jsonl
            return original_open(path, *args, **kwargs)

        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch("builtins.open", side_effect=_patched_open):
                with patch(
                    "agentic_devtools.cli.copilot.session.threading.Thread",
                    side_effect=self._sync_thread_side_effect,
                ):
                    start_copilot_session(
                        prompt="Review the PR",
                        working_directory=str(temp_state),
                        interactive=False,
                    )

        # The .log file must still contain all output despite JSONL failure.
        log_dir = temp_state / "background-tasks" / "logs"
        log_files = list(log_dir.glob("*.log"))
        assert len(log_files) == 1
        log_content = log_files[0].read_text(encoding="utf-8")
        assert "line before jsonl error" in log_content
        assert "line after jsonl error" in log_content

    def test_jsonl_summary_write_failure_does_not_raise(self, temp_state, mock_available):
        """When the JSONL summary write fails, the tee still completes without raising."""
        import json

        output = b"line one\n"
        mock_proc = self._make_mock_process(output)

        call_count = 0
        original_open = open  # noqa: WPS125

        class _FailOnNthWriteFile:
            """Wrapper that delegates to a real file handle but raises on the Nth write."""

            def __init__(self, inner_fh):
                self._inner_fh = inner_fh

            def write(self, data):
                nonlocal call_count
                call_count += 1
                if call_count >= 2:
                    raise OSError("disk full on summary")
                return self._inner_fh.write(data)

            def __getattr__(self, name):
                return getattr(self._inner_fh, name)

        def _patched_open(path, *args, **kwargs):
            fh = original_open(path, *args, **kwargs)
            if str(path).endswith(".jsonl"):
                return _FailOnNthWriteFile(fh)
            return fh

        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch("builtins.open", side_effect=_patched_open):
                with patch(
                    "agentic_devtools.cli.copilot.session.threading.Thread",
                    side_effect=self._sync_thread_side_effect,
                ):
                    start_copilot_session(
                        prompt="Review the PR",
                        working_directory=str(temp_state),
                        interactive=False,
                    )

        # The .log file must still contain all output.
        log_dir = temp_state / "background-tasks" / "logs"
        log_files = list(log_dir.glob("*.log"))
        assert len(log_files) == 1
        log_content = log_files[0].read_text(encoding="utf-8")
        assert "line one" in log_content

        # The .jsonl file should have the output entry but no summary.
        jsonl_files = list(log_dir.glob("*.jsonl"))
        assert len(jsonl_files) == 1
        jsonl_content = jsonl_files[0].read_text(encoding="utf-8").strip()
        entries = [json.loads(line) for line in jsonl_content.split("\n") if line]
        assert len(entries) == 1
        assert entries[0]["event_type"] == "output"

    def test_jsonl_content_strips_trailing_crlf(self, temp_state, mock_available):
        """CRLF line endings are fully stripped from the JSONL content field."""
        import json

        mock_proc = self._make_mock_process(b"windows line\r\n")
        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch(
                "agentic_devtools.cli.copilot.session.threading.Thread",
                side_effect=self._sync_thread_side_effect,
            ):
                start_copilot_session(
                    prompt="Review the PR",
                    working_directory=str(temp_state),
                    interactive=False,
                )
        log_dir = temp_state / "background-tasks" / "logs"
        jsonl_file = list(log_dir.glob("*.jsonl"))[0]
        lines = jsonl_file.read_text(encoding="utf-8").strip().split("\n")
        output_entry = json.loads(lines[0])
        assert output_entry["content"] == "windows line"

    def test_session_starts_when_jsonl_open_fails(self, temp_state, mock_available):
        """Session starts and .log works even if .jsonl file creation fails."""
        output = b"session output\n"
        mock_proc = self._make_mock_process(output)

        original_open = open  # noqa: WPS125

        def _patched_open(path, *args, **kwargs):
            if str(path).endswith(".jsonl"):
                raise OSError("permission denied")
            return original_open(path, *args, **kwargs)

        with patch("agentic_devtools.cli.copilot.session.subprocess.Popen", return_value=mock_proc):
            with patch("builtins.open", side_effect=_patched_open):
                with patch(
                    "agentic_devtools.cli.copilot.session.threading.Thread",
                    side_effect=self._sync_thread_side_effect,
                ):
                    result = start_copilot_session(
                        prompt="Review the PR",
                        working_directory=str(temp_state),
                        interactive=False,
                    )

        assert result is not None
        # The .log file must still contain all output.
        log_dir = temp_state / "background-tasks" / "logs"
        log_files = list(log_dir.glob("*.log"))
        assert len(log_files) == 1
        log_content = log_files[0].read_text(encoding="utf-8")
        assert "session output" in log_content


class TestInlinePrompt:
    """Tests for the _inline_prompt helper and its integration in start_copilot_session."""

    def test_replaces_newlines_with_br(self):
        """Newlines are replaced with '   <br>   ' in the inlined prompt."""
        from agentic_devtools.cli.copilot.session import _inline_prompt

        result = _inline_prompt("Line 1\nLine 2\nLine 3", "/tmp/prompt.md")
        assert "   <br>   " in result
        assert "Line 1   <br>   Line 2   <br>   Line 3" in result

    def test_includes_backup_file_reference(self):
        """The inlined prompt ends with a backup file reference."""
        from agentic_devtools.cli.copilot.session import _inline_prompt

        result = _inline_prompt("Hello", "/tmp/prompt.md")
        assert "The full prompt is also saved at: /tmp/prompt.md" in result

    def test_truncation_emits_warning(self):
        """When the prompt exceeds _SAFE_ARGV_LENGTH with no focus areas, a file-reference fallback is used."""
        from agentic_devtools.cli.copilot.session import _SAFE_ARGV_LENGTH, _inline_prompt

        large_prompt = "x" * (_SAFE_ARGV_LENGTH + 1000)
        with pytest.warns(UserWarning, match="(?i)too large for inline"):
            result = _inline_prompt(large_prompt, "/tmp/prompt.md")
        assert len(result) <= _SAFE_ARGV_LENGTH
        assert "The full prompt is also saved at: /tmp/prompt.md" in result

    def test_truncation_of_focus_areas_section(self):
        """When prompt with focus areas exceeds the limit, focus areas are trimmed first."""
        from agentic_devtools.cli.copilot.session import _SAFE_ARGV_LENGTH, _inline_prompt

        # Build a prompt where the focus areas section makes it too long
        prefix = "# Header\n\n## Repo-Specific Review Focus Areas\n"
        focus_content = "x\n" * 5000  # Large focus areas
        suffix_section = "\n## Review Outcomes\nSome outcomes here."
        prompt = prefix + focus_content + suffix_section

        with pytest.warns(UserWarning, match="(?i)truncated"):
            result = _inline_prompt(prompt, "/tmp/prompt.md")

        assert len(result) <= _SAFE_ARGV_LENGTH
        # The Review Outcomes section should still be present
        assert "Review Outcomes" in result

    def test_no_truncation_for_short_prompts(self):
        """Short prompts are not truncated."""
        from agentic_devtools.cli.copilot.session import _inline_prompt

        result = _inline_prompt("Short prompt", "/tmp/prompt.md")
        assert "Short prompt" in result

    def test_partial_truncation_of_focus_areas(self):
        """When focus areas are partially truncated to fit, partial content is kept."""
        from agentic_devtools.cli.copilot.session import _SAFE_ARGV_LENGTH, _inline_prompt

        # Build a prompt where focus areas need partial truncation (not full removal).
        # Key: use focus content with very few newlines so <br> expansion is minimal.
        base_before = "# Header\n\n## Repo-Specific Review Focus Areas\n"
        base_after = "\n## Review Outcomes\nOutcome text."
        suffix = "   <br>   The full prompt is also saved at: /tmp/prompt.md"
        stripped = base_before + "...\n" + base_after
        stripped_inline_len = len(stripped.replace("\n", "   <br>   ") + suffix)
        available = _SAFE_ARGV_LENGTH - stripped_inline_len

        # Focus content: one long line of available-50 chars, then a newline,
        # then more text.  This ensures last_newline trim produces a result
        # that fits within the argv limit after <br> expansion.
        focus_content = ("F" * (available - 50)) + "\n" + ("G" * 100) + "\n"
        prompt = base_before + focus_content + base_after

        with pytest.warns(UserWarning, match="(?i)trimmed"):
            result = _inline_prompt(prompt, "/tmp/prompt.md")

        assert len(result) <= _SAFE_ARGV_LENGTH
        # The result should contain partial focus content (Fs, not Gs after the trim)
        assert "FFF" in result
        assert "Review Outcomes" in result

    def test_focus_areas_fully_removed_when_partial_insufficient(self):
        """When partial truncation doesn't help, focus areas are fully removed."""
        from agentic_devtools.cli.copilot.session import _SAFE_ARGV_LENGTH, _inline_prompt

        # Create a prompt where the base (without focus areas) is very close
        # to the limit, so even partial focus areas don't fit.
        base_before = "# Header\n\n## Repo-Specific Review Focus Areas\n"
        base_after = "\n## Review Outcomes\n" + ("y" * (_SAFE_ARGV_LENGTH - 500))
        focus_content = "focus\n" * 100
        prompt = base_before + focus_content + base_after

        with pytest.warns(UserWarning, match="(?i)fully removed"):
            result = _inline_prompt(prompt, "/tmp/prompt.md")

        assert len(result) <= _SAFE_ARGV_LENGTH


class TestBuildCopilotArgsLargePrompt:
    """Tests for _build_copilot_args with prompts exceeding the argv limit."""

    def test_returns_none_for_large_prompt(self):
        """_build_copilot_args returns None when prompt exceeds _MAX_GH_COPILOT_ARGV_LENGTH."""
        from agentic_devtools.cli.copilot.session import _MAX_GH_COPILOT_ARGV_LENGTH, _build_copilot_args

        large = "x" * (_MAX_GH_COPILOT_ARGV_LENGTH + 1)
        assert _build_copilot_args(large, interactive=True) is None


class TestStartCopilotSessionArgsNoneFallback:
    """Test the fallback path when _build_copilot_args returns None."""

    def test_fallback_when_build_args_returns_none(self, temp_state, mock_available, capsys):
        """Falls back to printing the prompt when _build_copilot_args returns None."""
        with patch.object(session_module, "_build_copilot_args", return_value=None):
            with pytest.warns(UserWarning, match="too large"):
                result = start_copilot_session(
                    prompt="Some prompt",
                    working_directory=str(temp_state),
                )
        assert result.process is None
        assert result.pid is None
        captured = capsys.readouterr()
        assert "Some prompt" in captured.out


class TestStartCopilotSessionModel:
    """Tests for the model parameter in start_copilot_session."""

    def test_model_forwarded_to_build_args(self, temp_state, mock_available, mock_popen_interactive):
        """Model parameter is forwarded to _build_copilot_args."""
        with patch.object(
            session_module,
            "_build_copilot_args",
            return_value=["copilot", "--model", "gpt-4", "-i", "hello"],
        ) as mock_build:
            start_copilot_session(
                prompt="hello",
                working_directory=str(temp_state),
                interactive=True,
                model="gpt-4",
            )

        # Check _build_copilot_args was called with model="gpt-4"
        assert mock_build.call_count == 1
        _, kwargs = mock_build.call_args
        assert kwargs.get("model") == "gpt-4"

    def test_model_persisted_in_state(self, temp_state, mock_available, mock_popen_interactive):
        """copilot.model_id is persisted in state when model is provided."""
        with patch.object(
            session_module,
            "_build_copilot_args",
            return_value=["copilot", "--model", "gpt-4", "-i", "hello"],
        ):
            start_copilot_session(
                prompt="hello",
                working_directory=str(temp_state),
                interactive=True,
                model="gpt-4",
            )

        from agentic_devtools.state import get_value

        assert get_value("copilot.model_id") == "gpt-4"

    def test_model_none_not_persisted_in_state(self, temp_state, mock_available, mock_popen_interactive):
        """copilot.model_id is NOT persisted when model is None."""
        with patch.object(
            session_module,
            "_build_copilot_args",
            return_value=["copilot", "-i", "hello"],
        ):
            start_copilot_session(
                prompt="hello",
                working_directory=str(temp_state),
                interactive=True,
                model=None,
            )

        from agentic_devtools.state import get_value

        assert get_value("copilot.model_id") is None

    def test_model_printed_to_stdout(self, temp_state, mock_available, mock_popen_interactive, capsys):
        """Model name is printed to stdout when provided."""
        with patch.object(
            session_module,
            "_build_copilot_args",
            return_value=["copilot", "--model", "gemini-pro-3.1", "-i", "hello"],
        ):
            start_copilot_session(
                prompt="hello",
                working_directory=str(temp_state),
                interactive=True,
                model="gemini-pro-3.1",
            )

        captured = capsys.readouterr()
        assert "Copilot model: gemini-pro-3.1" in captured.out

    def test_model_none_not_printed(self, temp_state, mock_available, mock_popen_interactive, capsys):
        """No model line printed when model is None."""
        with patch.object(
            session_module,
            "_build_copilot_args",
            return_value=["copilot", "-i", "hello"],
        ):
            start_copilot_session(
                prompt="hello",
                working_directory=str(temp_state),
                interactive=True,
                model=None,
            )

        captured = capsys.readouterr()
        assert "Copilot model:" not in captured.out

    def test_whitespace_only_model_normalized_to_none(self, temp_state, mock_available, mock_popen_interactive, capsys):
        """A whitespace-only model is normalized to None — not printed, not persisted."""
        with patch.object(
            session_module,
            "_build_copilot_args",
            return_value=["copilot", "-i", "hello"],
        ):
            start_copilot_session(
                prompt="hello",
                working_directory=str(temp_state),
                interactive=True,
                model="   ",
            )

        captured = capsys.readouterr()
        assert "Copilot model:" not in captured.out
        assert state.get_value("copilot.model_id") is None

    def test_empty_string_model_normalized_to_none(self, temp_state, mock_available, mock_popen_interactive, capsys):
        """An empty string model is normalized to None — not printed, not persisted."""
        with patch.object(
            session_module,
            "_build_copilot_args",
            return_value=["copilot", "-i", "hello"],
        ):
            start_copilot_session(
                prompt="hello",
                working_directory=str(temp_state),
                interactive=True,
                model="",
            )

        captured = capsys.readouterr()
        assert "Copilot model:" not in captured.out
        assert state.get_value("copilot.model_id") is None
