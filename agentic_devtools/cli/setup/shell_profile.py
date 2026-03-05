"""Shell profile detection and environment variable persistence utilities.

Provides functions to detect the user's shell type and profile file, and to
persist environment variables (``export`` lines) to shell profile files in an
idempotent, error-tolerant way.

Supported shells: bash (``~/.bashrc``), zsh (``~/.zshrc``), PowerShell
(``$PROFILE``).  Unknown shells cause persistence to be skipped gracefully.
"""

import os
import re
import sys
from pathlib import Path
from typing import Optional


def _escape_for_double_quotes_posix(value: str) -> str:
    """Escape a value for safe inclusion inside POSIX double-quotes.

    Escapes ``\\``, ``"``, ``$``, and backtick — the characters that are
    special inside double-quoted strings in bash/zsh.
    """
    # Backslash must be escaped first to avoid double-escaping later replacements.
    value = value.replace("\\", "\\\\")
    value = value.replace('"', '\\"')
    value = value.replace("$", "\\$")
    value = value.replace("`", "\\`")
    return value


def _escape_for_double_quotes_powershell(value: str) -> str:
    """Escape a value for safe inclusion inside PowerShell double-quotes.

    In PowerShell double-quoted strings, backtick is the escape char and
    ``"`` must be doubled or backtick-escaped.  ``$`` triggers variable
    expansion and must be backtick-escaped.
    """
    value = value.replace("`", "``")
    value = value.replace('"', '`"')
    value = value.replace("$", "`$")
    return value


def detect_shell_type() -> str:
    """Detect the current shell type.

    Returns:
        One of ``"bash"``, ``"zsh"``, ``"powershell"``, or ``"unknown"``.
    """
    # On Windows, check for Git Bash / MSYS2 environment before defaulting
    # to PowerShell.  Git Bash sets $SHELL and/or MSYSTEM.
    if sys.platform == "win32":
        shell = os.environ.get("SHELL", "")
        if shell.endswith("bash"):
            return "bash"
        if shell.endswith("zsh"):
            return "zsh"
        if os.environ.get("MSYSTEM"):
            return "bash"
        return "powershell"

    shell = os.environ.get("SHELL", "")
    if shell.endswith("bash"):
        return "bash"
    if shell.endswith("zsh"):
        return "zsh"
    return "unknown"


def detect_shell_profile() -> Optional[Path]:
    """Detect the path to the user's shell profile file.

    Returns:
        Path to the profile file, or ``None`` if the shell cannot be
        determined or the profile directory does not exist (Windows only).
    """
    shell_type = detect_shell_type()

    if shell_type == "bash":
        return Path.home() / ".bashrc"
    if shell_type == "zsh":
        return Path.home() / ".zshrc"
    if shell_type == "powershell":
        user_profile = os.environ.get("USERPROFILE", "")
        if not user_profile:
            return None
        # Try PowerShell Core first, then Windows PowerShell
        ps_core = Path(user_profile) / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
        if ps_core.parent.is_dir():
            return ps_core
        ps_legacy = Path(user_profile) / "Documents" / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1"
        if ps_legacy.parent.is_dir():
            return ps_legacy
        return None
    return None


def persist_env_var(
    profile_path: Path,
    var_name: str,
    var_value: str,
    shell_type: str,
    *,
    overwrite: bool = False,
) -> bool:
    """Persist an environment variable to a shell profile file.

    Appends an ``export VAR="value"`` (bash/zsh) or ``$env:VAR = "value"``
    (PowerShell) line to the profile.  Idempotent: skips if the variable is
    already set in the file (unless *overwrite* is ``True``).

    Args:
        profile_path: Path to the shell profile file.
        var_name: Environment variable name.
        var_value: Environment variable value.
        shell_type: One of ``"bash"``, ``"zsh"``, or ``"powershell"``.
        overwrite: Replace existing line if ``True``.

    Returns:
        ``True`` if the line was written (or replaced), ``False`` if skipped
        or on error.
    """
    try:
        # Build the export line with shell-appropriate escaping
        if shell_type in ("bash", "zsh"):
            safe_value = _escape_for_double_quotes_posix(var_value)
            new_line = f'export {var_name}="{safe_value}"'
            # Match common assignment patterns:
            #   export VAR=...  |  export VAR  |  VAR=...
            pattern = re.compile(rf"^(?:export\s+{re.escape(var_name)}(?:\s*=.*)?|{re.escape(var_name)}\s*=)")
        else:  # powershell
            safe_value = _escape_for_double_quotes_powershell(var_value)
            new_line = f'$env:{var_name} = "{safe_value}"'
            pattern = re.compile(rf"^\$env:{re.escape(var_name)}\s*=")

        # Read existing content
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        if profile_path.exists():
            lines = profile_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        else:
            lines = []

        # Check for existing line
        existing_idx = None
        for idx, line in enumerate(lines):
            if pattern.match(line.strip()):
                existing_idx = idx
                break

        if existing_idx is not None and not overwrite:
            return False

        if existing_idx is not None and overwrite:
            # Replace in-place
            lines[existing_idx] = new_line + "\n"
        else:
            # Append with a comment marker
            if lines and not lines[-1].endswith("\n"):
                lines.append("\n")
            lines.append("# Added by agdt-setup\n")
            lines.append(new_line + "\n")

        profile_path.write_text("".join(lines), encoding="utf-8")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠ Could not persist {var_name} to {profile_path}: {exc}", file=sys.stderr)
        return False


def persist_path_entry(
    profile_path: Path,
    path_entry: str,
    shell_type: str,
    *,
    overwrite: bool = False,
) -> bool:
    """Persist a PATH entry to a shell profile file.

    Appends an ``export PATH="<entry>:$PATH"`` (bash/zsh) or the equivalent
    PowerShell ``$env:PATH`` prepend to the profile.  Idempotent for a given
    ``path_entry``: if a PATH-assignment line that already contains
    ``path_entry`` exists, it is left unchanged unless ``overwrite`` is
    ``True``.

    Args:
        profile_path: Path to the shell profile file.
        path_entry: Directory to prepend to PATH.
        shell_type: One of ``"bash"``, ``"zsh"``, or ``"powershell"``.
        overwrite: If ``True`` and a PATH-assignment line already containing
            ``path_entry`` exists, replace that line with the new
            PATH-prepend line instead of leaving it unchanged.  When no such
            line exists, a new line is appended regardless of this flag.

    Returns:
        ``True`` if the line was written (or replaced), ``False`` if skipped
        or on error.
    """
    try:
        # Build new PATH-prepend line with shell-appropriate escaping
        if shell_type in ("bash", "zsh"):
            safe_entry = _escape_for_double_quotes_posix(path_entry)
            new_line = f'export PATH="{safe_entry}:$PATH"'
            # Match lines like: export PATH=... or PATH=...
            path_line_re = re.compile(r"^\s*(?:export\s+)?PATH\s*=")
        else:  # powershell
            safe_entry = _escape_for_double_quotes_powershell(path_entry)
            new_line = f'$env:PATH = "{safe_entry};$env:PATH"'
            path_line_re = re.compile(r"^\s*\$env:PATH\s*=", re.IGNORECASE)

        # Read existing content
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        if profile_path.exists():
            content = profile_path.read_text(encoding="utf-8", errors="replace")
        else:
            content = ""

        # Check only actual PATH assignment lines for the entry
        lines = content.splitlines(keepends=True)
        found_in_path_line = False
        found_line_idx = None
        for idx, line in enumerate(lines):
            if path_line_re.match(line) and path_entry in line:
                found_in_path_line = True
                found_line_idx = idx
                break

        if found_in_path_line and not overwrite:
            return False

        if found_in_path_line and overwrite:
            # Replace the matching PATH line in-place
            lines[found_line_idx] = new_line + "\n"  # type: ignore[index]
            profile_path.write_text("".join(lines), encoding="utf-8")
            return True

        # Append
        if lines and not lines[-1].endswith("\n"):
            lines.append("\n")
        lines.append("# Added by agdt-setup\n")
        lines.append(new_line + "\n")
        profile_path.write_text("".join(lines), encoding="utf-8")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠ Could not persist PATH entry to {profile_path}: {exc}", file=sys.stderr)
        return False
