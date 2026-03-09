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

.. note::

   These functions use :func:`_run_plumbing` (which wraps ``run_safe``
   with ``shell=False``) instead of :func:`~agentic_devtools.cli.git.core.run_git`.
   ``run_git`` calls ``sys.exit`` on failure, which is appropriate for
   CLI entry-points but not for library functions whose callers need to
   catch :class:`GitPlumbingError`.  ``build_tree`` also requires the
   ``env`` parameter (for ``GIT_INDEX_FILE``), which ``run_git`` does
   not support.
"""

import os
import shutil
import tempfile
from subprocess import CompletedProcess
from typing import Any, Dict, Optional

from ..subprocess_utils import run_safe


class GitPlumbingError(Exception):
    """Raised when a git plumbing command fails."""


def _run_plumbing(*args: str, **kwargs: Any) -> CompletedProcess:
    """Run a git plumbing command.

    Wraps :func:`~agentic_devtools.cli.subprocess_utils.run_safe` with
    ``capture_output=True``, ``text=True``, and ``shell=False``.

    Unlike :func:`~agentic_devtools.cli.git.core.run_git` this helper
    does **not** call ``sys.exit`` on failure — callers inspect
    ``returncode`` and raise :class:`GitPlumbingError` as appropriate.

    Args:
        *args: Git sub-command and its arguments (e.g. ``"hash-object"``,
            ``"-w"``, ``"--"``, ``"/tmp/file"``).
        **kwargs: Extra keyword arguments forwarded to ``run_safe``
            (e.g. ``env``).

    Returns:
        :class:`~subprocess.CompletedProcess` with captured output.
    """
    cmd = ["git"] + list(args)
    return run_safe(
        cmd,
        capture_output=True,
        text=True,
        shell=False,
        **kwargs,
    )


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
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        result = _run_plumbing("hash-object", "-w", "--", tmp_path)
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

    Uses a temporary ``GIT_INDEX_FILE`` pointing at a non-existent path
    so the real index (and working directory) are never touched.  Git
    creates the index file on the first ``update-index --add`` call.
    All entries are stored with mode ``100644``.

    Args:
        entries: Mapping of ``path`` → ``blob_sha``.

    Returns:
        The 40-character hex tree SHA.

    Raises:
        GitPlumbingError: If any plumbing command fails.
    """
    # Use a non-existent path inside a temp directory so git creates
    # a fresh index rather than reading an empty (invalid) file.
    tmp_dir = tempfile.mkdtemp()
    tmp_index = os.path.join(tmp_dir, "index")
    try:
        env = dict(os.environ, GIT_INDEX_FILE=tmp_index)
        for path, blob_sha in sorted(entries.items()):
            # Use the three-argument ``--cacheinfo`` form so git parses
            # the path safely, even when it contains commas.
            result = _run_plumbing(
                "update-index",
                "--add",
                "--cacheinfo",
                "100644",
                blob_sha,
                path,
                env=env,
            )
            if result.returncode != 0:
                raise GitPlumbingError(f"git update-index failed for {path}: {result.stderr.strip()}")

        result = _run_plumbing("write-tree", env=env)
        if result.returncode != 0:
            raise GitPlumbingError("git write-tree failed: " + result.stderr.strip())
        sha = result.stdout.strip()
        if not sha:
            raise GitPlumbingError("git write-tree returned empty output")
        return sha
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


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
    cmd_args = ["commit-tree", tree_sha]
    if parent_sha is not None:
        cmd_args += ["-p", parent_sha]
    cmd_args += ["-m", message]

    result = _run_plumbing(*cmd_args)
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
    result = _run_plumbing("update-ref", "refs/heads/" + branch_name, commit_sha)
    if result.returncode != 0:
        raise GitPlumbingError("git update-ref failed: " + result.stderr.strip())


def read_branch_tree(branch_ref: str) -> Dict[str, str]:
    """Read the full file tree of *branch_ref*.

    Resolves the branch to a commit SHA, then runs
    ``git ls-tree -r --full-tree <commit_sha>`` to list every blob.

    Args:
        branch_ref: Branch name (e.g. ``"my-branch-agdt"``).

    Returns:
        A ``{path: blob_sha}`` dict.  Returns an empty dict when the
        branch does not exist.

    Raises:
        GitPlumbingError: If ``git rev-parse`` fails for a reason other
            than a missing ref (e.g. not a git repository), or if
            ``git ls-tree`` fails.
    """
    # Resolve the ref — return {} for missing refs, raise for other failures.
    rev_result = _run_plumbing("rev-parse", "--verify", "refs/heads/" + branch_ref)
    if rev_result.returncode != 0:
        raw_stderr = (rev_result.stderr or "").strip()
        stderr_lower = raw_stderr.lower()
        # Known patterns emitted by ``git rev-parse --verify`` when
        # the ref simply does not exist.
        missing_ref_patterns = (
            "needed a single revision",
            "unknown revision or path not in the working tree",
        )
        if any(pat in stderr_lower for pat in missing_ref_patterns):
            return {}
        # Any other failure (permissions, corrupt repo, etc.) is an error.
        raise GitPlumbingError("git rev-parse failed: " + raw_stderr)

    commit_sha = rev_result.stdout.strip()
    if not commit_sha:
        raise GitPlumbingError("git rev-parse returned empty output")

    result = _run_plumbing("ls-tree", "-r", "--full-tree", commit_sha)
    if result.returncode != 0:
        raise GitPlumbingError("git ls-tree failed: " + result.stderr.strip())

    tree = {}  # type: Dict[str, str]
    for line in result.stdout.splitlines():
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
    return _run_plumbing("push", "origin", branch_name)
