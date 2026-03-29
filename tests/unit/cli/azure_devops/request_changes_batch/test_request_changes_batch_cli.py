"""Tests for agentic_devtools.cli.azure_devops.request_changes_batch.request_changes_batch_cli."""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_cli(*cli_args: str):
    """Invoke request_changes_batch_cli with the given CLI arguments."""
    from agentic_devtools.cli.azure_devops.request_changes_batch import request_changes_batch_cli

    with patch.object(sys, "argv", ["agdt-request-changes-batch", *cli_args]):
        request_changes_batch_cli()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRequestChangesBatchCli:
    """Tests for request_changes_batch_cli."""

    # -- success path -------------------------------------------------------

    def test_successful_batch(self, temp_state_dir, clear_state_before, capsys):
        """Verify resolve → validate → enqueue is called correctly."""
        reviews_json = json.dumps(
            {
                "default_summary": "Needs fixes",
                "items": [
                    {
                        "file_path": "/src/a.ts",
                        "suggestions": [{"line": 10, "severity": "high", "content": "Fix"}],
                    },
                ],
            }
        )
        mock_manager = MagicMock()
        with (
            patch(
                "agentic_devtools.submission_manager_instance.get_submission_manager",
                return_value=mock_manager,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.is_dry_run",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.resolve_batch_reviews",
                return_value=[
                    {
                        "file_path": "/src/a.ts",
                        "outcome": "request-changes",
                        "summary": "Needs fixes",
                        "suggestions": [{"line": 10, "severity": "high", "content": "Fix"}],
                    },
                ],
            ) as mock_resolve,
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.validate_batch_reviews",
                return_value=[],
            ) as mock_validate,
        ):
            _run_cli("--reviews", reviews_json, "-p", "12345")

        # resolve called with correct payload (default_outcome injected)
        mock_resolve.assert_called_once()
        payload = mock_resolve.call_args[0][0]
        assert payload["default_outcome"] == "request-changes"

        mock_validate.assert_called_once()
        assert mock_manager.enqueue.call_count == 1
        assert mock_manager.enqueue.call_args.kwargs["pr_id"] == 12345

        captured = capsys.readouterr()
        assert "1 file(s) enqueued with request-changes" in captured.out

    def test_default_outcome_injection(self, temp_state_dir, clear_state_before):
        """default_outcome is set to 'request-changes' via setdefault."""
        reviews_json = json.dumps(
            {
                "items": [{"file_path": "/a.ts"}],
            }
        )
        mock_manager = MagicMock()
        with (
            patch(
                "agentic_devtools.submission_manager_instance.get_submission_manager",
                return_value=mock_manager,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.is_dry_run",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.resolve_batch_reviews",
                return_value=[{"file_path": "/a.ts", "outcome": "request-changes", "summary": "s"}],
            ) as mock_resolve,
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.validate_batch_reviews",
                return_value=[],
            ),
        ):
            _run_cli("--reviews", reviews_json, "-p", "1")

        payload = mock_resolve.call_args[0][0]
        assert payload["default_outcome"] == "request-changes"

    def test_user_provided_default_outcome_not_overwritten(self, temp_state_dir, clear_state_before):
        """If user sets default_outcome in JSON, it is respected."""
        reviews_json = json.dumps(
            {
                "default_outcome": "approve",
                "items": [{"file_path": "/a.ts"}],
            }
        )
        mock_manager = MagicMock()
        with (
            patch(
                "agentic_devtools.submission_manager_instance.get_submission_manager",
                return_value=mock_manager,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.is_dry_run",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.resolve_batch_reviews",
                return_value=[{"file_path": "/a.ts", "outcome": "approve", "summary": "ok"}],
            ) as mock_resolve,
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.validate_batch_reviews",
                return_value=[],
            ),
        ):
            _run_cli("--reviews", reviews_json, "-p", "1")

        payload = mock_resolve.call_args[0][0]
        assert payload["default_outcome"] == "approve"

    def test_pr_id_via_cli(self, temp_state_dir, clear_state_before):
        """--pull-request-id is used when provided."""
        reviews_json = json.dumps({"items": [{"file_path": "/a.ts"}]})
        mock_manager = MagicMock()
        with (
            patch(
                "agentic_devtools.submission_manager_instance.get_submission_manager",
                return_value=mock_manager,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.is_dry_run",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.resolve_batch_reviews",
                return_value=[{"file_path": "/a.ts", "outcome": "request-changes", "summary": "s"}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.validate_batch_reviews",
                return_value=[],
            ),
        ):
            _run_cli("--reviews", reviews_json, "-p", "777")

        assert mock_manager.enqueue.call_args.kwargs["pr_id"] == 777

    def test_pr_id_falls_back_to_state(self, temp_state_dir, clear_state_before):
        """Falls back to get_pull_request_id when --pull-request-id not given."""
        reviews_json = json.dumps({"items": [{"file_path": "/a.ts"}]})
        mock_manager = MagicMock()
        with (
            patch(
                "agentic_devtools.submission_manager_instance.get_submission_manager",
                return_value=mock_manager,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.is_dry_run",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.get_pull_request_id",
                return_value=333,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.resolve_batch_reviews",
                return_value=[{"file_path": "/a.ts", "outcome": "request-changes", "summary": "s"}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.validate_batch_reviews",
                return_value=[],
            ),
        ):
            _run_cli("--reviews", reviews_json)

        assert mock_manager.enqueue.call_args.kwargs["pr_id"] == 333

    # -- dry-run ------------------------------------------------------------

    def test_dry_run_prints_plan_without_enqueuing(self, temp_state_dir, clear_state_before, capsys):
        """In dry-run mode, items are printed but not enqueued."""
        reviews_json = json.dumps({"items": [{"file_path": "/a.ts"}]})
        with (
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.is_dry_run",
                return_value=True,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.resolve_batch_reviews",
                return_value=[{"file_path": "/a.ts", "outcome": "request-changes", "summary": "s"}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.validate_batch_reviews",
                return_value=[],
            ),
        ):
            _run_cli("--reviews", reviews_json, "-p", "1")

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "/a.ts" in captured.out

    # -- error paths --------------------------------------------------------

    def test_invalid_json_reviews(self, temp_state_dir, clear_state_before, capsys):
        """--reviews with invalid JSON exits 1."""
        with pytest.raises(SystemExit) as exc:
            _run_cli("--reviews", "not json", "-p", "1")
        assert exc.value.code == 1
        assert "not valid JSON" in capsys.readouterr().err

    def test_reviews_not_dict(self, temp_state_dir, clear_state_before, capsys):
        """--reviews that is not a JSON object exits 1."""
        with pytest.raises(SystemExit) as exc:
            _run_cli("--reviews", "[]", "-p", "1")
        assert exc.value.code == 1
        assert "must be a JSON object" in capsys.readouterr().err

    def test_validation_failure_exits_1(self, temp_state_dir, clear_state_before, capsys):
        """Errors from validate_batch_reviews are printed to stderr and exit 1."""
        reviews_json = json.dumps({"items": [{"file_path": "/x.ts"}]})
        with (
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.resolve_batch_reviews",
                return_value=[{"file_path": "/x.ts", "outcome": "request-changes", "summary": None}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.validate_batch_reviews",
                return_value=["Item 0 (/x.ts): summary is required."],
            ),
        ):
            with pytest.raises(SystemExit) as exc:
                _run_cli("--reviews", reviews_json, "-p", "1")
        assert exc.value.code == 1
        assert "summary is required" in capsys.readouterr().err

    def test_missing_pr_id_exits(self, temp_state_dir, clear_state_before):
        """Missing --pull-request-id with no state raises."""
        reviews_json = json.dumps({"items": [{"file_path": "/x.ts"}]})
        with patch(
            "agentic_devtools.cli.azure_devops.request_changes_batch.get_pull_request_id",
            side_effect=KeyError("pull_request_id"),
        ):
            with pytest.raises(KeyError, match="pull_request_id"):
                _run_cli("--reviews", reviews_json)

    def test_success_output(self, temp_state_dir, clear_state_before, capsys):
        """Success output contains count and file paths."""
        reviews_json = json.dumps(
            {
                "items": [
                    {"file_path": "/a.ts"},
                    {"file_path": "/b.ts"},
                ],
            }
        )
        mock_manager = MagicMock()
        with (
            patch(
                "agentic_devtools.submission_manager_instance.get_submission_manager",
                return_value=mock_manager,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.is_dry_run",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.resolve_batch_reviews",
                return_value=[
                    {"file_path": "/a.ts", "outcome": "request-changes", "summary": "s"},
                    {"file_path": "/b.ts", "outcome": "request-changes", "summary": "s"},
                ],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.request_changes_batch.validate_batch_reviews",
                return_value=[],
            ),
        ):
            _run_cli("--reviews", reviews_json, "-p", "1")

        captured = capsys.readouterr()
        assert "2 file(s) enqueued with request-changes" in captured.out
        assert "/a.ts" in captured.out
        assert "/b.ts" in captured.out
