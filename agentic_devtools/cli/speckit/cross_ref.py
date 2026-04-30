"""CLI entry point for Pass G — Code Reference Cross-Referencing.

Provides ``agdt-speckit-cross-ref`` as a standalone command following
the ``validate_frs.py`` precedent.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .pass_g import (
    build_inventory,
    classify_references,
    extract_references,
    render_json,
    render_markdown,
)


def cross_ref_command(argv: list[str] | None = None) -> None:
    """CLI entry point for agdt-speckit-cross-ref."""
    parser = argparse.ArgumentParser(
        prog="agdt-speckit-cross-ref",
        description="Cross-reference plan code references against the actual codebase.",
    )
    parser.add_argument(
        "--plan-file",
        type=str,
        default="plan.md",
        help="Path to the plan file (default: plan.md)",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=".",
        help="Path to the repository root (default: current directory)",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        default=False,
        help="Output results as JSON instead of Markdown",
    )

    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    plan_path = Path(args.plan_file)
    if not plan_path.is_absolute():
        plan_path = repo_root / plan_path

    # Read plan content
    if not plan_path.is_file():
        print(f"Error: plan file '{plan_path}' not found.", file=sys.stderr)
        raise SystemExit(2)

    try:
        plan_text = plan_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"Error reading plan file: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    # Run the pipeline
    start_time = time.time()

    references = extract_references(plan_text)
    inventory = build_inventory(repo_root)
    findings = classify_references(references, inventory)

    elapsed = time.time() - start_time

    # Output
    if args.json_output:
        print(render_json(findings, elapsed))
    else:
        print(render_markdown(findings, elapsed, plan_filename=Path(args.plan_file).name))

    # Exit code: 0 if no HIGH severity findings, 1 otherwise
    from .pass_g.models import MatchStatus

    high_findings = [f for f in findings if f.status == MatchStatus.INVALID and not f.candidates]
    raise SystemExit(1 if high_findings else 0)
