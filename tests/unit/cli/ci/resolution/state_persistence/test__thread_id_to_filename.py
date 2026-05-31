"""Tests for _thread_id_to_filename."""

import base64

from agentic_devtools.cli.ci.resolution.state_persistence import _thread_id_to_filename


def test_thread_id_encoding_is_injective() -> None:
    a = _thread_id_to_filename("a/b")
    b = _thread_id_to_filename("a_b")
    assert a != b


def test_thread_id_encoding_roundtrip() -> None:
    original = "PRRT_kwDORBcJXc6F4EAZ"
    encoded = _thread_id_to_filename(original)
    decoded = base64.urlsafe_b64decode(encoded.encode()).decode()
    assert decoded == original
