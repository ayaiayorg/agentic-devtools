"""Tests for GuardsAction."""

from agentic_devtools.cli.ci.pipeline.actions.guards import GuardsAction
from agentic_devtools.cli.ci.pipeline.models import ActionDecision
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot


class TestGuardsAction:
    """Tests for guard evaluation."""

    def test_all_guards_pass(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            head_repo_full_name="org/repo",
            base_repo_full_name="org/repo",
            labels=[],
            files=["src/main.py"],
            title="My PR",
        )
        derived = DerivedState(snapshot)
        action = GuardsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.EXECUTE
        assert result.preconditions["not_fork"] is True
        assert result.preconditions["no_exclusion_label"] is True
        assert result.preconditions["not_wip"] is True
        assert result.preconditions["has_changes"] is True

    def test_wip_title_blocked(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            head_repo_full_name="org/repo",
            base_repo_full_name="org/repo",
            files=["src/main.py"],
            title="[WIP] work in progress",
        )
        derived = DerivedState(snapshot)
        action = GuardsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.BLOCKED
        assert "wip" in result.details.lower()

    def test_wip_title_blocked_case_insensitive(self) -> None:
        """[wip] in any case is also blocked."""
        snapshot = PRStateSnapshot(
            pr_number=1,
            head_repo_full_name="org/repo",
            base_repo_full_name="org/repo",
            files=["src/main.py"],
            title="[wip] lowercase wip title",
        )
        derived = DerivedState(snapshot)
        action = GuardsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.BLOCKED

    def test_no_changes_blocked(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            head_repo_full_name="org/repo",
            base_repo_full_name="org/repo",
            files=[],
            title="Normal title",
        )
        derived = DerivedState(snapshot)
        action = GuardsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.BLOCKED
        assert "no file changes" in result.details.lower()

    def test_fork_pr_blocked(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            head_repo_full_name="attacker/repo",
            base_repo_full_name="org/repo",
            files=["src/main.py"],
            title="Normal",
        )
        derived = DerivedState(snapshot)
        action = GuardsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.BLOCKED
        assert "fork" in result.details.lower()

    def test_exclusion_label_blocked(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            head_repo_full_name="org/repo",
            base_repo_full_name="org/repo",
            labels=["ai-pr-loop-ignore"],
            files=["src/main.py"],
            title="Normal",
        )
        derived = DerivedState(snapshot)
        action = GuardsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.BLOCKED
        assert "exclusion" in result.details.lower()

    def test_privileged_paths_blocked(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            head_repo_full_name="org/repo",
            base_repo_full_name="org/repo",
            files=[".github/workflows/ci.yml"],
            title="Normal",
        )
        derived = DerivedState(snapshot)
        action = GuardsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.BLOCKED
        assert "privileged" in result.details.lower()

    def test_docker_files_blocked(self) -> None:
        snapshot = PRStateSnapshot(
            pr_number=1,
            head_repo_full_name="org/repo",
            base_repo_full_name="org/repo",
            files=["Dockerfile"],
            title="Normal",
        )
        derived = DerivedState(snapshot)
        action = GuardsAction()
        result = action.evaluate(snapshot, derived)
        assert result.decision == ActionDecision.BLOCKED
        assert "docker" in result.details.lower()
