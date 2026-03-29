"""Tests for submit_reviews_cli function."""

import json
import sys
from unittest.mock import patch

from agentic_devtools.cli.azure_devops.async_commands import submit_reviews_cli
from tests.unit.cli.azure_devops.async_commands._helpers import assert_function_in_script, get_script_from_call


class TestSubmitReviewsCli:
    """Tests for submit_reviews_cli CLI entry point."""

    def test_spawns_background_task_via_cli(self, mock_background_and_state, capsys):
        """Should spawn a background task when invoked with CLI args."""
        reviews = json.dumps([{"file_path": "src/a.ts"}])
        with patch.object(
            sys,
            "argv",
            [
                "agdt-submit-reviews",
                "--reviews",
                reviews,
                "--pull-request-id",
                "12345",
                "--outcome",
                "approve",
                "--summary",
                "LGTM",
            ],
        ):
            submit_reviews_cli()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out

    def test_spawns_correct_function(self, mock_background_and_state):
        """Should call submit_reviews in file_review_commands module."""
        reviews = json.dumps([{"file_path": "src/a.ts"}])
        with patch.object(
            sys,
            "argv",
            [
                "agdt-submit-reviews",
                "--reviews",
                reviews,
                "--pull-request-id",
                "12345",
            ],
        ):
            submit_reviews_cli()

        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(
            script,
            "agentic_devtools.cli.azure_devops.file_review_commands",
            "submit_reviews",
        )

    def test_stores_all_cli_args_in_state(self, mock_background_and_state):
        """Should store all CLI args into state."""
        from agentic_devtools.state import get_value

        reviews = json.dumps([{"file_path": "a.ts"}, {"file_path": "b.ts"}])
        with patch.object(
            sys,
            "argv",
            [
                "agdt-submit-reviews",
                "--reviews",
                reviews,
                "--pull-request-id",
                "12345",
                "--outcome",
                "approve",
                "--summary",
                "Mechanical refactor LGTM",
            ],
        ):
            submit_reviews_cli()

        assert get_value("batch_reviews.items") == reviews
        assert get_value("batch_reviews.default_outcome") == "approve"
        assert get_value("batch_reviews.default_summary") == "Mechanical refactor LGTM"
        assert get_value("pull_request_id") == 12345

    def test_short_flags(self, mock_background_and_state, capsys):
        """Should accept short flags -r, -o, -s, -p."""
        reviews = json.dumps([{"file_path": "a.ts"}])
        with patch.object(
            sys,
            "argv",
            [
                "agdt-submit-reviews",
                "-r",
                reviews,
                "-p",
                "12345",
                "-o",
                "approve",
                "-s",
                "LGTM",
            ],
        ):
            submit_reviews_cli()

        captured = capsys.readouterr()
        assert "Background task started" in captured.out
