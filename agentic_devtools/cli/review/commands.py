"""``agdt-review`` CLI command entry point and argument parser.

Builds the argparse parser with subcommands and dispatches to the
appropriate handler.
"""

import argparse
import sys
from collections.abc import Sequence

from .config_commands import run_config_get, run_config_validate
from .consolidate import run_consolidate
from .dispatch import run_dispatch
from .status import run_status


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level ``agdt-review`` argument parser."""
    parser = argparse.ArgumentParser(
        prog="agdt-review",
        description="Configurable multi-model PR review pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # --- dispatch -----------------------------------------------------------
    dispatch_parser = subparsers.add_parser(
        "dispatch",
        help="Orchestrate the full multi-model review sequence.",
    )
    dispatch_parser.add_argument("--pr-id", required=True, type=int, help="Pull request ID")
    dispatch_parser.add_argument("--label", required=True, help="PR label that triggered the review")
    dispatch_parser.add_argument(
        "--config-path",
        default=None,
        help=(
            "Repo root directory or canonical config file path"
            " (.agdt/review-config.yaml or .yml). Uses CWD as repo root"
            " when omitted."
        ),
    )
    dispatch_parser.add_argument("--dry-run", action="store_true", help="Print dispatch plan without executing")

    # --- consolidate --------------------------------------------------------
    consolidate_parser = subparsers.add_parser(
        "consolidate",
        help="Run consolidation as the boss model (resolve conflicts).",
    )
    consolidate_parser.add_argument("--pr-id", required=True, type=int, help="Pull request ID")
    consolidate_parser.add_argument(
        "--model-id",
        default=None,
        help="Consolidator model ID (defaults to config's consolidator model)",
    )

    # --- config-get ---------------------------------------------------------
    config_get_parser = subparsers.add_parser(
        "config-get",
        help="Read and display the resolved review config (internal representation).",
    )
    config_get_parser.add_argument(
        "--config-path",
        default=None,
        help=(
            "Repo root directory or canonical config file path"
            " (.agdt/review-config.yaml or .yml). Uses CWD as repo root"
            " when omitted."
        ),
    )

    # --- config-validate ----------------------------------------------------
    config_validate_parser = subparsers.add_parser(
        "config-validate",
        help="Validate config file syntax and model references.",
    )
    config_validate_parser.add_argument(
        "--config-path",
        default=None,
        help=(
            "Repo root directory or canonical config file path"
            " (.agdt/review-config.yaml or .yml). Uses CWD as repo root"
            " when omitted."
        ),
    )

    # --- status -------------------------------------------------------------
    status_parser = subparsers.add_parser(
        "status",
        help="Show multi-model review progress for a PR.",
    )
    status_parser.add_argument("--pr-id", required=True, type=int, help="Pull request ID")

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point for ``agdt-review``."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.subcommand is None:
        parser.print_help()
        sys.exit(0)

    if args.subcommand == "dispatch":
        run_dispatch(
            pr_id=args.pr_id,
            label=args.label,
            config_path=args.config_path,
            dry_run=args.dry_run,
        )
    elif args.subcommand == "consolidate":
        run_consolidate(pr_id=args.pr_id, model_id=args.model_id)
    elif args.subcommand == "config-get":
        run_config_get(config_path=args.config_path)
    elif args.subcommand == "config-validate":
        run_config_validate(config_path=args.config_path)
    elif args.subcommand == "status":
        run_status(pr_id=args.pr_id)
