"""Tests for agentic_devtools.submission_manager_instance.get_submission_manager."""

from unittest.mock import MagicMock, patch

import agentic_devtools.submission_manager_instance as smi_module
from agentic_devtools.submission_manager import SubmissionManager

# Patch targets for lazy imports inside get_submission_manager()
_PATCH_CONFIG = "agentic_devtools.cli.azure_devops.config.AzureDevOpsConfig.from_state"
_PATCH_GET_PAT = "agentic_devtools.cli.azure_devops.auth.get_pat"
_PATCH_GET_AUTH = "agentic_devtools.cli.azure_devops.auth.get_auth_headers"
_PATCH_GET_REPO_ID = "agentic_devtools.cli.azure_devops.helpers.get_repository_id"
_PATCH_CREATE_PROC = "agentic_devtools.submission_processor.create_review_processor"


class TestGetSubmissionManager:
    """Tests for the get_submission_manager lazy singleton."""

    def teardown_method(self):
        """Reset the singleton after each test."""
        smi_module._manager = None

    @patch(_PATCH_GET_REPO_ID, return_value="repo-id-123")
    @patch(_PATCH_GET_PAT, return_value="fake-pat")
    @patch(_PATCH_GET_AUTH, return_value={"Authorization": "Basic abc"})
    @patch(_PATCH_CONFIG)
    @patch(_PATCH_CREATE_PROC)
    def test_returns_submission_manager_instance(
        self,
        mock_create_processor,
        mock_config,
        mock_auth_headers,
        mock_pat,
        mock_repo_id,
    ):
        """get_submission_manager() should return a SubmissionManager instance."""
        mock_create_processor.return_value = MagicMock()
        mock_config.return_value = MagicMock(organization="org", project="proj", repository="repo")

        manager = smi_module.get_submission_manager()

        assert isinstance(manager, SubmissionManager)
        manager.shutdown(wait=True)

    @patch(_PATCH_GET_REPO_ID, return_value="repo-id-123")
    @patch(_PATCH_GET_PAT, return_value="fake-pat")
    @patch(_PATCH_GET_AUTH, return_value={"Authorization": "Basic abc"})
    @patch(_PATCH_CONFIG)
    @patch(_PATCH_CREATE_PROC)
    def test_singleton_returns_same_instance(
        self,
        mock_create_processor,
        mock_config,
        mock_auth_headers,
        mock_pat,
        mock_repo_id,
    ):
        """Calling get_submission_manager() twice should return the same instance."""
        mock_create_processor.return_value = MagicMock()
        mock_config.return_value = MagicMock(organization="org", project="proj", repository="repo")

        first = smi_module.get_submission_manager()
        second = smi_module.get_submission_manager()

        assert first is second
        first.shutdown(wait=True)

    @patch(_PATCH_GET_REPO_ID, return_value="repo-id-123")
    @patch(_PATCH_GET_PAT, return_value="fake-pat")
    @patch(_PATCH_GET_AUTH, return_value={"Authorization": "Basic abc"})
    @patch(_PATCH_CONFIG)
    @patch(_PATCH_CREATE_PROC)
    def test_wires_processor_from_create_review_processor(
        self,
        mock_create_processor,
        mock_config,
        mock_auth_headers,
        mock_pat,
        mock_repo_id,
    ):
        """create_review_processor() should be called and its return passed to SubmissionManager."""
        fake_processor = MagicMock()
        mock_create_processor.return_value = fake_processor
        config_obj = MagicMock(organization="org", project="proj", repository="repo")
        mock_config.return_value = config_obj

        manager = smi_module.get_submission_manager()

        mock_create_processor.assert_called_once_with(
            config_obj,
            {"Authorization": "Basic abc"},
            "repo-id-123",
        )
        assert manager._processor is fake_processor
        manager.shutdown(wait=True)

    @patch(_PATCH_GET_REPO_ID, return_value="repo-id-123")
    @patch(_PATCH_GET_PAT, return_value="fake-pat")
    @patch(_PATCH_GET_AUTH, return_value={"Authorization": "Basic abc"})
    @patch(_PATCH_CONFIG)
    @patch(_PATCH_CREATE_PROC)
    def test_resolves_config_headers_repo_id(
        self,
        mock_create_processor,
        mock_config,
        mock_auth_headers,
        mock_pat,
        mock_repo_id,
    ):
        """Should call AzureDevOpsConfig.from_state(), get_auth_headers(get_pat()), get_repository_id()."""
        mock_create_processor.return_value = MagicMock()
        config_obj = MagicMock(organization="org", project="proj", repository="repo")
        mock_config.return_value = config_obj

        manager = smi_module.get_submission_manager()

        mock_config.assert_called_once()
        mock_pat.assert_called_once()
        mock_auth_headers.assert_called_once_with("fake-pat")
        mock_repo_id.assert_called_once_with("org", "proj", "repo")
        manager.shutdown(wait=True)
