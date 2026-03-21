"""Tests for agentic_devtools.tools.git.get_recent_changes."""

from unittest.mock import MagicMock, patch

from agentic_devtools.tools.git import get_recent_changes


class TestGetRecentChanges:
    """Tests for the get_recent_changes tool function."""

    @patch("agentic_devtools.cli.git.core.run_safe")
    def test_returns_parsed_commits(self, mock_run_safe):
        sep = "\x1f"
        mock_run_safe.return_value = MagicMock(
            returncode=0,
            stdout=(
                f"abc123{sep}feat: add feature{sep}John Doe{sep}2024-01-15 10:00:00 +0000\n"
                f"def456{sep}fix: bug fix{sep}Jane Doe{sep}2024-01-14 09:00:00 +0000\n"
            ),
            stderr="",
        )

        result = get_recent_changes(num_commits=5)

        assert len(result["commits"]) == 2
        assert result["commits"][0]["sha"] == "abc123"
        assert result["commits"][0]["message"] == "feat: add feature"
        assert result["commits"][0]["author"] == "John Doe"
        assert result["commits"][0]["date"] == "2024-01-15 10:00:00 +0000"
        assert result["commits"][1]["sha"] == "def456"

    @patch("agentic_devtools.cli.git.core.run_safe")
    def test_returns_empty_on_no_commits(self, mock_run_safe):
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = get_recent_changes()

        assert result["commits"] == []

    @patch("agentic_devtools.cli.git.core.run_safe")
    def test_returns_empty_on_nonzero_exit(self, mock_run_safe):
        mock_run_safe.return_value = MagicMock(returncode=128, stdout="", stderr="")

        result = get_recent_changes()

        assert result["commits"] == []

    @patch("agentic_devtools.cli.git.core.run_safe")
    def test_passes_correct_max_count(self, mock_run_safe):
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="", stderr="")

        get_recent_changes(num_commits=3)

        cmd = mock_run_safe.call_args[0][0]
        assert "git" in cmd
        assert "--max-count=3" in cmd

    @patch("agentic_devtools.cli.git.core.run_safe")
    def test_handles_malformed_line(self, mock_run_safe):
        sep = "\x1f"
        stdout = (
            f"abc123{sep}feat: add feature{sep}John Doe{sep}2024-01-15\n"
            f"badline\n"
            f"def456{sep}fix{sep}Jane{sep}2024-01-14\n"
        )
        mock_run_safe.return_value = MagicMock(
            returncode=0,
            stdout=stdout,
            stderr="",
        )

        result = get_recent_changes()

        assert len(result["commits"]) == 2  # Skips the malformed line

    @patch("agentic_devtools.cli.git.core.run_safe")
    def test_handles_pipe_in_message(self, mock_run_safe):
        """Commit messages containing pipe characters are parsed correctly."""
        sep = "\x1f"
        mock_run_safe.return_value = MagicMock(
            returncode=0,
            stdout=f"abc123{sep}feat: add a|b feature{sep}John{sep}2024-01-15\n",
            stderr="",
        )

        result = get_recent_changes()

        assert len(result["commits"]) == 1
        assert result["commits"][0]["message"] == "feat: add a|b feature"
        assert result["commits"][0]["author"] == "John"
        assert result["commits"][0]["date"] == "2024-01-15"

    @patch("agentic_devtools.cli.git.core.run_safe")
    def test_uses_unit_separator_format(self, mock_run_safe):
        """Verify the git log format uses %x1f (unit separator) not pipe."""
        mock_run_safe.return_value = MagicMock(returncode=0, stdout="", stderr="")

        get_recent_changes()

        cmd = mock_run_safe.call_args[0][0]
        fmt_arg = [a for a in cmd if a.startswith("--format=")][0]
        assert "%x1f" in fmt_arg
        assert "|" not in fmt_arg.replace("--format=", "")
