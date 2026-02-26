"""
Speckit command implementations.

Each command reads the corresponding ``.github/prompts/speckit.<name>.prompt.md``
template, strips its YAML frontmatter, replaces ``$ARGUMENTS`` with the
arguments the user supplied on the CLI, then starts an interactive
``gh copilot`` session.
"""

import re
import sys
from pathlib import Path
from typing import Optional

from ...state import _get_git_repo_root


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)


def _load_prompt(name: str, arguments: str) -> str:
    """
    Load a speckit agent template and substitute ``$ARGUMENTS``.

    Reads from ``.github/agents/speckit.<name>.agent.md`` (the full agent
    content) rather than the thin ``.github/prompts/`` router files.

    Args:
        name: Speckit command name, e.g. ``"specify"``.
        arguments: User-supplied arguments string (may be empty).

    Returns:
        Rendered prompt text.

    Raises:
        SystemExit: If the repo root or agent file cannot be found.
    """
    repo_root = _get_git_repo_root()
    if repo_root is None:
        print("ERROR: Not inside a git repository.", file=sys.stderr)
        sys.exit(1)

    agent_file = repo_root / ".github" / "agents" / f"speckit.{name}.agent.md"
    if not agent_file.exists():
        print(f"ERROR: Agent file not found: {agent_file}", file=sys.stderr)
        sys.exit(1)

    content = agent_file.read_text(encoding="utf-8")
    # Strip YAML frontmatter (between leading --- and closing ---)
    content = _FRONTMATTER_RE.sub("", content, count=1)
    # Replace $ARGUMENTS placeholder
    content = content.replace("$ARGUMENTS", arguments)
    return content


def _run(name: str, arguments: str) -> None:
    """
    Load prompt for *name*, print it to stdout, and save it to scripts/temp/.

    Printing to stdout lets the Copilot CLI agent (running in the terminal)
    see the prompt and act on it immediately, without spawning a nested
    ``gh copilot`` process.

    Args:
        name: Speckit command name.
        arguments: User-supplied arguments string.
    """
    prompt = _load_prompt(name, arguments)
    repo_root = _get_git_repo_root()

    # Save to scripts/temp/ so the prompt can be referenced later
    if repo_root is not None:
        temp_dir = repo_root / "scripts" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        saved_path = temp_dir / f"temp-speckit-{name}-prompt.md"
        saved_path.write_text(prompt, encoding="utf-8")
        save_notice = f"\n[Prompt saved to: {saved_path}]"
    else:
        save_notice = ""

    separator = "=" * 80
    print(f"\n{separator}")
    print(f"SPECKIT: {name.upper()}")
    print(separator)
    print(prompt)
    print(separator)
    print(save_notice)


def _parse_args(argv: Optional[list] = None) -> str:
    """Return remaining CLI args joined as a single string."""
    args = argv if argv is not None else sys.argv[1:]
    return " ".join(args)


# ---------------------------------------------------------------------------
# Command entry points
# ---------------------------------------------------------------------------


def speckit_specify(argv: Optional[list] = None) -> None:
    """agdt-speckit-specify — create or update a feature specification."""
    _run("specify", _parse_args(argv))


def speckit_plan(argv: Optional[list] = None) -> None:
    """agdt-speckit-plan — generate an implementation plan."""
    _run("plan", _parse_args(argv))


def speckit_tasks(argv: Optional[list] = None) -> None:
    """agdt-speckit-tasks — generate actionable tasks from design artifacts."""
    _run("tasks", _parse_args(argv))


def speckit_implement(argv: Optional[list] = None) -> None:
    """agdt-speckit-implement — execute the implementation plan."""
    _run("implement", _parse_args(argv))


def speckit_clarify(argv: Optional[list] = None) -> None:
    """agdt-speckit-clarify — identify underspecified areas in the spec."""
    _run("clarify", _parse_args(argv))


def speckit_checklist(argv: Optional[list] = None) -> None:
    """agdt-speckit-checklist — generate a custom checklist for the feature."""
    _run("checklist", _parse_args(argv))


def speckit_analyze(argv: Optional[list] = None) -> None:
    """agdt-speckit-analyze — cross-artifact consistency and quality analysis."""
    _run("analyze", _parse_args(argv))


def speckit_constitution(argv: Optional[list] = None) -> None:
    """agdt-speckit-constitution — create or update the project constitution."""
    _run("constitution", _parse_args(argv))


def speckit_taskstoissues(argv: Optional[list] = None) -> None:
    """agdt-speckit-taskstoissues — convert tasks to GitHub issues."""
    _run("taskstoissues", _parse_args(argv))
