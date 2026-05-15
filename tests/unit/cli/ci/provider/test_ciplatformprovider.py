"""Tests for CIPlatformProvider ABC."""

import pytest

from agentic_devtools.cli.ci.models import (
    CheckRunStatus,
    EventPayload,
    PRMetadata,
    ReviewInfo,
)
from agentic_devtools.cli.ci.provider import CIPlatformProvider


class _ConcreteProvider(CIPlatformProvider):
    """Minimal concrete implementation for testing the ABC contract."""

    def parse_event(self, raw_payload: dict, event_name: str) -> EventPayload:
        return EventPayload(pr_number=raw_payload.get("number", 0), action=event_name)

    def get_pr_metadata(self, pr_number: int) -> PRMetadata:
        return PRMetadata(number=pr_number, title="test", head_branch="b", head_sha="s", base_branch="main")

    def list_check_runs(self, head_sha: str) -> list[CheckRunStatus]:
        return [CheckRunStatus(id=1, name="ci", status="completed", conclusion="success")]

    def list_reviews(self, pr_number: int) -> list[ReviewInfo]:
        return [ReviewInfo(id=1, user="reviewer", state="APPROVED")]

    def post_comment(self, pr_number: int, body: str) -> int:
        return 100

    def update_comment(self, comment_id: int, body: str) -> None:
        pass

    def find_comment(self, pr_number: int, marker: str) -> tuple[int, str] | None:
        return None

    def approve_pr(self, pr_number: int, head_sha: str, body: str) -> None:
        pass

    def merge_pr(self, pr_number: int, head_sha: str, method: str) -> None:
        pass

    def request_reviewer(self, pr_number: int, reviewer: str) -> None:
        pass

    def list_pr_files(self, pr_number: int) -> list[str]:
        return ["file.py"]

    def get_check_annotations(self, check_run_id: int, limit: int) -> list[str]:
        return ["annotation"]

    def dispatch_repair(
        self,
        pr_number: int,
        head_sha: str,
        repair_type: str,
        failed_checks: list[CheckRunStatus],
        review_comments: list[str],
    ) -> int:
        return 200

    def list_review_comments(self, pr_number: int, review_id: int) -> list[str]:
        return ["review comment"]


class TestCIPlatformProvider:
    """Tests for the CIPlatformProvider abstract base class."""

    def test_cannot_instantiate_abc(self) -> None:
        with pytest.raises(TypeError, match="abstract method"):
            CIPlatformProvider()  # type: ignore[abstract]

    def test_concrete_provider_instantiates(self) -> None:
        provider = _ConcreteProvider()
        assert isinstance(provider, CIPlatformProvider)

    def test_parse_event_signature(self) -> None:
        provider = _ConcreteProvider()
        result = provider.parse_event({"number": 42}, "pull_request")
        assert isinstance(result, EventPayload)
        assert result.pr_number == 42

    def test_get_pr_metadata_returns_correct_type(self) -> None:
        provider = _ConcreteProvider()
        result = provider.get_pr_metadata(10)
        assert isinstance(result, PRMetadata)
        assert result.number == 10

    def test_list_check_runs_returns_list(self) -> None:
        provider = _ConcreteProvider()
        result = provider.list_check_runs("abc123")
        assert isinstance(result, list)
        assert all(isinstance(r, CheckRunStatus) for r in result)

    def test_list_reviews_returns_list(self) -> None:
        provider = _ConcreteProvider()
        result = provider.list_reviews(1)
        assert isinstance(result, list)
        assert all(isinstance(r, ReviewInfo) for r in result)

    def test_post_comment_returns_int(self) -> None:
        provider = _ConcreteProvider()
        result = provider.post_comment(1, "hello")
        assert isinstance(result, int)

    def test_update_comment_returns_none(self) -> None:
        provider = _ConcreteProvider()
        result = provider.update_comment(1, "updated")
        assert result is None

    def test_find_comment_returns_none_or_tuple(self) -> None:
        provider = _ConcreteProvider()
        result = provider.find_comment(1, "marker")
        assert result is None

    def test_approve_pr_returns_none(self) -> None:
        provider = _ConcreteProvider()
        result = provider.approve_pr(1, "sha", "LGTM")
        assert result is None

    def test_merge_pr_returns_none(self) -> None:
        provider = _ConcreteProvider()
        result = provider.merge_pr(1, "sha", "squash")
        assert result is None

    def test_request_reviewer_returns_none(self) -> None:
        provider = _ConcreteProvider()
        result = provider.request_reviewer(1, "user")
        assert result is None

    def test_list_pr_files_returns_list(self) -> None:
        provider = _ConcreteProvider()
        result = provider.list_pr_files(1)
        assert isinstance(result, list)
        assert all(isinstance(f, str) for f in result)

    def test_get_check_annotations_returns_list(self) -> None:
        provider = _ConcreteProvider()
        result = provider.get_check_annotations(1, 10)
        assert isinstance(result, list)
        assert all(isinstance(a, str) for a in result)

    def test_abstract_methods_list(self) -> None:
        """Verify all expected abstract methods are defined."""
        expected_methods = {
            "parse_event",
            "get_pr_metadata",
            "list_check_runs",
            "list_reviews",
            "post_comment",
            "update_comment",
            "find_comment",
            "approve_pr",
            "merge_pr",
            "request_reviewer",
            "list_pr_files",
            "get_check_annotations",
            "dispatch_repair",
            "list_review_comments",
        }
        actual_abstracts = CIPlatformProvider.__abstractmethods__
        assert actual_abstracts == expected_methods
