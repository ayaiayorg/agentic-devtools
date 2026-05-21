"""Dependency preflight validation for the LangChain review engine.

Validates that required packages are importable and configuration is present
before attempting to run the LangGraph review pipeline.
"""

from __future__ import annotations

import sys


def validate_langchain_dependencies() -> bool:
    """Validate that LangChain/LangGraph dependencies are available.

    Checks:
    1. ``langchain_core`` is importable
    2. ``langgraph`` is importable

    Returns:
        True if all dependencies are satisfied.

    Raises:
        SystemExit: With actionable error message if dependencies are missing.
    """
    missing = []

    try:
        import langchain_core  # noqa: F401
    except ImportError:
        missing.append("langchain-core")

    try:
        import langgraph  # noqa: F401
    except ImportError:
        missing.append("langgraph")

    if missing:
        print(
            f"ERROR: Missing required packages for LangChain review engine: {', '.join(missing)}",
            file=sys.stderr,
        )
        print(
            '\nTo install, run:\n  pip install "agentic-devtools[langchain]"',
            file=sys.stderr,
        )
        sys.exit(1)

    return True
