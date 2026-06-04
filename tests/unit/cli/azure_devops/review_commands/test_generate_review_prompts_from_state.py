"""Tests for generate_review_prompts_from_state."""

import json
from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.azure_devops.review_commands import generate_review_prompts_from_state


class TestGenerateReviewPromptsFromState:
    """Tests for generate_review_prompts_from_state."""

    def test_exits_when_pull_request_id_missing(self):
        with patch("agentic_devtools.cli.azure_devops.review_commands.get_value", return_value=None):
            with pytest.raises(SystemExit):
                generate_review_prompts_from_state()

    def test_exits_when_pr_details_missing(self, tmp_path):
        with (
            patch("agentic_devtools.cli.azure_devops.review_commands.get_value", return_value="123"),
            patch("agentic_devtools.cli.azure_devops.review_commands.get_state_dir", return_value=tmp_path),
        ):
            with pytest.raises(SystemExit):
                generate_review_prompts_from_state()

    def test_calls_generate_review_prompts_with_detected_unchanged_files(self, tmp_path):
        details_path = tmp_path / "temp-get-pull-request-details-response.json"
        pr_details = {"pullRequest": {"pullRequestId": 123}, "files": [], "threads": []}
        details_path.write_text(json.dumps(pr_details), encoding="utf-8")

        with (
            patch("agentic_devtools.cli.azure_devops.review_commands.get_value", return_value="123"),
            patch("agentic_devtools.cli.azure_devops.review_commands.get_state_dir", return_value=tmp_path),
            patch(
                "agentic_devtools.cli.azure_devops.review_commands._detect_unchanged_files",
                return_value={"/src/app.ts"},
            ),
            patch(
                "agentic_devtools.cli.azure_devops.review_commands.generate_review_prompts",
                return_value=(0, 0, 0, MagicMock(), []),
            ) as mock_generate,
            patch(
                "agentic_devtools.cli.azure_devops.review_commands._persist_processing_paths_to_review_state"
            ) as mock_persist,
        ):
            generate_review_prompts_from_state()

        mock_generate.assert_called_once_with(
            123,
            pr_details,
            unchanged_files={"/src/app.ts"},
        )
        mock_persist.assert_called_once_with(123, mock_generate.return_value[3])
