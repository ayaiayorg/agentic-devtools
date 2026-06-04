"""Tests for checkout_and_sync_branch_from_state."""

import json
from unittest.mock import patch

import pytest

from agentic_devtools.cli.azure_devops.review_commands import checkout_and_sync_branch_from_state


class TestCheckoutAndSyncBranchFromState:
    """Tests for checkout_and_sync_branch_from_state."""

    def test_exits_when_pull_request_id_missing(self):
        with patch("agentic_devtools.cli.azure_devops.review_commands.get_value", return_value=None):
            with pytest.raises(SystemExit):
                checkout_and_sync_branch_from_state()

    def test_exits_when_pr_details_missing(self, tmp_path):
        with (
            patch("agentic_devtools.cli.azure_devops.review_commands.get_value", return_value="123"),
            patch("agentic_devtools.cli.azure_devops.review_commands.get_state_dir", return_value=tmp_path),
        ):
            with pytest.raises(SystemExit):
                checkout_and_sync_branch_from_state()

    def test_exits_when_source_branch_missing(self, tmp_path):
        details_path = tmp_path / "temp-get-pull-request-details-response.json"
        details_path.write_text(json.dumps({"pullRequest": {"sourceRefName": ""}}), encoding="utf-8")

        with (
            patch("agentic_devtools.cli.azure_devops.review_commands.get_value", return_value="123"),
            patch("agentic_devtools.cli.azure_devops.review_commands.get_state_dir", return_value=tmp_path),
        ):
            with pytest.raises(SystemExit):
                checkout_and_sync_branch_from_state()

    def test_exits_when_checkout_fails(self, tmp_path):
        details_path = tmp_path / "temp-get-pull-request-details-response.json"
        details_path.write_text(
            json.dumps({"pullRequest": {"sourceRefName": "refs/heads/feature/test"}}),
            encoding="utf-8",
        )

        with (
            patch("agentic_devtools.cli.azure_devops.review_commands.get_value", return_value="123"),
            patch("agentic_devtools.cli.azure_devops.review_commands.get_state_dir", return_value=tmp_path),
            patch(
                "agentic_devtools.cli.azure_devops.review_commands.checkout_and_sync_branch",
                return_value=(False, "nope", set(), False, None),
            ),
        ):
            with pytest.raises(SystemExit):
                checkout_and_sync_branch_from_state()

    def test_calls_checkout_with_required_arguments(self, tmp_path):
        details_path = tmp_path / "temp-get-pull-request-details-response.json"
        details_path.write_text(
            json.dumps({"pullRequest": {"sourceRefName": "refs/heads/feature/test"}}),
            encoding="utf-8",
        )

        with (
            patch("agentic_devtools.cli.azure_devops.review_commands.get_value", return_value="123"),
            patch("agentic_devtools.cli.azure_devops.review_commands.get_state_dir", return_value=tmp_path),
            patch("agentic_devtools.cli.azure_devops.review_commands.is_dry_run", return_value=False),
            patch(
                "agentic_devtools.cli.azure_devops.review_commands.checkout_and_sync_branch",
                return_value=(True, None, set(), False, None),
            ) as mock_checkout,
        ):
            checkout_and_sync_branch_from_state()

        mock_checkout.assert_called_once_with(
            "feature/test",
            123,
            save_files_on_branch=True,
            dry_run=False,
        )
