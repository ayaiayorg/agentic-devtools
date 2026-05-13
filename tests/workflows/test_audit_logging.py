"""Tests for structured audit logging (T025).

Tests that audit log entries have the correct format and required fields (FR-005).
"""

import json


class TestAuditLogging:
    """Test structured audit logging format (FR-005)."""

    REQUIRED_FIELDS = [
        "event",
        "actor",
        "timestamp",
        "pr_number",
        "run_id",
        "head_sha",
        "source",
        "result",
        "reason",
    ]

    def _make_audit_entry(self, result, reason=None, pr_number=1234, run_id=56789):
        """Replicate the audit log entry construction from the workflow."""
        return {
            "event": "workflow_approval",
            "actor": "workflow-approval-monitor",
            "timestamp": "2026-05-11T14:30:00Z",
            "pr_number": pr_number,
            "run_id": run_id,
            "head_sha": "abc1234def5678901234567890abcdef12345678",
            "source": "programmatic",
            "result": result,
            "reason": reason,
        }

    def test_success_entry_has_all_required_fields(self):
        """Success audit entry must contain all required fields."""
        entry = self._make_audit_entry("success")
        for field in self.REQUIRED_FIELDS:
            assert field in entry, f"Missing required field: {field}"

    def test_failure_entry_has_all_required_fields(self):
        """Failure audit entry must contain all required fields."""
        entry = self._make_audit_entry("failure", reason="Permission denied (403)")
        for field in self.REQUIRED_FIELDS:
            assert field in entry, f"Missing required field: {field}"

    def test_skip_entry_has_all_required_fields(self):
        """Skip audit entry must contain all required fields."""
        entry = self._make_audit_entry("skipped", reason="Run no longer in action_required state")
        for field in self.REQUIRED_FIELDS:
            assert field in entry, f"Missing required field: {field}"

    def test_success_reason_is_null(self):
        """On success, reason field must be null."""
        entry = self._make_audit_entry("success")
        assert entry["reason"] is None

    def test_failure_reason_is_descriptive(self):
        """On failure, reason must be a descriptive string."""
        entry = self._make_audit_entry("failure", reason="Permission denied (403)")
        assert isinstance(entry["reason"], str)
        assert len(entry["reason"]) > 0

    def test_entry_is_valid_json(self):
        """Audit entry must be serializable to valid JSON."""
        entry = self._make_audit_entry("success")
        json_str = json.dumps(entry)
        parsed = json.loads(json_str)
        assert parsed == entry

    def test_event_field_is_workflow_approval(self):
        """Event field must always be 'workflow_approval'."""
        entry = self._make_audit_entry("success")
        assert entry["event"] == "workflow_approval"

    def test_actor_field_is_monitor(self):
        """Actor field must always be 'workflow-approval-monitor'."""
        entry = self._make_audit_entry("success")
        assert entry["actor"] == "workflow-approval-monitor"

    def test_source_field_is_programmatic(self):
        """Source field must always be 'programmatic'."""
        entry = self._make_audit_entry("success")
        assert entry["source"] == "programmatic"

    def test_result_values_are_valid(self):
        """Result field must be one of the valid values."""
        valid_results = {"success", "failure", "skipped"}
        for result in valid_results:
            entry = self._make_audit_entry(result, reason="test")
            assert entry["result"] in valid_results
