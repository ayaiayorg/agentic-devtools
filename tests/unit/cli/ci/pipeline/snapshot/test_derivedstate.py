"""Tests for DerivedState."""

import pytest

from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot


class TestDerivedState:
    """Tests for DerivedState proxy behavior."""

    def test_getattr_fallthrough(self) -> None:
        """Attributes fall through to the snapshot."""
        snapshot = PRStateSnapshot(pr_number=42, head_sha="abc123", is_draft=True)
        derived = DerivedState(snapshot)
        assert derived.pr_number == 42
        assert derived.head_sha == "abc123"
        assert derived.is_draft is True

    def test_set_override(self) -> None:
        """set() overrides the snapshot value."""
        snapshot = PRStateSnapshot(is_draft=True)
        derived = DerivedState(snapshot)
        assert derived.is_draft is True

        derived.set("is_draft", False)
        assert derived.is_draft is False

    def test_snapshot_unchanged(self) -> None:
        """Setting a derived override does not mutate the snapshot."""
        snapshot = PRStateSnapshot(is_draft=True)
        derived = DerivedState(snapshot)
        derived.set("is_draft", False)
        assert snapshot.is_draft is True

    def test_snapshot_property(self) -> None:
        """snapshot property returns the underlying snapshot."""
        snapshot = PRStateSnapshot(pr_number=7)
        derived = DerivedState(snapshot)
        assert derived.snapshot is snapshot

    def test_private_attribute_lookup_raises_attribute_error(self) -> None:
        snapshot = PRStateSnapshot(pr_number=7)
        derived = DerivedState(snapshot)
        with pytest.raises(AttributeError):
            _ = derived._private_attr  # type: ignore[attr-defined]

    def test_get_returns_override_value_when_set(self) -> None:
        snapshot = PRStateSnapshot(unresolved_threads=3)
        derived = DerivedState(snapshot)
        derived.set("unresolved_threads", 0)
        assert derived.get("unresolved_threads", 99) == 0

    def test_get_returns_default_for_missing_attribute(self) -> None:
        snapshot = PRStateSnapshot(pr_number=7)
        derived = DerivedState(snapshot)
        assert derived.get("not_present", 123) == 123

    def test_get_private_attribute_lookup_raises_attribute_error(self) -> None:
        snapshot = PRStateSnapshot(pr_number=7)
        derived = DerivedState(snapshot)
        with pytest.raises(AttributeError):
            derived.get("_private_attr")
