"""Rebase action — rebases branch onto base when behind.

Ensures single-commit PRs (which skip squash) get rebased when the base
branch has advanced. For multi-commit PRs, Squash's internal rebase runs
first; this action verifies the branch is current afterward.
"""

from __future__ import annotations

import logging

from agentic_devtools.cli.ci.pipeline.exceptions import ForceWithLeaseError, RebaseConflictError
from agentic_devtools.cli.ci.pipeline.models import ActionDecision, ActionResult
from agentic_devtools.cli.ci.pipeline.session_detector import is_copilot_session_active_via_agent_task
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot
from agentic_devtools.cli.ci.provider import CIPlatformProvider

logger = logging.getLogger(__name__)


class RebaseAction:
    """Rebase the PR branch onto base when behind.

    Detects whether the PR's branch is behind its base branch and, if so,
    performs a rebase and force-push-with-lease. Sets ``invalidates_snapshot=True``
    on success so downstream actions wait for fresh CI.

    Preconditions:
    - Branch is behind base (commits_behind > 0)
    - No repair dispatched in this run
    - No active Copilot coding session

    Idempotency: Already up-to-date → skip.
    """

    @property
    def name(self) -> str:
        return "rebase"

    def evaluate(self, snapshot: PRStateSnapshot, derived: DerivedState) -> ActionResult:
        """Evaluate whether rebase is needed."""
        preconditions: dict[str, bool] = {}

        # Must be behind base branch
        commits_behind = snapshot.commits_behind
        preconditions["commits_behind_gt_0"] = commits_behind > 0
        if commits_behind == 0:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="Branch is up-to-date with base — no rebase needed",
            )

        # Repair dispatch in this run should keep HEAD stable
        repair_dispatched = getattr(derived, "repair_dispatched", False)
        preconditions["no_repair_dispatched"] = not repair_dispatched
        if repair_dispatched:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="Repair dispatched — deferring rebase",
            )

        # Rewriting branches that modify workflow files is frequently blocked by
        # token scope restrictions in CI (missing workflow scope on PAT).
        touches_workflow_files = any(
            path.startswith(".github/workflows/") and not path.endswith(".md") for path in snapshot.files
        )
        preconditions["no_workflow_file_changes"] = not touches_workflow_files
        if touches_workflow_files:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="Workflow files changed — deferring rebase to avoid force-push scope restrictions",
            )

        # No active Copilot session
        active_session = is_copilot_session_active_via_agent_task(snapshot.base_repo_full_name, snapshot.pr_number)
        preconditions["no_active_session"] = not active_session
        if active_session:
            return ActionResult(
                name=self.name,
                decision=ActionDecision.SKIP,
                preconditions=preconditions,
                details="Copilot session active — deferring rebase",
            )

        return ActionResult(
            name=self.name,
            decision=ActionDecision.EXECUTE,
            preconditions=preconditions,
            details=f"Branch is {commits_behind} commit(s) behind base — rebase needed",
        )

    def execute(
        self,
        provider: CIPlatformProvider,
        snapshot: PRStateSnapshot,
        derived: DerivedState,
    ) -> ActionResult:
        """Execute the rebase operation."""
        try:
            provider.rebase_onto_base(
                pr_number=snapshot.pr_number,
                base_branch=snapshot.base_branch,
                head_branch=snapshot.head_branch,
                head_sha=snapshot.head_sha,
            )
        except RebaseConflictError as exc:
            logger.warning("PR #%d: Rebase blocked by conflicts: %s", snapshot.pr_number, exc)
            return ActionResult(
                name=self.name,
                decision=ActionDecision.BLOCKED,
                error=str(exc),
                details="Rebase conflicts could not be auto-resolved",
            )
        except ForceWithLeaseError as exc:
            logger.error("PR #%d: Force-push-with-lease failed: %s", snapshot.pr_number, exc)
            return ActionResult(
                name=self.name,
                decision=ActionDecision.FAILED,
                error=str(exc),
                details="Force-push-with-lease failed — concurrent update detected",
            )
        except Exception as exc:
            logger.error("PR #%d: Rebase failed: %s", snapshot.pr_number, exc)
            return ActionResult(
                name=self.name,
                decision=ActionDecision.FAILED,
                error=str(exc),
                details="rebase_onto_base failed",
            )

        logger.info("PR #%d: Rebased onto %s", snapshot.pr_number, snapshot.base_branch)

        return ActionResult(
            name=self.name,
            decision=ActionDecision.EXECUTE,
            details=f"Rebased onto {snapshot.base_branch} (was {snapshot.commits_behind} commit(s) behind)",
            invalidates_snapshot=True,
        )
