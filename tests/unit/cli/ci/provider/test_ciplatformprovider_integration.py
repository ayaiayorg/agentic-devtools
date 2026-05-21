"""Integration test verifying CIPlatformProvider ABC extensibility.

Validates that a stub Azure DevOps provider can satisfy the same ABC
contract without changes to orchestration code (acceptance scenario 2).
"""

from agentic_devtools.cli.ci.models import (
    CheckRunStatus,
    EventPayload,
    IssueEvent,
    PRMetadata,
    ReviewCommentInfo,
    ReviewInfo,
)
from agentic_devtools.cli.ci.provider import CIPlatformProvider


class _StubAdoProvider(CIPlatformProvider):
    """Stub Azure DevOps provider for ABC contract validation.

    Implements all abstract methods with minimal stubs to prove
    the interface is satisfiable by a non-GitHub provider.
    """

    def parse_event(self, raw_payload: dict, event_name: str) -> EventPayload:
        resource = raw_payload.get("resource", {})
        pr_id = resource.get("pullRequestId", 0)
        return EventPayload(
            pr_number=pr_id,
            action=event_name,
            repository_full_name=raw_payload.get("resourceContainers", {}).get("project", {}).get("id", ""),
        )

    def get_pr_metadata(self, pr_number: int) -> PRMetadata:
        raise NotImplementedError("ADO provider stub")

    def list_check_runs(self, head_sha: str) -> list[CheckRunStatus]:
        raise NotImplementedError("ADO provider stub")

    def list_reviews(self, pr_number: int) -> list[ReviewInfo]:
        raise NotImplementedError("ADO provider stub")

    def post_comment(self, pr_number: int, body: str) -> int:
        raise NotImplementedError("ADO provider stub")

    def update_comment(self, comment_id: int, body: str) -> None:
        raise NotImplementedError("ADO provider stub")

    def find_comment(self, pr_number: int, marker: str) -> tuple[int, str] | None:
        raise NotImplementedError("ADO provider stub")

    def approve_pr(self, pr_number: int, head_sha: str, body: str) -> bool:
        raise NotImplementedError("ADO provider stub")

    def merge_pr(self, pr_number: int, head_sha: str, method: str) -> None:
        raise NotImplementedError("ADO provider stub")

    def request_reviewer(self, pr_number: int, reviewer: str) -> None:
        raise NotImplementedError("ADO provider stub")

    def list_pr_files(self, pr_number: int) -> list[str]:
        raise NotImplementedError("ADO provider stub")

    def get_check_annotations(self, check_run_id: int, limit: int) -> list[str]:
        raise NotImplementedError("ADO provider stub")

    def dispatch_repair(
        self,
        pr_number: int,
        head_sha: str,
        repair_type: str,
        failed_checks: list[CheckRunStatus],
        review_comments: list[ReviewCommentInfo],
        review_id: int = 0,
    ) -> int:
        raise NotImplementedError("ADO provider stub")

    def list_review_comments(self, pr_number: int, review_id: int) -> list[ReviewCommentInfo]:
        raise NotImplementedError("ADO provider stub")

    def finalize_post_repair(
        self,
        *,
        pr_number: int,
        base_branch: str,
        head_branch: str,
        head_sha: str,
        review_id: int,
    ) -> None:
        raise NotImplementedError("ADO provider stub")

    def squash_post_repair(
        self,
        *,
        pr_number: int,
        base_branch: str,
        head_branch: str,
        head_sha: str,
    ) -> None:
        raise NotImplementedError("ADO provider stub")

    def list_pr_issue_events(self, pr_number: int) -> list[IssueEvent]:
        return []

    def publish_pr(self, pr_number: int) -> None:
        raise NotImplementedError("ADO provider stub")

    def squash_before_publish(
        self,
        *,
        pr_number: int,
        base_branch: str,
        head_branch: str,
        head_sha: str,
    ) -> None:
        raise NotImplementedError("ADO provider stub")


class TestCIPlatformProviderIntegration:
    """Integration tests verifying the ABC contract is satisfiable by different providers."""

    def test_stub_ado_provider_satisfies_abc(self) -> None:
        """A non-GitHub provider can implement the ABC without interface changes."""
        provider = _StubAdoProvider()
        assert isinstance(provider, CIPlatformProvider)

    def test_stub_ado_provider_parse_event(self) -> None:
        """ADO service hook payload can be normalized to EventPayload."""
        provider = _StubAdoProvider()
        raw = {
            "resource": {"pullRequestId": 99},
            "resourceContainers": {"project": {"id": "my-project"}},
        }
        result = provider.parse_event(raw, "git.pullrequest.updated")
        assert isinstance(result, EventPayload)
        assert result.pr_number == 99
        assert result.action == "git.pullrequest.updated"

    def test_stub_ado_provider_parse_event_empty_payload(self) -> None:
        """ADO provider handles empty payloads gracefully."""
        provider = _StubAdoProvider()
        result = provider.parse_event({}, "unknown")
        assert result.pr_number == 0
        assert result.action == "unknown"
