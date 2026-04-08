"""Tests for _select_latest_copilot_review in copilot_review_status module."""

from agentic_devtools.cli.github.copilot_review_status import (
    COPILOT_REVIEWER_LOGIN,
    _select_latest_copilot_review,
)

HEAD_SHA = "abc123def456abc123def456abc123def456abc1"


def _make_review(
    login: str = COPILOT_REVIEWER_LOGIN,
    commit_id: str = HEAD_SHA,
    review_id: int = 100,
    submitted_at: str = "2026-04-07T09:00:00Z",
    **extra,
):
    """Helper to build a review dict."""
    return {
        "id": review_id,
        "user": {"login": login},
        "commit_id": commit_id,
        "submitted_at": submitted_at,
        **extra,
    }


class TestSelectLatestCopilotReview:
    """Tests for _select_latest_copilot_review."""

    def test_single_matching_review(self):
        """Single Copilot review matching head SHA is returned."""
        reviews = [_make_review()]
        result = _select_latest_copilot_review(reviews, HEAD_SHA)
        assert result is not None
        assert result["id"] == 100

    def test_multiple_reviews_returns_most_recent(self):
        """Most recent Copilot review by submitted_at is returned."""
        reviews = [
            _make_review(review_id=1, submitted_at="2026-04-07T08:00:00Z"),
            _make_review(review_id=2, submitted_at="2026-04-07T10:00:00Z"),
            _make_review(review_id=3, submitted_at="2026-04-07T09:00:00Z"),
        ]
        result = _select_latest_copilot_review(reviews, HEAD_SHA)
        assert result is not None
        assert result["id"] == 2

    def test_review_on_different_commit_excluded(self):
        """Copilot review on a different commit is excluded."""
        reviews = [_make_review(commit_id="other_sha")]
        result = _select_latest_copilot_review(reviews, HEAD_SHA)
        assert result is None

    def test_non_copilot_review_excluded(self):
        """Human reviews are excluded."""
        reviews = [_make_review(login="human-user")]
        result = _select_latest_copilot_review(reviews, HEAD_SHA)
        assert result is None

    def test_empty_reviews_list(self):
        """Empty review list returns None."""
        result = _select_latest_copilot_review([], HEAD_SHA)
        assert result is None

    def test_tie_breaking_by_id(self):
        """When submitted_at is identical, higher id wins."""
        reviews = [
            _make_review(review_id=10, submitted_at="2026-04-07T09:00:00Z"),
            _make_review(review_id=20, submitted_at="2026-04-07T09:00:00Z"),
        ]
        result = _select_latest_copilot_review(reviews, HEAD_SHA)
        assert result is not None
        assert result["id"] == 20

    def test_missing_user_field_skipped(self):
        """Reviews with missing user field are safely skipped."""
        reviews = [
            {"id": 1, "commit_id": HEAD_SHA, "submitted_at": "2026-04-07T09:00:00Z"},
        ]
        result = _select_latest_copilot_review(reviews, HEAD_SHA)
        assert result is None

    def test_missing_login_field_skipped(self):
        """Reviews with user but no login field are safely skipped."""
        reviews = [
            {
                "id": 1,
                "user": {},
                "commit_id": HEAD_SHA,
                "submitted_at": "2026-04-07T09:00:00Z",
            },
        ]
        result = _select_latest_copilot_review(reviews, HEAD_SHA)
        assert result is None

    def test_mixed_reviews_only_matching_returned(self):
        """Only Copilot reviews on the correct commit are considered."""
        reviews = [
            _make_review(login="human", review_id=1),
            _make_review(commit_id="other", review_id=2),
            _make_review(review_id=3, submitted_at="2026-04-07T11:00:00Z"),
        ]
        result = _select_latest_copilot_review(reviews, HEAD_SHA)
        assert result is not None
        assert result["id"] == 3

    def test_null_user_field_skipped(self):
        """Reviews with user=None (ghost/deleted users) are safely skipped."""
        reviews = [
            {
                "id": 1,
                "user": None,
                "commit_id": HEAD_SHA,
                "submitted_at": "2026-04-07T09:00:00Z",
            },
        ]
        result = _select_latest_copilot_review(reviews, HEAD_SHA)
        assert result is None

    def test_null_submitted_at_does_not_crash(self):
        """Reviews with submitted_at=None are sorted safely (treated as empty string)."""
        reviews = [
            _make_review(review_id=1, submitted_at=None),
            _make_review(review_id=2, submitted_at="2026-04-07T10:00:00Z"),
        ]
        result = _select_latest_copilot_review(reviews, HEAD_SHA)
        assert result is not None
        assert result["id"] == 2
