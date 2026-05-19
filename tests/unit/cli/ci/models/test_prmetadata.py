"""Tests for PRMetadata dataclass."""

from agentic_devtools.cli.ci.models import PRMetadata


class TestPRMetadata:
    """Tests for the PRMetadata dataclass."""

    def test_required_fields(self) -> None:
        meta = PRMetadata(
            number=42,
            title="feat: add feature",
            head_branch="feature/test",
            head_sha="abc123",
            base_branch="main",
        )
        assert meta.number == 42
        assert meta.title == "feat: add feature"
        assert meta.head_branch == "feature/test"
        assert meta.head_sha == "abc123"
        assert meta.base_branch == "main"

    def test_default_values(self) -> None:
        meta = PRMetadata(
            number=1,
            title="t",
            head_branch="b",
            head_sha="s",
            base_branch="main",
        )
        assert meta.head_repo_full_name == ""
        assert meta.base_repo_full_name == ""
        assert meta.labels == []
        assert meta.requested_reviewers == []
        assert meta.is_draft is False
        assert meta.mergeable is None

    def test_with_all_fields(self) -> None:
        meta = PRMetadata(
            number=100,
            title="fix: bug",
            head_branch="fix/bug",
            head_sha="def456",
            base_branch="main",
            head_repo_full_name="fork/repo",
            base_repo_full_name="owner/repo",
            labels=["bug", "priority-high"],
            requested_reviewers=["copilot-pull-request-reviewer[bot]"],
            is_draft=True,
            mergeable=False,
        )
        assert meta.head_repo_full_name == "fork/repo"
        assert meta.base_repo_full_name == "owner/repo"
        assert meta.labels == ["bug", "priority-high"]
        assert meta.requested_reviewers == ["copilot-pull-request-reviewer[bot]"]
        assert meta.is_draft is True
        assert meta.mergeable is False

    def test_labels_are_independent_instances(self) -> None:
        meta1 = PRMetadata(number=1, title="t", head_branch="b", head_sha="s", base_branch="m")
        meta2 = PRMetadata(number=2, title="t", head_branch="b", head_sha="s", base_branch="m")
        assert meta1.labels is not meta2.labels
        assert meta1.requested_reviewers is not meta2.requested_reviewers

    def test_is_frozen(self) -> None:
        meta = PRMetadata(number=1, title="t", head_branch="b", head_sha="s", base_branch="m")
        try:
            meta.number = 2  # type: ignore[misc]
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass
