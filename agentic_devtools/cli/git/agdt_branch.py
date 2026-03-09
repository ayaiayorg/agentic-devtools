"""
Git plumbing utilities for -agdt branch commits.

Low-level functions that create/update commits on a branch ref **without
checking it out**, preserving the current working directory state.  All
operations work directly on the git object store using plumbing commands.

Consumers import directly from this module::

    from agentic_devtools.cli.git.agdt_branch import (
        hash_object,
        build_tree,
        create_commit,
        update_ref,
        read_branch_tree,
        push_branch,
    )
"""

import os
import tempfile
from subprocess import CompletedProcess
from typing import Dict, Optional

from ..subprocess_utils import run_safe


class GitPlumbingError(Exception):
    """Raised when a git plumbing command fails."""


def hash_object(content: bytes) -> str:
    """Add *content* to the git object store and return the blob SHA.

    Writes a temporary file and runs ``git hash-object -w -- <file>``.

    Args:
        content: Raw bytes to store as a blob.

    Returns:
        The 40-character hex blob SHA.

    Raises:
        GitPlumbingError: If the command fails or returns empty output.
    """
    fd, tmp_path = tempfile.mkstemp()
    try:
        os.write(fd, content)
        os.close(fd)
        result = run_safe(
            ["git", "hash-object", "-w", "--", tmp_path],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise GitPlumbingError("git hash-object failed: " + result.stderr.strip())
        sha = result.stdout.strip()
        if not sha:
            raise GitPlumbingError("git hash-object returned empty output")
        return sha
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def build_tree(entries: Dict[str, str]) -> str:
    """Build a git tree object from *{path: blob_sha}* entries.

    Uses a temporary ``GIT_INDEX_FILE`` so the real index (and working
    directory) are never touched.  All entries are stored with mode
    ``100644``.

    Args:
        entries: Mapping of ``path`` → ``blob_sha``.

    Returns:
        The 40-character hex tree SHA.

    Raises:
        GitPlumbingError: If any plumbing command fails.
    """
    fd, tmp_index = tempfile.mkstemp()
    os.close(fd)
    try:
        env = dict(os.environ, GIT_INDEX_FILE=tmp_index)
        for path, blob_sha in sorted(entries.items()):
            result = run_safe(
                [
                    "git",
                    "update-index",
                    "--add",
                    "--cacheinfo",
                    f"100644,{blob_sha},{path}",
                ],
                capture_output=True,
                text=True,
                env=env,
            )
            if result.returncode != 0:
                raise GitPlumbingError(f"git update-index failed for {path}: {result.stderr.strip()}")

        result = run_safe(
            ["git", "write-tree"],
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            raise GitPlumbingError("git write-tree failed: " + result.stderr.strip())
        sha = result.stdout.strip()
        if not sha:
            raise GitPlumbingError("git write-tree returned empty output")
        return sha
    finally:
        try:
            os.unlink(tmp_index)
        except OSError:
            pass


def create_commit(
    tree_sha: str,
    parent_sha: Optional[str],
    message: str,
) -> str:
    """Create a commit object pointing at *tree_sha*.

    Runs ``git commit-tree``.  If *parent_sha* is provided the new
    commit is linked to it; otherwise an orphan (root) commit is created.

    Args:
        tree_sha: SHA of the tree object for this commit.
        parent_sha: SHA of the parent commit, or ``None`` for a root commit.
        message: The commit message.

    Returns:
        The 40-character hex commit SHA.

    Raises:
        GitPlumbingError: If the command fails or returns empty output.
    """
    cmd = ["git", "commit-tree", tree_sha]
    if parent_sha is not None:
        cmd += ["-p", parent_sha]
    cmd += ["-m", message]

    result = run_safe(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise GitPlumbingError("git commit-tree failed: " + result.stderr.strip())
    sha = result.stdout.strip()
    if not sha:
        raise GitPlumbingError("git commit-tree returned empty output")
    return sha


def update_ref(branch_name: str, commit_sha: str) -> None:
    """Point *branch_name* at *commit_sha*.

    Runs ``git update-ref refs/heads/<branch_name> <commit_sha>``.

    Args:
        branch_name: Branch name (without ``refs/heads/`` prefix).
        commit_sha: The commit SHA to point the ref at.

    Raises:
        GitPlumbingError: If the command fails.
    """
    result = run_safe(
        ["git", "update-ref", "refs/heads/" + branch_name, commit_sha],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitPlumbingError("git update-ref failed: " + result.stderr.strip())


def read_branch_tree(branch_ref: str) -> Dict[str, str]:
    """Read the full file tree of *branch_ref*.

    Resolves the branch to a commit SHA, then runs
    ``git ls-tree -r <commit_sha>`` to list every blob.

    Args:
        branch_ref: Branch name (e.g. ``"my-branch-agdt"``).

    Returns:
        A ``{path: blob_sha}`` dict.  Returns an empty dict when the
        branch does not exist.

    Raises:
        GitPlumbingError: If ``git ls-tree`` fails for a reason other
            than a missing ref.
    """
    # Resolve the ref — if it doesn't exist, return empty dict.
    rev_result = run_safe(
        ["git", "rev-parse", "--verify", "refs/heads/" + branch_ref],
        capture_output=True,
        text=True,
    )
    if rev_result.returncode != 0:
        return {}

    commit_sha = rev_result.stdout.strip()
    if not commit_sha:
        return {}

    result = run_safe(
        ["git", "ls-tree", "-r", commit_sha],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitPlumbingError("git ls-tree failed: " + result.stderr.strip())

    tree = {}  # type: Dict[str, str]
    for line in result.stdout.splitlines():
        if not line:
            continue
        # Format: "<mode> <type> <sha>\t<path>"
        meta, path = line.split("\t", 1)
        parts = meta.split()
        blob_sha = parts[2]
        tree[path] = blob_sha
    return tree


def push_branch(branch_name: str) -> CompletedProcess:
    """Push *branch_name* to ``origin``.

    Runs ``git push origin <branch_name>`` with ``check=False`` so the
    caller can inspect the result.

    Args:
        branch_name: Branch name to push.

    Returns:
        The :class:`~subprocess.CompletedProcess` from the push command.
    """
    return run_safe(
        ["git", "push", "origin", branch_name],
        capture_output=True,
        text=True,
    )
