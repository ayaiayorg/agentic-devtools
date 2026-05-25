"""Guards action — evaluates all safety guards."""

from __future__ import annotations

from agentic_devtools.cli.ci.guards import (
    check_docker_files,
    check_exclusion_labels,
    check_fork_pr,
    check_privileged_paths,
)
from agentic_devtools.cli.ci.pipeline.models import ActionDecision, ActionResult
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot
from agentic_devtools.cli.ci.provider import CIPlatformProvider


def _is_wip_title(title: str) -> bool:
    """Return True when the PR title is marked work-in-progress."""
    return title.upper().startswith("[WIP]")


class GuardsAction:
    """Evaluate all safety guards that gate the pipeline.

    Guards are fail-closed: any exception blocks the entire pipeline.
    """

    @property
    def name(self) -> str:
        return "guards"

    def evaluate(self, snapshot: PRStateSnapshot, derived: DerivedState) -> ActionResult:
        """Evaluate all guards. Returns BLOCKED if any guard fails."""
        preconditions: dict[str, bool] = {}

        # WIP title check — matches legacy orchestrator _is_wip_title() gate
        is_wip = _is_wip_title(snapshot.title)
        preconditions["not_wip"] = not is_wip
        if is_wip:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.BLOCKED,
                preconditions=preconditions,
                details="PR title is marked WIP",
            )

        # No-changes check — matches legacy orchestrator no_changes gate
        has_changes = bool(snapshot.files)
        preconditions["has_changes"] = has_changes
        if not has_changes:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.BLOCKED,
                preconditions=preconditions,
                details="PR has no file changes",
            )

        # Fork check
        is_fork = check_fork_pr(snapshot.head_repo_full_name, snapshot.base_repo_full_name)
        preconditions["not_fork"] = not is_fork
        if is_fork:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.BLOCKED,
                preconditions=preconditions,
                details="PR is from a fork",
            )

        # Exclusion labels
        should_skip, _flag = check_exclusion_labels(snapshot.labels)
        preconditions["no_exclusion_label"] = not should_skip
        if should_skip:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.BLOCKED,
                preconditions=preconditions,
                details="PR has exclusion label",
            )

        # Privileged paths
        has_privileged = check_privileged_paths(snapshot.files)
        preconditions["no_privileged_paths"] = not has_privileged
        if has_privileged:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.BLOCKED,
                preconditions=preconditions,
                details="PR touches privileged paths",
            )

        # Docker files
        has_docker = check_docker_files(snapshot.files)
        preconditions["no_docker_files"] = not has_docker
        if has_docker:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.BLOCKED,
                preconditions=preconditions,
                details="PR touches Docker files",
            )

        # All guards passed
        return ActionResult(
            name=self.name,
            decision=ActionDecision.EXECUTE,
            preconditions=preconditions,
            details="All guards passed",
        )

    def execute(
        self,
        provider: CIPlatformProvider,
        snapshot: PRStateSnapshot,
        derived: DerivedState,
    ) -> ActionResult:
        """Guards have no execution — evaluation is the entire action."""
        return ActionResult(
            name=self.name,
            decision=ActionDecision.EXECUTE,
            details="All guards passed",
        )
