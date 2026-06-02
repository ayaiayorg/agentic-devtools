"""Tests for ReviewCommentInfo dataclass."""

import pytest

from agentic_devtools.cli.ci.models import ReviewCommentInfo


class TestReviewCommentInfo:
    """Tests for the ReviewCommentInfo frozen dataclass."""

    def test_required_fields(self) -> None:
        comment = ReviewCommentInfo(
            id=101,
            path="src/foo.py",
            body="Fix the null check",
            html_url="https://github.com/owner/repo/pull/42#pullreviewcomment-101",
        )
        assert comment.id == 101
        assert comment.path == "src/foo.py"
        assert comment.body == "Fix the null check"
        assert comment.html_url == "https://github.com/owner/repo/pull/42#pullreviewcomment-101"

    def test_default_is_suppressed_false(self) -> None:
        comment = ReviewCommentInfo(id=1, path="f.py", body="text", html_url="http://x")
        assert comment.is_suppressed is False

    def test_suppressed_comment(self) -> None:
        comment = ReviewCommentInfo(
            id=202,
            path="models.py",
            body="Consider extracting this helper",
            html_url="https://github.com/owner/repo/pull/42#pullreviewcomment-202",
            is_suppressed=True,
        )
        assert comment.is_suppressed is True

    def test_is_frozen(self) -> None:
        comment = ReviewCommentInfo(id=1, path="f.py", body="x", html_url="http://x")
        with pytest.raises(AttributeError):
            comment.body = "changed"  # type: ignore[misc]

    def test_equality(self) -> None:
        a = ReviewCommentInfo(id=1, path="f.py", body="x", html_url="http://x")
        b = ReviewCommentInfo(id=1, path="f.py", body="x", html_url="http://x")
        assert a == b

    def test_inequality_different_id(self) -> None:
        a = ReviewCommentInfo(id=1, path="f.py", body="x", html_url="http://x")
        b = ReviewCommentInfo(id=2, path="f.py", body="x", html_url="http://x")
        assert a != b

    def test_inequality_different_suppressed(self) -> None:
        a = ReviewCommentInfo(id=1, path="f.py", body="x", html_url="http://x", is_suppressed=False)
        b = ReviewCommentInfo(id=1, path="f.py", body="x", html_url="http://x", is_suppressed=True)
        assert a != b

    def test_default_commit_id_empty_string(self) -> None:
        comment = ReviewCommentInfo(id=1, path="f.py", body="x", html_url="http://x")
        assert comment.commit_id == ""

    def test_commit_id_set(self) -> None:
        comment = ReviewCommentInfo(
            id=1,
            path="f.py",
            body="x",
            html_url="http://x",
            commit_id="abc123def",
        )
        assert comment.commit_id == "abc123def"

    def test_default_original_commit_id_empty_string(self) -> None:
        comment = ReviewCommentInfo(id=1, path="f.py", body="x", html_url="http://x")
        assert comment.original_commit_id == ""

    def test_original_commit_id_set(self) -> None:
        comment = ReviewCommentInfo(
            id=1,
            path="f.py",
            body="x",
            html_url="http://x",
            commit_id="remapped_sha",
            original_commit_id="original_sha",
        )
        assert comment.original_commit_id == "original_sha"
        assert comment.commit_id == "remapped_sha"

    def test_original_commit_id_differs_from_commit_id(self) -> None:
        """original_commit_id can differ from commit_id when GitHub remaps after squash."""
        comment = ReviewCommentInfo(
            id=42,
            path="src/main.py",
            body="Fix this",
            html_url="http://x",
            commit_id="5008f6e",
            original_commit_id="83bf0725",
        )
        assert comment.commit_id == "5008f6e"
        assert comment.original_commit_id == "83bf0725"
        assert comment.commit_id != comment.original_commit_id
