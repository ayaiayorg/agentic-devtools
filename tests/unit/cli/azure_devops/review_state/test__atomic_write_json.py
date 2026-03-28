"""Tests for _atomic_write_json helper."""

import json
from unittest.mock import patch

import pytest

from agentic_devtools.cli.azure_devops.review_state import _atomic_write_json


class TestAtomicWriteJson:
    """Tests for _atomic_write_json private helper."""

    def test_writes_content_to_target(self, tmp_path):
        """Target file contains the written content after an atomic write."""
        target = tmp_path / "data.json"
        _atomic_write_json(target, '{"key": "value"}')

        assert target.exists()
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data == {"key": "value"}

    def test_overwrites_existing_file(self, tmp_path):
        """Existing file is replaced with new content."""
        target = tmp_path / "data.json"
        target.write_text('{"old": true}', encoding="utf-8")

        _atomic_write_json(target, '{"new": true}')

        data = json.loads(target.read_text(encoding="utf-8"))
        assert data == {"new": True}

    def test_no_tmp_files_remain_on_success(self, tmp_path):
        """No leftover .tmp files after a successful write."""
        target = tmp_path / "data.json"
        _atomic_write_json(target, '{"ok": 1}')

        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []

    def test_cleans_up_temp_on_replace_error(self, tmp_path):
        """Temp file is removed when os.replace raises an error."""
        target = tmp_path / "data.json"
        target.write_text('{"original": true}', encoding="utf-8")

        with patch("agentic_devtools.cli.azure_devops.review_state.os.replace", side_effect=OSError("boom")):
            with pytest.raises(OSError, match="boom"):
                _atomic_write_json(target, '{"bad": true}')

        # Original file untouched
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data == {"original": True}

        # No leftover temp files
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []

    def test_original_file_untouched_on_write_error(self, tmp_path):
        """Original file remains unchanged when a write error occurs before os.replace."""
        target = tmp_path / "data.json"
        target.write_text('{"safe": true}', encoding="utf-8")

        with patch("tempfile.NamedTemporaryFile", side_effect=OSError("disk full")):
            with pytest.raises(OSError, match="disk full"):
                _atomic_write_json(target, '{"bad": true}')

        data = json.loads(target.read_text(encoding="utf-8"))
        assert data == {"safe": True}
