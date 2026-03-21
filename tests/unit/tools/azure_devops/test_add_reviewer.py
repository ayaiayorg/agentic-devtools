"""Tests for agentic_devtools.tools.azure_devops stub functions (add_reviewer, complete_pull_request, file_review)."""

import pytest

from agentic_devtools.tools.azure_devops import (
    add_reviewer,
    complete_pull_request,
    file_review,
)


class TestAddReviewer:
    """Tests for the add_reviewer stub."""

    def test_raises_not_implemented(self):
        with pytest.raises(NotImplementedError, match="Planned for future implementation"):
            add_reviewer(config=None, pat="pat", pull_request_id=1, reviewer_id="user@example.com")


class TestCompletePullRequest:
    """Tests for the complete_pull_request stub."""

    def test_raises_not_implemented(self):
        with pytest.raises(NotImplementedError, match="Planned for future implementation"):
            complete_pull_request(config=None, pat="pat", pull_request_id=1)

    def test_raises_not_implemented_with_merge_strategy(self):
        with pytest.raises(NotImplementedError, match="Planned for future implementation"):
            complete_pull_request(config=None, pat="pat", pull_request_id=1, merge_strategy="rebase")


class TestFileReview:
    """Tests for the file_review stub."""

    def test_raises_not_implemented(self):
        with pytest.raises(NotImplementedError, match="Planned for future implementation"):
            file_review(config=None, pat="pat", pull_request_id=1, file_path="/src/main.py")

    def test_raises_not_implemented_with_params(self):
        with pytest.raises(NotImplementedError, match="Planned for future implementation"):
            file_review(
                config=None,
                pat="pat",
                pull_request_id=1,
                file_path="/src/main.py",
                status="needs-work",
                comment="Please fix",
            )
