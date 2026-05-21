"""Engine resolution for the pull request review workflow.

Determines which review engine to use based on priority:
1. CLI flag (``--engine`` or ``--use-langchain``)
2. State key (``review.engine``)
3. Environment variable (``AGDT_REVIEW_ENGINE``)
4. Default: ``"default"``

Only ``"default"`` and ``"langchain"`` are supported engine values.
"""

import os

# Valid engine identifiers
VALID_ENGINES = frozenset({"default", "langchain"})
DEFAULT_ENGINE = "default"

# Environment variable name
ENGINE_ENV_VAR = "AGDT_REVIEW_ENGINE"


def resolve_review_engine(
    cli_flag: str | None = None,
    state_key: str | None = None,
    env_var: str | None = None,
) -> str:
    """Resolve which review engine to use.

    Priority (highest to lowest):
        1. ``cli_flag`` — explicit CLI argument (``--engine``)
        2. ``state_key`` — value from ``review.engine`` in agdt state
        3. ``env_var`` — value from ``AGDT_REVIEW_ENGINE`` environment variable
        4. Default: ``"default"``

    Args:
        cli_flag: Value from ``--engine`` CLI argument, or ``None``.
        state_key: Value from ``review.engine`` state key, or ``None``.
        env_var: Override for the environment variable value (used for testing).
            When ``None``, reads from ``os.environ``.

    Returns:
        The resolved engine string (``"default"`` or ``"langchain"``).

    Raises:
        SystemExit: If the resolved engine value is not recognized.
    """
    import sys

    cli_value = cli_flag.strip().lower() if isinstance(cli_flag, str) else ""
    state_value = state_key.strip().lower() if isinstance(state_key, str) else ""

    # Priority 1: CLI flag
    if cli_value:
        resolved = cli_value
    # Priority 2: State key
    elif state_value:
        resolved = state_value
    # Priority 3: Environment variable
    else:
        env_value = env_var if env_var is not None else os.environ.get(ENGINE_ENV_VAR, "")
        if env_value.strip():
            resolved = env_value.strip().lower()
        else:
            resolved = DEFAULT_ENGINE

    if resolved not in VALID_ENGINES:
        print(
            f"ERROR: Unknown review engine '{resolved}'. Valid options: {', '.join(sorted(VALID_ENGINES))}",
            file=sys.stderr,
        )
        sys.exit(1)

    return resolved
