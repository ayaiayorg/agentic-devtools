"""Tests for _emit_decision_summary() structured logging."""

import json
from io import StringIO
from unittest.mock import patch

from agentic_devtools.cli.ci.orchestrator import _emit_decision_summary


class TestEmitDecisionSummary:
    """Tests for the structured decision summary emission."""

    def test_emits_json_to_stdout(self) -> None:
        """Summary dict is serialised as pretty-printed JSON to stdout."""
        summary = {"decision": "merged", "exit_code": 0}
        buf = StringIO()
        with patch("agentic_devtools.cli.ci.orchestrator.sys.stdout", buf):
            with patch("agentic_devtools.cli.ci.orchestrator._is_github_actions", return_value=False):
                _emit_decision_summary(summary)
        output = buf.getvalue()
        parsed = json.loads(output)
        assert parsed == summary

    def test_emits_group_annotations_in_github_actions(self) -> None:
        """When running in GHA, ::group:: / ::endgroup:: are emitted."""
        summary = {"decision": "skip", "exit_code": 0}
        out_buf = StringIO()
        err_buf = StringIO()
        with (
            patch("agentic_devtools.cli.ci.orchestrator.sys.stdout", out_buf),
            patch("agentic_devtools.cli.ci.orchestrator.sys.stderr", err_buf),
            patch("agentic_devtools.cli.ci.orchestrator._is_github_actions", return_value=True),
        ):
            _emit_decision_summary(summary)
        assert json.loads(out_buf.getvalue()) == summary
        stderr_output = err_buf.getvalue()
        assert "::group::" in stderr_output
        assert "::endgroup::" in stderr_output

    def test_no_group_annotations_outside_github_actions(self) -> None:
        """When not in GHA, no ::group:: annotations are emitted."""
        summary = {"decision": "merged", "exit_code": 0}
        out_buf = StringIO()
        err_buf = StringIO()
        with (
            patch("agentic_devtools.cli.ci.orchestrator.sys.stdout", out_buf),
            patch("agentic_devtools.cli.ci.orchestrator.sys.stderr", err_buf),
            patch("agentic_devtools.cli.ci.orchestrator._is_github_actions", return_value=False),
        ):
            _emit_decision_summary(summary)
        assert json.loads(out_buf.getvalue()) == summary
        assert err_buf.getvalue() == ""
