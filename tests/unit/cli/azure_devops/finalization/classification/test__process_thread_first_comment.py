"""Tests for _process_thread_first_comment function."""

from agentic_devtools.cli.azure_devops.finalization.classification import _process_thread_first_comment
from agentic_devtools.cli.azure_devops.finalization.models import EligibleComments


class TestProcessThreadFirstComment:
    """Tests for _process_thread_first_comment function."""

    def test_appends_comment_when_valid(self):
        """Should append to file_summaries when _extract_first_comment returns a comment."""
        thread = {
            "id": 10,
            "comments": [
                {
                    "id": 1,
                    "content": "<!-- agdt-review:v1 type:file-summary file:/src/a.py -->\nContent",
                    "author": {"id": "my-user"},
                }
            ],
        }
        result = EligibleComments()
        _process_thread_first_comment(thread, "my-user", "file-summary", result)
        assert len(result.file_summaries) == 1
        assert result.file_summaries[0].thread_id == 10

    def test_does_not_append_when_empty_comments(self):
        """Should not append when thread has empty comments list."""
        thread = {"id": 10, "comments": []}
        result = EligibleComments()
        _process_thread_first_comment(thread, "my-user", "file-summary", result)
        assert len(result.file_summaries) == 0

    def test_does_not_append_when_wrong_author(self):
        """Should not append and add skip entry when author does not match."""
        thread = {
            "id": 10,
            "comments": [
                {
                    "id": 1,
                    "content": "<!-- agdt-review:v1 type:file-summary -->\nContent",
                    "author": {"id": "other-user"},
                }
            ],
        }
        result = EligibleComments()
        _process_thread_first_comment(thread, "my-user", "file-summary", result)
        assert len(result.file_summaries) == 0
        assert len(result.skipped) == 1
