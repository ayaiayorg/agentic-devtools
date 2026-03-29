"""Tests for submit_reviews_async function."""

import json

import pytest

from agentic_devtools.cli.azure_devops.async_commands import submit_reviews_async
from tests.unit.cli.azure_devops.async_commands._helpers import assert_function_in_script, get_script_from_call


class TestSubmitReviewsAsync:
    """Tests for submit_reviews_async function."""

    def test_spawns_background_task(self, mock_background_and_state, capsys):
        """Should spawn a background task with the correct function."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        reviews = json.dumps([{"file_path": "src/a.ts"}])
        submit_reviews_async(reviews=reviews)
        captured = capsys.readouterr()
        assert "Background task started" in captured.out
        script = get_script_from_call(mock_background_and_state["mock_popen"])
        assert_function_in_script(
            script,
            "agentic_devtools.cli.azure_devops.file_review_commands",
            "submit_reviews",
        )

    def test_stores_cli_args_in_state(self, mock_background_and_state):
        """Should store CLI args in state before spawning."""
        from agentic_devtools.state import get_value

        reviews = json.dumps([{"file_path": "src/a.ts"}])
        submit_reviews_async(
            reviews=reviews,
            default_outcome="approve",
            default_summary="LGTM",
            pull_request_id=99999,
        )
        assert get_value("batch_reviews.items") == reviews
        assert get_value("batch_reviews.default_outcome") == "approve"
        assert get_value("batch_reviews.default_summary") == "LGTM"
        assert get_value("pull_request_id") == 99999

    def test_prints_file_count_in_tracking_info(self, mock_background_and_state, capsys):
        """Should print the number of files in the tracking info."""
        reviews = json.dumps([{"file_path": "a.ts"}, {"file_path": "b.ts"}, {"file_path": "c.ts"}])
        submit_reviews_async(reviews=reviews, pull_request_id=12345)
        captured = capsys.readouterr()
        assert "3 file review(s)" in captured.out

    def test_exits_when_reviews_not_json(self, mock_background_and_state, capsys):
        """Should exit with error when reviews is not valid JSON."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews_async(reviews="not-json")
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not valid JSON" in captured.err

    def test_exits_when_reviews_empty_array(self, mock_background_and_state, capsys):
        """Should exit with error when reviews is an empty array."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews_async(reviews="[]")
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "non-empty" in captured.err

    def test_exits_when_pull_request_id_missing(self, mock_background_and_state, capsys):
        """Should exit when pull_request_id is not set."""
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews_async(reviews='[{"file_path": "a.ts"}]')
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "pull_request_id" in captured.err

    def test_exits_when_reviews_missing(self, mock_background_and_state, capsys):
        """Should exit when batch_reviews.items is not provided."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews_async()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "batch_reviews.items" in captured.err

    def test_empty_list_in_state_reports_non_empty_error(self, mock_background_and_state, capsys):
        """Empty list stored in state should report 'non-empty', not 'is required'."""
        from agentic_devtools.state import set_value

        set_value("pull_request_id", 12345)
        set_value("batch_reviews.items", [])
        with pytest.raises(SystemExit) as exc_info:
            submit_reviews_async()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "non-empty" in captured.err
