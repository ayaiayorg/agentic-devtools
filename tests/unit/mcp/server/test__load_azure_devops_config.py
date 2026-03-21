"""Tests for agentic_devtools.mcp.server._load_azure_devops_config."""

import base64
import os
from unittest.mock import patch

from agentic_devtools.mcp.server import _load_azure_devops_config


class TestLoadAzureDevOpsConfig:
    """Tests for the _load_azure_devops_config helper."""

    def test_returns_config_when_all_vars_set(self):
        env = {
            "AZURE_DEVOPS_ORG": "https://dev.azure.com/myorg",
            "AZURE_DEVOPS_PROJECT": "MyProject",
            "AZURE_DEVOPS_PAT": "mypat123",
        }
        with patch.dict(os.environ, env, clear=True):
            result = _load_azure_devops_config()

        assert result is not None
        config, pat, headers = result
        assert config.organization == "https://dev.azure.com/myorg"
        assert config.project == "MyProject"
        assert pat == "mypat123"

    def test_returns_none_when_org_missing(self):
        env = {
            "AZURE_DEVOPS_PROJECT": "MyProject",
            "AZURE_DEVOPS_PAT": "mypat123",
        }
        with patch.dict(os.environ, env, clear=True):
            result = _load_azure_devops_config()

        assert result is None

    def test_returns_none_when_project_missing(self):
        env = {
            "AZURE_DEVOPS_ORG": "https://dev.azure.com/myorg",
            "AZURE_DEVOPS_PAT": "mypat123",
        }
        with patch.dict(os.environ, env, clear=True):
            result = _load_azure_devops_config()

        assert result is None

    def test_returns_none_when_pat_missing(self):
        env = {
            "AZURE_DEVOPS_ORG": "https://dev.azure.com/myorg",
            "AZURE_DEVOPS_PROJECT": "MyProject",
        }
        with patch.dict(os.environ, env, clear=True):
            result = _load_azure_devops_config()

        assert result is None

    def test_returns_none_when_all_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            result = _load_azure_devops_config()

        assert result is None

    def test_auth_headers_format(self):
        env = {
            "AZURE_DEVOPS_ORG": "https://dev.azure.com/myorg",
            "AZURE_DEVOPS_PROJECT": "MyProject",
            "AZURE_DEVOPS_PAT": "mypat123",
        }
        with patch.dict(os.environ, env, clear=True):
            result = _load_azure_devops_config()

        assert result is not None
        _config, _pat, headers = result
        expected = base64.b64encode(b":mypat123").decode()
        assert headers == {"Authorization": f"Basic {expected}"}

    def test_config_repository_is_empty_string(self):
        env = {
            "AZURE_DEVOPS_ORG": "https://dev.azure.com/myorg",
            "AZURE_DEVOPS_PROJECT": "MyProject",
            "AZURE_DEVOPS_PAT": "mypat123",
        }
        with patch.dict(os.environ, env, clear=True):
            result = _load_azure_devops_config()

        assert result is not None
        config, _pat, _headers = result
        assert config.repository == ""
