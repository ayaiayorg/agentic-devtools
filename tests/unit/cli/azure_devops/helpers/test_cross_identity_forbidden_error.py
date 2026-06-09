"""Tests for CrossIdentityForbiddenError and patch_comment 403 handling."""

from unittest.mock import MagicMock

import pytest

from agentic_devtools.cli.azure_devops.config import AzureDevOpsConfig
from agentic_devtools.cli.azure_devops.helpers import CrossIdentityForbiddenError, patch_comment


class TestCrossIdentityForbiddenError:
    """Tests for CrossIdentityForbiddenError exception class."""

    def test_is_exception(self):
        """Should be an Exception subclass."""
        err = CrossIdentityForbiddenError(10, 5)
        assert isinstance(err, Exception)

    def test_stores_thread_and_comment_id(self):
        """Should store thread_id and comment_id."""
        err = CrossIdentityForbiddenError(10, 5)
        assert err.thread_id == 10
        assert err.comment_id == 5

    def test_default_message(self):
        """Should produce a meaningful default message."""
        err = CrossIdentityForbiddenError(10, 5)
        assert "403" in str(err)
        assert "10" in str(err)
        assert "5" in str(err)

    def test_custom_message(self):
        """Should accept a custom message."""
        err = CrossIdentityForbiddenError(10, 5, "custom msg")
        assert str(err) == "custom msg"


class TestPatchComment403:
    """Tests for patch_comment catching 403 and raising CrossIdentityForbiddenError."""

    def _make_config(self) -> AzureDevOpsConfig:
        return AzureDevOpsConfig(
            organization="https://dev.azure.com/myorg",
            project="MyProject",
            repository="MyRepo",
        )

    def test_raises_cross_identity_forbidden_on_403(self):
        """Should raise CrossIdentityForbiddenError when response is 403."""
        mock_requests = MagicMock()
        error_response = MagicMock()
        error_response.status_code = 403
        mock_requests.patch.return_value = error_response

        config = self._make_config()

        with pytest.raises(CrossIdentityForbiddenError) as exc_info:
            patch_comment(
                requests_module=mock_requests,
                headers={},
                config=config,
                repo_id="repo-123",
                pull_request_id=42,
                thread_id=7,
                comment_id=1,
                new_content="content",
            )

        assert exc_info.value.thread_id == 7
        assert exc_info.value.comment_id == 1

    def test_403_does_not_retry(self):
        """Should not retry on 403 (unlike 429)."""
        mock_requests = MagicMock()
        error_response = MagicMock()
        error_response.status_code = 403
        mock_requests.patch.return_value = error_response

        config = self._make_config()

        with pytest.raises(CrossIdentityForbiddenError):
            patch_comment(
                requests_module=mock_requests,
                headers={},
                config=config,
                repo_id="repo-123",
                pull_request_id=42,
                thread_id=7,
                comment_id=1,
                new_content="content",
            )

        assert mock_requests.patch.call_count == 1

    def test_success_does_not_raise(self):
        """Should succeed normally when status is 200."""
        mock_requests = MagicMock()
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"id": 1}
        mock_requests.patch.return_value = success_response

        config = self._make_config()

        result = patch_comment(
            requests_module=mock_requests,
            headers={},
            config=config,
            repo_id="repo-123",
            pull_request_id=42,
            thread_id=7,
            comment_id=1,
            new_content="content",
        )

        assert result == {"id": 1}
