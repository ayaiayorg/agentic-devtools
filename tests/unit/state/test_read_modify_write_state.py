"""Tests for read_modify_write_state context manager."""

import json
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from agentic_devtools import state as state_module
from agentic_devtools.state import read_modify_write_state


class TestReadModifyWriteState:
    """Tests for read_modify_write_state context manager."""

    def _setup_state(self, tmp_path, data=None):
        """Helper: write initial state.json and patch get_state_dir."""
        state_dir = tmp_path / "state_dir"
        state_dir.mkdir(parents=True)
        state_file = state_dir / "state.json"
        state_file.write_text(json.dumps(data or {}), encoding="utf-8")
        return state_dir

    def test_mutates_and_saves(self, tmp_path):
        """Mutation inside context is persisted to disk."""
        state_dir = self._setup_state(tmp_path, {"existing": "value"})
        with patch.object(state_module, "get_state_dir", return_value=state_dir):
            with read_modify_write_state() as state:
                state["new_key"] = 42

            data = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
            assert data["existing"] == "value"
            assert data["new_key"] == 42

    def test_skips_save_on_exception(self, tmp_path):
        """File remains unchanged when exception is raised inside context."""
        state_dir = self._setup_state(tmp_path, {"safe": True})
        with patch.object(state_module, "get_state_dir", return_value=state_dir):
            with pytest.raises(RuntimeError):
                with read_modify_write_state() as state:
                    state["bad"] = True
                    raise RuntimeError("boom")

            data = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
            assert data == {"safe": True}

    def test_yields_dict(self, tmp_path):
        """Context manager yields a dictionary."""
        state_dir = self._setup_state(tmp_path, {"k": "v"})
        with patch.object(state_module, "get_state_dir", return_value=state_dir):
            with read_modify_write_state() as state:
                assert isinstance(state, dict)
                assert state["k"] == "v"

    def test_empty_state_file(self, tmp_path):
        """Handles truly empty state file content."""
        state_dir = self._setup_state(tmp_path, {})
        (state_dir / "state.json").write_text("", encoding="utf-8")
        with patch.object(state_module, "get_state_dir", return_value=state_dir):
            with read_modify_write_state() as state:
                state["first"] = "entry"

            data = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
            assert data == {"first": "entry"}

    def test_lock_reacquirable_after_exception(self, tmp_path):
        """Lock is released after exception so it can be re-acquired."""
        state_dir = self._setup_state(tmp_path, {"val": 1})
        with patch.object(state_module, "get_state_dir", return_value=state_dir):
            with pytest.raises(RuntimeError):
                with read_modify_write_state():
                    raise RuntimeError("fail")

            # Should be able to re-acquire immediately
            with read_modify_write_state() as state:
                assert state["val"] == 1

    def test_marks_dirty_after_successful_save(self, tmp_path):
        """Successful writes mark workflow state as dirty for persistence."""
        state_dir = self._setup_state(tmp_path, {"existing": "value"})
        with (
            patch.object(state_module, "get_state_dir", return_value=state_dir),
            patch("agentic_devtools.cli.git.agdt_branch.mark_dirty") as mock_mark_dirty,
        ):
            with read_modify_write_state() as state:
                state["new_key"] = "new_value"

        mock_mark_dirty.assert_called_once_with()

    def test_does_not_mark_dirty_when_context_raises(self, tmp_path):
        """Failed writes do not mark workflow state as dirty."""
        state_dir = self._setup_state(tmp_path, {"safe": True})
        with (
            patch.object(state_module, "get_state_dir", return_value=state_dir),
            patch("agentic_devtools.cli.git.agdt_branch.mark_dirty") as mock_mark_dirty,
        ):
            with pytest.raises(RuntimeError):
                with read_modify_write_state() as state:
                    state["bad"] = True
                    raise RuntimeError("boom")

        mock_mark_dirty.assert_not_called()

    def test_corrupted_json_treated_as_empty(self, tmp_path):
        """Corrupted state file (invalid JSON) is treated as an empty dict."""
        state_dir = self._setup_state(tmp_path, {})
        (state_dir / "state.json").write_text("{not valid json", encoding="utf-8")
        with patch.object(state_module, "get_state_dir", return_value=state_dir):
            with read_modify_write_state() as state:
                assert state == {}
                state["recovered"] = True

        data = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
        assert data == {"recovered": True}

    def test_concurrent_writers_no_data_dropped(self, tmp_path):
        """Concurrent writers serialize correctly; every unique key is preserved."""
        import threading

        state_dir = self._setup_state(tmp_path, {})
        n_writers = 10
        errors: list[Exception] = []

        def write_key(key: str) -> None:
            try:
                with read_modify_write_state() as state:
                    state[key] = True
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        with patch.object(state_module, "get_state_dir", return_value=state_dir):
            threads = [threading.Thread(target=write_key, args=(f"key_{i}",)) for i in range(n_writers)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        assert not errors, f"Unexpected errors during concurrent writes: {errors}"
        data = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
        assert len(data) == n_writers
        for i in range(n_writers):
            assert data[f"key_{i}"] is True, f"key_{i} missing from final state"

    def test_write_collision_last_writer_wins_deterministically(self, tmp_path):
        """Serialized write collisions: last serialized writer wins, no data dropped."""
        import threading

        state_dir = self._setup_state(tmp_path, {})
        write_order: list[int] = []
        order_lock = threading.Lock()

        def write_value(i: int) -> None:
            with read_modify_write_state() as state:
                state["collision_key"] = i
                # Append inside the file lock so write_order reflects
                # the true serialization order of writers.
                with order_lock:
                    write_order.append(i)

        with patch.object(state_module, "get_state_dir", return_value=state_dir):
            threads = [threading.Thread(target=write_value, args=(i,)) for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        data = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
        assert "collision_key" in data, "collision_key must not be silently dropped"
        # The value written by the last serialized writer (last item in write_order)
        # must be exactly what is stored — no silent data corruption.
        assert data["collision_key"] == write_order[-1]

    def test_flushes_and_fsyncs_before_unlocking(self, tmp_path):
        """Writes are flushed and fsynced before the file lock context exits."""
        state_dir = self._setup_state(tmp_path, {"existing": "value"})
        operations: list[str] = []

        class FakeLockedFile:
            def __init__(self):
                self.content = json.dumps({"existing": "value"})

            def read(self):
                operations.append("read")
                return self.content

            def seek(self, offset):
                operations.append(f"seek:{offset}")

            def write(self, content):
                operations.append("write")
                self.content = content
                return len(content)

            def truncate(self):
                operations.append("truncate")

            def flush(self):
                operations.append("flush")

            def fileno(self):
                operations.append("fileno")
                return 123

        fake_file = FakeLockedFile()

        @contextmanager
        def fake_locked_state_file(path, timeout=5.0):
            operations.append("enter")
            yield fake_file
            operations.append("exit")

        with (
            patch.object(state_module, "get_state_dir", return_value=state_dir),
            patch.object(state_module, "locked_state_file", fake_locked_state_file),
            patch.object(state_module.os, "fsync", side_effect=lambda fd: operations.append(f"fsync:{fd}")),
            patch("agentic_devtools.cli.git.agdt_branch.mark_dirty"),
        ):
            with read_modify_write_state() as state:
                state["new_key"] = True

        assert operations == [
            "enter",
            "read",
            "seek:0",
            "write",
            "truncate",
            "flush",
            "fileno",
            "fsync:123",
            "exit",
        ]
