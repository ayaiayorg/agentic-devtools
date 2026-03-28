"""Tests for agentic_devtools.submission_processor._get_attribution_params."""

from unittest.mock import patch

from agentic_devtools.submission_processor import _get_attribution_params

from .conftest import make_review_state, make_session


class TestGetAttributionParams:
    """Tests for the _get_attribution_params helper."""

    def test_uses_session_model_id_when_available(self, config):
        """When sessions are populated, modelId comes from the last session."""
        session = make_session(model_id="gpt-4")
        state = make_review_state(sessions=[session], model_id="fallback-model")

        result = _get_attribution_params(state, config)

        assert result["model_name"] == "gpt-4"

    def test_falls_back_to_state_model_id(self, config):
        """When no sessions, falls back to modelId attribute."""
        state = make_review_state(sessions=[], model_id="fallback-model")

        result = _get_attribution_params(state, config)

        assert result["model_name"] == "fallback-model"

    def test_none_model_when_both_absent(self, config):
        """When no sessions and no modelId, model_name is None."""
        state = make_review_state(sessions=[], model_id=None)

        result = _get_attribution_params(state, config)

        assert result["model_name"] is None

    @patch("agentic_devtools.submission_processor.build_commit_file_url", return_value="https://file-url")
    def test_file_path_builds_file_url(self, mock_build, config):
        """When file_path is provided, builds a file-level commit URL."""
        state = make_review_state(commit_hash="abc123")

        result = _get_attribution_params(state, config, file_path="/src/app.ts")

        assert result["commit_url"] == "https://file-url"
        mock_build.assert_called_once()

    @patch("agentic_devtools.submission_processor.build_commit_pr_url", return_value="https://pr-url")
    def test_no_file_path_builds_pr_url(self, mock_build, config):
        """When file_path is omitted, builds a PR-level commit URL."""
        state = make_review_state(commit_hash="abc123")

        result = _get_attribution_params(state, config)

        assert result["commit_url"] == "https://pr-url"
        mock_build.assert_called_once()

    def test_no_commit_hash_skips_url(self, config):
        """When commit_hash is None, commit_url is None."""
        state = make_review_state(commit_hash=None)

        result = _get_attribution_params(state, config)

        assert result["commit_url"] is None

    @patch("agentic_devtools.submission_processor.build_commit_pr_url", side_effect=Exception("url error"))
    def test_url_build_exception_returns_none(self, mock_build, config):
        """Exception during URL building is caught and commit_url becomes None."""
        state = make_review_state(commit_hash="abc123")

        result = _get_attribution_params(state, config)

        assert result["commit_url"] is None
        assert result["commit_hash"] == "abc123"

    def test_returns_all_expected_keys(self, config):
        """Result dict always contains model_name, commit_hash, and commit_url."""
        state = make_review_state()

        result = _get_attribution_params(state, config)

        assert set(result.keys()) == {"model_name", "commit_hash", "commit_url"}
