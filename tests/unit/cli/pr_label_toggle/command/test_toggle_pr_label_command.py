"""Tests for toggle_pr_label_command."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agentic_devtools.cli.pr_label_toggle.command import toggle_pr_label_command

_MOD = "agentic_devtools.cli.pr_label_toggle.command"


class TestTogglePrLabelCommand:
    """Tests for the toggle_pr_label_command CLI entry point."""

    @patch(f"{_MOD}.run_toggle_loop")
    @patch(f"{_MOD}.resolve_github_repo", return_value="org/repo")
    def test_runs_with_defaults(self, mock_resolve, mock_loop, monkeypatch):
        """Runs toggle loop with default config when no args given."""
        from agentic_devtools.cli.pr_label_toggle.toggle_loop import ToggleResult

        mock_loop.return_value = ToggleResult(cycles_completed=5, stop_reason="interrupted")
        monkeypatch.setattr("sys.argv", ["agdt-toggle-pr-label"])

        toggle_pr_label_command()

        mock_loop.assert_called_once()
        _, kwargs = mock_loop.call_args
        config = kwargs.get("config") or mock_loop.call_args[0][1]
        assert config.label == "ai-pr-loop-trigger"
        assert config.interval_seconds == 120
        assert config.max_hours == 12
        assert config.max_consecutive_no_pr == 5

    @patch(f"{_MOD}.run_toggle_loop")
    @patch(f"{_MOD}.resolve_github_repo", return_value="org/repo")
    def test_passes_custom_args(self, mock_resolve, mock_loop, monkeypatch):
        """Passes custom CLI args to config."""
        from agentic_devtools.cli.pr_label_toggle.toggle_loop import ToggleResult

        mock_loop.return_value = ToggleResult(cycles_completed=0, stop_reason="max_duration")
        monkeypatch.setattr(
            "sys.argv",
            ["agdt-toggle-pr-label", "--label", "custom-lbl", "--interval", "90", "--hours", "24", "--max-no-pr", "3"],
        )

        toggle_pr_label_command()

        config = mock_loop.call_args[0][1]
        assert config.label == "custom-lbl"
        assert config.interval_seconds == 90
        assert config.max_hours == 24
        assert config.max_consecutive_no_pr == 3

    def test_rejects_interval_below_min(self, monkeypatch, capsys):
        """Exits with error for interval below 60."""
        monkeypatch.setattr("sys.argv", ["agdt-toggle-pr-label", "--interval", "30"])
        with pytest.raises(SystemExit) as exc_info:
            toggle_pr_label_command()
        assert exc_info.value.code == 1
        assert "--interval must be between 60 and 600" in capsys.readouterr().err

    def test_rejects_interval_above_max(self, monkeypatch, capsys):
        """Exits with error for interval above 600."""
        monkeypatch.setattr("sys.argv", ["agdt-toggle-pr-label", "--interval", "700"])
        with pytest.raises(SystemExit) as exc_info:
            toggle_pr_label_command()
        assert exc_info.value.code == 1
        assert "--interval must be between 60 and 600" in capsys.readouterr().err

    def test_rejects_hours_below_min(self, monkeypatch, capsys):
        """Exits with error for hours below 1."""
        monkeypatch.setattr("sys.argv", ["agdt-toggle-pr-label", "--hours", "0"])
        with pytest.raises(SystemExit) as exc_info:
            toggle_pr_label_command()
        assert exc_info.value.code == 1
        assert "--hours must be between 1 and 1200" in capsys.readouterr().err

    def test_rejects_hours_above_max(self, monkeypatch, capsys):
        """Exits with error for hours above 1200."""
        monkeypatch.setattr("sys.argv", ["agdt-toggle-pr-label", "--hours", "1300"])
        with pytest.raises(SystemExit) as exc_info:
            toggle_pr_label_command()
        assert exc_info.value.code == 1
        assert "--hours must be between 1 and 1200" in capsys.readouterr().err

    def test_rejects_max_no_pr_below_min(self, monkeypatch, capsys):
        """Exits with error for max-no-pr below 1."""
        monkeypatch.setattr("sys.argv", ["agdt-toggle-pr-label", "--max-no-pr", "0"])
        with pytest.raises(SystemExit) as exc_info:
            toggle_pr_label_command()
        assert exc_info.value.code == 1
        assert "--max-no-pr must be between 1 and 10" in capsys.readouterr().err

    def test_rejects_max_no_pr_above_max(self, monkeypatch, capsys):
        """Exits with error for max-no-pr above 10."""
        monkeypatch.setattr("sys.argv", ["agdt-toggle-pr-label", "--max-no-pr", "15"])
        with pytest.raises(SystemExit) as exc_info:
            toggle_pr_label_command()
        assert exc_info.value.code == 1
        assert "--max-no-pr must be between 1 and 10" in capsys.readouterr().err

    @patch(f"{_MOD}.run_toggle_loop")
    @patch(f"{_MOD}.resolve_github_repo", return_value="custom/repo")
    def test_passes_repo_to_provider(self, mock_resolve, mock_loop, monkeypatch):
        """Passes --repo to resolve_github_repo."""
        from agentic_devtools.cli.pr_label_toggle.toggle_loop import ToggleResult

        mock_loop.return_value = ToggleResult(cycles_completed=0, stop_reason="max_duration")
        monkeypatch.setattr("sys.argv", ["agdt-toggle-pr-label", "--repo", "custom/repo"])

        toggle_pr_label_command()

        mock_resolve.assert_called_once_with("custom/repo")
