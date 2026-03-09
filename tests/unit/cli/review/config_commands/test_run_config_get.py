"""Tests for run_config_get."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.azure_devops.review_config import (
    ReviewConfig,
    ReviewConfigError,
    ReviewerConfig,
)
from agentic_devtools.cli.review.config_commands import run_config_get


class TestRunConfigGet:
    """Tests for run_config_get."""

    @patch("agentic_devtools.cli.review.config_commands.load_review_config")
    def test_prints_yaml_output(self, mock_load, capsys):
        """Prints config as YAML to stdout."""
        mock_load.return_value = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
        )
        run_config_get()
        captured = capsys.readouterr()
        assert "claude-opus-4-6" in captured.out
        assert "reviewers" in captured.out

    @patch("agentic_devtools.cli.review.config_commands.load_review_config")
    def test_error_exits_with_message(self, mock_load):
        """Exits with error message on config error."""
        mock_load.side_effect = ReviewConfigError("bad config")
        with pytest.raises(SystemExit):
            run_config_get()

    @patch("agentic_devtools.cli.review.config_commands._resolve_repo_root")
    def test_resolve_repo_root_error_exits_cleanly(self, mock_resolve):
        """Exits cleanly when _resolve_repo_root raises ReviewConfigError."""
        mock_resolve.side_effect = ReviewConfigError("bad path")
        with pytest.raises(SystemExit):
            run_config_get(config_path="/nonexistent/path")

    @patch("agentic_devtools.cli.review.config_commands.load_review_config")
    def test_config_path_override(self, mock_load, capsys, tmp_path):
        """Passes config_path to load_review_config."""
        mock_load.return_value = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
        )
        config_file = tmp_path / ".agdt" / "review-config.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.touch()
        run_config_get(config_path=str(config_file))
        captured = capsys.readouterr()
        assert "claude-opus-4-6" in captured.out
