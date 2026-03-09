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
        persist_workflow_state,
        PersistResult,
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
from dataclasses import dataclass
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, Dict, Optional

from ...state import get_value
from ..subprocess_utils import run_safe


class GitPlumbingError(Exception):
    """Raised when a git plumbing command fails."""


@dataclass
class PersistResult:
    """Result of a persist_workflow_state() operation.

    Callers are responsible for using this result to perform any tracking
    actions (posting activity log comments to PR/Jira, updating external
    systems, etc.). The persist layer does NOT perform tracking automatically.

    Example::

        result = persist_workflow_state(
            source_branch="feature/DFLY-1234", worktree_key="DFLY-1234",
        )
        if result.success:
            post_activity_log(
                f"Persisted to {result.branch_name} @ {result.commit_hash}"
            )
        else:
            log_error(f"Persist failed: {result.error}")

    Attributes:
        success: Whether the persist operation completed successfully.
        branch_name: The target -agdt branch name.
        commit_hash: The SHA of the created/amended commit (empty on failure).
        worktree_key: The worktree key used for the persist.
        workflow_type: The workflow type label (may be empty).
        error: Human-readable error message (None on success).
    """

    success: bool = False
    branch_name: str = ""
    commit_hash: str = ""
    worktree_key: str = ""
    workflow_type: str = ""
    error: Optional[str] = None


def _run_plumbing(*args: str, **kwargs: Any) -> CompletedProcess:
    """Run a git plumbing command.

    Wraps :func:`~agentic_devtools.cli.subprocess_utils.run_safe` with
    ``capture_output=True``, ``text=True``, and ``shell=False``.  These
    three parameters are enforced and cannot be overridden via *kwargs*.

    Unlike :func:`~agentic_devtools.cli.git.core.run_git` this helper
    does **not** call ``sys.exit`` on failure — callers inspect
    ``returncode`` and raise :class:`GitPlumbingError` as appropriate.

    Args:
        *args: Git sub-command and its arguments (e.g. ``"hash-object"``,
            ``"-w"``, ``"--"``, ``"/tmp/file"``).
        **kwargs: Extra keyword arguments forwarded to ``run_safe``
            (e.g. ``env``, ``check``).  ``capture_output``, ``text``,
            and ``shell`` are silently stripped — they are always set by
            this function.

    Returns:
        :class:`~subprocess.CompletedProcess` with captured output.
    """
    # Strip security-critical keys so callers cannot weaken the defaults.
    for key in ("capture_output", "text", "shell"):
        kwargs.pop(key, None)
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


def read_branch_tree(branch_name: str) -> Dict[str, str]:
    """Read the full file tree of *branch_name*.

    Resolves the branch to a commit SHA, then runs
    ``git ls-tree -r --full-tree <commit_sha>`` to list every blob.

    Args:
        branch_name: Branch name without ``refs/heads/`` prefix
            (e.g. ``"my-branch-agdt"``).

    Returns:
        A ``{path: blob_sha}`` dict.  Returns an empty dict when the
        branch does not exist.

    Raises:
        GitPlumbingError: If ``git rev-parse`` fails for a reason other
            than a missing ref (e.g. not a git repository), or if
            ``git ls-tree`` fails.
    """
    # Resolve the ref — return {} for missing refs, raise for other failures.
    rev_result = _run_plumbing("rev-parse", "--verify", "refs/heads/" + branch_name)
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
    return _run_plumbing("push", "origin", branch_name, check=False)


# ---------------------------------------------------------------------------
#  Helpers for persist_workflow_state()
# ---------------------------------------------------------------------------


def _get_repo_root() -> Path:
    """Return the git repository root directory.

    Raises:
        GitPlumbingError: If ``git rev-parse --show-toplevel`` fails.
    """
    result = _run_plumbing("rev-parse", "--show-toplevel")
    if result.returncode != 0:
        raise GitPlumbingError("git rev-parse --show-toplevel failed: " + result.stderr.strip())
    toplevel = result.stdout.strip()
    if not toplevel:
        raise GitPlumbingError("git rev-parse --show-toplevel returned empty output")
    return Path(toplevel)


def _discover_workflow_files(repo_root: Path, identity: str, worktree_key: str) -> Dict[str, str]:
    """Walk the workflow directory and hash each file.

    Args:
        repo_root: Absolute path to the repository root.
        identity: Identity segment (e.g. ``"default"``).
        worktree_key: Worktree key segment (e.g. ``"DFLY-1234"``).

    Returns:
        ``{relative_path: blob_sha}`` dict where *relative_path* is
        relative to *repo_root*.
    """
    base = repo_root / ".agdt" / "workflows" / identity / worktree_key
    if not base.is_dir():
        return {}
    files = {}  # type: Dict[str, str]
    for file_path in sorted(base.rglob("*")):
        if not file_path.is_file():
            continue
        content = file_path.read_bytes()
        blob_sha = hash_object(content)
        rel = str(file_path.relative_to(repo_root))
        # Normalise to forward slashes (for Windows compatibility).
        files[rel.replace("\\", "/")] = blob_sha
    return files


def _branch_exists_locally(branch_name: str) -> bool:
    """Return ``True`` if *branch_name* exists as a local ref."""
    result = _run_plumbing("rev-parse", "--verify", "refs/heads/" + branch_name)
    return result.returncode == 0


def _branch_exists_remotely(branch_name: str) -> bool:
    """Return ``True`` if *branch_name* exists on ``origin``."""
    result = _run_plumbing("ls-remote", "--heads", "origin", branch_name)
    return result.returncode == 0 and bool(result.stdout.strip())


def _read_commit_message(commit_sha: str) -> str:
    """Read the commit message body of *commit_sha*.

    Returns an empty string if the commit cannot be read.
    """
    result = _run_plumbing("cat-file", "commit", commit_sha)
    if result.returncode != 0:
        return ""
    parts = result.stdout.split("\n\n", 1)
    if len(parts) < 2:
        return ""
    return parts[1]


def _has_matching_run_id(commit_sha: str, run_id: str) -> bool:
    """Return ``True`` if *commit_sha*'s message contains a matching Run-Id trailer."""
    msg = _read_commit_message(commit_sha)
    return "Run-Id: " + run_id in msg


def _get_parent_sha(commit_sha: str) -> Optional[str]:
    """Return the parent SHA of *commit_sha*, or ``None`` if it has no parent."""
    result = _run_plumbing("rev-parse", commit_sha + "~1")
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha if sha else None


# ---------------------------------------------------------------------------
#  persist_workflow_state()
# ---------------------------------------------------------------------------

_MAX_PUSH_ATTEMPTS = 3


def persist_workflow_state(
    source_branch: str,
    worktree_key: Optional[str] = None,
    workflow_type: str = "",
    identity: Optional[str] = None,
    commit_message: str = "",
) -> PersistResult:
    """Persist workflow artifacts to the ``-agdt`` branch.

    Walks ``.agdt/workflows/{identity}/{worktree_key}/`` on disk, hashes
    every file into the git object store, commits the result to
    ``{source_branch}-agdt`` (creating the branch when necessary), and
    pushes to ``origin``.

    Within the same workflow run (matching ``Run-Id:`` trailer in the
    HEAD commit message) the commit is *amended* (same parent as HEAD)
    rather than stacked.

    Args:
        source_branch: The feature branch this state belongs to.
        worktree_key: The worktree key (e.g. Jira issue key).  Required.
        workflow_type: Workflow type label for the commit message.
        identity: Identity segment.  Defaults to ``"default"``.
        commit_message: Custom commit message.  Auto-generated when empty.

    Returns:
        A :class:`PersistResult` indicating success or failure.
    """
    # 1. Validate worktree_key ------------------------------------------------
    if worktree_key is None:
        return PersistResult(
            success=False,
            error=("worktree_key is required. Auto-resolution will be available via resolve_worktree_key()."),
        )

    # 2. Defaults -------------------------------------------------------------
    identity = identity or "default"
    wf_label = workflow_type or "workflow"

    # 3. Target branch (double-suffix prevention) -----------------------------
    if source_branch.endswith("-agdt"):
        target_branch = source_branch
    else:
        target_branch = source_branch + "-agdt"

    base_result = PersistResult(
        branch_name=target_branch,
        worktree_key=worktree_key,
        workflow_type=workflow_type,
    )

    try:
        # 4. Repo root & file discovery ---------------------------------------
        repo_root = _get_repo_root()
        updates = _discover_workflow_files(repo_root, identity, worktree_key)
        if not updates:
            base_result.error = f"No workflow files found under .agdt/workflows/{identity}/{worktree_key}/"
            return base_result

        # 5. Branch setup -----------------------------------------------------
        branch_is_new = False
        if _branch_exists_locally(target_branch):
            pass  # proceed normally
        elif _branch_exists_remotely(target_branch):
            _run_plumbing(
                "fetch",
                "origin",
                target_branch + ":" + target_branch,
            )
        else:
            branch_is_new = True

        # 6. Read existing tree and merge updates -----------------------------
        if branch_is_new:
            existing_tree = {}  # type: Dict[str, str]
        else:
            existing_tree = read_branch_tree(target_branch)
        merged = dict(existing_tree, **updates)
        tree_sha = build_tree(merged)

        # 7. Commit message + Run-Id trailer ----------------------------------
        if not commit_message:
            commit_message = f"agdt: persist {wf_label} state for {worktree_key}"

        run_id = get_value("agdt_run_id")
        if run_id:
            full_message = commit_message + "\n\nRun-Id: " + str(run_id)
        else:
            full_message = commit_message

        # 8. Determine parent (amend vs new commit) ---------------------------
        is_amend = False
        if branch_is_new:
            # Parent = source branch HEAD (or None if source doesn't exist).
            src_result = _run_plumbing("rev-parse", source_branch)
            src_sha = src_result.stdout.strip() if src_result.returncode == 0 else ""
            parent_sha = src_sha or None
        else:
            head_result = _run_plumbing("rev-parse", target_branch)
            head_sha = head_result.stdout.strip() if head_result.returncode == 0 else ""
            if head_sha and run_id and _has_matching_run_id(head_sha, str(run_id)):
                is_amend = True
                parent_sha = _get_parent_sha(head_sha)
            else:
                parent_sha = head_sha or None

        # 9. Create commit & update ref ---------------------------------------
        commit_sha = create_commit(tree_sha, parent_sha, full_message)
        update_ref(target_branch, commit_sha)

        # 10. Push (with retry on rejection) ----------------------------------
        for attempt in range(_MAX_PUSH_ATTEMPTS):
            if is_amend:
                push_result = _run_plumbing(
                    "push",
                    "--force-with-lease",
                    "origin",
                    target_branch,
                    check=False,
                )
            else:
                push_result = push_branch(target_branch)

            if push_result.returncode == 0:
                base_result.success = True
                base_result.commit_hash = commit_sha
                return base_result

            # Push rejected — fetch, re-merge, re-commit, retry.
            _run_plumbing("fetch", "origin", target_branch, check=False)

            remote_head_result = _run_plumbing("rev-parse", "origin/" + target_branch)
            if remote_head_result.returncode != 0:
                continue  # nothing to rebase onto; retry push

            remote_head = remote_head_result.stdout.strip()
            remote_tree = read_branch_tree("origin/" + target_branch)
            merged = dict(remote_tree, **updates)
            tree_sha = build_tree(merged)

            if is_amend:
                parent_sha = _get_parent_sha(remote_head)
            else:
                parent_sha = remote_head

            commit_sha = create_commit(tree_sha, parent_sha, full_message)
            update_ref(target_branch, commit_sha)

        # All retries exhausted.
        stderr = (push_result.stderr or "").strip()
        base_result.error = f"Push failed after {_MAX_PUSH_ATTEMPTS} attempts: {stderr}"
        return base_result

    except GitPlumbingError as exc:
        base_result.error = str(exc)
        return base_result
    except Exception as exc:
        base_result.error = str(exc)
        return base_result
