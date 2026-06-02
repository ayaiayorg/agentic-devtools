"""Tests for speckit_trigger module (deprecated).

The process_speckit_label_event function and all supporting private functions
have been removed as part of consolidating Phase 1 into the unified
speckit-phase-progression.yml workflow.

These tests verify the deprecation stub and remaining constants.
"""

from agentic_devtools.cli.ci.speckit_trigger import (
    DEPRECATION_MESSAGE,
    EXIT_FAILED,
    EXIT_MALFORMED_EVENT,
    EXIT_MISSING_CONFIG,
    EXIT_SUCCESS,
)


class TestSpeckitTriggerModuleDeprecation:
    """Tests for the deprecated speckit_trigger module surface."""

    def test_exit_constants_preserved(self) -> None:
        """Exit code constants remain available for backward compatibility."""
        assert EXIT_SUCCESS == 0
        assert EXIT_FAILED == 1
        assert EXIT_MALFORMED_EVENT == 2
        assert EXIT_MISSING_CONFIG == 10

    def test_deprecation_message_present(self) -> None:
        """Deprecation message references the new workflow."""
        assert "deprecated" in DEPRECATION_MESSAGE.lower()
        assert "speckit-phase-progression.yml" in DEPRECATION_MESSAGE
