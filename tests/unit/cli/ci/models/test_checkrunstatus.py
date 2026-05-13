"""Tests for CheckRunStatus dataclass."""

from agentic_devtools.cli.ci.models import CheckRunStatus


class TestCheckRunStatus:
    """Tests for the CheckRunStatus dataclass."""

    def test_completed_check(self) -> None:
        check = CheckRunStatus(
            id=12345,
            name="ci/build",
            status="completed",
            conclusion="success",
        )
        assert check.id == 12345
        assert check.name == "ci/build"
        assert check.status == "completed"
        assert check.conclusion == "success"

    def test_in_progress_check(self) -> None:
        check = CheckRunStatus(
            id=99,
            name="ci/test",
            status="in_progress",
        )
        assert check.status == "in_progress"
        assert check.conclusion == ""

    def test_default_conclusion(self) -> None:
        check = CheckRunStatus(id=1, name="lint", status="queued")
        assert check.conclusion == ""

    def test_failed_check(self) -> None:
        check = CheckRunStatus(
            id=5,
            name="ci/deploy",
            status="completed",
            conclusion="failure",
        )
        assert check.conclusion == "failure"

    def test_is_frozen(self) -> None:
        check = CheckRunStatus(id=1, name="test", status="completed")
        try:
            check.id = 2  # type: ignore[misc]
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass
