"""
Auto-detect issue tracking and code hosting platforms.

Inspects environment variables, ``.github/agdt-config.json``, and the
``origin`` git remote URL to determine which platforms the user's project uses.
Returns a frozen :class:`DetectionResult` dataclass and provides a user-facing
:func:`confirm_and_override` helper.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from agentic_devtools.config import (
    DEFAULT_CODE_HOSTING,
    DEFAULT_ISSUE_ADAPTER,
    VALID_CODE_HOSTING,
    VALID_ISSUE_ADAPTERS,
    load_platform_config,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns for remote URL parsing
# ---------------------------------------------------------------------------

# GitHub: https://github.com/owner/repo.git  or  git@github.com:owner/repo.git
_GITHUB_REMOTE_RE = re.compile(
    r"github\.com[:/]([\w.-]+)/([\w.-]+?)(?:\.git)?$",
)

# Azure DevOps HTTPS: https://dev.azure.com/{org}/{project}/_git/{repo}
_ADO_HTTPS_RE = re.compile(
    r"dev\.azure\.com/([^/]+)/([^/]+)/_git/",
)

# Azure DevOps SSH (new): git@ssh.dev.azure.com:v3/{org}/{project}/{repo}
_ADO_SSH_RE = re.compile(
    r"ssh\.dev\.azure\.com:v3/([^/]+)/([^/]+)/",
)

# Azure DevOps legacy (SSH + HTTPS):
#   {org}@vs-ssh.visualstudio.com:v3/{org}/{project}/{repo}
#   https://{org}.visualstudio.com/{project}/_git/{repo}
_ADO_LEGACY_RE = re.compile(
    r"([^@/]+)(?:@vs-ssh)?\.visualstudio\.com[:/](?:v3/[^/]+/)?([^/]+)",
)


# ---------------------------------------------------------------------------
# DetectionResult dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DetectionResult:
    """Immutable result of platform auto-detection."""

    detected_issue_platforms: tuple[str, ...] = ()
    detected_code_hosting: str | None = None
    github_repo: str | None = None
    azure_devops_project: str | None = None
    confidence: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_origin_remote_url(repo_path: str | None = None) -> str | None:
    """Return the ``origin`` remote URL, or *None* on any failure.

    If *repo_path* is provided, run the git command in that directory so
    that the correct repository's remote is queried regardless of CWD.
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=False,
            cwd=repo_path,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, OSError) as exc:
        logger.debug("Could not retrieve origin remote URL: %s", exc)
    return None


def _detect_jira(
    repo_path: str,
    platform_config: dict,
) -> tuple[bool, str]:
    """Detect Jira usage from env vars and config.

    Returns ``(detected, confidence)`` where *confidence* is ``"high"``
    or ``"medium"``.
    """
    env_signal = bool(
        os.environ.get("JIRA_COPILOT_PAT") or os.environ.get("JIRA_BASE_URL") or os.environ.get("JIRA_API_TOKEN")
    )

    config_signal = platform_config.get("issue_adapter") == "jira" or bool(platform_config.get("jira"))

    if env_signal and config_signal:
        return True, "high"
    if env_signal or config_signal:
        return True, "medium"
    return False, ""


def _detect_github(
    repo_path: str,
    remote_url: str | None,
) -> tuple[bool, str | None, str]:
    """Detect GitHub from ``.git/`` directory and remote URL.

    Returns ``(detected, github_repo, confidence)``.
    """
    git_dir_exists = (Path(repo_path) / ".git").exists()

    if remote_url:
        m = _GITHUB_REMOTE_RE.search(remote_url)
        if m:
            owner, repo = m.group(1), m.group(2)
            return True, f"{owner}/{repo}", "high"

    if git_dir_exists:
        return True, None, "medium"

    return False, None, ""


def _detect_azure_devops(
    remote_url: str | None,
) -> tuple[bool, str | None, str]:
    """Detect Azure DevOps from remote URL patterns.

    Returns ``(detected, org_project, confidence)``.
    """
    if not remote_url:
        return False, None, ""

    for pattern in (_ADO_HTTPS_RE, _ADO_SSH_RE, _ADO_LEGACY_RE):
        m = pattern.search(remote_url)
        if m:
            org, project = m.group(1), m.group(2)
            return True, f"{org}/{project}", "high"

    return False, None, ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_platforms(repo_path: str) -> DetectionResult:
    """Detect issue tracking and code hosting platforms.

    Inspects environment variables, ``.github/agdt-config.json``, and the
    ``origin`` git remote URL.  Individual sub-detector failures do **not**
    prevent the other detectors from running.

    Args:
        repo_path: Absolute (or relative) path to the root of the target repo.

    Returns:
        A frozen :class:`DetectionResult` with aggregated detection data.
    """
    platform_config = load_platform_config(repo_path)
    remote_url = _get_origin_remote_url(repo_path)

    issue_platforms: list[str] = []
    confidence: dict[str, str] = {}
    code_hosting: str | None = None
    github_repo: str | None = None
    azure_devops_project: str | None = None

    # --- Jira ---
    jira_detected, jira_conf = _detect_jira(repo_path, platform_config)
    if jira_detected:
        issue_platforms.append("jira")
        confidence["jira"] = jira_conf

    # --- GitHub ---
    gh_detected, gh_repo, gh_conf = _detect_github(repo_path, remote_url)
    if gh_detected:
        github_repo = gh_repo
        confidence["github"] = gh_conf
        if gh_conf == "high":
            code_hosting = "github"
            issue_platforms.append("github")

    # --- Azure DevOps ---
    ado_detected, ado_project, ado_conf = _detect_azure_devops(remote_url)
    if ado_detected:
        azure_devops_project = ado_project
        confidence["azure_devops"] = ado_conf
        code_hosting = "azure_devops"

    return DetectionResult(
        detected_issue_platforms=tuple(issue_platforms),
        detected_code_hosting=code_hosting,
        github_repo=github_repo,
        azure_devops_project=azure_devops_project,
        confidence=confidence,
    )


def confirm_and_override(
    result: DetectionResult,
    *,
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[..., None] = print,
) -> dict:
    """Display detection results and prompt the user to confirm or override.

    Args:
        result: The auto-detected :class:`DetectionResult`.
        input_fn: Callable used to read user input (default: ``input``).
        print_fn: Callable used for output (default: ``print``).

    Returns:
        A ``dict`` compatible with :func:`save_platform_config`.
    """

    def _build_config_from_result(res: DetectionResult) -> dict:
        """Convert a DetectionResult into a save_platform_config-compatible dict."""
        issue_adapter = DEFAULT_ISSUE_ADAPTER
        if res.detected_issue_platforms:
            issue_adapter = res.detected_issue_platforms[0]

        hosting = res.detected_code_hosting or DEFAULT_CODE_HOSTING

        jira_sub: dict = {}
        github_sub: dict = {}
        ado_sub: dict = {}
        if res.github_repo:
            github_sub["repo"] = res.github_repo
        if res.azure_devops_project:
            ado_sub["project"] = res.azure_devops_project

        return {
            "issue_adapter": issue_adapter,
            "code_hosting": hosting,
            "jira": jira_sub,
            "github": github_sub,
            "azure_devops": ado_sub,
        }

    # --- Print summary ---
    print_fn("\n--- Detected Platforms ---")
    if result.detected_issue_platforms:
        print_fn(f"  Issue tracking : {', '.join(result.detected_issue_platforms)}")
    else:
        print_fn("  Issue tracking : (none detected)")
    print_fn(f"  Code hosting   : {result.detected_code_hosting or '(none detected)'}")
    if result.github_repo:
        print_fn(f"  GitHub repo    : {result.github_repo}")
    if result.azure_devops_project:
        print_fn(f"  ADO project    : {result.azure_devops_project}")
    if result.confidence:
        print_fn(f"  Confidence     : {result.confidence}")
    print_fn("")

    # --- Prompt ---
    try:
        answer = input_fn("Accept detected platforms? [Y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return _build_config_from_result(result)

    if answer in ("", "y", "yes"):
        return _build_config_from_result(result)

    # --- Override flow ---
    valid_adapters = sorted(VALID_ISSUE_ADAPTERS)
    valid_hosting = sorted(VALID_CODE_HOSTING)

    issue_adapter = DEFAULT_ISSUE_ADAPTER
    max_attempts = 3
    for _ in range(max_attempts):
        try:
            choice = (
                input_fn(
                    f"Issue adapter ({', '.join(valid_adapters)}) [{DEFAULT_ISSUE_ADAPTER}]: ",
                )
                .strip()
                .lower()
            )
        except (EOFError, KeyboardInterrupt):
            break
        if not choice:
            break
        if choice in VALID_ISSUE_ADAPTERS:
            issue_adapter = choice
            break
        print_fn(f"  Invalid choice. Valid options: {', '.join(valid_adapters)}")

    hosting = DEFAULT_CODE_HOSTING
    for _ in range(max_attempts):
        try:
            choice = (
                input_fn(
                    f"Code hosting ({', '.join(valid_hosting)}) [{DEFAULT_CODE_HOSTING}]: ",
                )
                .strip()
                .lower()
            )
        except (EOFError, KeyboardInterrupt):
            break
        if not choice:
            break
        if choice in VALID_CODE_HOSTING:
            hosting = choice
            break
        print_fn(f"  Invalid choice. Valid options: {', '.join(valid_hosting)}")

    return {
        "issue_adapter": issue_adapter,
        "code_hosting": hosting,
        "jira": {},
        "github": {},
        "azure_devops": {},
    }
