"""Tests for _deduplicate_review_comments() in the GitHub provider."""

from agentic_devtools.cli.ci.github_provider import _deduplicate_review_comments
from agentic_devtools.cli.ci.models import ReviewCommentInfo


def _rest(*, id: int = 1, path: str = "f.py", body: str = "comment") -> ReviewCommentInfo:
    return ReviewCommentInfo(id=id, path=path, body=body, html_url="http://x")


def _suppressed(*, id: int = -1, path: str = "f.py", body: str = "comment") -> ReviewCommentInfo:
    return ReviewCommentInfo(id=id, path=path, body=body, html_url="", is_suppressed=True)


class TestDeduplicateReviewComments:
    """Tests for _deduplicate_review_comments()."""

    def test_no_overlap_preserves_all(self) -> None:
        rest = [_rest(id=1, path="a.py", body="A")]
        suppressed = [_suppressed(id=-1, path="b.py", body="B")]
        result = _deduplicate_review_comments(rest, suppressed)
        assert len(result) == 2
        assert result[0].path == "a.py"
        assert result[1].path == "b.py"
        assert result[1].is_suppressed is True

    def test_exact_duplicate_drops_suppressed(self) -> None:
        rest = [_rest(id=1, path="f.py", body="same")]
        suppressed = [_suppressed(id=-1, path="f.py", body="same")]
        result = _deduplicate_review_comments(rest, suppressed)
        assert len(result) == 1
        assert result[0].is_suppressed is False

    def test_whitespace_normalization_on_body(self) -> None:
        rest = [_rest(id=1, path="f.py", body="  body  ")]
        suppressed = [_suppressed(id=-1, path="f.py", body="body")]
        result = _deduplicate_review_comments(rest, suppressed)
        assert len(result) == 1

    def test_crlf_normalization_on_body(self) -> None:
        rest = [_rest(id=1, path="f.py", body="line1\nline2")]
        suppressed = [_suppressed(id=-1, path="f.py", body="line1\r\nline2")]
        result = _deduplicate_review_comments(rest, suppressed)
        assert len(result) == 1

    def test_leading_slash_normalization_on_path(self) -> None:
        rest = [_rest(id=1, path="src/foo.py", body="comment")]
        suppressed = [_suppressed(id=-1, path="/src/foo.py", body="comment")]
        result = _deduplicate_review_comments(rest, suppressed)
        assert len(result) == 1

    def test_partial_substring_match_preserves_both(self) -> None:
        rest = [_rest(id=1, path="f.py", body="fix this issue")]
        suppressed = [_suppressed(id=-1, path="f.py", body="fix this")]
        result = _deduplicate_review_comments(rest, suppressed)
        assert len(result) == 2

    def test_empty_suppressed_returns_rest_only(self) -> None:
        rest = [_rest(id=1)]
        result = _deduplicate_review_comments(rest, [])
        assert len(result) == 1
        assert result[0].id == 1

    def test_empty_rest_returns_suppressed(self) -> None:
        suppressed = [_suppressed(id=-1, body="feedback")]
        result = _deduplicate_review_comments([], suppressed)
        assert len(result) == 1
        assert result[0].is_suppressed is True

    def test_rest_order_is_preserved(self) -> None:
        rest = [_rest(id=1, path="a.py", body="A"), _rest(id=2, path="b.py", body="B")]
        suppressed = [_suppressed(id=-1, path="c.py", body="C")]
        result = _deduplicate_review_comments(rest, suppressed)
        assert [c.path for c in result] == ["a.py", "b.py", "c.py"]
