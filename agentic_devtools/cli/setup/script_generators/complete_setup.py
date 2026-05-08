"""Generator for ``agentic-devtools-complete-setup.py``.

The generated script orchestrates ``required-setup`` → ``configured-setup``
with fail-fast semantics.
"""

from __future__ import annotations

from .constants import CONFIGURED_SETUP_FILENAME, REQUIRED_SETUP_FILENAME


def generate_complete_setup_script() -> str:
    """Return the full content of ``agentic-devtools-complete-setup.py``."""
    return _COMPLETE_TEMPLATE.format(
        required=REQUIRED_SETUP_FILENAME,
        configured=CONFIGURED_SETUP_FILENAME,
    )


_COMPLETE_TEMPLATE = '''\
#!/usr/bin/env python3
"""agentic-devtools complete setup — orchestrator.

Calls required-setup then configured-setup with fail-fast semantics.
If required-setup fails, configured-setup is NOT executed.

This script is managed by agentic-devtools and regenerated on every
``agdt-setup`` run.  DO NOT EDIT — your changes will be overwritten.

Supports: ``--foreground`` (default, forward-compatible no-op).
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="agentic-devtools complete setup — orchestrator.",
    )
    parser.add_argument(
        "--foreground", action="store_true", default=True,
        help="Run in foreground (default, forward-compatible).",
    )
    parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    foreground_args = ["--foreground"]

    # Step 1: Required setup (fail-fast)
    required = script_dir / "{required}"
    if not required.exists():
        print(f"  ✗ Required setup script not found: {{required}}", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(
        [sys.executable, str(required)] + foreground_args,
    )
    if result.returncode != 0:
        print(
            "  ✗ Required setup failed — skipping configured setup.",
            file=sys.stderr,
        )
        sys.exit(result.returncode)

    # Step 2: Configured setup
    configured = script_dir / "{configured}"
    if not configured.exists():
        print(f"  ✗ Configured setup script not found: {{configured}}", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(
        [sys.executable, str(configured)] + foreground_args,
    )
    if result.returncode != 0:
        print("  ✗ Configured setup failed.", file=sys.stderr)
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
'''
