"""Tests for _try_recover_state_from_pr_threads cross-identity tagging."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
from agentic_devtools.cli.azure_devops.review_scaffold import _try_recover_state_from_pr_threads
from agentic_devtools.cli.azure_devops.review_state import ReviewState

_ORG = "https://dev.azure.com/testorg"
_PROJECT = "TestProject"
_REPO = "test-repo"
_REPO_ID = "repo-guid"
_PR_ID = 12345


def _make_config():
    return AzureDevOpsConfig(organization=_ORG, project=_PROJECT, repository=_REPO)


def _make_agdt_thread(thread_id, marker_type, file_path=None, comment_id=1, author_id="other-user-guid"):
    """Create a mock ADO thread with an agdt marker and author."""
    if marker_type == "file-summary":
        marker = f"<!-- agdt-review:v1 type:file-summary file:{file_path} pr:{_PR_ID} -->"
    elif marker_type == "overall-summary":
        marker = f"<!-- agdt-review:v1 type:overall-summary pr:{_PR_ID} -->"
    elif marker_type == "activity-log":
        marker = f"<!-- agdt-review:v1 type:activity-log pr:{_PR_ID} -->"
    else:
        marker = f"<!-- agdt-review:v1 type:{marker_type} pr:{_PR_ID} -->"

    return {
        "id": thread_id,
        "status": "closed",
        "comments": [
            {
                "id": comment_id,
                "content": f"{marker}\n## Content",
                "author": {"id": author_id, "uniqueName": f"{author_id}@org.com"},
            }
        ],
    }


class TestRecoverCrossIdentityTagging:
    """Tests for cross-identity tagging during recovery."""

    @patch("agentic_devtools.cli.azure_devops.review_scaffold._resolve_scaffold_threads")
    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_tags_cross_identity_when_different_author(self, save_mock, resolve_mock):
        """FileEntry.crossIdentity=True when thread author differs from current identity."""
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "value": [
                _make_agdt_thread(200, "file-summary", "/src/a.ts", comment_id=201, author_id="other-user"),
                _make_agdt_thread(400, "overall-summary", comment_id=401, author_id="other-user"),
                _make_agdt_thread(500, "activity-log", comment_id=501, author_id="other-user"),
            ]
        }
        requests_mock.get.return_value = resp
        # Activity log reply succeeds
        reply_resp = MagicMock()
        reply_resp.raise_for_status = MagicMock()
        reply_resp.json.return_value = {"id": 502}
        requests_mock.post.return_value = reply_resp

        with patch(
            "agentic_devtools.cli.azure_devops.finalization.identity.resolve_pat_identity_snapshot",
            return_value={"id": "current-user", "uniqueName": "current@org.com", "displayName": "Current User"},
        ):
            result = _try_recover_state_from_pr_threads(
                pull_request_id=_PR_ID,
                files=["/src/a.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=5,
                requests_module=requests_mock,
                headers={},
                commit_hash="abc123def",
                model_id="gpt-5",
            )

        assert result is not None
        assert isinstance(result, ReviewState)
        assert result.files["/src/a.ts"].crossIdentity is True

    @patch("agentic_devtools.cli.azure_devops.review_scaffold._resolve_scaffold_threads")
    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_no_tag_when_same_identity(self, save_mock, resolve_mock):
        """FileEntry.crossIdentity=False when thread author is current identity."""
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "value": [
                _make_agdt_thread(200, "file-summary", "/src/a.ts", comment_id=201, author_id="current-user"),
                _make_agdt_thread(400, "overall-summary", comment_id=401, author_id="current-user"),
                _make_agdt_thread(500, "activity-log", comment_id=501, author_id="current-user"),
            ]
        }
        requests_mock.get.return_value = resp
        reply_resp = MagicMock()
        reply_resp.raise_for_status = MagicMock()
        reply_resp.json.return_value = {"id": 502}
        requests_mock.post.return_value = reply_resp

        with patch(
            "agentic_devtools.cli.azure_devops.finalization.identity.resolve_pat_identity_snapshot",
            return_value={"id": "current-user", "uniqueName": "current@org.com", "displayName": "Current User"},
        ):
            result = _try_recover_state_from_pr_threads(
                pull_request_id=_PR_ID,
                files=["/src/a.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=5,
                requests_module=requests_mock,
                headers={},
                commit_hash="abc123def",
                model_id="gpt-5",
            )

        assert result is not None
        assert result.files["/src/a.ts"].crossIdentity is False

    @patch("agentic_devtools.cli.azure_devops.review_scaffold._resolve_scaffold_threads")
    @patch("agentic_devtools.cli.azure_devops.review_scaffold.save_review_state")
    def test_no_tag_when_identity_fetch_fails(self, save_mock, resolve_mock):
        """crossIdentity=False when identity resolution fails (graceful degradation)."""
        requests_mock = MagicMock()
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "value": [
                _make_agdt_thread(200, "file-summary", "/src/a.ts", comment_id=201, author_id="other-user"),
                _make_agdt_thread(400, "overall-summary", comment_id=401, author_id="other-user"),
                _make_agdt_thread(500, "activity-log", comment_id=501, author_id="other-user"),
            ]
        }
        requests_mock.get.return_value = resp
        reply_resp = MagicMock()
        reply_resp.raise_for_status = MagicMock()
        reply_resp.json.return_value = {"id": 502}
        requests_mock.post.return_value = reply_resp

        with patch(
            "agentic_devtools.cli.azure_devops.finalization.identity.resolve_pat_identity_snapshot",
            return_value=None,
        ):
            result = _try_recover_state_from_pr_threads(
                pull_request_id=_PR_ID,
                files=["/src/a.ts"],
                config=_make_config(),
                repo_id=_REPO_ID,
                repo_name=_REPO,
                latest_iteration_id=5,
                requests_module=requests_mock,
                headers={},
                commit_hash="abc123def",
                model_id="gpt-5",
            )

        assert result is not None
        # When identity resolution fails, crossIdentity defaults to False
        assert result.files["/src/a.ts"].crossIdentity is False
