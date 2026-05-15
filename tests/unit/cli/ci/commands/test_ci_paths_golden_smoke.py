"""Golden-file smoke tests for legacy and Python CI command paths."""

import json
import os
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_devtools.cli.ci.commands import ai_pr_loop_command, speckit_trigger_command

FIXTURES_DIR = Path(__file__).resolve().parents[4] / "fixtures" / "ci_events"


def _run_ai_command(event_file: str, event_name: str, flag_value: str) -> dict:
    env = {
        "AGDT_USE_PYTHON_ORCHESTRATOR": flag_value,
        "GITHUB_EVENT_PATH": str(FIXTURES_DIR / event_file),
        "GITHUB_EVENT_NAME": event_name,
        "GITHUB_REPOSITORY": "owner/repo",
    }
    with patch.dict(os.environ, env, clear=True):
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with patch("agentic_devtools.cli.ci.commands.run_ai_pr_loop", return_value=0) as mock_loop:
                with pytest.raises(SystemExit) as exc_info:
                    ai_pr_loop_command()
                result = {
                    "exit_code": exc_info.value.code,
                    "run_ai_pr_loop_called": mock_loop.called,
                }
                if mock_loop.called:
                    event_payload = mock_loop.call_args[0][1]
                    result["event_payload"] = asdict(event_payload)
                return result


def _run_speckit_command(event_file: str, event_name: str, flag_value: str) -> dict:
    env = {
        "AGDT_USE_PYTHON_ORCHESTRATOR": flag_value,
        "GITHUB_EVENT_PATH": str(FIXTURES_DIR / event_file),
        "GITHUB_EVENT_NAME": event_name,
        "GITHUB_REPOSITORY": "owner/repo",
    }
    with patch.dict(os.environ, env, clear=True):
        with patch("shutil.which", return_value="/usr/bin/gh"):
            with pytest.raises(SystemExit) as exc_info:
                speckit_trigger_command()
            return {"exit_code": exc_info.value.code}


@pytest.mark.parametrize(
    ("event_file", "event_name", "command", "golden_file"),
    [
        ("pull_request_opened.json", "pull_request", "ai", "golden_pull_request.json"),
        ("pull_request_review_submitted.json", "pull_request_review", "ai", "golden_pull_request_review.json"),
        ("workflow_run_completed.json", "workflow_run", "ai", "golden_workflow_run.json"),
        pytest.param(
            "issues_labeled.json",
            "issues",
            "speckit",
            "golden_issues_labeled.json",
            marks=pytest.mark.xfail(
                reason="speckit_trigger_command is a stub (exit 11); parity test deferred to Phase 6",
                strict=True,
            ),
        ),
    ],
)
def test_legacy_and_python_paths_match_goldens(
    event_file: str,
    event_name: str,
    command: str,
    golden_file: str,
) -> None:
    if command == "ai":
        legacy = _run_ai_command(event_file, event_name, "0")
        python = _run_ai_command(event_file, event_name, "1")
    else:
        legacy = _run_speckit_command(event_file, event_name, "0")
        python = _run_speckit_command(event_file, event_name, "1")

    actual = {"legacy": legacy, "python": python}
    expected = json.loads((FIXTURES_DIR / golden_file).read_text(encoding="utf-8"))
    assert actual == expected
