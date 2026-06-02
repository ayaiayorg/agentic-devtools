"""Tests for ReviewInfo dataclass."""

from agentic_devtools.cli.ci.models import ReviewInfo


class TestReviewInfo:
    """Tests for the ReviewInfo dataclass."""

    def test_approved_review(self) -> None:
        review = ReviewInfo(
            id=1001,
            user="reviewer1",
            state="APPROVED",
            body="LGTM!",
        )
        assert review.id == 1001
        assert review.user == "reviewer1"
        assert review.state == "APPROVED"
        assert review.body == "LGTM!"

    def test_changes_requested(self) -> None:
        review = ReviewInfo(
            id=2002,
            user="maintainer",
            state="CHANGES_REQUESTED",
            body="Please fix the tests",
        )
        assert review.state == "CHANGES_REQUESTED"

    def test_default_body(self) -> None:
        review = ReviewInfo(id=1, user="bot", state="COMMENTED")
        assert review.body == ""

    def test_is_frozen(self) -> None:
        review = ReviewInfo(id=1, user="u", state="APPROVED")
        try:
            review.state = "DISMISSED"  # type: ignore[misc]
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass

    def test_equality(self) -> None:
        r1 = ReviewInfo(id=1, user="u", state="APPROVED")
        r2 = ReviewInfo(id=1, user="u", state="APPROVED")
        assert r1 == r2

    def test_default_submitted_at_empty_string(self) -> None:
        review = ReviewInfo(id=1, user="bot", state="COMMENTED")
        assert review.submitted_at == ""

    def test_submitted_at_set(self) -> None:
        review = ReviewInfo(
            id=1,
            user="Copilot",
            state="CHANGES_REQUESTED",
            submitted_at="2026-05-01T12:00:00Z",
        )
        assert review.submitted_at == "2026-05-01T12:00:00Z"
