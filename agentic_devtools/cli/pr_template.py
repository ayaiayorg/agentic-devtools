"""
PR body template utilities.

Provides functions to resolve the PR body from a user-managed template file
with commit message interpolation and fallback chain.
"""

import sys
from pathlib import Path

from ..state import get_value
from .git.core import STATE_LAST_COMMIT_MESSAGE, run_git

# Template location relative to git root
TEMPLATE_RELATIVE_PATH = ".agdt/config/pull-request-template.md"

# Placeholder for commit message interpolation
PLACEHOLDER = "{{fullCommitMessage}}"

# Fallback literal when no commit message is available
FALLBACK_MESSAGE = "No commit message could be found."

# Default template content (German-language operational checklist)
DEFAULT_TEMPLATE_CONTENT = (
    "# Pull Request\n"
    "\n"
    "## **Checkliste für Schnittmenge mit dem Betrieb**\n"
    "\n"
    "1. **Getestet**\n"
    "\n"
    "   - [ ] Die Änderungen wurden ausgiebig lokal getestet"
    " und falls möglich/sinnvoll auch auf dev schon ausgeführt.\n"
    "   - [ ] Falls möglich/sinnvoll, wurden automatisierte Tests hinzugefügt,"
    " die das korrekte Verhalten der Changes bestätigen.\n"
    "\n"
    "1. **Database Schema Changes**\n"
    "\n"
    "   - [ ] Änderungen am Datenbank-Schema aus der Management oder sonstigen DB"
    " (z. B. Ad-hoc-Feld in Workbenches)"
    " wurden in der CLI und dem WB-Setup-Skript berücksichtigt.\n"
    "\n"
    "1. **Mgmt-CLI Updates**\n"
    "\n"
    "   - [ ] Anpassungen an der Mgmt-CLI wie neue Parameter für bestehende Endpunkte"
    " wurden im setup Skript oder in der Confluence Doku z.B"
    " <https://confluence.swica.ch/display/DPE/Workbench+Erstellung> aktualisiert.\n"
    "\n"
    "1. **Workbench Infrastruktur Updates**\n"
    "\n"
    "   - [ ] Anpassungen an der Workbench-Infrastruktur wurden ebenfalls"
    " im `wb-env`-Template vorgenommen.\n"
    "\n"
    "1. **Infrastruktur Kommunikation**\n"
    "\n"
    "   - [ ] Änderungen an der Infrastruktur"
    " (z. B. Synapse-Komponenten oder das Abstellen von Logical)"
    " wurden kommuniziert,"
    " sodass Automatisierungsskripte entsprechend angepasst werden können.\n"
    "\n"
    "1. **Dokumentation**\n"
    "   - [ ] Technische Dokumentation wurde ergänzt"
    " und ist unten als Kommentar angehängt für Review.\n"
    "   - [ ] User Dokumentation wurde ergänzt"
    " und ist unten als Kommentar angehängt für Review.\n"
    "\n"
    "---\n"
    "\n"
    "## Zusatzinformationen\n"
    "\n"
    f"{PLACEHOLDER}\n"
)


def resolve_main_ref() -> str | None:
    """Resolve the main branch reference.

    Tries ``origin/main`` first, then ``main``.

    Returns:
        The ref string if found, or ``None`` if neither exists.
    """
    result = run_git("rev-parse", "--verify", "origin/main", check=False)
    if result.returncode == 0:
        return "origin/main"

    result = run_git("rev-parse", "--verify", "main", check=False)
    if result.returncode == 0:
        return "main"

    return None


def get_template_path(git_root: Path | None = None) -> Path:
    """Get the absolute path to the PR template file.

    Args:
        git_root: Optional explicit git root path. If ``None``, resolved
            via ``git rev-parse --show-toplevel``.

    Returns:
        Absolute path to the template file.
    """
    if git_root is None:
        result = run_git("rev-parse", "--show-toplevel", check=False)
        if result.returncode != 0:
            # Fallback to cwd if not in a git repo
            git_root = Path.cwd()
        else:
            git_root = Path(result.stdout.strip())

    return git_root / TEMPLATE_RELATIVE_PATH


def resolve_full_commit_message() -> str:
    """Resolve the full commit message using the fallback chain.

    Fallback order:
        1. State key ``git.last_commit_message``
        2. ``git log --format=%B origin/main..HEAD`` (aggregated with ``---`` separator)
        3. Literal fallback message

    Returns:
        The resolved commit message string.
    """
    # Step 1: Check state
    state_message = get_value(STATE_LAST_COMMIT_MESSAGE)
    if state_message and str(state_message).strip():
        return str(state_message).rstrip("\n")

    # Step 2: Try git log
    ref = resolve_main_ref()
    if ref is not None:
        result = run_git("log", "--format=%B%x1e", f"{ref}..HEAD", check=False)
        if result.returncode == 0 and result.stdout.strip():
            raw = result.stdout
            # Split on record separator and filter empty entries
            commits = [c.rstrip("\n") for c in raw.split("\x1e") if c.strip()]
            if commits:  # pragma: no branch
                return "\n\n---\n\n".join(commits)

    # Step 3: Literal fallback
    return FALLBACK_MESSAGE


def resolve_pr_body() -> str:
    """Resolve the PR body from template with commit message interpolation.

    Loads the template file and replaces ``{{fullCommitMessage}}`` with the
    resolved commit message. If the template is missing, warns and returns
    just the commit message. If the template has no placeholder, returns
    the template content as-is.

    Returns:
        The final PR body string.
    """
    template_path = get_template_path()

    if not template_path.exists():
        print(
            f"Warning: PR template not found at {template_path}. Run 'agdt-init-pr-template' to create it.",
            file=sys.stderr,
        )
        return resolve_full_commit_message()

    try:
        content = template_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(
            f"Warning: Could not read PR template at {template_path}: {exc}. Using commit message as PR body.",
            file=sys.stderr,
        )
        return resolve_full_commit_message()

    if not content.strip():
        return resolve_full_commit_message()

    if PLACEHOLDER in content:
        message = resolve_full_commit_message()
        return content.replace(PLACEHOLDER, message)

    return content


def init_pr_template() -> None:
    """Create the default PR template if it does not exist.

    CLI entry point for ``agdt-init-pr-template``.
    """
    template_path = get_template_path()

    if template_path.exists():
        print(f"Template already exists at {template_path}")
        return

    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text(DEFAULT_TEMPLATE_CONTENT, encoding="utf-8")
    print(f"Created PR template at {template_path}")
