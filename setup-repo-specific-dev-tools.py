#!/usr/bin/env python3
"""Repo-specific development tool setup.

This file is YOURS — agentic-devtools will never overwrite it.
Add any repository-specific setup steps below (e.g., installing
project-specific linters, database migrations, or build tools).

It is called automatically by ``setup-dev-tools.py`` after the
managed agentic-devtools setup completes.

Supports: ``--foreground`` (default, forward-compatible no-op).
"""

import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Repo-specific development tool setup.",
    )
    parser.add_argument(
        "--foreground",
        action="store_true",
        default=False,
        help="Run in foreground (default, forward-compatible).",
    )
    parser.parse_args()

    print("  ℹ No repo-specific dev tools configured.")
    print("    Edit setup-repo-specific-dev-tools.py to add your own setup steps.")


if __name__ == "__main__":
    main()
