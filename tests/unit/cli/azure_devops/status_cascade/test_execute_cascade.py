"""Tests for execute_cascade function."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
from agentic_devtools.cli.azure_devops.status_cascade import (
    PatchOperation,
    execute_cascade,
)


def _make_config() -> AzureDevOpsConfig:
    return AzureDevOpsConfig(
        organization="https://dev.azure.com/org",
        project="proj",
        repository="repo",
    )


def _make_op(thread_id: int = 10, comment_id: int = 20, status: str = "active") -> PatchOperation:
    return PatchOperation(
        thread_id=thread_id,
        comment_id=comment_id,
        new_content=f"Content for thread {thread_id}",
        thread_status=status,
    )


class TestExecuteCascade:
    """Tests for execute_cascade function."""

    def test_empty_list_makes_no_calls(self, mock_azure_devops_env):
        """Empty patch_operations list → no API calls."""
        mock_requests = MagicMock()

        execute_cascade(
            patch_operations=[],
            requests_module=mock_requests,
            headers={},
            config=_make_config(),
            repo_id="repo-123",
            pull_request_id=42,
        )

        mock_requests.patch.assert_not_called()

    def test_calls_patch_comment_for_each_operation(self, mock_azure_devops_env):
        """Should call patch_comment once per PatchOperation."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_requests.patch.return_value = mock_response

        ops = [_make_op(10, 20), _make_op(30, 40)]

        execute_cascade(
            patch_operations=ops,
            requests_module=mock_requests,
            headers={},
            config=_make_config(),
            repo_id="repo-123",
            pull_request_id=42,
        )

        # 2 ops × 2 calls (patch_comment + patch_thread_status) = 4 total
        assert mock_requests.patch.call_count == 4

    def test_calls_patch_comment_with_correct_content(self, mock_azure_devops_env):
        """patch_comment should be called with the operation's new_content."""
        mock_requests = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_requests.patch.return_value = mock_response

        op = PatchOperation(thread_id=10, comment_id=20, new_content="Updated markdown", thread_status="closed")

        with patch("agentic_devtools.cli.azure_devops.status_cascade.patch_comment") as mock_patch_comment, patch(
            "agentic_devtools.cli.azure_devops.status_cascade.patch_thread_status"
        ) as mock_patch_thread:
            mock_patch_comment.return_value = {}
            mock_patch_thread.return_value = {}

            execute_cascade(
                patch_operations=[op],
                requests_module=mock_requests,
                headers={"Authorization": "Basic test"},
                config=_make_config(),
                repo_id="repo-123",
                pull_request_id=42,
            )

            mock_patch_comment.assert_called_once_with(
                requests_module=mock_requests,
                headers={"Authorization": "Basic test"},
                config=_make_config(),
                repo_id="repo-123",
                pull_request_id=42,
                thread_id=10,
                comment_id=20,
                new_content="Updated markdown",
                dry_run=False,
            )

    def test_calls_patch_thread_status_with_correct_status(self, mock_azure_devops_env):
        """patch_thread_status should be called with the operation's thread_status."""
        mock_requests = MagicMock()

        op = PatchOperation(thread_id=10, comment_id=20, new_content="content", thread_status="closed")

        with patch("agentic_devtools.cli.azure_devops.status_cascade.patch_comment") as mock_patch_comment, patch(
            "agentic_devtools.cli.azure_devops.status_cascade.patch_thread_status"
        ) as mock_patch_thread:
            mock_patch_comment.return_value = {}
            mock_patch_thread.return_value = {}

            execute_cascade(
                patch_operations=[op],
                requests_module=mock_requests,
                headers={},
                config=_make_config(),
                repo_id="repo-123",
                pull_request_id=42,
            )

            mock_patch_thread.assert_called_once_with(
                requests_module=mock_requests,
                headers={},
                config=_make_config(),
                repo_id="repo-123",
                pull_request_id=42,
                thread_id=10,
                status="closed",
                dry_run=False,
            )

    def test_patch_comment_called_before_patch_thread_status(self, mock_azure_devops_env):
        """patch_comment should be called before patch_thread_status for each op."""
        call_order = []

        with patch("agentic_devtools.cli.azure_devops.status_cascade.patch_comment") as mock_pc, patch(
            "agentic_devtools.cli.azure_devops.status_cascade.patch_thread_status"
        ) as mock_pts:
            mock_pc.side_effect = lambda **kwargs: call_order.append("comment")
            mock_pts.side_effect = lambda **kwargs: call_order.append("thread")

            execute_cascade(
                patch_operations=[_make_op()],
                requests_module=MagicMock(),
                headers={},
                config=_make_config(),
                repo_id="repo-123",
                pull_request_id=42,
            )

        assert call_order == ["comment", "thread"]

    def test_passes_dry_run_true_to_patch_functions(self, mock_azure_devops_env):
        """dry_run=True should be forwarded to both patch functions."""
        with patch("agentic_devtools.cli.azure_devops.status_cascade.patch_comment") as mock_pc, patch(
            "agentic_devtools.cli.azure_devops.status_cascade.patch_thread_status"
        ) as mock_pts:
            mock_pc.return_value = {}
            mock_pts.return_value = {}

            execute_cascade(
                patch_operations=[_make_op()],
                requests_module=MagicMock(),
                headers={},
                config=_make_config(),
                repo_id="repo-123",
                pull_request_id=42,
                dry_run=True,
            )

            assert mock_pc.call_args.kwargs["dry_run"] is True
            assert mock_pts.call_args.kwargs["dry_run"] is True

    def test_processes_multiple_operations_in_order(self, mock_azure_devops_env):
        """All operations in the list should be processed in order."""
        thread_ids_seen = []

        with patch("agentic_devtools.cli.azure_devops.status_cascade.patch_comment") as mock_pc, patch(
            "agentic_devtools.cli.azure_devops.status_cascade.patch_thread_status"
        ) as mock_pts:
            mock_pc.side_effect = lambda **kwargs: thread_ids_seen.append(("comment", kwargs["thread_id"]))
            mock_pts.side_effect = lambda **kwargs: thread_ids_seen.append(("thread", kwargs["thread_id"]))

            execute_cascade(
                patch_operations=[_make_op(10, 20), _make_op(30, 40)],
                requests_module=MagicMock(),
                headers={},
                config=_make_config(),
                repo_id="repo-123",
                pull_request_id=42,
            )

        assert thread_ids_seen == [
            ("comment", 10),
            ("thread", 10),
            ("comment", 30),
            ("thread", 30),
        ]

    def test_dry_run_default_is_false(self, mock_azure_devops_env):
        """dry_run defaults to False."""
        with patch("agentic_devtools.cli.azure_devops.status_cascade.patch_comment") as mock_pc, patch(
            "agentic_devtools.cli.azure_devops.status_cascade.patch_thread_status"
        ) as mock_pts:
            mock_pc.return_value = {}
            mock_pts.return_value = {}

            execute_cascade(
                patch_operations=[_make_op()],
                requests_module=MagicMock(),
                headers={},
                config=_make_config(),
                repo_id="repo-123",
                pull_request_id=42,
            )

            assert mock_pc.call_args.kwargs["dry_run"] is False
