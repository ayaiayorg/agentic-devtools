"""Tests for agentic_devtools.cli.azure_devops.approve_files.approve_files_cli."""

import sys
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_cli(*cli_args: str):
    """Invoke approve_files_cli with the given CLI arguments."""
    from agentic_devtools.cli.azure_devops.approve_files import approve_files_cli

    with patch.object(sys, "argv", ["agdt-approve-files", *cli_args]):
        approve_files_cli()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestApproveFilesCli:
    """Tests for approve_files_cli."""

    # -- success path -------------------------------------------------------

    def test_successful_batch_approval(self, temp_state_dir, clear_state_before, capsys):
        """Verify resolve → validate → submit_reviews_async is called correctly."""
        with (
            patch(
                "agentic_devtools.cli.azure_devops.approve_files.is_dry_run",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.approve_files.resolve_batch_reviews",
                return_value=[
                    {"file_path": "/src/a.ts", "outcome": "approve", "summary": "LGTM"},
                    {"file_path": "/src/b.ts", "outcome": "approve", "summary": "LGTM"},
                ],
            ) as mock_resolve,
            patch(
                "agentic_devtools.cli.azure_devops.approve_files.validate_batch_reviews",
                return_value=[],
            ) as mock_validate,
            patch(
                "agentic_devtools.cli.azure_devops.async_commands.submit_reviews_async",
            ) as mock_submit,
        ):
            _run_cli(
                "--summary",
                "LGTM",
                "--file-paths",
                '["/src/a.ts","/src/b.ts"]',
                "--pull-request-id",
                "12345",
            )

        # resolve called with correct payload
        mock_resolve.assert_called_once()
        payload = mock_resolve.call_args[0][0]
        assert payload["default_outcome"] == "approve"
        assert payload["default_summary"] == "LGTM"
        assert len(payload["items"]) == 2

        # validate called
        mock_validate.assert_called_once()

        # submit_reviews_async called with correct args
        mock_submit.assert_called_once()
        call_kwargs = mock_submit.call_args.kwargs
        assert call_kwargs["default_outcome"] == "approve"
        assert call_kwargs["default_summary"] == "LGTM"
        assert call_kwargs["pull_request_id"] == 12345

    def test_pr_id_from_cli_arg(self, temp_state_dir, clear_state_before):
        """--pull-request-id is used when provided."""
        with (
            patch(
                "agentic_devtools.cli.azure_devops.approve_files.is_dry_run",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.approve_files.resolve_batch_reviews",
                return_value=[{"file_path": "/x.ts", "outcome": "approve", "summary": "ok"}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.approve_files.validate_batch_reviews",
                return_value=[],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.async_commands.submit_reviews_async",
            ) as mock_submit,
        ):
            _run_cli(
                "--summary",
                "ok",
                "--file-paths",
                '["/x.ts"]',
                "-p",
                "999",
            )

        assert mock_submit.call_args.kwargs["pull_request_id"] == 999

    def test_pr_id_falls_back_to_state(self, temp_state_dir, clear_state_before):
        """Falls back to get_pull_request_id when --pull-request-id not given."""
        with (
            patch(
                "agentic_devtools.cli.azure_devops.approve_files.is_dry_run",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.approve_files.get_pull_request_id",
                return_value=555,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.approve_files.resolve_batch_reviews",
                return_value=[{"file_path": "/x.ts", "outcome": "approve", "summary": "ok"}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.approve_files.validate_batch_reviews",
                return_value=[],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.async_commands.submit_reviews_async",
            ) as mock_submit,
        ):
            _run_cli("--summary", "ok", "--file-paths", '["/x.ts"]')

        assert mock_submit.call_args.kwargs["pull_request_id"] == 555

    # -- dry-run ------------------------------------------------------------

    def test_dry_run_prints_plan_without_enqueuing(self, temp_state_dir, clear_state_before, capsys):
        """In dry-run mode, items are printed but not enqueued."""
        with (
            patch(
                "agentic_devtools.cli.azure_devops.approve_files.is_dry_run",
                return_value=True,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.approve_files.resolve_batch_reviews",
                return_value=[
                    {"file_path": "/a.ts", "outcome": "approve", "summary": "s"},
                ],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.approve_files.validate_batch_reviews",
                return_value=[],
            ),
        ):
            _run_cli("--summary", "s", "--file-paths", '["/a.ts"]', "-p", "1")

        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "/a.ts" in captured.out

    # -- error paths --------------------------------------------------------

    def test_invalid_json_file_paths(self, temp_state_dir, clear_state_before, capsys):
        """--file-paths with invalid JSON exits 1."""
        with pytest.raises(SystemExit) as exc:
            _run_cli("--summary", "s", "--file-paths", "not json", "-p", "1")
        assert exc.value.code == 1
        assert "not valid JSON" in capsys.readouterr().err

    def test_file_paths_not_array(self, temp_state_dir, clear_state_before, capsys):
        """--file-paths that is not a JSON array exits 1."""
        with pytest.raises(SystemExit) as exc:
            _run_cli("--summary", "s", "--file-paths", '{"a":1}', "-p", "1")
        assert exc.value.code == 1
        assert "must be a JSON array" in capsys.readouterr().err

    def test_file_paths_empty_array(self, temp_state_dir, clear_state_before, capsys):
        """--file-paths with empty array exits 1."""
        with pytest.raises(SystemExit) as exc:
            _run_cli("--summary", "s", "--file-paths", "[]", "-p", "1")
        assert exc.value.code == 1
        assert "at least one file path" in capsys.readouterr().err

    def test_file_paths_contains_empty_string(self, temp_state_dir, clear_state_before, capsys):
        """--file-paths with an empty string entry exits 1."""
        with pytest.raises(SystemExit) as exc:
            _run_cli("--summary", "s", "--file-paths", '[""]', "-p", "1")
        assert exc.value.code == 1
        assert "non-empty string" in capsys.readouterr().err

    def test_file_paths_contains_non_string(self, temp_state_dir, clear_state_before, capsys):
        """--file-paths with non-string entry exits 1."""
        with pytest.raises(SystemExit) as exc:
            _run_cli("--summary", "s", "--file-paths", "[42]", "-p", "1")
        assert exc.value.code == 1
        assert "non-empty string" in capsys.readouterr().err

    def test_validation_failure_exits_1(self, temp_state_dir, clear_state_before, capsys):
        """Errors from validate_batch_reviews are printed to stderr and exit 1."""
        with (
            patch(
                "agentic_devtools.cli.azure_devops.approve_files.resolve_batch_reviews",
                return_value=[{"file_path": "/x.ts", "outcome": "approve", "summary": None}],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.approve_files.validate_batch_reviews",
                return_value=["Item 0 (/x.ts): summary is required."],
            ),
        ):
            with pytest.raises(SystemExit) as exc:
                _run_cli("--summary", "s", "--file-paths", '["/x.ts"]', "-p", "1")
        assert exc.value.code == 1
        assert "summary is required" in capsys.readouterr().err

    def test_missing_pr_id_exits_1(self, temp_state_dir, clear_state_before):
        """Missing --pull-request-id with no state raises."""
        with patch(
            "agentic_devtools.cli.azure_devops.approve_files.get_pull_request_id",
            side_effect=KeyError("pull_request_id"),
        ):
            with pytest.raises(KeyError, match="pull_request_id"):
                _run_cli("--summary", "s", "--file-paths", '["/x.ts"]')

    def test_payload_construction(self, temp_state_dir, clear_state_before):
        """Verify the payload dict passed to resolve_batch_reviews."""
        with (
            patch(
                "agentic_devtools.cli.azure_devops.approve_files.is_dry_run",
                return_value=False,
            ),
            patch(
                "agentic_devtools.cli.azure_devops.approve_files.resolve_batch_reviews",
                return_value=[{"file_path": "/a.ts", "outcome": "approve", "summary": "LGTM"}],
            ) as mock_resolve,
            patch(
                "agentic_devtools.cli.azure_devops.approve_files.validate_batch_reviews",
                return_value=[],
            ),
            patch(
                "agentic_devtools.cli.azure_devops.async_commands.submit_reviews_async",
            ),
        ):
            _run_cli(
                "--summary",
                "LGTM",
                "--file-paths",
                '["/a.ts"]',
                "-p",
                "1",
            )

        payload = mock_resolve.call_args[0][0]
        assert payload == {
            "default_outcome": "approve",
            "default_summary": "LGTM",
            "items": [{"file_path": "/a.ts"}],
        }
