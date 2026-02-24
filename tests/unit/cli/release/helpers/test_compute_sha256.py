"""Tests for agentic_devtools.cli.release.helpers.compute_sha256."""

import hashlib

from agentic_devtools.cli.release.helpers import compute_sha256


def test_computes_correct_sha256(tmp_path):
    """Test compute_sha256 returns the correct SHA-256 hex digest."""
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"hello world")

    expected = hashlib.sha256(b"hello world").hexdigest()
    assert compute_sha256(test_file) == expected
