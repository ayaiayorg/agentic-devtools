"""Compatibility shim for the legacy dfly_ai_helpers package name."""

from importlib import import_module
import sys as _sys

_new_pkg = import_module("agentic_devtools")
_sys.modules[__name__] = _new_pkg
