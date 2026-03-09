"""``agdt-review`` parent command for the configurable multi-model review pipeline.

Subcommands:
    dispatch        Orchestrate the full multi-model review sequence.
    consolidate     Run consolidation as the boss model.
    config-get      Read and display the target repo's review config.
    config-validate Validate config file syntax and model references.
    status          Show multi-model review progress for a PR.
"""

from .commands import build_parser, main
from .config_commands import run_config_get, run_config_validate
from .consolidate import run_consolidate
from .dispatch import run_dispatch
from .status import run_status

__all__ = [
    "build_parser",
    "main",
    "run_config_get",
    "run_config_validate",
    "run_consolidate",
    "run_dispatch",
    "run_status",
]
