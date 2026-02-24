"""
Async wrappers for GitHub issue creation commands.

Provides async versions that run in background processes, plus CLI entry points
with argparse for all agdt-create-agdt-* commands.
"""

import argparse
import sys
from typing import Optional

from agentic_devtools.background_tasks import run_function_in_background
from agentic_devtools.state import set_value
from agentic_devtools.task_state import print_task_tracking_info

from .state_helpers import get_issue_value

_ISSUE_MODULE = "agentic_devtools.cli.github.issue_commands"

_SEE_ALSO = (
    "See also: agdt-create-agdt-bug-issue, agdt-create-agdt-feature-issue,\n"
    "          agdt-create-agdt-documentation-issue, agdt-create-agdt-task-issue"
)

_SEE_ALSO_BASE = (
    "See also: agdt-create-agdt-issue, agdt-create-agdt-feature-issue,\n"
    "          agdt-create-agdt-documentation-issue, agdt-create-agdt-task-issue"
)


def _require_issue_value(key: str, error_example: str) -> str:
    """Get a required issue state value or exit with error."""
    value = get_issue_value(key)
    if not value:
        print(
            f"Error: issue.{key} is required. Use: {error_example}",
            file=sys.stderr,
        )
        sys.exit(1)
    return value


def _set_issue_value_if_provided(key: str, value: Optional[str]) -> None:
    """Set an issue state value if provided (not None)."""
    if value is not None:
        set_value(f"issue.{key}", value)


# =============================================================================
# Base Issue Command (Async)
# =============================================================================


def create_agdt_issue_async(
    title: Optional[str] = None,
    description: Optional[str] = None,
    labels: Optional[str] = None,
    issue_type: Optional[str] = None,
    assignees: Optional[str] = None,
    milestone: Optional[str] = None,
    related_issue: Optional[str] = None,
    dry_run: Optional[bool] = None,
) -> None:
    """
    Create a GitHub issue in ayaiayorg/agentic-devtools (background task).

    Args:
        title: Issue title (overrides state)
        description: Issue body markdown (overrides state)
        labels: Comma-separated labels (overrides state)
        issue_type: GitHub issue type: Bug, Feature, Task (overrides state)
        assignees: Comma-separated GitHub usernames (overrides state)
        milestone: Milestone name or number (overrides state)
        related_issue: Issue number(s) to link (overrides state)
        dry_run: Preview without submitting (overrides state)

    State keys (prefixed with 'issue.'):
    - issue.title (required)
    - issue.description (required)
    - issue.labels, issue.issue_type, issue.assignees, issue.milestone,
      issue.related_issue, issue.terminal_log, issue.dry_run (optional)

    Usage:
        agdt-set issue.title "My issue"
        agdt-set issue.description "Details"
        agdt-create-agdt-issue
    """
    _set_issue_value_if_provided("title", title)
    _set_issue_value_if_provided("description", description)
    _set_issue_value_if_provided("labels", labels)
    _set_issue_value_if_provided("issue_type", issue_type)
    _set_issue_value_if_provided("assignees", assignees)
    _set_issue_value_if_provided("milestone", milestone)
    _set_issue_value_if_provided("related_issue", related_issue)
    if dry_run is not None:  # pragma: no cover
        set_value("issue.dry_run", dry_run)

    resolved_title = _require_issue_value("title", 'agdt-create-agdt-issue --title "My issue"')
    _require_issue_value("description", 'agdt-create-agdt-issue --description "Details"')

    task = run_function_in_background(
        _ISSUE_MODULE,
        "create_agdt_issue",
        command_display_name="agdt-create-agdt-issue",
    )
    print_task_tracking_info(task, f"Creating issue: {resolved_title}")


def create_agdt_issue_async_cli() -> None:
    """CLI entry point for agdt-create-agdt-issue with argparse."""
    parser = argparse.ArgumentParser(
        prog="agdt-create-agdt-issue",
        description=(
            "Create an issue in the agentic-devtools repository (ayaiayorg/agentic-devtools).\n\n"
            "Base command with full control over all fields. For structured issue types,\n"
            "prefer the wrapper commands: agdt-create-agdt-bug-issue, agdt-create-agdt-feature-issue,\n"
            "agdt-create-agdt-documentation-issue, agdt-create-agdt-task-issue."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Create a simple issue\n"
            '  agdt-create-agdt-issue --title "My issue" --description "Details here"\n\n'
            "  # Create with labels and type\n"
            '  agdt-create-agdt-issue --title "My issue" --description "Details" \\\n'
            '    --labels "bug,high-priority" --issue-type Bug\n\n'
            "  # Preview before submitting\n"
            '  agdt-create-agdt-issue --title "My issue" --description "Details" --dry-run\n\n' + _SEE_ALSO
        ),
        add_help=False,
    )

    required_group = parser.add_argument_group("Required")
    required_group.add_argument("--title", type=str, default=None, metavar="TEXT", help="Issue title")
    required_group.add_argument("--description", type=str, default=None, metavar="TEXT", help="Issue body (markdown)")

    optional_group = parser.add_argument_group("Optional")
    optional_group.add_argument(
        "--labels", type=str, default=None, metavar="TEXT", help="Comma-separated labels (e.g., bug,enhancement)"
    )
    optional_group.add_argument(
        "--issue-type", type=str, default=None, metavar="TEXT", help="GitHub issue type: Bug, Feature, Task"
    )
    optional_group.add_argument(
        "--assignees", type=str, default=None, metavar="TEXT", help="Comma-separated GitHub usernames"
    )
    optional_group.add_argument("--milestone", type=str, default=None, metavar="TEXT", help="Milestone name or number")
    optional_group.add_argument(
        "--related-issue",
        type=str,
        default=None,
        metavar="NUMBER",
        help='Link to related issue(s) with "Related to #NNN"',
    )
    optional_group.add_argument(
        "--dry-run", action="store_true", default=False, help="Preview the composed issue without submitting"
    )
    optional_group.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    args = parser.parse_args()
    create_agdt_issue_async(
        title=args.title,
        description=args.description,
        labels=args.labels,
        issue_type=args.issue_type,
        assignees=args.assignees,
        milestone=args.milestone,
        related_issue=args.related_issue,
        dry_run=args.dry_run if args.dry_run else None,
    )


# =============================================================================
# Bug Issue Command (Async)
# =============================================================================


def create_agdt_bug_issue_async(
    title: Optional[str] = None,
    steps_to_reproduce: Optional[str] = None,
    expected_behavior: Optional[str] = None,
    actual_behavior: Optional[str] = None,
    workaround: Optional[str] = None,
    error_output: Optional[str] = None,
    related_issue: Optional[str] = None,
    assignees: Optional[str] = None,
    milestone: Optional[str] = None,
    dry_run: Optional[bool] = None,
) -> None:
    """
    Create a bug report in ayaiayorg/agentic-devtools (background task).

    Auto-sets: label 'bug', issue type 'Bug', auto-populates Environment section.

    State keys (prefixed with 'issue.'):
    - issue.title (required)
    - issue.steps_to_reproduce (required)
    - issue.expected_behavior (required)
    - issue.actual_behavior (required)
    - issue.workaround, issue.error_output, issue.terminal_log,
      issue.related_issue, issue.assignees, issue.milestone, issue.dry_run (optional)

    Usage:
        agdt-set issue.title "Bug title"
        agdt-set issue.steps_to_reproduce "1. Step one"
        agdt-set issue.expected_behavior "What should happen"
        agdt-set issue.actual_behavior "What actually happens"
        agdt-create-agdt-bug-issue
    """
    _set_issue_value_if_provided("title", title)
    _set_issue_value_if_provided("steps_to_reproduce", steps_to_reproduce)
    _set_issue_value_if_provided("expected_behavior", expected_behavior)
    _set_issue_value_if_provided("actual_behavior", actual_behavior)
    _set_issue_value_if_provided("workaround", workaround)
    _set_issue_value_if_provided("error_output", error_output)
    _set_issue_value_if_provided("related_issue", related_issue)
    _set_issue_value_if_provided("assignees", assignees)
    _set_issue_value_if_provided("milestone", milestone)
    if dry_run is not None:  # pragma: no cover
        set_value("issue.dry_run", dry_run)

    resolved_title = _require_issue_value("title", 'agdt-create-agdt-bug-issue --title "Bug title"')
    _require_issue_value(
        "steps_to_reproduce",
        'agdt-create-agdt-bug-issue --steps-to-reproduce "1. Step one"',
    )
    _require_issue_value(
        "expected_behavior",
        'agdt-create-agdt-bug-issue --expected-behavior "What should happen"',
    )
    _require_issue_value(
        "actual_behavior",
        'agdt-create-agdt-bug-issue --actual-behavior "What actually happens"',
    )

    task = run_function_in_background(
        _ISSUE_MODULE,
        "create_agdt_bug_issue",
        command_display_name="agdt-create-agdt-bug-issue",
    )
    print_task_tracking_info(task, f"Creating bug report: {resolved_title}")


def create_agdt_bug_issue_async_cli() -> None:
    """CLI entry point for agdt-create-agdt-bug-issue with argparse."""
    parser = argparse.ArgumentParser(
        prog="agdt-create-agdt-bug-issue",
        description=(
            "Create a bug report in the agentic-devtools repository (ayaiayorg/agentic-devtools).\n\n"
            "Composes a structured issue with sections for Steps to Reproduce, Expected Behavior,\n"
            "Actual Behavior, Workaround, and an auto-populated Environment section.\n"
            "Auto-sets label: bug, issue type: Bug."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Auto-populated:\n"
            "  Environment section (OS, agentic-devtools version, Python, VS Code, Git)\n\n"
            "Examples:\n"
            "  # Full bug report (with optional fields)\n"
            "  agdt-create-agdt-bug-issue \\\n"
            '    --title "Workspace file not found" \\\n'
            '    --steps-to-reproduce "1. Run agdt-git-save-work" \\\n'
            '    --expected-behavior "Commit succeeds" \\\n'
            '    --actual-behavior "Error: file not found" \\\n'
            '    --workaround "Use git commit directly" \\\n'
            '    --error-output "FileNotFoundError: agdt-state.json"\n\n'
            "  # Minimal (required fields only)\n"
            "  agdt-create-agdt-bug-issue \\\n"
            '    --title "Workspace file not found" \\\n'
            '    --steps-to-reproduce "1. Run agdt-git-save-work" \\\n'
            '    --expected-behavior "Commit succeeds" \\\n'
            '    --actual-behavior "Error: file not found"\n\n'
            "  # Preview before submitting\n"
            "  agdt-create-agdt-bug-issue \\\n"
            '    --title "Workspace file not found" \\\n'
            '    --steps-to-reproduce "1. Run agdt-git-save-work" \\\n'
            '    --expected-behavior "Commit succeeds" \\\n'
            '    --actual-behavior "Error: file not found" --dry-run\n\n' + _SEE_ALSO_BASE
        ),
        add_help=False,
    )

    required_group = parser.add_argument_group("Required")
    required_group.add_argument("--title", type=str, default=None, metavar="TEXT", help="Issue title")
    required_group.add_argument(
        "--steps-to-reproduce", type=str, default=None, metavar="TEXT", help="Numbered steps to reproduce the bug"
    )
    required_group.add_argument(
        "--expected-behavior", type=str, default=None, metavar="TEXT", help="What should happen"
    )
    required_group.add_argument(
        "--actual-behavior", type=str, default=None, metavar="TEXT", help="What actually happens"
    )

    optional_group = parser.add_argument_group("Optional")
    optional_group.add_argument("--workaround", type=str, default=None, metavar="TEXT", help="Known workaround")
    optional_group.add_argument(
        "--error-output", type=str, default=None, metavar="TEXT", help="Exact error message or log snippet"
    )
    optional_group.add_argument(
        "--related-issue",
        type=str,
        default=None,
        metavar="NUMBER",
        help='Link to related issue(s) with "Related to #NNN"',
    )
    optional_group.add_argument(
        "--assignees", type=str, default=None, metavar="TEXT", help="Comma-separated GitHub usernames"
    )
    optional_group.add_argument("--milestone", type=str, default=None, metavar="TEXT", help="Milestone name or number")
    optional_group.add_argument(
        "--dry-run", action="store_true", default=False, help="Preview the composed issue without submitting"
    )
    optional_group.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    args = parser.parse_args()
    create_agdt_bug_issue_async(
        title=args.title,
        steps_to_reproduce=args.steps_to_reproduce,
        expected_behavior=args.expected_behavior,
        actual_behavior=args.actual_behavior,
        workaround=args.workaround,
        error_output=args.error_output,
        related_issue=args.related_issue,
        assignees=args.assignees,
        milestone=args.milestone,
        dry_run=args.dry_run if args.dry_run else None,
    )


# =============================================================================
# Feature Issue Command (Async)
# =============================================================================


def create_agdt_feature_issue_async(
    title: Optional[str] = None,
    motivation: Optional[str] = None,
    proposed_solution: Optional[str] = None,
    alternatives_considered: Optional[str] = None,
    breaking_changes: Optional[str] = None,
    examples: Optional[str] = None,
    related_issue: Optional[str] = None,
    assignees: Optional[str] = None,
    milestone: Optional[str] = None,
    dry_run: Optional[bool] = None,
) -> None:
    """
    Create a feature request in ayaiayorg/agentic-devtools (background task).

    Auto-sets: label 'enhancement', issue type 'Feature'.

    State keys (prefixed with 'issue.'):
    - issue.title (required)
    - issue.motivation (required)
    - issue.proposed_solution (required)
    - issue.alternatives_considered, issue.breaking_changes, issue.examples,
      issue.related_issue, issue.assignees, issue.milestone, issue.dry_run (optional)

    Usage:
        agdt-set issue.title "New feature"
        agdt-set issue.motivation "Why we need this"
        agdt-set issue.proposed_solution "How it would work"
        agdt-create-agdt-feature-issue
    """
    _set_issue_value_if_provided("title", title)
    _set_issue_value_if_provided("motivation", motivation)
    _set_issue_value_if_provided("proposed_solution", proposed_solution)
    _set_issue_value_if_provided("alternatives_considered", alternatives_considered)
    _set_issue_value_if_provided("breaking_changes", breaking_changes)
    _set_issue_value_if_provided("examples", examples)
    _set_issue_value_if_provided("related_issue", related_issue)
    _set_issue_value_if_provided("assignees", assignees)
    _set_issue_value_if_provided("milestone", milestone)
    if dry_run is not None:  # pragma: no cover
        set_value("issue.dry_run", dry_run)

    resolved_title = _require_issue_value("title", 'agdt-create-agdt-feature-issue --title "Feature title"')
    _require_issue_value("motivation", 'agdt-create-agdt-feature-issue --motivation "Why we need this"')
    _require_issue_value(
        "proposed_solution",
        'agdt-create-agdt-feature-issue --proposed-solution "How it would work"',
    )

    task = run_function_in_background(
        _ISSUE_MODULE,
        "create_agdt_feature_issue",
        command_display_name="agdt-create-agdt-feature-issue",
    )
    print_task_tracking_info(task, f"Creating feature request: {resolved_title}")


def create_agdt_feature_issue_async_cli() -> None:
    """CLI entry point for agdt-create-agdt-feature-issue with argparse."""
    parser = argparse.ArgumentParser(
        prog="agdt-create-agdt-feature-issue",
        description=(
            "Create a feature request in the agentic-devtools repository (ayaiayorg/agentic-devtools).\n\n"
            "Composes a structured issue with sections for Motivation, Proposed Solution,\n"
            "Alternatives Considered, Breaking Changes, and Examples.\n"
            "Auto-sets label: enhancement, issue type: Feature."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Full feature request (with optional fields)\n"
            "  agdt-create-agdt-feature-issue \\\n"
            '    --title "Add dark mode" \\\n'
            '    --motivation "Reduce eye strain in low-light environments" \\\n'
            '    --proposed-solution "Add --theme dark flag to all commands" \\\n'
            '    --alternatives-considered "CSS media query only" \\\n'
            '    --breaking-changes "None"\n\n'
            "  # Minimal (required fields only)\n"
            "  agdt-create-agdt-feature-issue \\\n"
            '    --title "Add dark mode" \\\n'
            '    --motivation "Reduce eye strain in low-light environments" \\\n'
            '    --proposed-solution "Add --theme dark flag to all commands"\n\n'
            "  # Preview before submitting\n"
            '  agdt-create-agdt-feature-issue --title "..." --motivation "..." --proposed-solution "..." --dry-run\n\n'
            + _SEE_ALSO_BASE
        ),
        add_help=False,
    )

    required_group = parser.add_argument_group("Required")
    required_group.add_argument("--title", type=str, default=None, metavar="TEXT", help="Issue title")
    required_group.add_argument(
        "--motivation", type=str, default=None, metavar="TEXT", help="Why this feature is needed / use case"
    )
    required_group.add_argument(
        "--proposed-solution",
        type=str,
        default=None,
        metavar="TEXT",
        help="Proposed commands, API, or behavior",
    )

    optional_group = parser.add_argument_group("Optional")
    optional_group.add_argument(
        "--alternatives-considered", type=str, default=None, metavar="TEXT", help="Other approaches considered"
    )
    optional_group.add_argument(
        "--breaking-changes",
        type=str,
        default=None,
        metavar="TEXT",
        help="Any breaking changes this would introduce",
    )
    optional_group.add_argument(
        "--examples", type=str, default=None, metavar="TEXT", help="Usage examples showing the feature in action"
    )
    optional_group.add_argument(
        "--related-issue",
        type=str,
        default=None,
        metavar="NUMBER",
        help='Link to related issue(s) with "Related to #NNN"',
    )
    optional_group.add_argument(
        "--assignees", type=str, default=None, metavar="TEXT", help="Comma-separated GitHub usernames"
    )
    optional_group.add_argument("--milestone", type=str, default=None, metavar="TEXT", help="Milestone name or number")
    optional_group.add_argument(
        "--dry-run", action="store_true", default=False, help="Preview the composed issue without submitting"
    )
    optional_group.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    args = parser.parse_args()
    create_agdt_feature_issue_async(
        title=args.title,
        motivation=args.motivation,
        proposed_solution=args.proposed_solution,
        alternatives_considered=args.alternatives_considered,
        breaking_changes=args.breaking_changes,
        examples=args.examples,
        related_issue=args.related_issue,
        assignees=args.assignees,
        milestone=args.milestone,
        dry_run=args.dry_run if args.dry_run else None,
    )


# =============================================================================
# Documentation Issue Command (Async)
# =============================================================================


def create_agdt_documentation_issue_async(
    title: Optional[str] = None,
    whats_missing: Optional[str] = None,
    suggested_content: Optional[str] = None,
    affected_commands: Optional[str] = None,
    related_issue: Optional[str] = None,
    assignees: Optional[str] = None,
    milestone: Optional[str] = None,
    dry_run: Optional[bool] = None,
) -> None:
    """
    Create a documentation issue in ayaiayorg/agentic-devtools (background task).

    Auto-sets: label 'documentation', issue type 'Task'.

    State keys (prefixed with 'issue.'):
    - issue.title (required)
    - issue.whats_missing (required)
    - issue.suggested_content, issue.affected_commands,
      issue.related_issue, issue.assignees, issue.milestone, issue.dry_run (optional)

    Usage:
        agdt-set issue.title "Document new commands"
        agdt-set issue.whats_missing "No docs for agdt-create-agdt-* commands"
        agdt-create-agdt-documentation-issue
    """
    _set_issue_value_if_provided("title", title)
    _set_issue_value_if_provided("whats_missing", whats_missing)
    _set_issue_value_if_provided("suggested_content", suggested_content)
    _set_issue_value_if_provided("affected_commands", affected_commands)
    _set_issue_value_if_provided("related_issue", related_issue)
    _set_issue_value_if_provided("assignees", assignees)
    _set_issue_value_if_provided("milestone", milestone)
    if dry_run is not None:  # pragma: no cover
        set_value("issue.dry_run", dry_run)

    resolved_title = _require_issue_value("title", 'agdt-create-agdt-documentation-issue --title "Doc title"')
    _require_issue_value(
        "whats_missing",
        'agdt-create-agdt-documentation-issue --whats-missing "What is missing"',
    )

    task = run_function_in_background(
        _ISSUE_MODULE,
        "create_agdt_documentation_issue",
        command_display_name="agdt-create-agdt-documentation-issue",
    )
    print_task_tracking_info(task, f"Creating documentation issue: {resolved_title}")


def create_agdt_documentation_issue_async_cli() -> None:
    """CLI entry point for agdt-create-agdt-documentation-issue with argparse."""
    parser = argparse.ArgumentParser(
        prog="agdt-create-agdt-documentation-issue",
        description=(
            "Create a documentation issue in the agentic-devtools repository (ayaiayorg/agentic-devtools).\n\n"
            "Composes a structured issue with sections for What's Missing/Incorrect,\n"
            "Suggested Content, and Affected Commands.\n"
            "Auto-sets label: documentation, issue type: Task."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Full documentation issue (with optional fields)\n"
            "  agdt-create-agdt-documentation-issue \\\n"
            '    --title "Document agdt-create-agdt-issue" \\\n'
            '    --whats-missing "No documentation for the new issue creation commands" \\\n'
            '    --suggested-content "Add CLI reference with examples" \\\n'
            '    --affected-commands "agdt-create-agdt-issue,agdt-create-agdt-bug-issue"\n\n'
            "  # Minimal (required fields only)\n"
            "  agdt-create-agdt-documentation-issue \\\n"
            '    --title "Missing docs" \\\n'
            '    --whats-missing "High-level overview is missing"\n\n'
            "  # Preview before submitting\n"
            "  agdt-create-agdt-documentation-issue \\\n"
            '    --title "..." \\\n'
            '    --whats-missing "Describe what is missing" --dry-run\n\n' + _SEE_ALSO_BASE
        ),
        add_help=False,
    )

    required_group = parser.add_argument_group("Required")
    required_group.add_argument("--title", type=str, default=None, metavar="TEXT", help="Issue title")
    required_group.add_argument(
        "--whats-missing",
        type=str,
        default=None,
        metavar="TEXT",
        help="What documentation is missing, wrong, or outdated",
    )

    optional_group = parser.add_argument_group("Optional")
    optional_group.add_argument(
        "--suggested-content",
        type=str,
        default=None,
        metavar="TEXT",
        help="Proposed documentation text or outline",
    )
    optional_group.add_argument(
        "--affected-commands",
        type=str,
        default=None,
        metavar="TEXT",
        help="Which agdt-* commands are affected",
    )
    optional_group.add_argument(
        "--related-issue",
        type=str,
        default=None,
        metavar="NUMBER",
        help='Link to related issue(s) with "Related to #NNN"',
    )
    optional_group.add_argument(
        "--assignees", type=str, default=None, metavar="TEXT", help="Comma-separated GitHub usernames"
    )
    optional_group.add_argument("--milestone", type=str, default=None, metavar="TEXT", help="Milestone name or number")
    optional_group.add_argument(
        "--dry-run", action="store_true", default=False, help="Preview the composed issue without submitting"
    )
    optional_group.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    args = parser.parse_args()
    create_agdt_documentation_issue_async(
        title=args.title,
        whats_missing=args.whats_missing,
        suggested_content=args.suggested_content,
        affected_commands=args.affected_commands,
        related_issue=args.related_issue,
        assignees=args.assignees,
        milestone=args.milestone,
        dry_run=args.dry_run if args.dry_run else None,
    )


# =============================================================================
# Task Issue Command (Async)
# =============================================================================


def create_agdt_task_issue_async(
    title: Optional[str] = None,
    description: Optional[str] = None,
    acceptance_criteria: Optional[str] = None,
    labels: Optional[str] = None,
    related_issue: Optional[str] = None,
    assignees: Optional[str] = None,
    milestone: Optional[str] = None,
    dry_run: Optional[bool] = None,
) -> None:
    """
    Create a task issue in ayaiayorg/agentic-devtools (background task).

    Auto-sets: issue type 'Task'.

    State keys (prefixed with 'issue.'):
    - issue.title (required)
    - issue.description (required)
    - issue.acceptance_criteria, issue.labels,
      issue.related_issue, issue.assignees, issue.milestone, issue.dry_run (optional)

    Usage:
        agdt-set issue.title "Task title"
        agdt-set issue.description "What needs to be done"
        agdt-create-agdt-task-issue
    """
    _set_issue_value_if_provided("title", title)
    _set_issue_value_if_provided("description", description)
    _set_issue_value_if_provided("acceptance_criteria", acceptance_criteria)
    _set_issue_value_if_provided("labels", labels)
    _set_issue_value_if_provided("related_issue", related_issue)
    _set_issue_value_if_provided("assignees", assignees)
    _set_issue_value_if_provided("milestone", milestone)
    if dry_run is not None:  # pragma: no cover
        set_value("issue.dry_run", dry_run)

    resolved_title = _require_issue_value("title", 'agdt-create-agdt-task-issue --title "Task title"')
    _require_issue_value("description", 'agdt-create-agdt-task-issue --description "What needs to be done"')

    task = run_function_in_background(
        _ISSUE_MODULE,
        "create_agdt_task_issue",
        command_display_name="agdt-create-agdt-task-issue",
    )
    print_task_tracking_info(task, f"Creating task issue: {resolved_title}")


def create_agdt_task_issue_async_cli() -> None:
    """CLI entry point for agdt-create-agdt-task-issue with argparse."""
    parser = argparse.ArgumentParser(
        prog="agdt-create-agdt-task-issue",
        description=(
            "Create a task issue in the agentic-devtools repository (ayaiayorg/agentic-devtools).\n\n"
            "Composes a structured issue with sections for description and optional Acceptance Criteria.\n"
            "Auto-sets issue type: Task."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Full task issue\n"
            "  agdt-create-agdt-task-issue \\\n"
            '    --title "Refactor state module" \\\n'
            '    --description "Split state.py into smaller modules"\n\n'
            "  # With acceptance criteria\n"
            "  agdt-create-agdt-task-issue \\\n"
            '    --title "Add tests" \\\n'
            '    --description "Add unit tests for github module" \\\n'
            '    --acceptance-criteria "- [ ] 90% coverage achieved"\n\n'
            "  # Preview before submitting\n"
            '  agdt-create-agdt-task-issue --title "..." --description "..." --dry-run\n\n' + _SEE_ALSO_BASE
        ),
        add_help=False,
    )

    required_group = parser.add_argument_group("Required")
    required_group.add_argument("--title", type=str, default=None, metavar="TEXT", help="Issue title")
    required_group.add_argument("--description", type=str, default=None, metavar="TEXT", help="What needs to be done")

    optional_group = parser.add_argument_group("Optional")
    optional_group.add_argument(
        "--acceptance-criteria", type=str, default=None, metavar="TEXT", help="Bullet list of done conditions"
    )
    optional_group.add_argument(
        "--labels", type=str, default=None, metavar="TEXT", help="Additional comma-separated labels"
    )
    optional_group.add_argument(
        "--related-issue",
        type=str,
        default=None,
        metavar="NUMBER",
        help='Link to related issue(s) with "Related to #NNN"',
    )
    optional_group.add_argument(
        "--assignees", type=str, default=None, metavar="TEXT", help="Comma-separated GitHub usernames"
    )
    optional_group.add_argument("--milestone", type=str, default=None, metavar="TEXT", help="Milestone name or number")
    optional_group.add_argument(
        "--dry-run", action="store_true", default=False, help="Preview the composed issue without submitting"
    )
    optional_group.add_argument("-h", "--help", action="help", help="Show this help message and exit")

    args = parser.parse_args()
    create_agdt_task_issue_async(
        title=args.title,
        description=args.description,
        acceptance_criteria=args.acceptance_criteria,
        labels=args.labels,
        related_issue=args.related_issue,
        assignees=args.assignees,
        milestone=args.milestone,
        dry_run=args.dry_run if args.dry_run else None,
    )
