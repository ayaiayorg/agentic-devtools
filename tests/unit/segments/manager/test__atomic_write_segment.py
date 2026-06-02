"""Tests for _atomic_write_segment."""

from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_devtools.segments.manager import _atomic_write_segment


def test_atomic_write_segment_cleans_up_temp_file_on_replace_error(tmp_path):
    """Temporary file is removed when os.replace fails."""
    target = tmp_path / "segments" / "x.json"
    with patch("agentic_devtools.segments.manager.os.replace", side_effect=OSError("replace failed")):
        with pytest.raises(OSError, match="replace failed"):
            _atomic_write_segment(target, "{}")

    leftovers = list((tmp_path / "segments").glob("*.tmp"))
    assert leftovers == []
    assert not Path(target).exists()
