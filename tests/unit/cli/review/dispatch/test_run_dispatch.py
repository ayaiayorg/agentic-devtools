"""Tests for agdt-review dispatch command."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli.azure_devops.review_config import (
    ConsolidationConfig,
    ReviewConfig,
    ReviewerConfig,
    TriggerConfig,
)
from agentic_devtools.cli.review.dispatch import run_dispatch


@pytest.fixture(autouse=True)
def _unset_emoji_env(monkeypatch):
    """Ensure AGDT_USE_EMOJI is unset for deterministic test output."""
    monkeypatch.delenv("AGDT_USE_EMOJI", raising=False)


class TestRunDispatch:
    """Tests for run_dispatch."""

    @patch("agentic_devtools.cli.review.dispatch.load_review_config")
    @patch("agentic_devtools.cli.review.dispatch._invoke_reviewer", return_value=True)
    @patch("agentic_devtools.cli.review.dispatch._check_files_need_consolidation", return_value=[])
    def test_dry_run_prints_plan(self, mock_check, mock_invoke, mock_load, capsys, tmp_path):
        """Dry run prints the dispatch plan without invoking reviewers."""
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            triggers=[TriggerConfig(type="pr-label", label="ai-review")],
            skip_consolidation=True,
        )
        mock_load.return_value = config

        run_dispatch(pr_id=123, label="ai-review", dry_run=True)

        mock_invoke.assert_not_called()
        captured = capsys.readouterr()
        assert "DISPATCH PLAN" in captured.out
        assert "claude-opus-4-6" in captured.out

    @patch("agentic_devtools.cli.review.dispatch.load_review_config")
    @patch("agentic_devtools.cli.review.dispatch._invoke_reviewer", return_value=True)
    @patch("agentic_devtools.cli.review.dispatch._check_files_need_consolidation", return_value=[])
    def test_single_reviewer_dispatch(self, mock_check, mock_invoke, mock_load, capsys):
        """Single reviewer dispatch calls the reviewer once."""
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            triggers=[TriggerConfig(type="pr-label", label="ai-review")],
        )
        mock_load.return_value = config

        run_dispatch(pr_id=123, label="ai-review")

        mock_invoke.assert_called_once_with(123, "claude-opus-4-6", "primary", use_emoji=False)
        captured = capsys.readouterr()
        assert "Reviewers completed: 1/1" in captured.out

    @patch("agentic_devtools.cli.review.dispatch.load_review_config")
    @patch("agentic_devtools.cli.review.dispatch._invoke_reviewer", return_value=True)
    @patch("agentic_devtools.cli.review.dispatch._check_files_need_consolidation", return_value=[])
    def test_multi_reviewer_dispatch(self, mock_check, mock_invoke, mock_load, capsys):
        """Multi-reviewer dispatch calls each reviewer in order."""
        config = ReviewConfig(
            reviewers=[
                ReviewerConfig(model_id="claude-opus-4-6", role="primary"),
                ReviewerConfig(model_id="gemini-pro-3-1", role="secondary"),
            ],
            triggers=[TriggerConfig(type="pr-label", label="ai-review")],
        )
        mock_load.return_value = config

        run_dispatch(pr_id=456, label="ai-review")

        assert mock_invoke.call_count == 2
        captured = capsys.readouterr()
        assert "Reviewers completed: 2/2" in captured.out

    @patch("agentic_devtools.cli.review.dispatch.load_review_config")
    @patch("agentic_devtools.cli.review.dispatch._invoke_reviewer", return_value=False)
    def test_all_reviewers_unavailable_exits(self, mock_invoke, mock_load):
        """Exits with error when all reviewers are unavailable."""
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            triggers=[TriggerConfig(type="pr-label", label="ai-review")],
        )
        mock_load.return_value = config

        with pytest.raises(SystemExit):
            run_dispatch(pr_id=123, label="ai-review")

    @patch("agentic_devtools.cli.review.dispatch.load_review_config")
    def test_config_error_exits(self, mock_load):
        """Exits on config error."""
        from agentic_devtools.cli.azure_devops.review_config import ReviewConfigError

        mock_load.side_effect = ReviewConfigError("bad config")

        with pytest.raises(SystemExit):
            run_dispatch(pr_id=123, label="ai-review")

    @patch("agentic_devtools.cli.review.dispatch.load_review_config")
    @patch("agentic_devtools.cli.review.dispatch.resolve_trigger_overrides")
    def test_trigger_override_error_exits(self, mock_resolve, mock_load):
        """Exits on ReviewConfigError from resolve_trigger_overrides."""
        from agentic_devtools.cli.azure_devops.review_config import ReviewConfigError

        mock_load.return_value = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            triggers=[TriggerConfig(type="pr-label", label="ai-review")],
        )
        mock_resolve.side_effect = ReviewConfigError("min_reviewers > max_reviewers")

        with pytest.raises(SystemExit):
            run_dispatch(pr_id=123, label="ai-review")

    @patch("agentic_devtools.cli.review.dispatch.load_review_config")
    @patch("agentic_devtools.cli.review.dispatch._invoke_reviewer", return_value=True)
    @patch("agentic_devtools.cli.review.dispatch._check_files_need_consolidation", return_value=[])
    def test_config_path_override(self, mock_check, mock_invoke, mock_load, capsys, tmp_path):
        """Uses config_path override when provided as YAML file path."""
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            triggers=[TriggerConfig(type="pr-label", label="ai-review")],
        )
        mock_load.return_value = config

        config_file = tmp_path / ".agdt" / "review-config.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.touch()
        run_dispatch(
            pr_id=123,
            label="ai-review",
            config_path=str(config_file),
        )

        mock_invoke.assert_called_once()

    @patch("agentic_devtools.cli.review.dispatch.load_review_config")
    @patch("agentic_devtools.cli.review.dispatch._invoke_reviewer", return_value=True)
    @patch("agentic_devtools.cli.review.dispatch._check_files_need_consolidation", return_value=[])
    def test_config_path_as_directory(self, mock_check, mock_invoke, mock_load, capsys, tmp_path):
        """Uses config_path as repo root directory when not a YAML file."""
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            triggers=[TriggerConfig(type="pr-label", label="ai-review")],
        )
        mock_load.return_value = config

        run_dispatch(
            pr_id=123,
            label="ai-review",
            config_path=str(tmp_path),
        )

        mock_load.assert_called_once_with(tmp_path.resolve())

    def test_non_canonical_yaml_config_path_exits(self):
        """Exits with error for non-canonical YAML config path."""
        with pytest.raises(SystemExit):
            run_dispatch(pr_id=123, label="ai-review", config_path="/repo/custom.yaml")

    def test_non_canonical_yaml_error_mentions_both_extensions(self, capsys):
        """Error message for non-canonical config path mentions both .yaml and .yml."""
        with pytest.raises(SystemExit):
            run_dispatch(pr_id=123, label="ai-review", config_path="/repo/custom.yaml")
        captured = capsys.readouterr()
        assert ".yaml" in captured.err
        assert ".yml" in captured.err

    def test_missing_yaml_config_file_exits(self, tmp_path, capsys):
        """Exits with error when canonical YAML config file does not exist."""
        missing = tmp_path / ".agdt" / "review-config.yaml"
        with pytest.raises(SystemExit):
            run_dispatch(pr_id=123, label="ai-review", config_path=str(missing))
        captured = capsys.readouterr()
        assert "does not exist" in captured.err

    def test_nonexistent_directory_config_path_exits(self, tmp_path, capsys):
        """Exits with error when directory config_path does not exist."""
        missing = tmp_path / "no-such-dir"
        with pytest.raises(SystemExit):
            run_dispatch(pr_id=123, label="ai-review", config_path=str(missing))
        captured = capsys.readouterr()
        assert "does not exist" in captured.err

    def test_file_as_directory_config_path_exits(self, tmp_path, capsys):
        """Exits with error when config_path is a file, not a directory."""
        some_file = tmp_path / "not-a-dir.txt"
        some_file.touch()
        with pytest.raises(SystemExit):
            run_dispatch(pr_id=123, label="ai-review", config_path=str(some_file))
        captured = capsys.readouterr()
        assert "is not a directory" in captured.err

    @patch("agentic_devtools.cli.review.dispatch.load_review_config")
    @patch("agentic_devtools.cli.review.dispatch._invoke_reviewer")
    @patch(
        "agentic_devtools.cli.review.dispatch._check_files_need_consolidation",
        return_value=["/file.ts"],
    )
    @patch("agentic_devtools.cli.review.dispatch._invoke_consolidation", return_value=True)
    def test_consolidation_triggered_for_files(self, mock_consolidate, mock_check, mock_invoke, mock_load, capsys):
        """Consolidation is triggered when files need it."""
        mock_invoke.return_value = True
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            consolidation=ConsolidationConfig(model_id="claude-opus-4-6"),
            triggers=[TriggerConfig(type="pr-label", label="ai-review")],
        )
        mock_load.return_value = config

        run_dispatch(pr_id=123, label="ai-review")

        mock_consolidate.assert_called_once()
        captured = capsys.readouterr()
        assert "Files needing consolidation: 1" in captured.out

    @patch("agentic_devtools.cli.review.dispatch.load_review_config")
    @patch("agentic_devtools.cli.review.dispatch._invoke_reviewer", return_value=True)
    @patch(
        "agentic_devtools.cli.review.dispatch._check_files_need_consolidation",
        return_value=["/file.ts"],
    )
    def test_skip_consolidation_uses_mechanical(self, mock_check, mock_invoke, mock_load, capsys):
        """When skip_consolidation=True, uses mechanical consensus."""
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            triggers=[TriggerConfig(type="pr-label", label="ai-review")],
            skip_consolidation=True,
        )
        mock_load.return_value = config

        run_dispatch(pr_id=123, label="ai-review")

        captured = capsys.readouterr()
        assert "mechanical consensus" in captured.out.lower() or "Consolidation skipped" in captured.out

    @patch("agentic_devtools.cli.review.dispatch.load_review_config")
    @patch("agentic_devtools.cli.review.dispatch._invoke_reviewer")
    @patch(
        "agentic_devtools.cli.review.dispatch._check_files_need_consolidation",
        return_value=["/file.ts"],
    )
    @patch("agentic_devtools.cli.review.dispatch._invoke_consolidation", return_value=False)
    def test_consolidator_unavailable_falls_back(self, mock_consolidate, mock_check, mock_invoke, mock_load, capsys):
        """Falls back to mechanical consensus when consolidator unavailable."""
        mock_invoke.return_value = True
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            consolidation=ConsolidationConfig(model_id="claude-opus-4-6"),
            triggers=[TriggerConfig(type="pr-label", label="ai-review")],
        )
        mock_load.return_value = config

        run_dispatch(pr_id=123, label="ai-review")

        captured = capsys.readouterr()
        assert "unavailable" in captured.err or "Consolidation skipped" in captured.err

    @patch("agentic_devtools.cli.review.dispatch.load_review_config")
    @patch("agentic_devtools.cli.review.dispatch._invoke_reviewer")
    @patch(
        "agentic_devtools.cli.review.dispatch._check_files_need_consolidation",
        return_value=[],
    )
    def test_partial_reviewer_failure(self, mock_check, mock_invoke, mock_load, capsys):
        """Some reviewers failing still completes with others."""
        mock_invoke.side_effect = [True, False]
        config = ReviewConfig(
            reviewers=[
                ReviewerConfig(model_id="claude-opus-4-6", role="primary"),
                ReviewerConfig(model_id="gemini-pro-3-1", role="secondary"),
            ],
            triggers=[TriggerConfig(type="pr-label", label="ai-review")],
        )
        mock_load.return_value = config

        run_dispatch(pr_id=123, label="ai-review")

        captured = capsys.readouterr()
        assert "Reviewers completed: 1/2" in captured.out

    @patch("agentic_devtools.cli.review.dispatch.load_review_config")
    @patch("agentic_devtools.cli.review.dispatch._invoke_reviewer", return_value=True)
    @patch(
        "agentic_devtools.cli.review.dispatch._check_files_need_consolidation",
        return_value=["/file.ts"],
    )
    def test_no_consolidation_configured_warns(self, mock_check, mock_invoke, mock_load, capsys):
        """Warns when files need consolidation but consolidation is not configured."""
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            triggers=[TriggerConfig(type="pr-label", label="ai-review")],
        )
        mock_load.return_value = config

        run_dispatch(pr_id=123, label="ai-review")

        captured = capsys.readouterr()
        assert "not configured" in captured.err
        assert "mechanical consensus" in captured.err.lower()

    @patch("agentic_devtools.cli.review.dispatch.load_review_config")
    @patch("agentic_devtools.cli.review.dispatch._invoke_reviewer", return_value=True)
    @patch("agentic_devtools.cli.review.dispatch._check_files_need_consolidation", return_value=[])
    def test_final_status_uses_mapped_status(self, mock_check, mock_invoke, mock_load, capsys):
        """Final status uses a format_status-mapped value (stub — in-progress)."""
        config = ReviewConfig(
            reviewers=[ReviewerConfig(model_id="claude-opus-4-6", role="primary")],
            triggers=[TriggerConfig(type="pr-label", label="ai-review")],
        )
        mock_load.return_value = config

        run_dispatch(pr_id=123, label="ai-review")

        captured = capsys.readouterr()
        assert "[IN PROGRESS]" in captured.out
        assert "Dispatch complete (stub)" in captured.out
