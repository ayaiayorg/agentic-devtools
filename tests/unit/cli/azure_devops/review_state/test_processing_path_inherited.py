"""Tests for PROCESSING_PATH_INHERITED."""

from agentic_devtools.cli.azure_devops.review_state import PROCESSING_PATH_INHERITED


def test_processing_path_inherited_value():
    assert PROCESSING_PATH_INHERITED == "inherited"
