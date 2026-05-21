"""Tests for get_dedup_writer_token."""

from unittest.mock import patch

import agentic_devtools.cli.ci.guards as guards_module
from agentic_devtools.cli.ci.guards import get_dedup_writer_token


class TestGetDedupWriterToken:
    """Tests for get_dedup_writer_token."""

    def setup_method(self):
        """Reset global token between tests."""
        guards_module._DEDUP_WRITER_TOKEN = None

    def teardown_method(self):
        """Reset global token after tests."""
        guards_module._DEDUP_WRITER_TOKEN = None

    def test_returns_local_token_when_no_github_env(self):
        """Returns a local.* token when GITHUB_RUN_ID is not set."""
        with patch.dict("os.environ", {}, clear=True):
            token = get_dedup_writer_token()
        assert token.startswith("local.")
        assert len(token) == len("local.") + 12

    def test_returns_run_id_based_token(self):
        """Returns run_id.attempt.job when all GitHub env vars set."""
        env = {
            "GITHUB_RUN_ID": "12345",
            "GITHUB_RUN_ATTEMPT": "2",
            "GITHUB_JOB": "test-job",
        }
        with patch.dict("os.environ", env, clear=True):
            token = get_dedup_writer_token()
        assert token == "12345.2.test-job"

    def test_caches_token(self):
        """Returns the same token on subsequent calls."""
        with patch.dict("os.environ", {"GITHUB_RUN_ID": "99"}, clear=True):
            token1 = get_dedup_writer_token()
            token2 = get_dedup_writer_token()
        assert token1 == token2
