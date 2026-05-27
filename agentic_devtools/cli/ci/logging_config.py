"""Logging configuration for CI orchestration commands.

Provides shared logging setup used by ``ai_pr_loop_command()`` and
``speckit_trigger_command()`` entry points so that Python log output
is visible in GitHub Actions job logs.
"""

from __future__ import annotations

import contextlib
import logging
import os
import sys
from collections.abc import Generator

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_LOG_DATEFMT = "%H:%M:%S"

_logger = logging.getLogger(__name__)


def is_github_actions() -> bool:
    """Return True when running inside GitHub Actions."""
    return os.environ.get("GITHUB_ACTIONS") == "true"


def setup_logging() -> None:
    """Configure root logger for CI output visibility.

    Idempotent: does nothing if the root logger already has handlers
    (e.g. from a test harness or prior call).

    Reads the ``AGDT_LOG_LEVEL`` environment variable to override the
    default INFO level.  Invalid level names emit a warning and fall
    back to INFO.
    """
    root = logging.getLogger()
    if root.handlers:
        return

    level_name = os.environ.get("AGDT_LOG_LEVEL", "INFO").upper()
    level = logging.getLevelName(level_name)
    if not isinstance(level, int):
        # getLevelName returns the string "Level X" for unknown names
        logging.basicConfig(
            level=logging.INFO,
            format=_LOG_FORMAT,
            datefmt=_LOG_DATEFMT,
            stream=sys.stderr,
        )
        _logger.warning(
            "Invalid AGDT_LOG_LEVEL %r — falling back to INFO",
            level_name,
        )
        return

    logging.basicConfig(
        level=level,
        format=_LOG_FORMAT,
        datefmt=_LOG_DATEFMT,
        stream=sys.stderr,
    )


@contextlib.contextmanager
def log_group(title: str) -> Generator[None, None, None]:
    """Context manager that emits GitHub Actions group annotations.

    Emits ``::group::{title}`` on entry and ``::endgroup::`` on exit
    when running inside GitHub Actions.  Outside Actions, this is a
    no-op.  Uses ``try/finally`` to guarantee cleanup even on exception.
    """
    if is_github_actions():
        print(f"::group::{title}", file=sys.stderr, flush=True)
    try:
        yield
    finally:
        if is_github_actions():
            print("::endgroup::", file=sys.stderr, flush=True)
