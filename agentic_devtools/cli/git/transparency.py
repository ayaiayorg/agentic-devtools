"""
Transparency logging helpers for git commit operations.

These functions produce canonical log output so that AI agents and auditors
can see exactly what commit message was used and what title changes occurred.
"""


def print_resolved_commit_message(message: str) -> None:
    """Print the full resolved commit message in canonical format.

    Output format::

        --- Resolved Commit Message ---
        <message>
        --- End Commit Message ---

    Args:
        message: The fully resolved commit message to display.
    """
    print("--- Resolved Commit Message ---")
    print(message, end="" if message.endswith("\n") else "\n")
    print("--- End Commit Message ---")


def print_commit_title_change(old_title: str, new_title: str) -> None:
    """Print before/after commit title diff in canonical format.

    Output format::

        --- Commit Title Change ---
        Before: <old_title>
        After:  <new_title>
        --- End Title Change ---

    Args:
        old_title: The previous commit title.
        new_title: The new commit title.
    """
    print("--- Commit Title Change ---")
    print(f"Before: {old_title}")
    print(f"After:  {new_title}")
    print("--- End Title Change ---")
