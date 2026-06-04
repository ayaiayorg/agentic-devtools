"""Tests for PROCESSING_PATH_REVIEWED_NO_PRIOR."""

from agentic_devtools.cli.azure_devops.review_state import PROCESSING_PATH_REVIEWED_NO_PRIOR


def test_processing_path_reviewed_no_prior_value():
    assert PROCESSING_PATH_REVIEWED_NO_PRIOR == "reviewed-no-prior"
