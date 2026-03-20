"""SqliteSaver checkpoint configuration for LangGraph workflows."""

import os
import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from agentic_devtools.state import _get_git_repo_root


def get_checkpointer(db_path: str | None = None) -> SqliteSaver:
    """Create a SqliteSaver checkpointer for durable workflow state.

    Args:
        db_path: Path to the SQLite database file. Defaults to
            ``.agdt/orchestration.db`` relative to the git repository/worktree
            root when available, otherwise relative to the current working
            directory.

    Returns:
        A configured ``SqliteSaver`` instance with the schema initialized.
    """
    if db_path is None:
        root = _get_git_repo_root() or Path.cwd()
        resolved = root / ".agdt" / "orchestration.db"
    else:
        resolved = Path(db_path)

    os.makedirs(resolved.parent, exist_ok=True)

    conn = sqlite3.connect(str(resolved), check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()
    return saver
