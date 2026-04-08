"""Tests for _resolve_thread mutation helper."""

import json
import subprocess
from unittest.mock import patch

from agentic_devtools.cli.github.resolve_review_threads import _resolve_thread

_MODULE = "agentic_devtools.cli.github.resolve_review_threads"


class TestResolveThread:
    """Tests for _resolve_thread."""

    @patch(f"{_MODULE}.run_safe")
    def test_successful_resolution(self, mock_run):
        """Return True when mutation reports isResolved=true."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps({"data": {"resolveReviewThread": {"thread": {"id": "PRT_a", "isResolved": True}}}}),
            stderr="",
        )
        assert _resolve_thread("PRT_a") is True

    @patch(f"{_MODULE}.run_safe")
    def test_nonzero_exit_returns_false(self, mock_run):
        """Return False on non-zero exit code."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
        assert _resolve_thread("PRT_a") is False

    @patch(f"{_MODULE}.run_safe")
    def test_malformed_json_returns_false(self, mock_run):
        """Return False on malformed JSON response."""
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="not-json", stderr="")
        assert _resolve_thread("PRT_a") is False

    @patch(f"{_MODULE}.run_safe")
    def test_mutation_returns_not_resolved(self, mock_run):
        """Return False when mutation reports isResolved=false."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps({"data": {"resolveReviewThread": {"thread": {"id": "PRT_a", "isResolved": False}}}}),
            stderr="",
        )
        assert _resolve_thread("PRT_a") is False

    @patch(f"{_MODULE}.run_safe")
    def test_missing_key_returns_false(self, mock_run):
        """Return False when response is missing expected keys."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps({"data": {}}),
            stderr="",
        )
        assert _resolve_thread("PRT_a") is False

    @patch(f"{_MODULE}.run_safe")
    def test_oserror_returns_false(self, mock_run):
        """Return False when run_safe raises OSError."""
        mock_run.side_effect = OSError("gh not found")
        assert _resolve_thread("PRT_a") is False
