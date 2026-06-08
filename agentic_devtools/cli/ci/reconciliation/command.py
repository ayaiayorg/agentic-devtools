"""CLI entry point for the reconciliation engine.

Provides the ``agdt-ci-reconcile`` command that instantiates the appropriate
CI provider and invokes the reconciliation engine.
"""

from __future__ import annotations

import argparse
import json
import logging

from agentic_devtools.cli.ci.reconciliation.engine import reconcile
from agentic_devtools.cli.ci.reconciliation.models import ReconciliationAction

logger = logging.getLogger(__name__)


def _positive_int(value: str) -> int:
    """Argparse type helper that rejects non-positive integers."""
    try:
        v = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not a valid integer") from None
    if v < 1:
        raise argparse.ArgumentTypeError(f"{value} must be >= 1")
    return v


def reconcile_command(argv: list[str] | None = None) -> int:
    """CLI entry point for ``agdt-ci-reconcile``.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 for success/retry, 1 for errors, 2 when escalation occurs.
    """
    parser = argparse.ArgumentParser(
        prog="agdt-ci-reconcile",
        description="Reconcile failed SpecKit pipeline workflow runs.",
    )
    parser.add_argument(
        "--workflow-id",
        required=True,
        help="Workflow file name or ID to reconcile (e.g., 'speckit-phase-progression.yml').",
    )
    parser.add_argument(
        "--provider",
        choices=["github", "ado"],
        default="github",
        help="CI provider to use (default: github).",
    )
    parser.add_argument(
        "--repo",
        default="",
        help="Repository in 'owner/repo' format (GitHub provider). Defaults to current context.",
    )
    parser.add_argument(
        "--max-attempts",
        type=_positive_int,
        default=None,
        help="Override max retry attempts; must be >= 1 (default: from env/config).",
    )
    parser.add_argument(
        "--window-hours",
        type=_positive_int,
        default=None,
        help="Override lookback window in hours; must be >= 1 (default: from env/config).",
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output result as JSON.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging.",
    )

    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    provider = _create_provider(args.provider, args.repo)

    try:
        result = reconcile(
            provider,
            args.workflow_id,
            max_run_attempts=args.max_attempts,
            window_hours=args.window_hours,
        )
    except (NotImplementedError, RuntimeError) as exc:
        logger.error("Reconciliation failed: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected reconciliation error: %s", exc)
        return 1

    if args.json_output:
        output = {
            "action": result.action.value,
            "message": result.message,
            "run_id": result.run.id if result.run else None,
        }
        print(json.dumps(output, indent=2))
    else:
        print(result.message)

    return 0 if result.action != ReconciliationAction.ESCALATED else 2


def _create_provider(provider_name: str, repo: str):
    """Create the appropriate CI provider instance."""
    if provider_name == "github":
        from agentic_devtools.cli.ci.github_provider import GitHubActionsProvider

        return GitHubActionsProvider(repo=repo)
    elif provider_name == "ado":
        from agentic_devtools.cli.ci.ado_provider import AzureDevOpsProvider

        return AzureDevOpsProvider()
    else:
        raise ValueError(f"Unknown provider: {provider_name!r}")
