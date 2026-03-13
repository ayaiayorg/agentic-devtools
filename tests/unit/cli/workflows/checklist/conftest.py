"""Conftest for checklist tests — ensures get_state_dir is patched on the state module.

The ``temp_state_dir`` fixture from ``tests/unit/conftest.py`` already
patches ``agentic_devtools.state.get_state_dir``, and ``checklist.py``
accesses it through the module attribute ``_state_module.get_state_dir``,
so no additional patch is needed here.  This file is kept as a sentinel
so that future additions can be placed here if required.
"""
