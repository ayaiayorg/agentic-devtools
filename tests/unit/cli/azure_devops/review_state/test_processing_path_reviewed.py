"""Tests for PROCESSING_PATH_REVIEWED."""

from agentic_devtools.cli.azure_devops.review_state import PROCESSING_PATH_REVIEWED


def test_processing_path_reviewed_value():
    assert PROCESSING_PATH_REVIEWED == "reviewed"
