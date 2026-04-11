#!/usr/bin/env python3
"""CLI helper for context budget enforcement in SpecKit trigger scripts.

Reads content from stdin or arguments and applies the context budget.
Prints the budget-compliant content to stdout and diagnostic metadata to stderr.

Usage:
    echo "$content" | python enforce_budget.py [--budget N]
    python enforce_budget.py --description "desc" --comments "comm" [--budget N]

Exit Codes:
    0 - Success (budget-compliant content written to stdout)
    1 - Permanent failure (budget cannot be met)
    2 - Invalid arguments
"""

from __future__ import annotations

import argparse
import json
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce context budget on plan-phase content.")
    parser.add_argument("--budget", type=int, default=None, help="Context budget in characters")
    parser.add_argument("--description", type=str, default=None, help="Description content")
    parser.add_argument("--comments", type=str, default="", help="Comments content")
    args = parser.parse_args()

    # Import here to avoid import errors when the module is not installed
    try:
        from agentic_devtools.context_budget import (
            DEFAULT_CONTEXT_BUDGET,
            ContextBudgetError,
            enforce_context_budget,
        )
    except ImportError:
        print(
            "Warning: agentic_devtools package not available. Budget enforcement skipped (passthrough mode).",
            file=sys.stderr,
        )
        # Passthrough: read from stdin or use provided content
        if args.description is not None:
            sys.stdout.write(args.description)
        else:
            sys.stdout.write(sys.stdin.read())
        return 0

    budget = args.budget if args.budget is not None else DEFAULT_CONTEXT_BUDGET

    if budget <= 0:
        print(f"Warning: Invalid budget {budget}, using default {DEFAULT_CONTEXT_BUDGET}", file=sys.stderr)
        budget = DEFAULT_CONTEXT_BUDGET

    # Get description content
    if args.description is not None:
        description = args.description
    else:
        description = sys.stdin.read()

    comments = args.comments

    try:
        result = enforce_context_budget(description, comments, budget=budget)
    except ContextBudgetError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Emit diagnostic metadata to stderr as JSON
    metadata = {
        "stage": result.stage.value,
        "original_chars": result.original_chars,
        "final_chars": result.final_chars,
        "budget": result.budget,
    }
    print(f"[Context Budget] {json.dumps(metadata)}", file=sys.stderr)

    if result.stage.value != "passthrough":
        print(
            f"[Context Budget] Content reduced: {result.original_chars} → {result.final_chars} chars "
            f"(stage: {result.stage.value})",
            file=sys.stderr,
        )

    # Write the budget-compliant content to stdout
    sys.stdout.write(result.description)
    if result.comments:
        sys.stdout.write("\n")
        sys.stdout.write(result.comments)

    return 0


if __name__ == "__main__":
    sys.exit(main())
