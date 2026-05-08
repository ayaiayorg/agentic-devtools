"""Tests for _extract_first_comment function."""

from agentic_devtools.cli.azure_devops.finalization.classification import _extract_first_comment
from agentic_devtools.cli.azure_devops.finalization.models import EligibleComments


class TestExtractFirstComment:
    """Tests for _extract_first_comment function."""

    def test_returns_none_when_no_comments(self):
        """Should return None when thread has empty comments list."""
        thread = {"id": 10, "comments": []}
        result = EligibleComments()
        comment = _extract_first_comment(thread, "my-user", "file-summary", result)
        assert comment is None
        assert len(result.skipped) == 0

    def test_returns_none_for_wrong_author(self):
        """Should return None and add skip entry for different author."""
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
        comment = _extract_first_comment(thread, "my-user", "file-summary", result)
        assert comment is None
        assert len(result.skipped) == 1
        assert "not editable" in result.skipped[0]["reason"]

    def test_returns_eligible_comment_for_matching_author(self):
        """Should return EligibleComment when author matches."""
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
        comment = _extract_first_comment(thread, "my-user", "file-summary", result)
        assert comment is not None
        assert comment.thread_id == 10
        assert comment.marker_type == "file-summary"
        assert comment.file_path == "/src/a.py"
