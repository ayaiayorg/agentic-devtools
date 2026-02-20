"""Compatibility shim for the legacy agdt_ai_helpers package name."""

import importlib.abc
import importlib.util
import sys as _sys
from importlib import import_module

_new_pkg = import_module("agentic_devtools")
_sys.modules[__name__] = _new_pkg


class _AliasFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Redirect agdt_ai_helpers.* imports to agentic_devtools.* modules."""

    def find_spec(self, fullname, path, target=None):
        if not fullname.startswith("agdt_ai_helpers."):
            return None
        target_name = "agentic_devtools" + fullname[len("agdt_ai_helpers") :]
        target_spec = importlib.util.find_spec(target_name)
        if target_spec is None:
            return None
        return importlib.util.spec_from_loader(fullname, self)

    def create_module(self, spec):  # pragma: no cover - default module creation
        return None

    def exec_module(self, module):
        target_name = "agentic_devtools" + module.__name__[len("agdt_ai_helpers") :]
        target_module = import_module(target_name)
        _sys.modules[module.__name__] = target_module


if not any(isinstance(finder, _AliasFinder) for finder in _sys.meta_path):
    _sys.meta_path.insert(0, _AliasFinder())
