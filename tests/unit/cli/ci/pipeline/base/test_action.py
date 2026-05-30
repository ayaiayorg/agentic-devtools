"""Tests for pipeline Action protocol stubs."""

from typing import Any, cast
from unittest.mock import MagicMock

from agentic_devtools.cli.ci.pipeline.base import Action
from agentic_devtools.cli.ci.pipeline.snapshot import DerivedState, PRStateSnapshot


def test_action_protocol_stub_bodies_return_ellipsis() -> None:
    snapshot = PRStateSnapshot()
    derived = DerivedState(snapshot)
    dummy = cast(Any, object())

    assert Action.__dict__["name"].fget(dummy) is None
    assert Action.evaluate(dummy, snapshot, derived) is None
    assert Action.execute(dummy, cast(Any, MagicMock()), snapshot, derived) is None
