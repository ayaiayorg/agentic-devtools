"""Tests for remove_auto_start_task."""

import json

import pytest

from agentic_devtools.cli.vscode_tasks import remove_auto_start_task


class TestRemoveAutoStartTask:
    """Tests for the remove_auto_start_task helper."""

    # ------------------------------------------------------------------
    # File doesn't exist
    # ------------------------------------------------------------------

    def test_noop_when_tasks_json_absent(self, tmp_path):
        """Does nothing when tasks.json doesn't exist (no error)."""
        vscode_dir = tmp_path / ".vscode"
        tasks_path = str(vscode_dir / "tasks.json")
        remove_auto_start_task(tasks_path, str(vscode_dir), "agdt-copilot-auto-start")
        # No exception raised, .vscode/ not created

    # ------------------------------------------------------------------
    # Tasks remain after removal
    # ------------------------------------------------------------------

    def test_rewrites_file_when_other_tasks_remain(self, tmp_path):
        """Rewrites tasks.json when other tasks remain after removing the target."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        data = {
            "version": "2.0.0",
            "tasks": [
                {"label": "agdt-copilot-auto-start", "type": "process", "command": "x"},
                {"label": "user-task", "type": "shell", "command": "echo hi"},
            ],
        }
        tasks_path.write_text(json.dumps(data), encoding="utf-8")

        remove_auto_start_task(str(tasks_path), str(vscode_dir), "agdt-copilot-auto-start")

        result = json.loads(tasks_path.read_text(encoding="utf-8"))
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["label"] == "user-task"
        assert vscode_dir.exists()

    # ------------------------------------------------------------------
    # No tasks remain, delete_if_empty=True (no extra keys)
    # ------------------------------------------------------------------

    def test_deletes_file_when_delete_if_empty_and_no_extra_keys(self, tmp_path):
        """Deletes tasks.json when delete_if_empty=True and no extra top-level keys."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        data = {"version": "2.0.0", "tasks": [{"label": "agdt-copilot-auto-start"}]}
        tasks_path.write_text(json.dumps(data), encoding="utf-8")

        remove_auto_start_task(str(tasks_path), str(vscode_dir), "agdt-copilot-auto-start", delete_if_empty=True)

        assert not tasks_path.exists()

    def test_removes_vscode_dir_when_empty_after_file_deletion(self, tmp_path):
        """Removes .vscode/ when empty after tasks.json deletion."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        data = {"version": "2.0.0", "tasks": [{"label": "agdt-copilot-auto-start"}]}
        tasks_path.write_text(json.dumps(data), encoding="utf-8")

        remove_auto_start_task(str(tasks_path), str(vscode_dir), "agdt-copilot-auto-start", delete_if_empty=True)

        assert not vscode_dir.exists()

    def test_keeps_vscode_dir_when_not_empty_after_file_deletion(self, tmp_path):
        """Keeps .vscode/ when other files remain after tasks.json deletion."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        (vscode_dir / "settings.json").write_text("{}", encoding="utf-8")
        data = {"version": "2.0.0", "tasks": [{"label": "agdt-copilot-auto-start"}]}
        tasks_path.write_text(json.dumps(data), encoding="utf-8")

        remove_auto_start_task(str(tasks_path), str(vscode_dir), "agdt-copilot-auto-start", delete_if_empty=True)

        assert not tasks_path.exists()
        assert vscode_dir.exists()

    # ------------------------------------------------------------------
    # No tasks remain, delete_if_empty=True (with extra keys)
    # ------------------------------------------------------------------

    def test_rewrites_with_empty_tasks_when_delete_if_empty_and_extra_keys(self, tmp_path):
        """Rewrites with empty tasks (not deletes) when delete_if_empty=True but extra keys are present."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        data = {
            "version": "2.0.0",
            "tasks": [{"label": "agdt-copilot-auto-start"}],
            "inputs": [{"id": "myInput", "type": "promptString"}],
        }
        tasks_path.write_text(json.dumps(data), encoding="utf-8")

        remove_auto_start_task(str(tasks_path), str(vscode_dir), "agdt-copilot-auto-start", delete_if_empty=True)

        assert tasks_path.exists()
        result = json.loads(tasks_path.read_text(encoding="utf-8"))
        assert result["tasks"] == []
        assert result["inputs"] == [{"id": "myInput", "type": "promptString"}]

    # ------------------------------------------------------------------
    # No tasks remain, delete_if_empty=False (default)
    # ------------------------------------------------------------------

    def test_rewrites_with_empty_tasks_when_not_delete_if_empty_no_extra_keys(self, tmp_path):
        """Rewrites with empty tasks array when delete_if_empty=False and no extra keys."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        data = {"version": "2.0.0", "tasks": [{"label": "agdt-copilot-auto-start"}]}
        tasks_path.write_text(json.dumps(data), encoding="utf-8")

        remove_auto_start_task(str(tasks_path), str(vscode_dir), "agdt-copilot-auto-start", delete_if_empty=False)

        result = json.loads(tasks_path.read_text(encoding="utf-8"))
        assert result["tasks"] == []
        assert tasks_path.exists()

    def test_rewrites_preserving_extra_keys_when_not_delete_if_empty(self, tmp_path):
        """Rewrites preserving extra top-level keys when delete_if_empty=False."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        data = {
            "version": "2.0.0",
            "tasks": [{"label": "agdt-copilot-auto-start"}],
            "inputs": [{"id": "myInput", "type": "promptString"}],
        }
        tasks_path.write_text(json.dumps(data), encoding="utf-8")

        remove_auto_start_task(str(tasks_path), str(vscode_dir), "agdt-copilot-auto-start", delete_if_empty=False)

        result = json.loads(tasks_path.read_text(encoding="utf-8"))
        assert result["tasks"] == []
        assert result["inputs"] == [{"id": "myInput", "type": "promptString"}]

    # ------------------------------------------------------------------
    # Task not present — noop
    # ------------------------------------------------------------------

    def test_noop_when_task_not_present(self, tmp_path):
        """Does nothing when the target task is not in tasks.json."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        data = {"version": "2.0.0", "tasks": [{"label": "user-task", "type": "shell", "command": "echo hi"}]}
        original = json.dumps(data)
        tasks_path.write_text(original, encoding="utf-8")

        remove_auto_start_task(str(tasks_path), str(vscode_dir), "agdt-copilot-auto-start")

        assert tasks_path.read_text(encoding="utf-8") == original

    # ------------------------------------------------------------------
    # Non-dict items in tasks array preserved
    # ------------------------------------------------------------------

    def test_preserves_non_dict_items_in_tasks(self, tmp_path):
        """Non-dict items in the tasks array are preserved during removal."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        data = {
            "version": "2.0.0",
            "tasks": [
                "a string task",
                42,
                {"label": "agdt-copilot-auto-start"},
            ],
        }
        tasks_path.write_text(json.dumps(data), encoding="utf-8")

        remove_auto_start_task(str(tasks_path), str(vscode_dir), "agdt-copilot-auto-start")

        result = json.loads(tasks_path.read_text(encoding="utf-8"))
        assert "a string task" in result["tasks"]
        assert 42 in result["tasks"]
        assert not any(isinstance(t, dict) and t.get("label") == "agdt-copilot-auto-start" for t in result["tasks"])

    # ------------------------------------------------------------------
    # Error handling — silently caught
    # ------------------------------------------------------------------

    def test_silently_ignores_malformed_json(self, tmp_path):
        """Silently ignores malformed JSON in tasks.json."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        tasks_path.write_text("{invalid json", encoding="utf-8")

        remove_auto_start_task(str(tasks_path), str(vscode_dir), "agdt-copilot-auto-start")

        assert tasks_path.read_text(encoding="utf-8") == "{invalid json"

    def test_silently_ignores_non_dict_top_level(self, tmp_path):
        """Silently ignores tasks.json with a non-dict top-level value."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        tasks_path.write_text("[1, 2, 3]", encoding="utf-8")

        remove_auto_start_task(str(tasks_path), str(vscode_dir), "agdt-copilot-auto-start")

        assert tasks_path.read_text(encoding="utf-8") == "[1, 2, 3]"

    def test_silently_ignores_non_list_tasks_value(self, tmp_path):
        """Silently ignores tasks.json when tasks value is not a list."""
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        tasks_path = vscode_dir / "tasks.json"
        tasks_path.write_text('{"version": "2.0.0", "tasks": null}', encoding="utf-8")

        remove_auto_start_task(str(tasks_path), str(vscode_dir), "agdt-copilot-auto-start")

        assert "null" in tasks_path.read_text(encoding="utf-8")


@pytest.mark.parametrize("delete_if_empty", [True, False])
def test_delete_if_empty_controls_file_removal(tmp_path, delete_if_empty):
    """Verify delete_if_empty controls whether an empty tasks.json is deleted or rewritten."""
    vscode_dir = tmp_path / ".vscode"
    vscode_dir.mkdir()
    tasks_path = vscode_dir / "tasks.json"
    data = {"version": "2.0.0", "tasks": [{"label": "agdt-copilot-auto-start"}]}
    tasks_path.write_text(json.dumps(data), encoding="utf-8")

    remove_auto_start_task(
        str(tasks_path),
        str(vscode_dir),
        "agdt-copilot-auto-start",
        delete_if_empty=delete_if_empty,
    )

    if delete_if_empty:
        assert not tasks_path.exists()
    else:
        assert tasks_path.exists()
        result = json.loads(tasks_path.read_text(encoding="utf-8"))
        assert result["tasks"] == []


def test_delete_if_empty_default_is_false_when_argument_omitted(tmp_path):
    """Verify delete_if_empty defaults to False (file is rewritten, not deleted)."""
    vscode_dir = tmp_path / ".vscode"
    vscode_dir.mkdir()
    tasks_path = vscode_dir / "tasks.json"
    data = {"version": "2.0.0", "tasks": [{"label": "agdt-copilot-auto-start"}]}
    tasks_path.write_text(json.dumps(data), encoding="utf-8")

    # Call without specifying delete_if_empty to exercise the default value.
    remove_auto_start_task(str(tasks_path), str(vscode_dir), "agdt-copilot-auto-start")

    assert tasks_path.exists()
    result = json.loads(tasks_path.read_text(encoding="utf-8"))
    assert result["tasks"] == []
