"""PR body and title template utilities.

Provides functions to resolve the PR body and title from user-managed
Jinja2 template files (``.j2``) with variable interpolation and fallback chain.
"""

import sys
from pathlib import Path

import jinja2
import jinja2.meta
import jinja2.sandbox

from ..state import get_value
from .git.core import STATE_LAST_COMMIT_MESSAGE, run_git

# Template location relative to git root
TEMPLATE_RELATIVE_PATH = ".agdt/config/pull-request-template.j2"

# PR title template location relative to git root
PR_TITLE_TEMPLATE_PATH = ".agdt/config/pr-title-template.j2"

# Fallback literal when no commit message is available
FALLBACK_MESSAGE = "No commit message could be found."

# Default template content (German-language operational checklist) - Jinja2 version
DEFAULT_TEMPLATE_CONTENT_J2 = (
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
    "{{ fullCommitMessage }}\n"
)

# Default PR title template content
DEFAULT_PR_TITLE_TEMPLATE = "{{ issueType }}({{ issueKey }}): {{ commitMessageTitle }}\n"


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
    """Get the absolute path to the PR body template file.

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


def get_pr_title_template_path(git_root: Path | None = None) -> Path:
    """Get the absolute path to the PR title template file.

    Args:
        git_root: Optional explicit git root path. If ``None``, resolved
            via ``git rev-parse --show-toplevel``.

    Returns:
        Absolute path to the PR title template file.
    """
    if git_root is None:
        result = run_git("rev-parse", "--show-toplevel", check=False)
        if result.returncode != 0:
            git_root = Path.cwd()
        else:
            git_root = Path(result.stdout.strip())

    return git_root / PR_TITLE_TEMPLATE_PATH


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
    """Resolve the PR body from the Jinja2 template with commit message interpolation.

    Renders ``.agdt/config/pull-request-template.j2`` with ``fullCommitMessage``
    as a template variable. If the template is missing, warns and returns
    just the commit message.

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

    return _render_j2_body_template(content)


def _render_j2_body_template(content: str) -> str:
    """Render a Jinja2 PR body template.

    Args:
        content: The template content string.

    Returns:
        Rendered PR body string.
    """
    message = resolve_full_commit_message()
    context = {"fullCommitMessage": message}

    try:
        env = jinja2.sandbox.SandboxedEnvironment(
            loader=jinja2.BaseLoader(),
            autoescape=False,
            keep_trailing_newline=True,
            undefined=jinja2.Undefined,
        )

        # Warn on unresolved variables (they will render as empty with jinja2.Undefined)
        ast = env.parse(content)
        referenced = jinja2.meta.find_undeclared_variables(ast)
        known_names = set(env.globals.keys())
        missing = referenced - set(context.keys()) - known_names
        for var in sorted(missing):
            print(
                f"Warning: PR body template variable '{var}' is unresolved — it will render as empty in the PR body",
                file=sys.stderr,
            )

        tmpl = env.from_string(content)
        rendered = tmpl.render(context)
    except jinja2.TemplateSyntaxError as exc:
        print(
            f"Warning: PR body template has syntax error: {exc}. Using commit message as PR body.",
            file=sys.stderr,
        )
        return message
    except (jinja2.UndefinedError, jinja2.TemplateRuntimeError) as exc:  # pragma: no cover
        print(
            f"Warning: PR body template rendering failed: {exc}. Using commit message as PR body.",
            file=sys.stderr,
        )
        return message

    return rendered


def resolve_pr_title() -> str | None:
    """Resolve the PR title from the Jinja2 title template.

    Renders ``.agdt/config/pr-title-template.j2`` using the same variable
    resolution as the commit template (issueType, issueKey, commitMessageTitle).

    Returns:
        Rendered PR title string, or ``None`` if the template is missing
        or rendering fails (caller should fall back to existing title logic).
    """
    template_path = get_pr_title_template_path()

    if not template_path.exists():
        return None

    try:
        content = template_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(
            f"Warning: Cannot read PR title template: {exc}",
            file=sys.stderr,
        )
        return None

    if not content.strip():
        return None

    # Build render context from state (reuse commit template variable resolution)
    from .git.commit_template import _resolve_commit_title, _resolve_issue_key, _resolve_issue_type

    context: dict[str, str] = {}

    normalized_key, _raw_key = _resolve_issue_key()
    if normalized_key is not None:
        context["issueKey"] = normalized_key

    issue_type = _resolve_issue_type()
    if issue_type is not None:
        context["issueType"] = issue_type

    title = _resolve_commit_title()
    if title is not None:
        context["commitMessageTitle"] = title

    try:
        env = jinja2.sandbox.SandboxedEnvironment(
            loader=jinja2.BaseLoader(),
            autoescape=False,
            keep_trailing_newline=False,
            undefined=jinja2.StrictUndefined,
        )
        tmpl = env.from_string(content)
        rendered = tmpl.render(context).strip()
    except (jinja2.TemplateSyntaxError, jinja2.UndefinedError, jinja2.TemplateRuntimeError) as exc:
        print(
            f"Warning: PR title template rendering failed: {exc}",
            file=sys.stderr,
        )
        return None

    if not rendered:
        return None

    return rendered


def init_pr_template() -> None:
    """Create the default PR body template if it does not exist.

    CLI entry point for ``agdt-init-pr-template``.
    """
    template_path = get_template_path()

    if template_path.exists():
        print(f"Template already exists at {template_path}")
        return

    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text(DEFAULT_TEMPLATE_CONTENT_J2, encoding="utf-8")
    print(f"Created PR template at {template_path}")


def ensure_pr_title_template(git_root: Path) -> bool:
    """Create the default PR title template if it does not exist.

    Args:
        git_root: Repository root path.

    Returns:
        ``True`` if the template was created, ``False`` if it already existed.
    """
    template_path = git_root / PR_TITLE_TEMPLATE_PATH
    if template_path.is_file():
        return False

    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text(DEFAULT_PR_TITLE_TEMPLATE, encoding="utf-8")
    return True


def ensure_pr_body_template(git_root: Path) -> bool:
    """Create the default PR body template (.j2) if it does not exist.

    If a legacy ``.md`` template exists, it is removed and replaced with the default
    ``.j2`` template during setup.

    Args:
        git_root: Repository root path.

    Returns:
        ``True`` if a repo mutation occurred (default ``.j2`` created and/or legacy ``.md`` removed),
        ``False`` if no changes were needed.
    """
    template_path = git_root / TEMPLATE_RELATIVE_PATH

    legacy_path = git_root / ".agdt/config/pull-request-template.md"
    legacy_backup_path = git_root / ".agdt/config/pull-request-template.md.bak"
    legacy_removed = False
    if legacy_path.is_file():
        try:
            if not legacy_backup_path.exists():
                legacy_backup_path.parent.mkdir(parents=True, exist_ok=True)
                legacy_backup_path.write_bytes(legacy_path.read_bytes())
            legacy_path.unlink()
            legacy_removed = True
        except OSError as exc:
            print(
                f"Warning: Could not migrate/remove legacy PR body template at {legacy_path}: {exc}",
                file=sys.stderr,
            )

    if template_path.is_file():
        return legacy_removed
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text(DEFAULT_TEMPLATE_CONTENT_J2, encoding="utf-8")
    return True
