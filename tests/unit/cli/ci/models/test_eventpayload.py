"""Tests for EventPayload dataclass."""

from agentic_devtools.cli.ci.models import EventPayload


class TestEventPayload:
    """Tests for the EventPayload dataclass."""

    def test_default_values(self) -> None:
        payload = EventPayload()
        assert payload.pr_number == 0
        assert payload.head_branch == ""
        assert payload.head_sha == ""
        assert payload.base_branch == ""
        assert payload.action == ""
        assert payload.trigger_label == ""
        assert payload.repository_full_name == ""

    def test_with_pr_fields(self) -> None:
        payload = EventPayload(
            pr_number=42,
            head_branch="feature/test",
            head_sha="abc123def456",
            base_branch="main",
            action="opened",
            repository_full_name="owner/repo",
        )
        assert payload.pr_number == 42
        assert payload.head_branch == "feature/test"
        assert payload.head_sha == "abc123def456"
        assert payload.base_branch == "main"
        assert payload.action == "opened"
        assert payload.repository_full_name == "owner/repo"

    def test_with_label_event(self) -> None:
        payload = EventPayload(
            action="labeled",
            trigger_label="speckit-ready",
            repository_full_name="org/project",
        )
        assert payload.trigger_label == "speckit-ready"
        assert payload.action == "labeled"

    def test_is_frozen(self) -> None:
        payload = EventPayload(pr_number=1)
        try:
            payload.pr_number = 2  # type: ignore[misc]
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass

    def test_equality(self) -> None:
        p1 = EventPayload(pr_number=1, head_sha="abc")
        p2 = EventPayload(pr_number=1, head_sha="abc")
        assert p1 == p2

    def test_inequality(self) -> None:
        p1 = EventPayload(pr_number=1)
        p2 = EventPayload(pr_number=2)
        assert p1 != p2
