"""Constants for the script-generators package."""

# Marker line written near the top of the generated ``setup-dev-tools.py``.
# Used by legacy-detection logic to distinguish the new modular orchestrator
# from a pre-existing monolithic script.
ORCHESTRATOR_MARKER = "# AGDT-MANAGED-ORCHESTRATOR"

# File names for the generated scripts (relative to repo root / .agdt/).
REQUIRED_SETUP_FILENAME = "agentic-devtools-required-setup.py"
CONFIGURED_SETUP_FILENAME = "agentic-devtools-configured-setup.py"
COMPLETE_SETUP_FILENAME = "agentic-devtools-complete-setup.py"
ROOT_ENTRY_POINT_FILENAME = "setup-dev-tools.py"
REPO_SPECIFIC_FILENAME = "setup-repo-specific-dev-tools.py"

# Known tool registry — maps tool names used by ``agdt-setup`` to their
# install commands.  Only tools the user has selected are included
# in the generated configured-setup script.
#
# ``install_argv`` is a list of argument tokens.  For pip-based installs
# the generated script prepends ``[sys.executable, "-m"]`` so the package
# is installed into the same environment as the running interpreter.
TOOL_REGISTRY: dict[str, dict[str, str | list[str]]] = {
    "ruff": {
        "install_argv": ["pip", "install", "ruff"],
        "check_cmd": "ruff --version",
        "description": "Python linter and formatter",
    },
    "cspell": {
        "install_argv": ["npm", "install", "-g", "cspell"],
        "check_cmd": "cspell --version",
        "description": "Spell checker for code",
    },
    "markdownlint-cli2": {
        "install_argv": ["npm", "install", "-g", "markdownlint-cli2"],
        "check_cmd": "markdownlint-cli2 --help",
        "description": "Markdown linter",
    },
}
