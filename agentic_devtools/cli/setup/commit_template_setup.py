"""Commit template creation and validation for ``agdt-setup``.

Provides:
- ``ensure_commit_template(git_root)`` — creates the default template if missing
- ``validate_commit_template(git_root)`` — checks an existing template for required variables
"""

from __future__ import annotations

from pathlib import Path

import jinja2
import jinja2.meta

from ..git.commit_template import REQUIRED_VARIABLES, TEMPLATE_PATH

# Default Jinja2 commit message template content (FR-001)
DEFAULT_TEMPLATE = """\
{{ issueType }}([#{{ issueKey }}]({{ issueLink }})): {{ commitMessageTitle }}

{{ commitMessageBody }}

[#{{ issueKey }}]({{ issueLink }})
"""


def ensure_commit_template(git_root: Path) -> bool:
    """Create the default commit template if it does not already exist.

    Args:
        git_root: Repository root path.

    Returns:
        ``True`` if the template was created, ``False`` if it already existed.
    """
    template_file = git_root / TEMPLATE_PATH
    if template_file.is_file():
        return False

    # Create directory structure (FR-008)
    template_file.parent.mkdir(parents=True, exist_ok=True)
    template_file.write_text(DEFAULT_TEMPLATE, encoding="utf-8")
    return True


def validate_commit_template(git_root: Path) -> list[str]:
    """Validate an existing commit template for required variables.

    Uses Jinja2 AST parsing to extract referenced variables and checks
    that all required variables are present.

    Args:
        git_root: Repository root path.

    Returns:
        List of warning messages (empty if template is valid). Each entry
        describes a missing required variable.
    """
    template_file = git_root / TEMPLATE_PATH
    if not template_file.is_file():
        return []

    try:
        content = template_file.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"Cannot read commit template: {exc}"]

    if not content.strip():
        return ["Commit template file is empty or whitespace-only"]

    try:
        env = jinja2.Environment(loader=jinja2.BaseLoader())
        ast = env.parse(content)
        referenced = jinja2.meta.find_undeclared_variables(ast)
    except jinja2.TemplateSyntaxError as exc:
        return [f"Commit template has Jinja2 syntax error: {exc}"]

    missing = REQUIRED_VARIABLES - referenced
    warnings_list: list[str] = []
    for var in sorted(missing):
        warnings_list.append(
            f"Commit template does not reference required variable '{{{{ {var} }}}}' — "
            f"add it to the template so it appears in generated commit messages"
        )

    return warnings_list
