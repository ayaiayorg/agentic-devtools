"""Tests for CopilotSessionResult dataclass."""

from agentic_devtools.cli.copilot.session import CopilotSessionResult


class TestCopilotSessionResult:
    """Tests for CopilotSessionResult dataclass."""

    def test_required_fields(self):
        """CopilotSessionResult stores required fields correctly."""
        result = CopilotSessionResult(
            session_id="abc123",
            mode="interactive",
            prompt_file="/tmp/copilot-session-abc123-prompt.md",
            start_time="2026-02-25T12:00:00+00:00",
        )
        assert result.session_id == "abc123"
        assert result.mode == "interactive"
        assert result.prompt_file == "/tmp/copilot-session-abc123-prompt.md"
        assert result.start_time == "2026-02-25T12:00:00+00:00"

    def test_pid_defaults_to_none(self):
        """pid defaults to None when not provided."""
        result = CopilotSessionResult(
            session_id="abc123",
            mode="interactive",
            prompt_file="/tmp/prompt.md",
            start_time="2026-02-25T12:00:00+00:00",
        )
        assert result.pid is None

    def test_process_defaults_to_none(self):
        """process defaults to None when not provided."""
        result = CopilotSessionResult(
            session_id="abc123",
            mode="interactive",
            prompt_file="/tmp/prompt.md",
            start_time="2026-02-25T12:00:00+00:00",
        )
        assert result.process is None

    def test_pid_and_process_can_be_set(self):
        """pid and process can be set explicitly."""
        result = CopilotSessionResult(
            session_id="xyz",
            mode="non-interactive",
            prompt_file="/tmp/prompt.md",
            start_time="2026-02-25T12:00:00+00:00",
            pid=12345,
            process=None,
        )
        assert result.pid == 12345
        assert result.process is None

    def test_mode_values(self):
        """Mode accepts both interactive and non-interactive strings."""
        for mode in ("interactive", "non-interactive"):
            result = CopilotSessionResult(
                session_id="s",
                mode=mode,
                prompt_file="/tmp/p.md",
                start_time="2026-01-01T00:00:00+00:00",
            )
            assert result.mode == mode
