"""Tests for stdlib-only constraint in generated scripts."""

from agentic_devtools.cli.setup.script_generators.complete_setup import generate_complete_setup_script
from agentic_devtools.cli.setup.script_generators.configured_setup import generate_configured_setup_script
from agentic_devtools.cli.setup.script_generators.repo_specific import generate_repo_specific_stub
from agentic_devtools.cli.setup.script_generators.required_setup import generate_required_setup_script
from agentic_devtools.cli.setup.script_generators.root_entry_point import generate_root_entry_point


class TestStdlibOnly:
    """All generated scripts must use only stdlib imports."""

    _FORBIDDEN_IMPORTS = [
        "import agentic_devtools",
        "from agentic_devtools",
        "import requests",
        "from requests",
    ]

    def _check_no_forbidden(self, script: str) -> None:
        for forbidden in self._FORBIDDEN_IMPORTS:
            assert forbidden not in script, f"Found forbidden import: {forbidden}"

    def test_required_setup(self):
        self._check_no_forbidden(generate_required_setup_script())

    def test_configured_setup_empty(self):
        self._check_no_forbidden(generate_configured_setup_script())

    def test_configured_setup_with_tools(self):
        self._check_no_forbidden(generate_configured_setup_script(["ruff", "cspell"]))

    def test_complete_setup(self):
        self._check_no_forbidden(generate_complete_setup_script())

    def test_root_entry_point(self):
        self._check_no_forbidden(generate_root_entry_point())

    def test_repo_specific_stub(self):
        self._check_no_forbidden(generate_repo_specific_stub())
