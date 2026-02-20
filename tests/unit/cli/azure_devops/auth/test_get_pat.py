"""Tests for get_pat function."""

from unittest.mock import patch

import pytest

from agentic_devtools.cli import azure_devops

class TestGetPat:
    """Tests for get_pat function."""

    def test_get_pat_from_env(self):
        """Test getting PAT from environment variable."""
        with patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "test-pat"}):
            pat = azure_devops.get_pat()
            assert pat == "test-pat"

    def test_get_pat_from_ext_env_fallback(self):
        """Test getting PAT from AZURE_DEVOPS_EXT_PAT as fallback."""
        with patch.dict("os.environ", {"AZURE_DEVOPS_EXT_PAT": "ext-test-pat"}, clear=True):
            pat = azure_devops.get_pat()
            assert pat == "ext-test-pat"

    def test_get_pat_prefers_copilot_pat(self):
        """Test that AZURE_DEV_OPS_COPILOT_PAT takes precedence over AZURE_DEVOPS_EXT_PAT."""
        with patch.dict("os.environ", {"AZURE_DEV_OPS_COPILOT_PAT": "copilot-pat", "AZURE_DEVOPS_EXT_PAT": "ext-pat"}):
            pat = azure_devops.get_pat()
            assert pat == "copilot-pat"

    def test_get_pat_missing_raises(self):
        """Test that missing PAT raises EnvironmentError."""
        with patch.dict("os.environ", clear=True):
            with pytest.raises(EnvironmentError, match="AZURE_DEV_OPS_COPILOT_PAT"):
                azure_devops.get_pat()
