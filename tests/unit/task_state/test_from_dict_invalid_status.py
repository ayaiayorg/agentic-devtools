"""Tests for BackgroundTask.from_dict() with invalid status values."""

from agentic_devtools.task_state import BackgroundTask, TaskStatus


def test_from_dict_invalid_status_string_defaults_to_pending():
    """An unrecognised status string should fall back to PENDING."""
    data = {
        "id": "inv-1",
        "command": "agdt-test-cmd",
        "status": "not_a_real_status",
        "startTime": "2024-01-01T00:00:00+00:00",
    }
    task = BackgroundTask.from_dict(data)
    assert task.status == TaskStatus.PENDING


def test_from_dict_non_string_status_used_directly():
    """A non-string status value (e.g. int) should be used as-is."""
    data = {
        "id": "inv-2",
        "command": "agdt-test-cmd",
        "status": 42,
        "startTime": "2024-01-01T00:00:00+00:00",
    }
    task = BackgroundTask.from_dict(data)
    assert task.status == 42
