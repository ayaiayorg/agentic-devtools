"""Tests for ReviewState multi-model fields (reviewerModels, bossModel)."""

from agentic_devtools.cli.azure_devops.review_state import (
    OverallSummary,
    ReviewState,
)


def _make_review_state(**kwargs):
    """Create a ReviewState with test defaults."""
    defaults = {
        "prId": 12345,
        "repoId": "repo-guid",
        "repoName": "test-repo",
        "project": "TestProject",
        "organization": "https://dev.azure.com/testorg",
        "latestIterationId": 1,
        "scaffoldedUtc": "2026-01-01T00:00:00Z",
        "overallSummary": OverallSummary(threadId=1, commentId=1),
    }
    defaults.update(kwargs)
    return ReviewState(**defaults)


class TestReviewStateMultiModel:
    """Tests for ReviewState multi-model fields."""

    def test_default_reviewer_models_none(self):
        """reviewerModels defaults to None."""
        state = _make_review_state()
        assert state.reviewerModels is None
        assert state.bossModel is None

    def test_set_reviewer_models(self):
        """Can set reviewer models and boss model."""
        state = _make_review_state(
            reviewerModels=["Model A", "Model B"],
            bossModel="Model A",
        )
        assert state.reviewerModels == ["Model A", "Model B"]
        assert state.bossModel == "Model A"

    def test_is_multi_model_true(self):
        """is_multi_model returns True for multiple reviewer models."""
        state = _make_review_state(reviewerModels=["A", "B"])
        assert state.is_multi_model is True

    def test_is_multi_model_false_single(self):
        """is_multi_model returns False for a single reviewer model."""
        state = _make_review_state(reviewerModels=["A"])
        assert state.is_multi_model is False

    def test_is_multi_model_false_none(self):
        """is_multi_model returns False when reviewerModels is None."""
        state = _make_review_state()
        assert state.is_multi_model is False

    def test_to_dict_includes_reviewer_models(self):
        """to_dict includes reviewerModels and bossModel when set."""
        state = _make_review_state(
            reviewerModels=["Model A", "Model B"],
            bossModel="Model A",
        )
        d = state.to_dict()
        assert d["reviewerModels"] == ["Model A", "Model B"]
        assert d["bossModel"] == "Model A"

    def test_to_dict_omits_none_reviewer_models(self):
        """to_dict omits reviewerModels and bossModel when None."""
        state = _make_review_state()
        d = state.to_dict()
        assert "reviewerModels" not in d
        assert "bossModel" not in d

    def test_from_dict_with_reviewer_models(self):
        """from_dict correctly reads reviewerModels and bossModel."""
        data = {
            "prId": 12345,
            "repoId": "repo-guid",
            "repoName": "test-repo",
            "project": "TestProject",
            "organization": "https://dev.azure.com/testorg",
            "latestIterationId": 1,
            "scaffoldedUtc": "2026-01-01T00:00:00Z",
            "overallSummary": {"threadId": 1, "commentId": 1},
            "reviewerModels": ["Claude Opus 4.6", "Gemini Pro 3.1"],
            "bossModel": "Claude Opus 4.6",
        }
        state = ReviewState.from_dict(data)
        assert state.reviewerModels == ["Claude Opus 4.6", "Gemini Pro 3.1"]
        assert state.bossModel == "Claude Opus 4.6"

    def test_from_dict_without_reviewer_models(self):
        """Backward compatibility: missing reviewerModels defaults to None."""
        data = {
            "prId": 12345,
            "repoId": "repo-guid",
            "repoName": "test-repo",
            "project": "TestProject",
            "organization": "https://dev.azure.com/testorg",
            "latestIterationId": 1,
            "scaffoldedUtc": "2026-01-01T00:00:00Z",
            "overallSummary": {"threadId": 1, "commentId": 1},
        }
        state = ReviewState.from_dict(data)
        assert state.reviewerModels is None
        assert state.bossModel is None

    def test_roundtrip(self):
        """Serialize/deserialize roundtrip preserves multi-model fields."""
        state = _make_review_state(
            reviewerModels=["A", "B", "C"],
            bossModel="A",
        )
        restored = ReviewState.from_dict(state.to_dict())
        assert restored.reviewerModels == ["A", "B", "C"]
        assert restored.bossModel == "A"
