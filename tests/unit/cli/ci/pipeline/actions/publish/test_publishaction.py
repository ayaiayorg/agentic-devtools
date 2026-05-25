"""Tests for PublishAction."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.pipeline.actions.publish import PublishAction
from agentic_devtools.cli.ci.pipeline.models import ActionDecision
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot


class TestPublishAction:
    """Tests for publish action evaluation and execution."""

    def test_skip_when_not_draft(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, is_draft=False, has_changes=True)
        derived = DerivedState(snapshot)
        action = PublishAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "not a draft" in result.details

    def test_skip_when_no_changes(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, is_draft=True, has_changes=False)
        derived = DerivedState(snapshot)
        action = PublishAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP

    def test_skip_when_wip_title(self) -> None:
        snapshot = PRStateSnapshot(pr_number=1, is_draft=True, has_changes=True, title="[WIP] work in progress")
        derived = DerivedState(snapshot)
        action = PublishAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.SKIP
        assert "WIP" in result.details

    def test_execute_when_draft_ready(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            is_draft=True,
            has_changes=True,
            title="feat: add feature",
            head_sha="abc123",
            base_branch="main",
            head_branch="feature/x",
        )
        derived = DerivedState(snapshot)
        action = PublishAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE

    def test_execute_updates_derived_state(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            is_draft=True,
            has_changes=True,
            title="feat: add feature",
            head_sha="abc123",
            base_branch="main",
            head_branch="feature/x",
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        action = PublishAction()
        result = action.execute(provider, snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE
        assert result.invalidates_snapshot is True
        assert derived.is_draft is False
        provider.squash_before_publish.assert_called_once()
        provider.publish_pr.assert_called_once_with(1)

    def test_execute_fails_when_squash_before_publish_raises(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            is_draft=True,
            has_changes=True,
            title="feat: add feature",
            head_sha="abc123",
            base_branch="main",
            head_branch="feature/x",
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.squash_before_publish.side_effect = RuntimeError("push failed")
        action = PublishAction()
        result = action.execute(provider, snapshot, derived)
        assert result.decision == ActionDecision.FAILED
        assert result.details == "squash_before_publish failed"
        assert result.error == "push failed"
        provider.publish_pr.assert_not_called()

    def test_execute_fails_when_publish_raises(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            is_draft=True,
            has_changes=True,
            title="feat: add feature",
            head_sha="abc123",
            base_branch="main",
            head_branch="feature/x",
        )
        derived = DerivedState(snapshot)
        provider = MagicMock()
        provider.publish_pr.side_effect = RuntimeError("publish failed")
        action = PublishAction()
        result = action.execute(provider, snapshot, derived)
        assert result.decision == ActionDecision.FAILED
        assert result.details == "publish_pr failed"
        assert result.error == "publish failed"
