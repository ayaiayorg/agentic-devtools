"""Tests for _get_attribution_params helper function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.file_review_commands import _get_attribution_params
from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewSession,
    ReviewState,
)

_ORG = "https://dev.azure.com/myorg"
_PROJECT = "myproject"
_REPO = "myrepo"
_PR_ID = 42
_ITERATION = 3
_COMMIT = "abcdef1234567890"


def _make_config(org=_ORG, project=_PROJECT, repo=_REPO):
    """Build a mock AzureDevOpsConfig."""
    cfg = MagicMock()
    cfg.organization = org
    cfg.project = project
    cfg.repository = repo
    return cfg


def _make_review_state(
    sessions=None,
    commit_hash=None,
    latest_iteration_id=_ITERATION,
) -> ReviewState:
    """Build a minimal ReviewState with optional sessions and commitHash."""
    return ReviewState(
        prId=_PR_ID,
        repoId="repo-guid",
        repoName=_REPO,
        project=_PROJECT,
        organization=_ORG,
        latestIterationId=latest_iteration_id,
        scaffoldedUtc="2026-01-01T00:00:00Z",
        overallSummary=OverallSummary(threadId=1, commentId=2),
        sessions=sessions or [],
        commitHash=commit_hash,
        files={
            "/src/app.py": FileEntry(
                threadId=10,
                commentId=20,
                folder="src",
                fileName="app.py",
            )
        },
        folders={"src": FolderGroup(files=["/src/app.py"])},
    )


def _make_session(model_id: str = "claude-opus-4") -> ReviewSession:
    return ReviewSession(
        sessionId="sess-001",
        modelId=model_id,
        startedUtc="2026-01-01T00:00:00Z",
    )


class TestGetAttributionParams:
    """Tests for _get_attribution_params helper."""

    def test_returns_dict_with_expected_keys(self):
        """Should return dict with model_name, commit_hash, commit_url keys."""
        state = _make_review_state()
        config = _make_config()
        result = _get_attribution_params(state, config)
        assert set(result.keys()) == {"model_name", "commit_hash", "commit_url"}

    def test_model_name_from_last_session(self):
        """Should extract modelId from the most recent session."""
        sessions = [_make_session("claude-opus-4"), _make_session("gpt-4o")]
        state = _make_review_state(sessions=sessions)
        config = _make_config()
        result = _get_attribution_params(state, config)
        assert result["model_name"] == "gpt-4o"

    def test_model_name_none_when_no_sessions(self):
        """Should return model_name=None when sessions list is empty."""
        state = _make_review_state(sessions=[])
        config = _make_config()
        result = _get_attribution_params(state, config)
        assert result["model_name"] is None

    def test_commit_hash_from_state(self):
        """Should return commitHash from review state."""
        state = _make_review_state(commit_hash=_COMMIT)
        config = _make_config()
        result = _get_attribution_params(state, config)
        assert result["commit_hash"] == _COMMIT

    def test_commit_hash_none_when_not_set(self):
        """Should return commit_hash=None when ReviewState.commitHash is None."""
        state = _make_review_state(commit_hash=None)
        config = _make_config()
        result = _get_attribution_params(state, config)
        assert result["commit_hash"] is None

    def test_commit_url_none_when_no_commit_hash(self):
        """Should return commit_url=None when commitHash is absent."""
        state = _make_review_state(commit_hash=None, latest_iteration_id=_ITERATION)
        config = _make_config()
        result = _get_attribution_params(state, config)
        assert result["commit_url"] is None

    def test_commit_url_none_when_iteration_is_zero(self):
        """Should return commit_url=None when latestIterationId is 0."""
        state = _make_review_state(commit_hash=_COMMIT, latest_iteration_id=0)
        config = _make_config()
        result = _get_attribution_params(state, config)
        assert result["commit_url"] is None

    def test_commit_url_pr_level_when_no_file_path(self):
        """Should build a PR-level URL when file_path is not provided."""
        state = _make_review_state(commit_hash=_COMMIT)
        config = _make_config()
        mock_pr_url = "https://dev.azure.com/myorg/myproject/_git/myrepo/pullrequest/42?_a=files&base=2&iteration=3"
        with patch(
            "agentic_devtools.cli.azure_devops.review_attribution.build_commit_pr_url",
            return_value=mock_pr_url,
        ) as mock_fn:
            result = _get_attribution_params(state, config)

        mock_fn.assert_called_once_with(_ORG, _PROJECT, _REPO, _PR_ID, _ITERATION)
        assert result["commit_url"] == mock_pr_url

    def test_commit_url_file_level_when_file_path_provided(self):
        """Should build a file-scoped URL when file_path is provided."""
        state = _make_review_state(commit_hash=_COMMIT)
        config = _make_config()
        mock_file_url = (
            "https://dev.azure.com/myorg/myproject/_git/myrepo/pullrequest/42"
            "?_a=files&base=2&iteration=3&path=/src/app.py"
        )
        with patch(
            "agentic_devtools.cli.azure_devops.review_attribution.build_commit_file_url",
            return_value=mock_file_url,
        ) as mock_fn:
            result = _get_attribution_params(state, config, file_path="/src/app.py")

        mock_fn.assert_called_once_with(_ORG, _PROJECT, _REPO, _PR_ID, "/src/app.py", _ITERATION)
        assert result["commit_url"] == mock_file_url

    def test_full_attribution_with_session_and_commit(self):
        """Should return fully populated dict when all data is present."""
        sessions = [_make_session("claude-opus-4")]
        state = _make_review_state(sessions=sessions, commit_hash=_COMMIT)
        config = _make_config()
        with patch(
            "agentic_devtools.cli.azure_devops.review_attribution.build_commit_pr_url",
            return_value="https://example.com/pr",
        ):
            result = _get_attribution_params(state, config)

        assert result["model_name"] == "claude-opus-4"
        assert result["commit_hash"] == _COMMIT
        assert result["commit_url"] == "https://example.com/pr"

    def test_commit_url_none_on_url_build_exception_pr_level(self):
        """Should fall back to commit_url=None when build_commit_pr_url raises."""
        state = _make_review_state(commit_hash=_COMMIT)
        config = _make_config()
        with patch(
            "agentic_devtools.cli.azure_devops.review_attribution.build_commit_pr_url",
            side_effect=Exception("URL build failed"),
        ):
            result = _get_attribution_params(state, config)

        assert result["commit_url"] is None
        assert result["commit_hash"] == _COMMIT  # hash still propagated

    def test_commit_url_none_on_url_build_exception_file_level(self):
        """Should fall back to commit_url=None when build_commit_file_url raises."""
        state = _make_review_state(commit_hash=_COMMIT)
        config = _make_config()
        with patch(
            "agentic_devtools.cli.azure_devops.review_attribution.build_commit_file_url",
            side_effect=Exception("URL build failed"),
        ):
            result = _get_attribution_params(state, config, file_path="/src/app.py")

        assert result["commit_url"] is None
        assert result["commit_hash"] == _COMMIT  # hash still propagated

    def test_model_name_falls_back_to_state_model_id_when_sessions_empty(self):
        """Should return ReviewState.modelId when sessions list is empty but modelId is set."""
        state = _make_review_state(sessions=[])
        # Manually set modelId on the state (the field is Optional[str] = None by default)
        state.modelId = "claude-opus-4"
        config = _make_config()
        result = _get_attribution_params(state, config)
        assert result["model_name"] == "claude-opus-4"
