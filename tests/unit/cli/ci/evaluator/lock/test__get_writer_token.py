"""Tests for _get_writer_token()."""

from unittest.mock import patch

from agentic_devtools.cli.ci.evaluator.lock import _get_writer_token


class TestGetWriterToken:
    """Tests for _get_writer_token helper."""

    def test_prefers_ci_run_identifiers(self):
        """Writer token uses GITHUB_RUN_ID + GITHUB_RUN_ATTEMPT when available."""
        with patch.dict(
            "os.environ",
            {"GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "2"},
            clear=False,
        ):
            token = _get_writer_token()
        assert token == "123-2"

    def test_falls_back_to_local_timestamp(self):
        """Writer token falls back to local timestamp format outside CI."""
        with (
            patch.dict("os.environ", {"GITHUB_RUN_ID": "", "GITHUB_RUN_ATTEMPT": ""}, clear=False),
            patch("time.time", return_value=1234),
        ):
            token = _get_writer_token()
        assert token == "local-1234"
