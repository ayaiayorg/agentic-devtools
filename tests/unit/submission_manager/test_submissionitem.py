"""Tests for agentic_devtools.submission_manager.SubmissionItem."""

import uuid

from agentic_devtools.submission_manager import SubmissionItem, SubmissionStatus


class TestSubmissionItem:
    """Tests for SubmissionItem dataclass."""

    def test_creation_with_defaults(self):
        """Test creating a SubmissionItem with minimal required fields."""
        item = SubmissionItem(
            id="test-id",
            pr_id=100,
            file_path="/src/app.ts",
            outcome="approve",
            summary="LGTM",
        )
        assert item.id == "test-id"
        assert item.pr_id == 100
        assert item.file_path == "/src/app.ts"
        assert item.outcome == "approve"
        assert item.summary == "LGTM"
        assert item.suggestions is None
        assert item.status == SubmissionStatus.QUEUED
        assert item.attempts == 0
        assert item.error_message is None
        assert item.created_at is not None
        assert item.completed_at is None

    def test_creation_with_all_fields(self):
        """Test creating a SubmissionItem with all fields populated."""
        item = SubmissionItem(
            id="full-item",
            pr_id=200,
            file_path="/src/service.ts",
            outcome="request-changes",
            summary="Issues found",
            suggestions=[{"line": 42, "severity": "high", "content": "Fix this"}],
            status=SubmissionStatus.SUCCEEDED,
            attempts=1,
            error_message=None,
            created_at="2024-01-01T00:00:00+00:00",
            completed_at="2024-01-01T00:01:00+00:00",
        )
        assert item.pr_id == 200
        assert item.status == SubmissionStatus.SUCCEEDED
        assert item.attempts == 1
        assert len(item.suggestions) == 1
        assert item.completed_at == "2024-01-01T00:01:00+00:00"

    def test_id_is_valid_uuid_format(self):
        """Test that auto-generated IDs are valid UUID format."""
        item = SubmissionItem(
            id=str(uuid.uuid4()),
            pr_id=1,
            file_path="/file.ts",
            outcome="approve",
            summary="ok",
        )
        # Should not raise
        uuid.UUID(item.id)

    def test_created_at_auto_set(self):
        """Test that created_at is automatically set when using default."""
        item = SubmissionItem(
            id="test",
            pr_id=1,
            file_path="/file.ts",
            outcome="approve",
            summary="ok",
        )
        assert item.created_at is not None
        assert len(item.created_at) > 0

    def test_to_dict(self):
        """Test converting submission item to dictionary."""
        item = SubmissionItem(
            id="dict-test",
            pr_id=42,
            file_path="/src/utils.ts",
            outcome="request-changes-with-suggestion",
            summary="Naming issue",
            suggestions=[{"line": 15, "content": "Rename variable"}],
            status=SubmissionStatus.FAILED,
            attempts=2,
            error_message="API error",
            created_at="2024-06-01T12:00:00+00:00",
            completed_at="2024-06-01T12:01:00+00:00",
        )
        d = item.to_dict()

        assert d["id"] == "dict-test"
        assert d["pr_id"] == 42
        assert d["file_path"] == "/src/utils.ts"
        assert d["outcome"] == "request-changes-with-suggestion"
        assert d["summary"] == "Naming issue"
        assert d["suggestions"] == [{"line": 15, "content": "Rename variable"}]
        assert d["status"] == "failed"
        assert d["attempts"] == 2
        assert d["error_message"] == "API error"
        assert d["created_at"] == "2024-06-01T12:00:00+00:00"
        assert d["completed_at"] == "2024-06-01T12:01:00+00:00"

    def test_from_dict(self):
        """Test creating a SubmissionItem from a dictionary."""
        data = {
            "id": "from-dict-id",
            "pr_id": 99,
            "file_path": "/component.ts",
            "outcome": "approve",
            "summary": "Clean code",
            "status": "succeeded",
            "attempts": 1,
            "created_at": "2024-01-01T00:00:00+00:00",
            "completed_at": "2024-01-01T00:01:00+00:00",
        }
        item = SubmissionItem.from_dict(data)

        assert item.id == "from-dict-id"
        assert item.pr_id == 99
        assert item.status == SubmissionStatus.SUCCEEDED
        assert item.attempts == 1

    def test_from_dict_with_invalid_status_defaults_to_queued(self):
        """Test from_dict falls back to QUEUED for invalid status strings."""
        data = {
            "id": "bad-status",
            "pr_id": 1,
            "file_path": "/file.ts",
            "outcome": "approve",
            "summary": "ok",
            "status": "invalid-status",
        }
        item = SubmissionItem.from_dict(data)
        assert item.status == SubmissionStatus.QUEUED

    def test_from_dict_with_enum_status(self):
        """Test from_dict accepts a SubmissionStatus enum value directly."""
        data = {
            "id": "enum-status",
            "pr_id": 1,
            "file_path": "/file.ts",
            "outcome": "approve",
            "summary": "ok",
            "status": SubmissionStatus.PROCESSING,
        }
        item = SubmissionItem.from_dict(data)
        assert item.status == SubmissionStatus.PROCESSING

    def test_from_dict_with_non_string_status_passthrough(self):
        """Test from_dict passes through non-string status values as-is."""
        data = {
            "id": "passthrough",
            "pr_id": 1,
            "file_path": "/file.ts",
            "outcome": "approve",
            "summary": "ok",
            "status": 42,
        }
        item = SubmissionItem.from_dict(data)
        assert item.status == 42

    def test_roundtrip(self):
        """Test SubmissionItem survives dict roundtrip."""
        original = SubmissionItem(
            id="roundtrip-test",
            pr_id=77,
            file_path="/src/main.ts",
            outcome="request-changes",
            summary="Needs work",
            suggestions=[{"line": 10, "severity": "medium", "content": "Refactor"}],
            status=SubmissionStatus.FAILED,
            attempts=3,
            error_message="Timeout",
            created_at="2024-06-15T10:30:00+00:00",
            completed_at="2024-06-15T10:31:00+00:00",
        )
        restored = SubmissionItem.from_dict(original.to_dict())

        assert restored.id == original.id
        assert restored.pr_id == original.pr_id
        assert restored.file_path == original.file_path
        assert restored.outcome == original.outcome
        assert restored.summary == original.summary
        assert restored.suggestions == original.suggestions
        assert restored.status == original.status
        assert restored.attempts == original.attempts
        assert restored.error_message == original.error_message
        assert restored.created_at == original.created_at
        assert restored.completed_at == original.completed_at
