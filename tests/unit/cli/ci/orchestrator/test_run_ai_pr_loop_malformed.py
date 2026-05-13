"""Tests for orchestrator malformed event handling."""

from unittest.mock import MagicMock

from agentic_devtools.cli.ci.models import EventPayload
from agentic_devtools.cli.ci.orchestrator import EXIT_METADATA_FAILED, run_ai_pr_loop


class TestRunAIPRLoopMalformed:
    """Tests for malformed event error handling."""

    def test_metadata_resolution_failure(self) -> None:
        """When get_pr_metadata fails, emit structured error and return EXIT_METADATA_FAILED."""
        provider = MagicMock()
        provider.get_pr_metadata.side_effect = RuntimeError("API error")

        payload = EventPayload(pr_number=42, head_sha="abc123")
        result = run_ai_pr_loop(provider, payload)

        assert result == EXIT_METADATA_FAILED
        provider.merge_pr.assert_not_called()
