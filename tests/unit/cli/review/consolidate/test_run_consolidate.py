"""Tests for agdt-review consolidate command."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.azure_devops.review_config import (
    ConsolidationConfig,
    ReviewConfig,
    ReviewConfigError,
    ReviewerConfig,
)
from agentic_devtools.cli.review.consolidate import run_consolidate


class TestRunConsolidate:
    """Tests for run_consolidate."""

    @patch("agentic_devtools.cli.review.consolidate._load_amendment_replies", return_value={})
    @patch("agentic_devtools.cli.review.consolidate.load_review_config")
    def test_no_amendments_exits_early(self, mock_config, mock_load, capsys):
        """When no amendment replies, consolidation is not needed."""
        mock_config.return_value = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            consolidation=ConsolidationConfig(model_id="claude-opus-4-6"),
        )
        run_consolidate(pr_id=123)
        captured = capsys.readouterr()
        assert "not needed" in captured.out

    @patch("agentic_devtools.cli.review.consolidate._apply_resolution")
    @patch(
        "agentic_devtools.cli.review.consolidate._invoke_consolidator_model",
        return_value={"resolution": "mock"},
    )
    @patch(
        "agentic_devtools.cli.review.consolidate._build_consolidation_prompt",
        return_value="prompt",
    )
    @patch(
        "agentic_devtools.cli.review.consolidate._load_amendment_replies",
        return_value={"file.ts": {"amendments": []}},
    )
    def test_runs_consolidation_with_amendments(self, mock_load, mock_prompt, mock_invoke, mock_apply, capsys):
        """When amendments exist, runs full consolidation pipeline."""
        run_consolidate(pr_id=456, model_id="claude-opus-4-6")
        mock_invoke.assert_called_once()
        mock_apply.assert_called_once()
        captured = capsys.readouterr()
        assert "Consolidation complete (stub)" in captured.out
        assert "[IN PROGRESS]" in captured.out
        assert "claude-opus-4-6" in captured.out

    @patch("agentic_devtools.cli.review.consolidate._load_amendment_replies", return_value={})
    @patch("agentic_devtools.cli.review.consolidate.load_review_config")
    def test_no_model_id_resolves_from_config(self, mock_config, mock_load, capsys):
        """When no model_id is provided, resolves from config consolidation."""
        mock_config.return_value = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            consolidation=ConsolidationConfig(model_id="gemini-pro-3-1"),
        )
        run_consolidate(pr_id=789)
        captured = capsys.readouterr()
        assert "gemini-pro-3-1" in captured.out

    @patch("agentic_devtools.cli.review.consolidate._load_amendment_replies", return_value={})
    @patch("agentic_devtools.cli.review.consolidate.load_review_config")
    def test_no_model_id_no_consolidation_falls_back_to_primary(self, mock_config, mock_load, capsys):
        """When no model_id and no consolidation config, falls back to primary reviewer."""
        mock_config.return_value = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
        )
        run_consolidate(pr_id=789)
        captured = capsys.readouterr()
        assert "claude-opus-4-6" in captured.out

    @patch("agentic_devtools.cli.review.consolidate.load_review_config")
    def test_config_error_exits_cleanly(self, mock_config):
        """Exits with code 1 and message on ReviewConfigError."""
        mock_config.side_effect = ReviewConfigError("bad config")
        with pytest.raises(SystemExit):
            run_consolidate(pr_id=123)
