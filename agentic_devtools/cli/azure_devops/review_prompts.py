"""
Prompt generation for PR review workflow.

Functions for creating review prompts and instructions.
"""

from datetime import datetime
from pathlib import Path

from .review_helpers import (
    build_full_file_content_section,
    convert_to_prompt_filename,
    get_root_folder,
    get_threads_for_file,
    normalize_repo_path,
    resolve_repository_root,
)


def get_prompts_output_dir() -> Path:
    """
    Get the prompts output directory.

    Returns:
        Path to the prompts output directory
    """
    return Path(__file__).parent.parent.parent.parent.parent / "temp" / "pr-review-prompts"


def build_file_prompt_content(
    file_path: str,
    change_type: str,
    pr_id: int,
    file_content: str,
    threads: list[dict],
    jira_issue_key: str | None = None,
    timestamp: str | None = None,
    repo_root: Path | None = None,
) -> str:
    """
    Build the markdown content for a file review prompt.

    Args:
        file_path: Repository file path
        change_type: Type of change (add, edit, delete, rename)
        pr_id: Pull request ID
        file_content: File diff/content
        threads: Review threads for this file
        jira_issue_key: Optional Jira issue key for context
        timestamp: Optional timestamp (defaults to now)
        repo_root: Optional repository root used to resolve ``file_path`` for
            the appended full-file-content section. When omitted, path
            resolution falls back through ``resolve_repository_root()``, which
            may invoke ``git rev-parse --show-toplevel`` and ultimately falls
            back to ``Path.cwd()``.

    Returns:
        Formatted markdown prompt content
    """
    if timestamp is None:
        timestamp = datetime.now(tz=None).astimezone().strftime("%Y-%m-%dT%H:%M:%SZ")

    root_folder = get_root_folder(file_path)

    lines = [
        f"# PR Review: {file_path}",
        "",
        "## Metadata",
        f"- **PR ID**: {pr_id}",
        f"- **File**: `{file_path}`",
        f"- **Change Type**: {change_type}",
        f"- **Root Folder**: {root_folder}",
        f"- **Generated**: {timestamp}",
    ]

    if jira_issue_key:
        try:
            from ..jira.config import get_jira_base_url

            jira_url = get_jira_base_url().rstrip("/")
        except (ValueError, ImportError):
            jira_url = ""
        if jira_url:
            lines.append(f"- **Jira Issue**: [{jira_issue_key}]({jira_url}/browse/{jira_issue_key})")
        else:
            lines.append(f"- **Jira Issue**: {jira_issue_key}")

    lines.extend(
        [
            "",
            "## Review Instructions",
            "",
            "Review this file change according to the project's review guidelines.",
            f"Check the relevant `copilot-instructions.md` for {root_folder} if available.",
            "",
            "## File Content / Diff",
            "",
            "```diff",
            file_content if file_content else "(no content available)",
            "```",
        ]
    )

    if threads:
        lines.extend(
            [
                "",
                "## Existing Review Comments",
                "",
            ]
        )
        for thread in threads:
            comments = thread.get("comments", [])
            if comments:
                first_comment = comments[0]
                author = first_comment.get("author", {}).get("displayName", "Unknown")
                content = first_comment.get("content", "(no content)")
                status = thread.get("status", "unknown")
                lines.append(f"### Thread ({status})")
                lines.append(f"**{author}**: {content}")
                lines.append("")

    lines.extend(build_full_file_content_section(file_path, change_type, repo_root=repo_root))

    return "\n".join(lines)


def write_file_prompt(
    file_path: str,
    change_type: str,
    pr_id: int,
    file_content: str,
    threads: list[dict],
    output_dir: Path,
    jira_issue_key: str | None = None,
    repo_root: Path | None = None,
) -> Path:
    """
    Write a review prompt file for a single changed file.

    Args:
        file_path: Repository file path
        change_type: Type of change (add, edit, delete, rename)
        pr_id: Pull request ID
        file_content: File diff/content
        threads: Review threads for this file
        output_dir: Directory to write prompt file
        jira_issue_key: Optional Jira issue key for context
        repo_root: Optional repository root forwarded to
            ``build_file_prompt_content()`` for full-file-content resolution.
            When omitted, repository resolution may invoke
            ``git rev-parse --show-toplevel`` and falls back to ``Path.cwd()``
            if the git toplevel cannot be determined.

    Returns:
        Path to the written prompt file
    """
    content = build_file_prompt_content(
        file_path=file_path,
        change_type=change_type,
        pr_id=pr_id,
        file_content=file_content,
        threads=threads,
        jira_issue_key=jira_issue_key,
        repo_root=repo_root,
    )

    filename = convert_to_prompt_filename(file_path)
    output_path = output_dir / filename
    output_path.write_text(content, encoding="utf-8")

    return output_path


def generate_review_prompts(
    pr_details: dict,
    output_dir: Path,
    jira_issue_key: str | None = None,
    verbose: bool = False,
) -> list[dict]:
    """
    Generate review prompt files for all changed files in a PR.

    Args:
        pr_details: Full PR details including changes and threads
        output_dir: Directory to write prompt files
        jira_issue_key: Optional Jira issue key for context
        verbose: Whether to print progress

    Returns:
        List of dicts with file_path, prompt_path, skipped status for each file
    """
    # Ensure output directory exists and is clean
    output_dir.mkdir(parents=True, exist_ok=True)
    for existing in output_dir.glob("file-*.md"):
        existing.unlink()

    pr_id = pr_details.get("pullRequest", {}).get("pullRequestId", 0)
    changes = pr_details.get("changes", []) or []
    threads = pr_details.get("threads", []) or []

    results = []
    repo_root = resolve_repository_root()

    for change in changes:
        item = change.get("item", {})
        file_path = item.get("path", "")
        normalized = normalize_repo_path(file_path)

        if not normalized:
            continue

        change_type = change.get("changeType", "edit")
        file_content = change.get("content", "")
        file_threads = get_threads_for_file(threads, file_path)

        prompt_path = write_file_prompt(
            file_path=file_path,
            change_type=change_type,
            pr_id=pr_id,
            file_content=file_content,
            threads=file_threads,
            output_dir=output_dir,
            jira_issue_key=jira_issue_key,
            repo_root=repo_root,
        )

        if verbose:
            print(f"  ✅ Generated: {prompt_path.name} <- {file_path}")

        results.append(
            {
                "file_path": file_path,
                "prompt_path": str(prompt_path),
                "skipped": False,
            }
        )

    return results


def print_review_instructions(
    pr_details: dict,
    output_dir: Path,
    results: list[dict],
) -> None:
    """
    Print instructions for reviewing the generated prompts.

    Args:
        pr_details: Full PR details
        output_dir: Directory containing prompt files
        results: Results from generate_review_prompts
    """
    pr_id = pr_details.get("pullRequest", {}).get("pullRequestId", 0)
    pr_title = pr_details.get("pullRequest", {}).get("title", "Unknown")

    generated = [r for r in results if not r.get("skipped")]

    print(f"\n{'=' * 60}")
    print(f"PR Review Ready: #{pr_id}")
    print(f"Title: {pr_title}")
    print(f"{'=' * 60}")
    print(f"\n📁 Prompts generated: {len(generated)}")
    print(f"\n📂 Output directory: {output_dir}")

    if generated:
        print("\n🔍 To review, open each .md file in the output directory.")
        print("   Each file contains the diff, metadata, and existing comments.")
