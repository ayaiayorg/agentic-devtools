"""Jinja2-based commit message template rendering.

Resolves commit messages from a ``.agdt/config/commit-template.j2`` template
using workflow state variables. Falls back gracefully when the template is
missing, empty, or contains errors.

Priority chain (implemented in ``commit_cmd()``):
1. ``--commit-message`` CLI argument
2. Template rendering via ``resolve_commit_message_from_template()``
3. ``commit_message`` state key fallback
"""

from __future__ import annotations

import sys
from pathlib import Path

import jinja2
import jinja2.meta
import jinja2.sandbox

from ...state import get_value
from ..github.repo_resolution import resolve_github_repo_safe
from .core import run_git

# Path to the commit template relative to git root
TEMPLATE_PATH = ".agdt/config/commit-template.j2"

# Variables that the default template references
REQUIRED_VARIABLES = frozenset({"issueType", "issueKey", "issueLink", "commitMessageTitle", "commitMessageBody"})

# Subset of REQUIRED_VARIABLES whose absence produces a structurally malformed
# commit message (e.g., broken markdown links, missing description).  When any
# of these is referenced by a template but absent from the render context,
# resolve_commit_message_from_template() returns None so the caller falls back
# to the commit_message state key rather than emitting a malformed message.
# commitMessageBody is intentionally excluded — an absent body is valid and
# simply results in blank lines.
HARD_REQUIRED_VARIABLES = REQUIRED_VARIABLES - {"commitMessageBody"}

# Default mapping from Jira issue type → conventional commit type prefix
DEFAULT_JIRA_TYPE_MAPPING: dict[str, str] = {
    "Bug": "fix",
    "bug": "fix",
    "Defect": "fix",
    "defect": "fix",
    "Story": "feat",
    "story": "feat",
    "Feature": "feat",
    "feature": "feat",
    "Task": "chore",
    "task": "chore",
    "Sub-task": "chore",
    "sub-task": "chore",
    "Epic": "feat",
    "epic": "feat",
    "Improvement": "feat",
    "improvement": "feat",
    "Documentation": "docs",
    "documentation": "docs",
    "Technical task": "chore",
    "technical task": "chore",
}


def resolve_commit_message_from_template(git_root: Path | None = None) -> str | None:
    """Resolve a commit message by rendering the Jinja2 template.

    Args:
        git_root: Git repository root. Discovered automatically if ``None``.

    Returns:
        Rendered commit message string, or ``None`` when the template does
        not exist or rendering fails (caller should fall back).
    """
    if git_root is None:
        git_root = _discover_git_root()
        if git_root is None:
            return None

    template_content = _load_template(git_root)
    if template_content is None:
        return None

    context = _build_render_context(git_root)
    missing_required = _get_missing_required_variables(context, template_content)
    if missing_required:
        for var in sorted(missing_required):
            print(
                f"Warning: Required template variable '{var}' is unresolved — falling back to commit_message state key",
                file=sys.stderr,
            )
        return None
    _warn_unresolved_variables(context, template_content)

    try:
        env = jinja2.sandbox.SandboxedEnvironment(
            loader=jinja2.BaseLoader(),
            autoescape=False,  # nosec B701 — commit messages are plain text
            keep_trailing_newline=True,
            undefined=jinja2.Undefined,
        )
        tmpl = env.from_string(template_content)
        rendered = tmpl.render(context)
    except jinja2.TemplateSyntaxError as exc:
        print(
            f"Warning: Commit template has syntax error: {exc}",
            file=sys.stderr,
        )
        return None
    except jinja2.UndefinedError as exc:
        print(
            f"Warning: Commit template rendering failed (undefined variable): {exc}",
            file=sys.stderr,
        )
        return None
    except jinja2.TemplateRuntimeError as exc:
        print(
            f"Warning: Commit template runtime error: {exc}",
            file=sys.stderr,
        )
        return None
    except Exception as exc:
        print(
            f"Warning: Unexpected commit template rendering error: {exc}",
            file=sys.stderr,
        )
        return None

    # Strip trailing whitespace but preserve intentional structure
    rendered = rendered.rstrip()
    if not rendered:
        print(
            "Warning: Commit template rendered to empty string — falling back",
            file=sys.stderr,
        )
        return None

    return rendered


def _discover_git_root() -> Path | None:
    """Discover the git repository root directory."""
    result = run_git("rev-parse", "--show-toplevel", check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip())


def _load_template(git_root: Path) -> str | None:
    """Load the commit template file content.

    Returns ``None`` (with a warning) when the file is missing, empty,
    whitespace-only, or contains a Jinja2 syntax error.
    """
    template_file = git_root / TEMPLATE_PATH
    if not template_file.is_file():
        return None

    try:
        content = template_file.read_text(encoding="utf-8")
    except OSError as exc:
        print(
            f"Warning: Cannot read commit template: {exc}",
            file=sys.stderr,
        )
        return None

    if not content.strip():
        print(
            "Warning: Commit template file is empty or whitespace-only — skipping template rendering",
            file=sys.stderr,
        )
        return None

    # Validate syntax early
    try:
        jinja2.sandbox.SandboxedEnvironment(loader=jinja2.BaseLoader()).parse(content)
    except jinja2.TemplateSyntaxError as exc:
        print(
            f"Warning: Commit template has Jinja2 syntax error: {exc}",
            file=sys.stderr,
        )
        return None

    return content


def _build_render_context(git_root: Path) -> dict[str, str]:
    """Assemble the render context from state.

    Only resolved (non-None) values are included. Unresolved variables
    are omitted so unresolved template variables render as empty strings.
    Missing variables are surfaced via the warning system.
    """
    context: dict[str, str] = {}

    # issueKey
    normalized_key, raw_key = _resolve_issue_key()
    if normalized_key is not None:
        context["issueKey"] = normalized_key

    # issueLink
    issue_link = _resolve_issue_link(normalized_key, raw_key, git_root)
    if issue_link is not None:
        context["issueLink"] = issue_link

    # issueType
    issue_type = _resolve_issue_type()
    if issue_type is not None:
        context["issueType"] = issue_type

    # commitMessageTitle
    title = _resolve_commit_title()
    if title is not None:
        context["commitMessageTitle"] = title

    # commitMessageBody
    body = _resolve_commit_body(git_root)
    if body is not None:
        context["commitMessageBody"] = body

    return context


def _resolve_issue_key() -> tuple[str | None, object]:
    """Resolve the issue key from state.

    Returns:
        Tuple of (normalized_key, raw_value). Normalized key strips ``#``
        prefixes for GitHub issues and preserves Jira-style keys as-is.
    """
    # Resolution priority: issue_key → jira.issue_key → workflow.context.jira_issue_key
    raw_values: list[object] = [get_value("issue_key"), get_value("jira.issue_key")]
    workflow = get_value("workflow")
    if isinstance(workflow, dict):
        context = workflow.get("context")
        if isinstance(context, dict):
            raw_values.append(context.get("jira_issue_key"))

    for raw in raw_values:
        # Accept only plain int and str values (exclude bool and complex types)
        if type(raw) is int:  # noqa: E721 - intentionally excludes bool
            return (str(raw), raw)
        if not isinstance(raw, str):
            continue

        raw_str = raw.strip()
        if not raw_str:
            continue

        # Strip leading # for GitHub-style #N
        if raw_str.startswith("#"):
            stripped = raw_str[1:]
            if stripped.isdigit():
                return (stripped, raw)

        # Digits-only string
        if raw_str.isdigit():
            return (raw_str, raw)

        # Jira-style key (e.g., PROJECT-1234) — keep as-is
        return (raw_str, raw)

    return (None, None)


def _resolve_issue_link(normalized_key: str | None, raw_key: object, git_root: Path) -> str | None:
    """Resolve the issue link URL.

    Priority:
    1. Explicit ``issueManagement.issueLink`` state key
    2. Derived from GitHub repo + numeric issue key
    """
    # Explicit override
    explicit = get_value("issueManagement.issueLink")
    if isinstance(explicit, str):
        explicit = explicit.strip()
        if explicit:
            return explicit

    # Can only derive for numeric (GitHub) issue keys
    if normalized_key is None:
        return None
    if not normalized_key.isdigit():
        return None

    # Need repo resolution
    repo = resolve_github_repo_safe()
    if repo is None:
        return None

    return f"https://github.com/{repo}/issues/{normalized_key}"


def _resolve_issue_type() -> str | None:
    """Resolve the conventional commit type prefix.

    Priority:
    1. ``versionControl.commitMessageType`` (explicit override)
    2. Mapped from ``issueManagement.issueType`` or ``jira.issue_type``
    """
    # Explicit override
    explicit = get_value("versionControl.commitMessageType")
    if isinstance(explicit, str):
        explicit = explicit.strip()
        if explicit:
            return explicit

    # Map from issue type — treat whitespace-only as unset so we fall back
    issue_type = get_value("issueManagement.issueType")
    if isinstance(issue_type, str):
        issue_type = issue_type.strip() or None
    if not issue_type:
        issue_type = get_value("jira.issue_type")

    if isinstance(issue_type, str):
        issue_type = issue_type.strip()
        if not issue_type:
            return None

        mapped = DEFAULT_JIRA_TYPE_MAPPING.get(issue_type)
        if mapped:
            return mapped

    return None


def _resolve_commit_title() -> str | None:
    """Resolve the commit message title/summary line."""
    title = get_value("versionControl.commitMessageTitle")
    if isinstance(title, str):
        title = title.strip()
        if title:
            return title
    return None


def _resolve_commit_body(git_root: Path) -> str | None:
    """Resolve the commit message body from a file.

    The file path is read from ``versionControl.commitMessageBodyFile``.
    Relative paths are resolved against the git repository root.
    """
    body_file = get_value("versionControl.commitMessageBodyFile")
    if not body_file or not isinstance(body_file, str):
        return None

    body_path = Path(body_file)
    if not body_path.is_absolute():
        body_path = git_root / body_path

    # Resolve to detect symlinks / path traversal
    try:
        resolved = body_path.resolve()
    except OSError:
        return None

    # Security: ensure path is within repo root
    try:
        repo_root = git_root.resolve()
    except OSError:
        return None

    try:
        resolved.relative_to(repo_root)
    except ValueError:
        print(
            f"Warning: Commit body file path escapes repository root: {body_file}",
            file=sys.stderr,
        )
        return None

    try:
        content = resolved.read_text(encoding="utf-8")
    except OSError:
        return None

    return content if content.strip() else None


def _warn_unresolved_variables(context: dict[str, str], template_content: str) -> None:
    """Emit warnings for template variables that are referenced but unresolved.

    Uses Jinja2 AST parsing to find all referenced variables and checks
    which ones are missing from the render context.
    """
    try:
        env = jinja2.sandbox.SandboxedEnvironment(loader=jinja2.BaseLoader())
        ast = env.parse(template_content)
        referenced = jinja2.meta.find_undeclared_variables(ast)
    except jinja2.TemplateSyntaxError:
        # Syntax errors are handled separately in _load_template
        return

    # Exclude Jinja2 built-in globals (e.g. range, dict, cycler, namespace)
    # so templates using them don't produce spurious "unresolved" warnings.
    known_names = set(env.globals.keys())
    missing = referenced - set(context.keys()) - known_names
    for var in sorted(missing):
        print(
            f"Warning: Template variable '{var}' is unresolved — it will render as empty in the commit message",
            file=sys.stderr,
        )


def _get_missing_required_variables(context: dict[str, str], template_content: str) -> frozenset[str]:
    """Return the set of hard-required variables referenced by the template but absent from context.

    Hard-required variables are those whose absence would produce a structurally
    malformed commit message (broken markdown links, empty description).  When
    the returned set is non-empty the caller should return ``None`` and let the
    commit pipeline fall back to the ``commit_message`` state key.

    ``commitMessageBody`` is intentionally excluded from the hard-required set —
    an absent body is valid and simply produces blank lines.

    Args:
        context: Resolved render context built by ``_build_render_context()``.
        template_content: Raw Jinja2 template string.

    Returns:
        Frozenset of hard-required variable names that are referenced in the
        template but not present in *context*.  Empty when all hard-required
        variables are resolved or when the template contains a syntax error.
    """
    try:
        env = jinja2.sandbox.SandboxedEnvironment(loader=jinja2.BaseLoader())
        ast = env.parse(template_content)
        referenced = jinja2.meta.find_undeclared_variables(ast)
    except jinja2.TemplateSyntaxError:
        # Syntax errors are handled separately in _load_template; treat as
        # no missing required vars here so we don't double-report.
        return frozenset()

    return frozenset((referenced & HARD_REQUIRED_VARIABLES) - set(context.keys()))
