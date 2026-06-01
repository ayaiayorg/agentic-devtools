#!/usr/bin/env python3
"""Development environment setup — entry point.

This script is managed by agentic-devtools and regenerated on every
``agdt-setup`` run.  DO NOT EDIT — your changes will be overwritten.

Calls ``.agdt/agentic-devtools-complete-setup.py`` (managed) then
``setup-repo-specific-dev-tools.py`` (customer-owned) with fail-fast
semantics: if the complete-setup script fails, the repo-specific
script is NOT executed.

Supports: ``--foreground`` (default, forward-compatible no-op).
"""

# AGDT-MANAGED-ORCHESTRATOR

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Development environment setup.",
    )
    parser.add_argument(
        "--foreground",
        action="store_true",
        default=False,
        help="Run in foreground (default, forward-compatible no-op).",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    foreground_args = ["--foreground"] if args.foreground else []
    # Step 1: Complete setup (managed by agentic-devtools)
    agdt_dir = repo_root / ".agdt"
    if not agdt_dir.is_dir():
        print(
            "  ✗ .agdt/ directory not found. Run 'agdt-setup' first to generate the required setup scripts.",
            file=sys.stderr,
        )
        sys.exit(1)

    complete = agdt_dir / "agentic-devtools-complete-setup.py"
    if not complete.exists():
        print(
            f"  ✗ Complete setup script not found: {complete}\n    Run 'agdt-setup' to regenerate setup scripts.",
            file=sys.stderr,
        )
        sys.exit(1)

    result = subprocess.run(
        [sys.executable, str(complete)] + foreground_args,
        cwd=str(repo_root),
    )
    if result.returncode != 0:
        print(
            "  ✗ Complete setup failed — skipping repo-specific setup.",
            file=sys.stderr,
        )
        sys.exit(result.returncode)

    # Step 2: Repo-specific setup (customer-owned, optional)
    repo_specific = repo_root / "setup-repo-specific-dev-tools.py"
    if repo_specific.exists():
        result = subprocess.run(
            [sys.executable, str(repo_specific)] + foreground_args,
            cwd=str(repo_root),
        )
        if result.returncode != 0:
            print("  ✗ Repo-specific setup failed.", file=sys.stderr)
            sys.exit(result.returncode)
    else:
        print("  ℹ No repo-specific setup found (setup-repo-specific-dev-tools.py).")


if __name__ == "__main__":
    main()
