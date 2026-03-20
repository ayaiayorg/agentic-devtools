"""Tests for get_checkpointer factory function."""

from langgraph.checkpoint.sqlite import SqliteSaver

from agentic_devtools.orchestration.checkpointing import get_checkpointer


class TestGetCheckpointer:
    """Tests for get_checkpointer()."""

    def test_returns_sqlite_saver_instance(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        saver = get_checkpointer(db_path)
        try:
            assert isinstance(saver, SqliteSaver)
        finally:
            saver.conn.close()

    def test_creates_sqlite_file(self, tmp_path):
        db_path = tmp_path / "test.db"
        saver = get_checkpointer(str(db_path))
        try:
            assert db_path.exists()
        finally:
            saver.conn.close()

    def test_creates_parent_directories(self, tmp_path):
        db_path = tmp_path / "nested" / "dir" / "test.db"
        saver = get_checkpointer(str(db_path))
        try:
            assert db_path.parent.exists()
            assert db_path.exists()
        finally:
            saver.conn.close()

    def test_default_path_uses_agdt_directory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        saver = get_checkpointer()
        try:
            expected = tmp_path / ".agdt" / "orchestration.db"
            assert expected.exists()
        finally:
            saver.conn.close()

    def test_custom_path_overrides_default(self, tmp_path):
        custom = tmp_path / "custom" / "my.db"
        saver = get_checkpointer(str(custom))
        try:
            assert custom.exists()
            default = tmp_path / ".agdt" / "orchestration.db"
            assert not default.exists()
        finally:
            saver.conn.close()

    def test_schema_is_initialized(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        saver = get_checkpointer(db_path)
        try:
            cursor = saver.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            assert "checkpoints" in tables
        finally:
            saver.conn.close()

    def test_existing_directory_no_error(self, tmp_path):
        db_dir = tmp_path / "existing"
        db_dir.mkdir()
        db_path = str(db_dir / "test.db")
        saver = get_checkpointer(db_path)
        try:
            assert isinstance(saver, SqliteSaver)
        finally:
            saver.conn.close()
