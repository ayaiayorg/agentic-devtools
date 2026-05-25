"""Tests for PRStateSnapshot."""

from dataclasses import FrozenInstanceError

import pytest

from agentic_devtools.cli.ci.pipeline.snapshot import PRStateSnapshot


class TestPRStateSnapshot:
    """Tests for PRStateSnapshot construction."""

    def test_default_construction(self) -> None:
        snapshot = PRStateSnapshot()
        assert snapshot.pr_number == 0
        assert snapshot.head_sha == ""
        assert snapshot.commit_count == 1
        assert snapshot.ci_status == "unknown"
        assert snapshot.active_session is False
        assert snapshot.is_draft is False
        assert snapshot.has_changes is False

    def test_custom_construction(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=42,
            head_sha="abc123",
            commit_count=3,
            ci_status="passing",
            is_draft=True,
            labels=["ai-auto-merge-allowed"],
        )
        assert snapshot.pr_number == 42
        assert snapshot.head_sha == "abc123"
        assert snapshot.commit_count == 3
        assert snapshot.ci_status == "passing"
        assert snapshot.is_draft is True
        assert "ai-auto-merge-allowed" in snapshot.labels

    def test_frozen(self) -> None:
        """PRStateSnapshot should be immutable."""
        snapshot = PRStateSnapshot(pr_number=1)
        with pytest.raises(FrozenInstanceError):
            snapshot.pr_number = 2  # type: ignore[misc]
