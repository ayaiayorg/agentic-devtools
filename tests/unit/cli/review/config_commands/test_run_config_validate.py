"""Tests for run_config_validate."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.azure_devops.review_config import (
    ReviewConfig,
    ReviewConfigError,
    ReviewerConfig,
)
from agentic_devtools.cli.review.config_commands import run_config_validate


class TestRunConfigValidate:
    """Tests for run_config_validate."""

    @patch("agentic_devtools.cli.review.config_commands.load_review_config")
    def test_valid_config_prints_success(self, mock_load, capsys):
        """Prints success message for valid config."""
        mock_load.return_value = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
        )
        run_config_validate()
        captured = capsys.readouterr()
        assert "Configuration valid." in captured.out

    @patch("agentic_devtools.cli.review.config_commands.load_review_config")
    def test_invalid_config_exits(self, mock_load):
        """Exits with code 1 on invalid config."""
        mock_load.side_effect = ReviewConfigError("bad config")
        with pytest.raises(SystemExit):
            run_config_validate()

    @patch("agentic_devtools.cli.review.config_commands._resolve_repo_root")
    def test_resolve_repo_root_error_exits_cleanly(self, mock_resolve):
        """Exits cleanly when _resolve_repo_root raises ReviewConfigError."""
        mock_resolve.side_effect = ReviewConfigError("bad path")
        with pytest.raises(SystemExit):
            run_config_validate(config_path="/nonexistent/path")
