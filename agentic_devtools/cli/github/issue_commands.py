"""
GitHub issue creation commands for the agentic-devtools repository.

Creates issues in ayaiayorg/agentic-devtools via the gh CLI.
"""

import platform
import shutil
import sys
from typing import List, Optional

from ..subprocess_utils import run_safe
from .state_helpers import get_issue_value, set_issue_value

# The target repository for all agdt-create-agdt-* commands
AGDT_REPO = "ayaiayorg/agentic-devtools"

# Mapping of issue-type names to gh CLI --type values
_ISSUE_TYPE_MAP = {
    "bug": "Bug",
    "feature": "Feature",
    "task": "Task",
}


def _check_gh_cli() -> None:
    """Verify gh CLI is installed and authenticated, or exit with a helpful error."""
    if not shutil.which("gh"):
        print(
            "Error: 'gh' CLI is not installed or not on PATH.\n"
            "Install it from https://cli.github.com/ and authenticate with 'gh auth login'.",
            file=sys.stderr,
        )
        sys.exit(1)


def _get_environment_info() -> str:
    """
    Collect environment information for bug reports.

    Returns:
        Markdown-formatted environment section
    """
    os_info = f"{platform.system()} {platform.release()}"

    python_version = platform.python_version()

    # agentic-devtools version
    try:
        from importlib.metadata import version

        agdt_version = version("agentic-devtools")
    except Exception:
        agdt_version = "unknown"

    # VS Code version
    vscode_version = "unknown"
    try:
        result = run_safe(["code", "--version"], capture_output=True, text=True, shell=False)
        if result.returncode == 0 and result.stdout.strip():
            vscode_version = result.stdout.strip().splitlines()[0]
    except OSError:
        pass

    # Git version
    git_version = "unknown"
    try:
        result = run_safe(["git", "--version"], capture_output=True, text=True, shell=False)
        if result.returncode == 0 and result.stdout.strip():
            git_version = result.stdout.strip().replace("git version ", "")
    except OSError:
        pass

    return (
        "## Environment\n\n"
        f"- OS: {os_info}\n"
        f"- agentic-devtools: {agdt_version}\n"
        f"- Python: {python_version}\n"
        f"- VS Code: {vscode_version}\n"
        f"- Git: {git_version}\n"
    )


def _build_gh_create_args(
    title: str,
    body: str,
    labels: Optional[List[str]] = None,
    issue_type: Optional[str] = None,
    assignees: Optional[List[str]] = None,
    milestone: Optional[str] = None,
) -> List[str]:
    """
    Build the gh issue create argument list.

    Args:
        title: Issue title
        body: Issue body (markdown)
        labels: List of label names
        issue_type: GitHub issue type (Bug, Feature, Task)
        assignees: List of GitHub usernames
        milestone: Milestone name or number

    Returns:
        List of arguments for gh issue create
    """
    args = [
        "gh",
        "issue",
        "create",
        "--repo",
        AGDT_REPO,
        "--title",
        title,
        "--body",
        body,
    ]

    if labels:
        for label in labels:
            args += ["--label", label]

    if issue_type:
        normalized = issue_type.strip().lower()
        canonical = _ISSUE_TYPE_MAP.get(normalized, issue_type)
        args += ["--type", canonical]

    if assignees:
        for assignee in assignees:
            args += ["--assignee", assignee]

    if milestone:
        args += ["--milestone", milestone]

    return args


def _append_related_issues(body: str, related_issues: Optional[str]) -> str:
    """Append 'Related to #NNN' lines for related issue references."""
    if not related_issues:
        return body
    refs = []
    for ref in related_issues.replace(",", " ").split():
        ref = ref.lstrip("#").strip()
        if ref.isdigit():
            refs.append(f"Related to #{ref}")
    if refs:
        body = body.rstrip() + "\n\n" + "\n".join(refs) + "\n"
    return body


def _append_terminal_log(body: str, terminal_log: Optional[str]) -> str:
    """Append terminal log output to the issue body."""
    if not terminal_log:
        return body
    body = body.rstrip() + "\n\n## Terminal Output\n\n```\n" + terminal_log.strip() + "\n```\n"
    return body


def create_agdt_issue() -> None:
    """
    Create an issue in the agentic-devtools repository (ayaiayorg/agentic-devtools).

    Reads from state (all keys prefixed with 'issue.'):
    - issue.title (required): Issue title
    - issue.description (required): Issue body (markdown)
    - issue.labels (optional): Comma-separated labels
    - issue.issue_type (optional): GitHub issue type: Bug, Feature, Task
    - issue.assignees (optional): Comma-separated GitHub usernames
    - issue.milestone (optional): Milestone name or number
    - issue.related_issue (optional): Issue number(s) to link
    - issue.terminal_log (optional): Terminal output to attach
    - issue.dry_run (optional): Preview without submitting

    Usage:
        agdt-set issue.title "My issue"
        agdt-set issue.description "Details here"
        agdt-create-agdt-issue
    """
    _check_gh_cli()

    title = get_issue_value("title")
    description = get_issue_value("description")

    missing = []
    if not title:
        missing.append("issue.title")
    if not description:
        missing.append("issue.description")

    if missing:
        print(f"Error: Missing required fields: {', '.join(missing)}", file=sys.stderr)
        print("\nUsage:", file=sys.stderr)
        print('  agdt-set issue.title "My issue"', file=sys.stderr)
        print('  agdt-set issue.description "Details here"', file=sys.stderr)
        print("  agdt-create-agdt-issue", file=sys.stderr)
        sys.exit(1)

    labels_raw = get_issue_value("labels") or ""
    labels = [lb.strip() for lb in labels_raw.split(",") if lb.strip()]
    issue_type = get_issue_value("issue_type") or None
    assignees_raw = get_issue_value("assignees") or ""
    assignees = [a.strip() for a in assignees_raw.split(",") if a.strip()]
    milestone = get_issue_value("milestone") or None
    related_issue = get_issue_value("related_issue") or None
    terminal_log = get_issue_value("terminal_log") or None
    dry_run = get_issue_value("dry_run") or False

    body = str(description)
    body = _append_related_issues(body, related_issue)
    body = _append_terminal_log(body, terminal_log)

    if dry_run:
        print("=== PREVIEW (not submitted) ===")
        print(f"Repository: {AGDT_REPO}")
        print(f"Title: {title}")
        if labels:
            print(f"Labels: {', '.join(labels)}")
        if issue_type:
            print(f"Type: {issue_type}")
        if assignees:
            print(f"Assignees: {', '.join(assignees)}")
        if milestone:
            print(f"Milestone: {milestone}")
        print(f"\n{body}")
        return

    gh_args = _build_gh_create_args(
        title=str(title),
        body=body,
        labels=labels if labels else None,
        issue_type=issue_type,
        assignees=assignees if assignees else None,
        milestone=milestone,
    )

    print(f"Creating issue in {AGDT_REPO}...")
    # shell=False is required here: gh is a proper .exe (not a .cmd batch script), and
    # the argument list contains user-controlled text (title, body). Using shell=True on
    # Windows would cause cmd.exe to expand %VAR% patterns in those arguments, potentially
    # leaking environment variables such as %GITHUB_TOKEN%.
    result = run_safe(gh_args, capture_output=True, text=True, shell=False)

    if result.returncode != 0:
        print(f"Error creating issue: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(result.returncode)

    issue_url = result.stdout.strip()
    print(f"Issue created: {issue_url}")
    set_issue_value("created_issue_url", issue_url)


def create_agdt_bug_issue() -> None:
    """
    Create a structured bug report in the agentic-devtools repository.

    Auto-sets: label 'bug', issue type 'Bug', auto-populates Environment section.

    Reads from state (all keys prefixed with 'issue.'):
    - issue.title (required): Issue title
    - issue.steps_to_reproduce (required): Numbered steps to reproduce the bug
    - issue.expected_behavior (required): What should happen
    - issue.actual_behavior (required): What actually happens
    - issue.workaround (optional): Known workaround
    - issue.error_output (optional): Exact error message or log snippet
    - issue.terminal_log (optional): Attach recent terminal/task log output
    - issue.related_issue (optional): Link to related issue(s)
    - issue.assignees (optional): Comma-separated GitHub usernames
    - issue.milestone (optional): Milestone name or number
    - issue.dry_run (optional): Preview without submitting

    Usage:
        agdt-set issue.title "Workspace file not found"
        agdt-set issue.steps_to_reproduce "1. Run agdt-git-save-work\n2. See error"
        agdt-set issue.expected_behavior "Commit succeeds"
        agdt-set issue.actual_behavior "Error: file not found"
        agdt-create-agdt-bug-issue
    """
    _check_gh_cli()

    title = get_issue_value("title")
    steps_to_reproduce = get_issue_value("steps_to_reproduce")
    expected_behavior = get_issue_value("expected_behavior")
    actual_behavior = get_issue_value("actual_behavior")

    missing = []
    if not title:
        missing.append("issue.title")
    if not steps_to_reproduce:
        missing.append("issue.steps_to_reproduce")
    if not expected_behavior:
        missing.append("issue.expected_behavior")
    if not actual_behavior:
        missing.append("issue.actual_behavior")

    if missing:
        print(f"Error: Missing required fields: {', '.join(missing)}", file=sys.stderr)
        print("\nUsage:", file=sys.stderr)
        print('  agdt-set issue.title "Bug title"', file=sys.stderr)
        print('  agdt-set issue.steps_to_reproduce "1. Step one\\n2. Step two"', file=sys.stderr)
        print('  agdt-set issue.expected_behavior "What should happen"', file=sys.stderr)
        print('  agdt-set issue.actual_behavior "What actually happens"', file=sys.stderr)
        print("  agdt-create-agdt-bug-issue", file=sys.stderr)
        sys.exit(1)

    workaround = get_issue_value("workaround") or None
    error_output = get_issue_value("error_output") or None

    # Compose structured body
    body = f"## Steps to Reproduce\n\n{steps_to_reproduce}\n\n"
    body += f"## Expected Behavior\n\n{expected_behavior}\n\n"
    body += f"## Actual Behavior\n\n{actual_behavior}\n"

    if workaround:
        body += f"\n## Workaround\n\n{workaround}\n"

    if error_output:
        body += f"\n## Error Output\n\n```\n{error_output}\n```\n"

    body += f"\n{_get_environment_info()}"

    # Store composed values in state for create_agdt_issue to pick up
    set_issue_value("title", title)
    set_issue_value("description", body)
    set_issue_value("labels", "bug")
    set_issue_value("issue_type", "Bug")

    create_agdt_issue()


def create_agdt_feature_issue() -> None:
    """
    Create a structured feature request in the agentic-devtools repository.

    Auto-sets: label 'enhancement', issue type 'Feature'.

    Reads from state (all keys prefixed with 'issue.'):
    - issue.title (required): Issue title
    - issue.motivation (required): Why this feature is needed / use case
    - issue.proposed_solution (required): Proposed commands, API, or behavior
    - issue.alternatives_considered (optional): Other approaches considered
    - issue.breaking_changes (optional): Any breaking changes this would introduce
    - issue.examples (optional): Usage examples
    - issue.related_issue (optional): Link to related issue(s)
    - issue.assignees (optional): Comma-separated GitHub usernames
    - issue.milestone (optional): Milestone name or number
    - issue.dry_run (optional): Preview without submitting

    Usage:
        agdt-set issue.title "New feature"
        agdt-set issue.motivation "Why we need this"
        agdt-set issue.proposed_solution "How it would work"
        agdt-create-agdt-feature-issue
    """
    _check_gh_cli()

    title = get_issue_value("title")
    motivation = get_issue_value("motivation")
    proposed_solution = get_issue_value("proposed_solution")

    missing = []
    if not title:
        missing.append("issue.title")
    if not motivation:
        missing.append("issue.motivation")
    if not proposed_solution:
        missing.append("issue.proposed_solution")

    if missing:
        print(f"Error: Missing required fields: {', '.join(missing)}", file=sys.stderr)
        print("\nUsage:", file=sys.stderr)
        print('  agdt-set issue.title "Feature title"', file=sys.stderr)
        print('  agdt-set issue.motivation "Why this feature is needed"', file=sys.stderr)
        print('  agdt-set issue.proposed_solution "How it would work"', file=sys.stderr)
        print("  agdt-create-agdt-feature-issue", file=sys.stderr)
        sys.exit(1)

    alternatives_considered = get_issue_value("alternatives_considered") or None
    breaking_changes = get_issue_value("breaking_changes") or None
    examples = get_issue_value("examples") or None

    # Compose structured body
    body = f"## Motivation / Use Case\n\n{motivation}\n\n"
    body += f"## Proposed Solution\n\n{proposed_solution}\n"

    if alternatives_considered:
        body += f"\n## Alternatives Considered\n\n{alternatives_considered}\n"

    if breaking_changes:
        body += f"\n## Breaking Changes\n\n{breaking_changes}\n"

    if examples:
        body += f"\n## Examples\n\n{examples}\n"

    # Store composed values in state for create_agdt_issue to pick up
    set_issue_value("title", title)
    set_issue_value("description", body)
    set_issue_value("labels", "enhancement")
    set_issue_value("issue_type", "Feature")

    create_agdt_issue()


def create_agdt_documentation_issue() -> None:
    """
    Create a structured documentation issue in the agentic-devtools repository.

    Auto-sets: label 'documentation', issue type 'Task'.

    Reads from state (all keys prefixed with 'issue.'):
    - issue.title (required): Issue title
    - issue.whats_missing (required): What documentation is missing, wrong, or outdated
    - issue.suggested_content (optional): Proposed documentation text or outline
    - issue.affected_commands (optional): Which agdt-* commands are affected
    - issue.related_issue (optional): Link to related issue(s)
    - issue.assignees (optional): Comma-separated GitHub usernames
    - issue.milestone (optional): Milestone name or number
    - issue.dry_run (optional): Preview without submitting

    Usage:
        agdt-set issue.title "Document agdt-create-agdt-issue"
        agdt-set issue.whats_missing "No documentation for the new commands"
        agdt-create-agdt-documentation-issue
    """
    _check_gh_cli()

    title = get_issue_value("title")
    whats_missing = get_issue_value("whats_missing")

    missing = []
    if not title:
        missing.append("issue.title")
    if not whats_missing:
        missing.append("issue.whats_missing")

    if missing:
        print(f"Error: Missing required fields: {', '.join(missing)}", file=sys.stderr)
        print("\nUsage:", file=sys.stderr)
        print('  agdt-set issue.title "Documentation issue title"', file=sys.stderr)
        print('  agdt-set issue.whats_missing "What is missing or wrong"', file=sys.stderr)
        print("  agdt-create-agdt-documentation-issue", file=sys.stderr)
        sys.exit(1)

    suggested_content = get_issue_value("suggested_content") or None
    affected_commands = get_issue_value("affected_commands") or None

    # Compose structured body
    body = f"## What's Missing / Incorrect\n\n{whats_missing}\n"

    if suggested_content:
        body += f"\n## Suggested Content\n\n{suggested_content}\n"

    if affected_commands:
        body += f"\n## Affected Commands\n\n{affected_commands}\n"

    # Store composed values in state for create_agdt_issue to pick up
    set_issue_value("title", title)
    set_issue_value("description", body)
    set_issue_value("labels", "documentation")
    set_issue_value("issue_type", "Task")

    create_agdt_issue()


def create_agdt_task_issue() -> None:
    """
    Create a structured task issue in the agentic-devtools repository.

    Auto-sets: issue type 'Task'.

    Reads from state (all keys prefixed with 'issue.'):
    - issue.title (required): Issue title
    - issue.description (required): What needs to be done
    - issue.acceptance_criteria (optional): Bullet list of done conditions
    - issue.labels (optional): Additional labels
    - issue.related_issue (optional): Link to related issue(s)
    - issue.assignees (optional): Comma-separated GitHub usernames
    - issue.milestone (optional): Milestone name or number
    - issue.dry_run (optional): Preview without submitting

    Usage:
        agdt-set issue.title "Task title"
        agdt-set issue.description "What needs to be done"
        agdt-create-agdt-task-issue
    """
    _check_gh_cli()

    title = get_issue_value("title")
    description = get_issue_value("description")

    missing = []
    if not title:
        missing.append("issue.title")
    if not description:
        missing.append("issue.description")

    if missing:
        print(f"Error: Missing required fields: {', '.join(missing)}", file=sys.stderr)
        print("\nUsage:", file=sys.stderr)
        print('  agdt-set issue.title "Task title"', file=sys.stderr)
        print('  agdt-set issue.description "What needs to be done"', file=sys.stderr)
        print("  agdt-create-agdt-task-issue", file=sys.stderr)
        sys.exit(1)

    acceptance_criteria = get_issue_value("acceptance_criteria") or None

    body = str(description)

    if acceptance_criteria:
        body += f"\n\n## Acceptance Criteria\n\n{acceptance_criteria}\n"

    # Store composed values in state for create_agdt_issue to pick up
    set_issue_value("title", title)
    set_issue_value("description", body)
    set_issue_value("issue_type", "Task")

    create_agdt_issue()
