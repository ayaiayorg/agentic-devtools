"""Tests for agentic_devtools.cli.setup.platform_detection.detect_platforms."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.setup.platform_detection import (
    DetectionResult,
    detect_platforms,
)

_MOD = "agentic_devtools.cli.setup.platform_detection"


class TestDetectJiraFromEnvVars:
    """Jira detection from environment variables."""

    @patch(f"{_MOD}._get_origin_remote_url", return_value=None)
    @patch(f"{_MOD}.load_platform_config")
    def test_detects_jira_from_copilot_pat(self, mock_cfg, _mock_url, tmp_path, monkeypatch):
        """Detect Jira with medium confidence from JIRA_COPILOT_PAT."""
        mock_cfg.return_value = {"issue_adapter": "github", "jira": {}, "github": {}, "azure_devops": {}}
        monkeypatch.setenv("JIRA_COPILOT_PAT", "token123")

        result = detect_platforms(str(tmp_path))

        assert "jira" in result.detected_issue_platforms
        assert result.confidence["jira"] == "medium"

    @patch(f"{_MOD}._get_origin_remote_url", return_value=None)
    @patch(f"{_MOD}.load_platform_config")
    def test_detects_jira_from_base_url(self, mock_cfg, _mock_url, tmp_path, monkeypatch):
        """Detect Jira with medium confidence from JIRA_BASE_URL."""
        mock_cfg.return_value = {"issue_adapter": "github", "jira": {}, "github": {}, "azure_devops": {}}
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.com")

        result = detect_platforms(str(tmp_path))

        assert "jira" in result.detected_issue_platforms
        assert result.confidence["jira"] == "medium"

    @patch(f"{_MOD}._get_origin_remote_url", return_value=None)
    @patch(f"{_MOD}.load_platform_config")
    def test_detects_jira_from_api_token(self, mock_cfg, _mock_url, tmp_path, monkeypatch):
        """Detect Jira with medium confidence from JIRA_API_TOKEN."""
        mock_cfg.return_value = {"issue_adapter": "github", "jira": {}, "github": {}, "azure_devops": {}}
        monkeypatch.setenv("JIRA_API_TOKEN", "token-abc")

        result = detect_platforms(str(tmp_path))

        assert "jira" in result.detected_issue_platforms
        assert result.confidence["jira"] == "medium"


class TestDetectJiraFromConfig:
    """Jira detection from config file."""

    @patch(f"{_MOD}._get_origin_remote_url", return_value=None)
    @patch(f"{_MOD}.load_platform_config")
    def test_detects_jira_from_issue_adapter_config(self, mock_cfg, _mock_url, tmp_path):
        """Detect Jira with medium confidence when issue_adapter is 'jira'."""
        mock_cfg.return_value = {"issue_adapter": "jira", "jira": {}, "github": {}, "azure_devops": {}}

        result = detect_platforms(str(tmp_path))

        assert "jira" in result.detected_issue_platforms
        assert result.confidence["jira"] == "medium"

    @patch(f"{_MOD}._get_origin_remote_url", return_value=None)
    @patch(f"{_MOD}.load_platform_config")
    def test_detects_jira_from_nonempty_jira_dict(self, mock_cfg, _mock_url, tmp_path):
        """Detect Jira with medium confidence when platform.jira is non-empty."""
        mock_cfg.return_value = {
            "issue_adapter": "github",
            "jira": {"base_url": "https://jira.example.com"},
            "github": {},
            "azure_devops": {},
        }

        result = detect_platforms(str(tmp_path))

        assert "jira" in result.detected_issue_platforms
        assert result.confidence["jira"] == "medium"


class TestDetectJiraHighConfidence:
    """Jira detection with both env and config signals."""

    @patch(f"{_MOD}._get_origin_remote_url", return_value=None)
    @patch(f"{_MOD}.load_platform_config")
    def test_high_confidence_with_env_and_config(self, mock_cfg, _mock_url, tmp_path, monkeypatch):
        """Detect Jira with high confidence when both env var and config present."""
        mock_cfg.return_value = {"issue_adapter": "jira", "jira": {}, "github": {}, "azure_devops": {}}
        monkeypatch.setenv("JIRA_COPILOT_PAT", "token123")

        result = detect_platforms(str(tmp_path))

        assert "jira" in result.detected_issue_platforms
        assert result.confidence["jira"] == "high"


class TestDetectJiraNotPresent:
    """Jira is not detected when no signals are present."""

    @patch(f"{_MOD}._get_origin_remote_url", return_value=None)
    @patch(f"{_MOD}.load_platform_config")
    def test_no_jira_when_no_signals(self, mock_cfg, _mock_url, tmp_path):
        """Do not detect Jira when no env vars or config signals exist."""
        mock_cfg.return_value = {"issue_adapter": "github", "jira": {}, "github": {}, "azure_devops": {}}

        result = detect_platforms(str(tmp_path))

        assert "jira" not in result.detected_issue_platforms
        assert "jira" not in result.confidence


class TestDetectGitHub:
    """GitHub detection from remote URL and .git/ directory."""

    @patch(f"{_MOD}._get_origin_remote_url")
    @patch(f"{_MOD}.load_platform_config")
    def test_detects_github_https_remote(self, mock_cfg, mock_url, tmp_path):
        """Detect GitHub with high confidence from HTTPS remote URL."""
        mock_cfg.return_value = {"issue_adapter": "github", "jira": {}, "github": {}, "azure_devops": {}}
        mock_url.return_value = "https://github.com/myorg/myrepo.git"
        (tmp_path / ".git").mkdir()

        result = detect_platforms(str(tmp_path))

        assert result.detected_code_hosting == "github"
        assert result.github_repo == "myorg/myrepo"
        assert result.confidence["github"] == "high"
        assert "github" in result.detected_issue_platforms

    @patch(f"{_MOD}._get_origin_remote_url")
    @patch(f"{_MOD}.load_platform_config")
    def test_detects_github_ssh_remote(self, mock_cfg, mock_url, tmp_path):
        """Detect GitHub with high confidence from SSH remote URL."""
        mock_cfg.return_value = {"issue_adapter": "github", "jira": {}, "github": {}, "azure_devops": {}}
        mock_url.return_value = "git@github.com:owner/repo-name.git"
        (tmp_path / ".git").mkdir()

        result = detect_platforms(str(tmp_path))

        assert result.detected_code_hosting == "github"
        assert result.github_repo == "owner/repo-name"
        assert result.confidence["github"] == "high"

    @patch(f"{_MOD}._get_origin_remote_url")
    @patch(f"{_MOD}.load_platform_config")
    def test_detects_github_https_no_git_suffix(self, mock_cfg, mock_url, tmp_path):
        """Detect GitHub from HTTPS URL without .git suffix."""
        mock_cfg.return_value = {"issue_adapter": "github", "jira": {}, "github": {}, "azure_devops": {}}
        mock_url.return_value = "https://github.com/owner/repo"
        (tmp_path / ".git").mkdir()

        result = detect_platforms(str(tmp_path))

        assert result.github_repo == "owner/repo"
        assert result.confidence["github"] == "high"

    @patch(f"{_MOD}._get_origin_remote_url")
    @patch(f"{_MOD}.load_platform_config")
    def test_medium_confidence_when_git_exists_but_not_github(self, mock_cfg, mock_url, tmp_path):
        """Detect GitHub with medium confidence when .git/ exists but remote is not GitHub."""
        mock_cfg.return_value = {"issue_adapter": "github", "jira": {}, "github": {}, "azure_devops": {}}
        mock_url.return_value = "https://gitlab.com/owner/repo.git"
        (tmp_path / ".git").mkdir()

        result = detect_platforms(str(tmp_path))

        assert result.github_repo is None
        assert result.confidence["github"] == "medium"
        # Not set as code_hosting since confidence is only medium
        assert result.detected_code_hosting is None

    @patch(f"{_MOD}._get_origin_remote_url", return_value=None)
    @patch(f"{_MOD}.load_platform_config")
    def test_no_github_when_no_git_directory(self, mock_cfg, _mock_url, tmp_path):
        """Do not detect GitHub when no .git/ directory exists."""
        mock_cfg.return_value = {"issue_adapter": "github", "jira": {}, "github": {}, "azure_devops": {}}

        result = detect_platforms(str(tmp_path))

        assert "github" not in result.confidence
        assert result.github_repo is None


class TestDetectAzureDevOps:
    """Azure DevOps detection from remote URL."""

    @patch(f"{_MOD}._get_origin_remote_url")
    @patch(f"{_MOD}.load_platform_config")
    def test_detects_ado_https_remote(self, mock_cfg, mock_url, tmp_path):
        """Detect ADO with high confidence from HTTPS remote URL."""
        mock_cfg.return_value = {"issue_adapter": "github", "jira": {}, "github": {}, "azure_devops": {}}
        mock_url.return_value = "https://dev.azure.com/myorg/myproject/_git/myrepo"

        result = detect_platforms(str(tmp_path))

        assert result.detected_code_hosting == "azure_devops"
        assert result.azure_devops_project == "myorg/myproject"
        assert result.confidence["azure_devops"] == "high"

    @patch(f"{_MOD}._get_origin_remote_url")
    @patch(f"{_MOD}.load_platform_config")
    def test_detects_ado_ssh_new_format(self, mock_cfg, mock_url, tmp_path):
        """Detect ADO from SSH (new format) remote URL."""
        mock_cfg.return_value = {"issue_adapter": "github", "jira": {}, "github": {}, "azure_devops": {}}
        mock_url.return_value = "git@ssh.dev.azure.com:v3/myorg/myproject/myrepo"

        result = detect_platforms(str(tmp_path))

        assert result.detected_code_hosting == "azure_devops"
        assert result.azure_devops_project == "myorg/myproject"
        assert result.confidence["azure_devops"] == "high"

    @patch(f"{_MOD}._get_origin_remote_url")
    @patch(f"{_MOD}.load_platform_config")
    def test_detects_ado_ssh_legacy(self, mock_cfg, mock_url, tmp_path):
        """Detect ADO from SSH (legacy visualstudio.com) remote URL."""
        mock_cfg.return_value = {"issue_adapter": "github", "jira": {}, "github": {}, "azure_devops": {}}
        mock_url.return_value = "myorg@vs-ssh.visualstudio.com:v3/myorg/myproject/myrepo"

        result = detect_platforms(str(tmp_path))

        assert result.detected_code_hosting == "azure_devops"
        assert result.azure_devops_project == "myorg/myproject"
        assert result.confidence["azure_devops"] == "high"

    @patch(f"{_MOD}._get_origin_remote_url")
    @patch(f"{_MOD}.load_platform_config")
    def test_detects_ado_https_visualstudio(self, mock_cfg, mock_url, tmp_path):
        """Detect ADO from HTTPS visualstudio.com URL."""
        mock_cfg.return_value = {"issue_adapter": "github", "jira": {}, "github": {}, "azure_devops": {}}
        mock_url.return_value = "https://myorg.visualstudio.com/myproject/_git/myrepo"

        result = detect_platforms(str(tmp_path))

        assert result.detected_code_hosting == "azure_devops"
        assert result.azure_devops_project == "myorg/myproject"
        assert result.confidence["azure_devops"] == "high"

    @patch(f"{_MOD}._get_origin_remote_url")
    @patch(f"{_MOD}.load_platform_config")
    def test_no_ado_when_github_remote(self, mock_cfg, mock_url, tmp_path):
        """Do not detect ADO when remote URL is GitHub."""
        mock_cfg.return_value = {"issue_adapter": "github", "jira": {}, "github": {}, "azure_devops": {}}
        mock_url.return_value = "https://github.com/owner/repo.git"
        (tmp_path / ".git").mkdir()

        result = detect_platforms(str(tmp_path))

        assert result.azure_devops_project is None
        assert "azure_devops" not in result.confidence


class TestDetectPlatformsEdgeCases:
    """Edge cases for detect_platforms orchestration."""

    @patch(f"{_MOD}._get_origin_remote_url", return_value=None)
    @patch(f"{_MOD}.load_platform_config")
    def test_empty_detection_when_no_signals(self, mock_cfg, _mock_url, tmp_path):
        """Return empty detection when no signals present at all."""
        mock_cfg.return_value = {"issue_adapter": "github", "jira": {}, "github": {}, "azure_devops": {}}

        result = detect_platforms(str(tmp_path))

        assert result.detected_issue_platforms == ()
        assert result.detected_code_hosting is None
        assert result.github_repo is None
        assert result.azure_devops_project is None
        assert result.confidence == {}

    @patch(f"{_MOD}._get_origin_remote_url")
    @patch(f"{_MOD}.load_platform_config")
    def test_multiple_platforms_detected(self, mock_cfg, mock_url, tmp_path, monkeypatch):
        """Detect Jira + GitHub simultaneously."""
        mock_cfg.return_value = {"issue_adapter": "jira", "jira": {}, "github": {}, "azure_devops": {}}
        mock_url.return_value = "https://github.com/org/repo.git"
        monkeypatch.setenv("JIRA_COPILOT_PAT", "secret")
        (tmp_path / ".git").mkdir()

        result = detect_platforms(str(tmp_path))

        assert "jira" in result.detected_issue_platforms
        assert "github" in result.detected_issue_platforms
        assert result.confidence["jira"] == "high"
        assert result.confidence["github"] == "high"
        assert result.detected_code_hosting == "github"


class TestGetOriginRemoteUrl:
    """Tests for _get_origin_remote_url helper."""

    @patch(f"{_MOD}.subprocess.run")
    def test_returns_url_on_success(self, mock_run, tmp_path):
        """Return stripped URL when git command succeeds."""
        from agentic_devtools.cli.setup.platform_detection import _get_origin_remote_url

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/org/repo.git\n"
        mock_run.return_value = mock_result

        url = _get_origin_remote_url(str(tmp_path))

        assert url == "https://github.com/org/repo.git"
        mock_run.assert_called_once_with(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(tmp_path),
        )

    @patch(f"{_MOD}.subprocess.run")
    def test_logs_debug_on_file_not_found(self, mock_run, tmp_path, caplog):
        """Log a debug message when git is not found."""
        import logging

        from agentic_devtools.cli.setup.platform_detection import _get_origin_remote_url

        mock_run.side_effect = FileNotFoundError("git not found")

        with caplog.at_level(logging.DEBUG, logger=_MOD):
            url = _get_origin_remote_url(str(tmp_path))

        assert url is None
        assert any("Could not retrieve origin remote URL" in r.message for r in caplog.records)

    @patch(f"{_MOD}.subprocess.run")
    def test_handles_git_not_installed(self, mock_run, tmp_path):
        """Return None when git is not installed (FileNotFoundError)."""
        mock_run.side_effect = FileNotFoundError("git not found")
        mock_cfg = {"issue_adapter": "github", "jira": {}, "github": {}, "azure_devops": {}}

        with patch(f"{_MOD}.load_platform_config", return_value=mock_cfg):
            result = detect_platforms(str(tmp_path))

        assert result.detected_code_hosting is None
        assert result.github_repo is None
        assert result.azure_devops_project is None

    @patch(f"{_MOD}.subprocess.run")
    def test_handles_no_origin_remote(self, mock_run, tmp_path):
        """Return None when subprocess returns non-zero (no origin remote)."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_run.return_value = mock_result
        mock_cfg = {"issue_adapter": "github", "jira": {}, "github": {}, "azure_devops": {}}

        with patch(f"{_MOD}.load_platform_config", return_value=mock_cfg):
            result = detect_platforms(str(tmp_path))

        assert result.detected_code_hosting is None

    @patch(f"{_MOD}.subprocess.run")
    def test_handles_os_error(self, mock_run, tmp_path):
        """Return None when OSError occurs."""
        mock_run.side_effect = OSError("Permission denied")
        mock_cfg = {"issue_adapter": "github", "jira": {}, "github": {}, "azure_devops": {}}

        with patch(f"{_MOD}.load_platform_config", return_value=mock_cfg):
            result = detect_platforms(str(tmp_path))

        assert result.detected_code_hosting is None


class TestDetectionResultDataclass:
    """Tests for DetectionResult frozen dataclass."""

    def test_default_values(self):
        """DetectionResult has correct defaults."""
        result = DetectionResult()

        assert result.detected_issue_platforms == ()
        assert result.detected_code_hosting is None
        assert result.github_repo is None
        assert result.azure_devops_project is None
        assert result.confidence == {}

    def test_is_frozen(self):
        """DetectionResult is immutable."""
        import dataclasses

        result = DetectionResult()

        try:
            result.github_repo = "test"  # type: ignore[misc]
            raise AssertionError("Should have raised FrozenInstanceError")  # pragma: no cover
        except dataclasses.FrozenInstanceError:
            pass

    def test_confidence_is_immutable(self):
        """Confidence mapping cannot be mutated after construction."""
        from types import MappingProxyType

        result = DetectionResult(confidence={"jira": "high"})

        assert isinstance(result.confidence, MappingProxyType)
        assert result.confidence["jira"] == "high"

        try:
            result.confidence["jira"] = "low"  # type: ignore[index]
            raise AssertionError("Should have raised TypeError")  # pragma: no cover
        except TypeError:
            pass

    def test_confidence_wraps_dict_to_mapping_proxy(self):
        """A plain dict passed as confidence is wrapped in MappingProxyType."""
        from types import MappingProxyType

        raw = {"github": "medium"}
        result = DetectionResult(confidence=raw)

        # Wrapped in MappingProxyType
        assert isinstance(result.confidence, MappingProxyType)
        # Original dict mutation does not affect the result
        raw["github"] = "changed"
        assert result.confidence["github"] == "medium"

    def test_confidence_wraps_non_dict_mapping(self):
        """A non-dict Mapping (e.g. UserDict) is also wrapped in MappingProxyType."""
        from collections import UserDict
        from types import MappingProxyType

        raw = UserDict({"jira": "high"})
        result = DetectionResult(confidence=raw)

        assert isinstance(result.confidence, MappingProxyType)
        assert result.confidence["jira"] == "high"

    def test_confidence_already_mapping_proxy_not_rewrapped(self):
        """A MappingProxyType passed as confidence is not double-wrapped."""
        from types import MappingProxyType

        proxy = MappingProxyType({"azure_devops": "high"})
        result = DetectionResult(confidence=proxy)

        assert result.confidence is proxy
