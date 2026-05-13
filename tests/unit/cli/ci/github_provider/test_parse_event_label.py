"""Tests for GitHubActionsProvider.parse_event() with label events."""

import json
from pathlib import Path

from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider
from agentic_devtools.cli.ci.models import EventPayload

FIXTURES_DIR = Path(__file__).resolve().parents[4] / "fixtures" / "ci_events"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


class TestParseEventLabel:
    """Tests for GitHubActionsProvider.parse_event() with issues/labeled events."""

    def test_issues_labeled_event(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = _load_fixture("issues_labeled.json")
        result = provider.parse_event(payload, "issues")
        assert isinstance(result, EventPayload)
        assert result.action == "labeled"
        assert result.trigger_label == "speckit-ready"
        assert result.repository_full_name == "owner/repo"

    def test_issues_labeled_no_label(self) -> None:
        """Event with no label field returns empty trigger_label."""
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = {"action": "labeled", "repository": {"full_name": "o/r"}}
        result = provider.parse_event(payload, "issues")
        assert result.trigger_label == ""

    def test_issues_unlabeled_event(self) -> None:
        provider = GitHubActionsProvider(repo="owner/repo")
        payload = {
            "action": "unlabeled",
            "label": {"name": "old-label"},
            "repository": {"full_name": "org/project"},
        }
        result = provider.parse_event(payload, "issues")
        assert result.action == "unlabeled"
        assert result.trigger_label == "old-label"
