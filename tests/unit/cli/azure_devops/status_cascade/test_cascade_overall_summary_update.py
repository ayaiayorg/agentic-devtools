"""Tests for cascade_overall_summary_update function."""

from unittest.mock import patch

from agentic_devtools.cli.azure_devops.review_state import (
    FileEntry,
    FolderGroup,
    OverallSummary,
    ReviewSession,
    ReviewState,
)
from agentic_devtools.cli.azure_devops.status_cascade import (
    PatchOperation,
    cascade_overall_summary_update,
)

_BASE_URL = "https://dev.azure.com/org/proj/_git/repo/pullrequest/100"


def _make_state(file_statuses: dict[str, str]) -> ReviewState:
    """Build a ReviewState with files at the given statuses.

    Each key is a file name (e.g. "src/a.py") and is placed in a folder
    derived from the first path component.
    """
    files = {}
    folder_files: dict[str, list[str]] = {}
    for i, (fname, status) in enumerate(file_statuses.items()):
        path = f"/{fname}"
        folder_name = fname.split("/")[0] if "/" in fname else "root"
        files[path] = FileEntry(
            threadId=10 + i,
            commentId=20 + i,
            folder=folder_name,
            fileName=fname.split("/")[-1],
            status=status,
        )
        folder_files.setdefault(folder_name, []).append(path)

    folders = {name: FolderGroup(files=fps) for name, fps in folder_files.items()}
    return ReviewState(
        prId=100,
        repoId="repo-guid",
        repoName="repo",
        project="proj",
        organization="https://dev.azure.com/org",
        latestIterationId=1,
        scaffoldedUtc="2026-01-01T00:00:00Z",
        overallSummary=OverallSummary(threadId=1, commentId=2),
        folders=folders,
        files=files,
    )


class TestCascadeOverallSummaryUpdate:
    """Tests for cascade_overall_summary_update function."""

    def test_returns_list_of_patch_operations(self):
        """Should return a list of PatchOperation objects."""
        state = _make_state({"src/a.py": "approved"})

        result = cascade_overall_summary_update(state, _BASE_URL)

        assert isinstance(result, list)
        assert all(isinstance(op, PatchOperation) for op in result)

    def test_returns_one_operation(self):
        """Should return exactly one PatchOperation (overall summary)."""
        state = _make_state({"src/a.py": "approved"})

        result = cascade_overall_summary_update(state, _BASE_URL)

        assert len(result) == 1

    def test_targets_overall_thread(self):
        """PatchOperation should target the overall summary thread."""
        state = _make_state({"src/a.py": "approved"})
        overall_thread_id = state.overallSummary.threadId
        overall_comment_id = state.overallSummary.commentId

        result = cascade_overall_summary_update(state, _BASE_URL)

        assert result[0].thread_id == overall_thread_id
        assert result[0].comment_id == overall_comment_id

    def test_updates_overall_status_in_state(self):
        """Should update the overall summary status in the state object."""
        state = _make_state({"src/a.py": "approved", "tests/b.py": "needs-work"})

        cascade_overall_summary_update(state, _BASE_URL)

        assert state.overallSummary.status == "needs-work"

    def test_approved_overall_gets_closed_thread_status(self):
        """All files approved → thread_status 'closed'."""
        state = _make_state({"src/a.py": "approved", "tests/b.py": "approved"})

        result = cascade_overall_summary_update(state, _BASE_URL)

        assert result[0].thread_status == "closed"

    def test_needs_work_overall_gets_active_thread_status(self):
        """Any file needs-work → thread_status 'active'."""
        state = _make_state({"src/a.py": "approved", "tests/b.py": "needs-work"})

        result = cascade_overall_summary_update(state, _BASE_URL)

        assert result[0].thread_status == "active"

    def test_content_contains_overall_pr_review_summary(self):
        """Rendered content should include the overall summary header."""
        state = _make_state({"src/a.py": "approved"})

        result = cascade_overall_summary_update(state, _BASE_URL)

        assert "Overall PR Review Summary" in result[0].new_content

    def test_no_file_path_required(self):
        """Should work without any file_path argument (unlike cascade_status_update)."""
        state = _make_state({"src/a.py": "approved", "src/b.py": "needs-work"})

        # Should not raise KeyError
        result = cascade_overall_summary_update(state, _BASE_URL)

        assert len(result) == 1
        assert state.overallSummary.status == "needs-work"

    def test_unreviewed_overall_gets_active_thread_status(self):
        """All files unreviewed → thread_status 'active'."""
        state = _make_state({"src/a.py": "unreviewed", "tests/b.py": "unreviewed"})

        result = cascade_overall_summary_update(state, _BASE_URL)

        assert result[0].thread_status == "active"
        assert state.overallSummary.status == "unreviewed"

    def test_in_progress_overall_gets_active_thread_status(self):
        """Mixed reviewed/unreviewed files → in-progress → thread_status 'active'."""
        state = _make_state({"src/a.py": "approved", "tests/b.py": "unreviewed"})

        result = cascade_overall_summary_update(state, _BASE_URL)

        assert result[0].thread_status == "active"
        assert state.overallSummary.status == "in-progress"


class TestCascadeOverallSummaryUpdateAttributionDerivation:
    """Tests for auto-derivation of attribution params from ReviewState in cascade_overall_summary_update."""

    def _make_state_with_sessions(self, model_id: str = "claude-opus-4", commit_hash: str = "abc1234") -> ReviewState:
        """Build a ReviewState with a session and commit hash."""
        state = _make_state({"src/a.py": "approved"})
        state.commitHash = commit_hash
        state.latestIterationId = 3
        state.sessions = [
            ReviewSession(
                sessionId="sess-1",
                modelId=model_id,
                startedUtc="2026-01-01T00:00:00Z",
            )
        ]
        return state

    def test_derives_model_name_from_sessions_when_not_passed(self):
        """Should auto-derive model_name from state.sessions[-1].modelId."""
        state = self._make_state_with_sessions(model_id="gpt-4o")

        result = cascade_overall_summary_update(state, _BASE_URL)

        # Attribution line should appear in rendered content
        assert "gpt-4o" in result[0].new_content

    def test_derives_model_name_from_state_modelid_when_no_sessions(self):
        """Should fall back to state.modelId when sessions list is empty."""
        state = _make_state({"src/a.py": "approved"})
        state.modelId = "my-fallback-model"
        state.commitHash = "abc123xyz"  # must be set for attribution line to render
        state.latestIterationId = 1
        state.sessions = []

        result = cascade_overall_summary_update(state, _BASE_URL)

        assert "my-fallback-model" in result[0].new_content

    def test_derives_commit_hash_from_state(self):
        """Should auto-derive commit_hash from state.commitHash."""
        state = self._make_state_with_sessions(commit_hash="deadbeef12345")

        result = cascade_overall_summary_update(state, _BASE_URL)

        # Attribution line shows truncated 7-char short hash
        assert "deadbee" in result[0].new_content

    def test_derives_commit_url_from_state(self):
        """Should build commit_url via build_commit_pr_url when commit_hash and iteration are set."""
        state = self._make_state_with_sessions()
        mock_url = "https://example.com/pr-url"

        with patch(
            "agentic_devtools.cli.azure_devops.review_attribution.build_commit_pr_url",
            return_value=mock_url,
        ):
            result = cascade_overall_summary_update(state, _BASE_URL)

        assert mock_url in result[0].new_content

    def test_no_commit_url_when_no_commit_hash(self):
        """Should not build commit_url when commitHash is None."""
        state = _make_state({"src/a.py": "approved"})
        state.commitHash = None
        state.sessions = []

        # Should not raise; commit_url remains None
        result = cascade_overall_summary_update(state, _BASE_URL)

        assert len(result) == 1

    def test_no_commit_url_when_iteration_zero(self):
        """Should not build commit_url when latestIterationId is 0."""
        state = _make_state({"src/a.py": "approved"})
        state.commitHash = "abc123"
        state.latestIterationId = 0

        result = cascade_overall_summary_update(state, _BASE_URL)

        assert len(result) == 1

    def test_explicit_params_override_state_derivation(self):
        """Explicit model_name / commit_hash / commit_url params override auto-derivation."""
        state = self._make_state_with_sessions(model_id="state-model")

        result = cascade_overall_summary_update(
            state, _BASE_URL, model_name="explicit-model", commit_hash="explicit123"
        )

        assert "explicit-model" in result[0].new_content
        assert "state-model" not in result[0].new_content

    def test_build_commit_url_exception_is_suppressed(self):
        """Errors from build_commit_pr_url should be swallowed; commit_url stays None."""
        state = self._make_state_with_sessions()

        with patch(
            "agentic_devtools.cli.azure_devops.review_attribution.build_commit_pr_url",
            side_effect=RuntimeError("network error"),
        ):
            # Should not raise
            result = cascade_overall_summary_update(state, _BASE_URL)

        assert len(result) == 1
