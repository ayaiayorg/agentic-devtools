"""Tests for agentic_devtools.cli.setup.platform_detection.confirm_and_override."""

from agentic_devtools.cli.setup.platform_detection import (
    DetectionResult,
    confirm_and_override,
)


class TestConfirmAccepted:
    """User accepts the detected platforms."""

    def test_accept_with_enter(self):
        """Accepting with empty input returns config from detection."""
        result = DetectionResult(
            detected_issue_platforms=("jira",),
            detected_code_hosting="github",
            github_repo="owner/repo",
            confidence={"jira": "high", "github": "high"},
        )
        printed: list[str] = []

        config = confirm_and_override(
            result,
            input_fn=lambda _prompt: "",
            print_fn=lambda *args: printed.append(" ".join(str(a) for a in args)),
        )

        assert config["issue_adapter"] == "jira"
        assert config["code_hosting"] == "github"
        assert config["github"]["repo"] == "owner/repo"
        assert isinstance(config["jira"], dict)
        assert isinstance(config["azure_devops"], dict)

    def test_accept_with_y(self):
        """Accepting with 'y' returns config from detection."""
        result = DetectionResult(
            detected_issue_platforms=("jira",),
            detected_code_hosting="azure_devops",
            azure_devops_project="org/proj",
            confidence={"jira": "medium", "azure_devops": "high"},
        )

        config = confirm_and_override(
            result,
            input_fn=lambda _prompt: "y",
            print_fn=lambda *args: None,
        )

        assert config["issue_adapter"] == "jira"
        assert config["code_hosting"] == "azure_devops"
        assert config["azure_devops"]["project"] == "org/proj"

    def test_accept_with_yes(self):
        """Accepting with 'yes' returns config from detection."""
        result = DetectionResult(
            detected_issue_platforms=("github",),
            detected_code_hosting="github",
            github_repo="org/repo",
            confidence={"github": "high"},
        )

        config = confirm_and_override(
            result,
            input_fn=lambda _prompt: "YES",
            print_fn=lambda *args: None,
        )

        assert config["issue_adapter"] == "github"
        assert config["code_hosting"] == "github"


class TestConfirmOverride:
    """User overrides the detected platforms."""

    def test_override_issue_adapter(self):
        """Override issue adapter when user declines."""
        result = DetectionResult(
            detected_issue_platforms=("jira",),
            detected_code_hosting="github",
            confidence={"jira": "medium"},
        )
        inputs = iter(["n", "github", ""])

        config = confirm_and_override(
            result,
            input_fn=lambda _prompt: next(inputs),
            print_fn=lambda *args: None,
        )

        assert config["issue_adapter"] == "github"
        assert config["code_hosting"] == "other"

    def test_override_preserves_auto_detected_details(self):
        """Override path preserves github_repo and azure_devops_project from detection."""
        result = DetectionResult(
            detected_issue_platforms=("jira", "github"),
            detected_code_hosting="github",
            github_repo="owner/repo",
            azure_devops_project="org/proj",
            confidence={"jira": "high", "github": "high"},
        )
        inputs = iter(["n", "jira", "azure_devops"])

        config = confirm_and_override(
            result,
            input_fn=lambda _prompt: next(inputs),
            print_fn=lambda *args: None,
        )

        assert config["issue_adapter"] == "jira"
        assert config["code_hosting"] == "azure_devops"
        # Auto-detected details are preserved, not discarded
        assert config["github"]["repo"] == "owner/repo"
        assert config["azure_devops"]["project"] == "org/proj"

    def test_override_code_hosting(self):
        """Override code hosting when user declines."""
        result = DetectionResult()
        inputs = iter(["N", "", "azure_devops"])

        config = confirm_and_override(
            result,
            input_fn=lambda _prompt: next(inputs),
            print_fn=lambda *args: None,
        )

        assert config["issue_adapter"] == "jira"  # default
        assert config["code_hosting"] == "azure_devops"

    def test_invalid_then_valid_adapter(self):
        """Re-prompt on invalid adapter, accept on valid."""
        result = DetectionResult()
        printed: list[str] = []
        inputs = iter(["no", "invalid", "markdown", "github"])

        config = confirm_and_override(
            result,
            input_fn=lambda _prompt: next(inputs),
            print_fn=lambda *args: printed.append(" ".join(str(a) for a in args)),
        )

        assert config["issue_adapter"] == "markdown"
        assert any("Invalid choice" in line for line in printed)

    def test_invalid_then_valid_code_hosting(self):
        """Re-prompt on invalid code hosting, accept on valid."""
        result = DetectionResult()
        printed: list[str] = []
        inputs = iter(["no", "jira", "invalid_host", "github"])

        config = confirm_and_override(
            result,
            input_fn=lambda _prompt: next(inputs),
            print_fn=lambda *args: printed.append(" ".join(str(a) for a in args)),
        )

        assert config["issue_adapter"] == "jira"
        assert config["code_hosting"] == "github"
        assert any("Invalid choice" in line for line in printed)


class TestConfirmEOFAndInterrupt:
    """Graceful handling of EOFError and KeyboardInterrupt."""

    def test_eof_returns_auto_config(self):
        """EOFError during prompt returns auto-detected config."""
        result = DetectionResult(
            detected_issue_platforms=("jira",),
            detected_code_hosting="github",
            github_repo="org/repo",
            confidence={"jira": "high", "github": "high"},
        )

        def raise_eof(_prompt: str) -> str:
            raise EOFError

        config = confirm_and_override(
            result,
            input_fn=raise_eof,
            print_fn=lambda *args: None,
        )

        assert config["issue_adapter"] == "jira"
        assert config["code_hosting"] == "github"
        assert config["github"]["repo"] == "org/repo"

    def test_keyboard_interrupt_returns_auto_config(self):
        """KeyboardInterrupt during prompt returns auto-detected config."""
        result = DetectionResult(
            detected_issue_platforms=("github",),
            detected_code_hosting="github",
            confidence={"github": "high"},
        )

        def raise_interrupt(_prompt: str) -> str:
            raise KeyboardInterrupt

        config = confirm_and_override(
            result,
            input_fn=raise_interrupt,
            print_fn=lambda *args: None,
        )

        assert config["issue_adapter"] == "github"
        assert config["code_hosting"] == "github"


class TestConfirmReturnedDictCompat:
    """Returned dict is compatible with save_platform_config()."""

    def test_has_all_required_keys(self):
        """Config dict contains all keys expected by save_platform_config."""
        result = DetectionResult()

        config = confirm_and_override(
            result,
            input_fn=lambda _prompt: "",
            print_fn=lambda *args: None,
        )

        assert "issue_adapter" in config
        assert "code_hosting" in config
        assert "jira" in config
        assert "github" in config
        assert "azure_devops" in config
        assert isinstance(config["jira"], dict)
        assert isinstance(config["github"], dict)
        assert isinstance(config["azure_devops"], dict)


class TestConfirmEmptyDetection:
    """confirm_and_override works with an empty DetectionResult."""

    def test_empty_detection_returns_defaults(self):
        """Empty detection result produces valid config with defaults."""
        result = DetectionResult()

        config = confirm_and_override(
            result,
            input_fn=lambda _prompt: "",
            print_fn=lambda *args: None,
        )

        assert config["issue_adapter"] == "jira"  # DEFAULT_ISSUE_ADAPTER
        assert config["code_hosting"] == "other"  # DEFAULT_CODE_HOSTING
        assert config["jira"] == {}
        assert config["github"] == {}
        assert config["azure_devops"] == {}


class TestConfirmPrintsSummary:
    """confirm_and_override prints detection summary."""

    def test_prints_issue_tracking(self):
        """Summary includes issue tracking info."""
        result = DetectionResult(
            detected_issue_platforms=("jira",),
            detected_code_hosting="github",
            github_repo="owner/repo",
            confidence={"jira": "medium", "github": "high"},
        )
        printed: list[str] = []

        confirm_and_override(
            result,
            input_fn=lambda _prompt: "",
            print_fn=lambda *args: printed.append(" ".join(str(a) for a in args)),
        )

        combined = "\n".join(printed)
        assert "jira" in combined
        assert "github" in combined
        assert "owner/repo" in combined


class TestConfirmEOFDuringOverride:
    """EOF during override prompts falls back gracefully."""

    def test_eof_during_adapter_override(self):
        """EOFError during adapter override uses default."""
        call_count = 0

        def mock_input(_prompt: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "n"
            raise EOFError

        result = DetectionResult()

        config = confirm_and_override(
            result,
            input_fn=mock_input,
            print_fn=lambda *args: None,
        )

        assert config["issue_adapter"] == "jira"  # default
        assert config["code_hosting"] == "other"  # default
