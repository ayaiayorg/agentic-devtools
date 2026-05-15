"""SpecKit trigger orchestration for issues label events."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from agentic_devtools.cli.ci.models import EventPayload
from agentic_devtools.cli.ci.provider import CIPlatformProvider
from agentic_devtools.cli.subprocess_utils import run_safe

logger = logging.getLogger(__name__)

EXIT_SUCCESS = 0
EXIT_FAILED = 1
EXIT_MALFORMED_EVENT = 2
EXIT_MISSING_CONFIG = 10

_SPECKIT_PHASE_LABEL = "speckit:phase-1"
_SPECKIT_PHASE_COMPLETE_LABEL = "speckit:phase-1-complete"
_SPECKIT_PROCESSING_LABEL = "speckit:processing"
_SPECKIT_FAILED_LABEL = "speckit:failed"


@dataclass(frozen=True)
class _IssueContext:
    issue_number: int
    issue_title: str
    issue_body: str
    issue_url: str
    labels: list[str]


def process_speckit_label_event(provider: CIPlatformProvider, event_payload: EventPayload) -> int:
    """Process a SpecKit issues/labeled trigger event.

    The ``provider`` argument is currently reserved for future provider-backed
    API calls as this path still relies on existing shell scripts and ``gh`` CLI
    commands for parity with the workflow implementation.
    """
    del provider  # reserved for future provider-backed execution

    if event_payload.action != "labeled":
        logger.info(
            "Skipping SpecKit trigger: action %r is not 'labeled'",
            event_payload.action,
        )
        return EXIT_SUCCESS

    expected_trigger_label = os.environ.get("SPECKIT_TRIGGER_LABEL", "speckit")
    if event_payload.trigger_label != expected_trigger_label:
        logger.info(
            "Skipping SpecKit trigger: label %r does not match configured trigger %r",
            event_payload.trigger_label,
            expected_trigger_label,
        )
        return EXIT_SUCCESS

    if not os.environ.get("GITHUB_REPOSITORY", "").strip():
        logger.error("GITHUB_REPOSITORY is required for SpecKit trigger processing")
        return EXIT_MISSING_CONFIG

    try:
        issue = _load_issue_context_from_event()
    except RuntimeError as exc:
        logger.error("Failed to read issue context from event payload: %s", exc)
        return EXIT_MALFORMED_EVENT

    # Dedup guard for repeated trigger runs.
    if (
        _SPECKIT_PROCESSING_LABEL in issue.labels
        or _SPECKIT_PHASE_LABEL in issue.labels
        or _SPECKIT_PHASE_COMPLETE_LABEL in issue.labels
    ):
        logger.info(
            "Skipping duplicate SpecKit trigger for issue #%d: phase already in progress/present",
            issue.issue_number,
        )
        return EXIT_SUCCESS

    try:
        _set_issue_labels(
            issue.issue_number,
            add=[_SPECKIT_PROCESSING_LABEL],
            remove=[expected_trigger_label, _SPECKIT_FAILED_LABEL],
        )

        idempotency = _run_script_with_outputs(
            ".github/scripts/speckit-trigger/check-idempotency.sh",
            [str(issue.issue_number), "--phase", "1"],
        )
        if idempotency.get("skipped") == "true":
            _set_issue_labels(
                issue.issue_number,
                add=[_SPECKIT_PHASE_COMPLETE_LABEL],
                remove=[_SPECKIT_PROCESSING_LABEL],
            )
            logger.info("Skipping issue #%d: phase 1 artifacts already exist", issue.issue_number)
            return EXIT_SUCCESS

        short_name_result = _run_script_with_outputs(
            ".github/scripts/speckit-trigger/sanitize-branch-name.sh",
            [issue.issue_title],
        )
        short_name = short_name_result.get("short_name", "").strip()
        if not short_name:
            raise RuntimeError("sanitize-branch-name.sh did not provide short_name")

        generate_outputs = _run_script_with_outputs(
            ".github/scripts/speckit-trigger/generate-spec-from-issue.sh",
            ["--phase", "1"],
            extra_env={
                "ISSUE_NUMBER": str(issue.issue_number),
                "ISSUE_TITLE": issue.issue_title,
                "ISSUE_BODY": issue.issue_body,
                "ISSUE_URL": issue.issue_url,
                "SHORT_NAME": short_name,
            },
        )
        spec_dir = generate_outputs.get("spec_dir", "").strip()
        if not spec_dir:
            raise RuntimeError("generate-spec-from-issue.sh did not provide spec_dir")

        _commit_and_push_phase_branch(issue.issue_number, spec_dir)
        _create_phase_pull_request(issue, spec_dir)
    except RuntimeError as exc:
        logger.error("SpecKit trigger failed: %s", exc)
        try:
            _set_issue_labels(
                issue.issue_number,
                add=[_SPECKIT_FAILED_LABEL],
                remove=[_SPECKIT_PROCESSING_LABEL],
            )
        except RuntimeError as label_exc:
            logger.warning("Failed to update failure labels: %s", label_exc)
        return EXIT_FAILED

    try:
        _set_issue_labels(
            issue.issue_number,
            add=[_SPECKIT_PHASE_LABEL],
            remove=[_SPECKIT_PROCESSING_LABEL],
        )
    except RuntimeError as exc:
        logger.error("Failed to update labels after successful processing: %s", exc)
        return EXIT_FAILED
    return EXIT_SUCCESS


def _load_issue_context_from_event() -> _IssueContext:
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_path:
        raise RuntimeError("GITHUB_EVENT_PATH is not set")

    try:
        with open(event_path, encoding="utf-8") as f:
            raw_payload = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"failed to read event payload: {exc}") from exc

    issue = raw_payload.get("issue", {})
    if not isinstance(issue, dict):
        raise RuntimeError("event payload 'issue' field is not a mapping")
    issue_number = issue.get("number")
    if not isinstance(issue_number, int) or issue_number <= 0:
        raise RuntimeError("missing issue.number in event payload")

    raw_labels = issue.get("labels", [])
    if not isinstance(raw_labels, list):
        raise RuntimeError("event payload 'issue.labels' field is not a list")
    labels = [lbl.get("name", "") for lbl in raw_labels if isinstance(lbl, dict)]
    return _IssueContext(
        issue_number=issue_number,
        issue_title=issue.get("title", ""),
        issue_body=issue.get("body") or "",
        issue_url=issue.get("html_url", "") or "",
        labels=[name for name in labels if name],
    )


def _set_issue_labels(issue_number: int, *, add: list[str] | None = None, remove: list[str] | None = None) -> None:
    add = [label for label in (add or []) if label]
    remove = [label for label in (remove or []) if label]

    base_cmd = ["gh", "issue", "edit", str(issue_number), "--repo", _require_repository()]
    for label in add:
        _run_checked(base_cmd + ["--add-label", label])
    for label in remove:
        _run_checked(base_cmd + ["--remove-label", label])


def _run_script_with_outputs(
    relative_script_path: str,
    args: list[str],
    *,
    extra_env: dict[str, str] | None = None,
) -> dict[str, str]:
    script_path = Path(relative_script_path)
    if not script_path.exists():
        raise RuntimeError(f"script not found: {relative_script_path}")

    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)

    with tempfile.NamedTemporaryFile(prefix="agdt-speckit-", suffix=".out", delete=False) as output_file:
        output_path = output_file.name

    env["GITHUB_OUTPUT"] = output_path
    try:
        _run_checked(["bash", str(script_path)] + args, env=env)
        return _parse_key_value_file(output_path)
    finally:
        try:
            os.unlink(output_path)
        except OSError:
            pass


def _parse_key_value_file(path: str) -> dict[str, str]:
    outputs: dict[str, str] = {}
    file_path = Path(path)
    if not file_path.exists():
        return outputs

    for line in file_path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        outputs[key.strip()] = value.strip()
    return outputs


def _commit_and_push_phase_branch(issue_number: int, spec_dir: str) -> None:
    branch_name = f"speckit/{issue_number}/phase-1-specify"
    _run_checked(["git", "config", "user.name", "github-actions[bot]"])
    _run_checked(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"])

    remote_check = run_safe(
        ["git", "ls-remote", "--exit-code", "--heads", "origin", branch_name],
        capture_output=True,
        text=True,
        shell=False,
    )
    if remote_check.returncode == 0:
        _run_checked(["git", "fetch", "origin", f"refs/heads/{branch_name}:refs/remotes/origin/{branch_name}"])
        _run_checked(["git", "checkout", "-B", branch_name, f"origin/{branch_name}"])
    elif remote_check.returncode == 2:
        _run_checked(["git", "checkout", "-b", branch_name])
    else:
        stderr = remote_check.stderr.strip()
        raise RuntimeError(
            f"git ls-remote failed (rc={remote_check.returncode}): {stderr or 'unknown error'}"
        )

    _run_checked(["git", "add", spec_dir])
    _run_checked(
        [
            "git",
            "commit",
            "-m",
            f"spec(specify): Phase 1 artifacts for issue #{issue_number}\n\nRelates to #{issue_number}",
        ]
    )
    _run_checked(["git", "push", "--force-with-lease", "-u", "origin", branch_name])


def _create_phase_pull_request(issue: _IssueContext, spec_dir: str) -> None:
    labels = json.dumps(issue.labels)
    _run_script_with_outputs(
        ".github/scripts/speckit-trigger/create-spec-pr.sh",
        [
            f"speckit/{issue.issue_number}/phase-1-specify",
            spec_dir,
            str(issue.issue_number),
            issue.issue_title,
            labels,
            "--phase-number",
            "1",
            "--phase-name",
            "specify",
        ],
    )


def _run_checked(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    result = run_safe(cmd, capture_output=True, text=True, shell=False, env=env)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(stderr or f"command failed: {' '.join(cmd)}")


def _require_repository() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not repo:
        raise RuntimeError("GITHUB_REPOSITORY is required")
    return repo
