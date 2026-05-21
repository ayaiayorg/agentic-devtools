"""Tests for _latest_copilot_review_on_head."""

from dataclasses import dataclass

from agentic_devtools.cli.ci.orchestrator import _latest_copilot_review_on_head


@dataclass
class _ReviewInfo:
    id: int
    user: str
    state: str
    body: str = ""
    commit_sha: str = ""


class TestLatestCopilotReviewOnHead:
    """Tests for _latest_copilot_review_on_head."""

    def test_skips_review_with_different_commit_sha(self):
        """Reviews targeting a different commit are skipped."""
        review = _ReviewInfo(id=1, user="Copilot", state="APPROVED", commit_sha="old_sha")
        result = _latest_copilot_review_on_head([review], "current_sha")
        assert result is None

    def test_includes_review_with_matching_commit_sha(self):
        """Reviews targeting current HEAD are included."""
        review = _ReviewInfo(id=1, user="Copilot", state="APPROVED", commit_sha="current_sha")
        result = _latest_copilot_review_on_head([review], "current_sha")
        assert result is review

    def test_includes_review_with_empty_commit_sha(self):
        """Reviews with empty commit_sha are treated as matching current HEAD."""
        review = _ReviewInfo(id=1, user="Copilot", state="APPROVED", commit_sha="")
        result = _latest_copilot_review_on_head([review], "current_sha")
        assert result is review

    def test_skips_non_copilot_user(self):
        """Reviews from non-Copilot users are skipped."""
        review = _ReviewInfo(id=1, user="some-human", state="APPROVED", commit_sha="current_sha")
        result = _latest_copilot_review_on_head([review], "current_sha")
        assert result is None

    def test_returns_highest_id_when_multiple(self):
        """Returns the review with highest ID among eligible ones."""
        r1 = _ReviewInfo(id=1, user="Copilot", state="APPROVED", commit_sha="sha")
        r2 = _ReviewInfo(id=5, user="Copilot", state="COMMENTED", commit_sha="sha")
        r3 = _ReviewInfo(id=3, user="Copilot", state="APPROVED", commit_sha="sha")
        result = _latest_copilot_review_on_head([r1, r2, r3], "sha")
        assert result is r2
