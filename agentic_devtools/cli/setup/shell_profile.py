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


def detect_shell_type() -> str:
    """Detect the current shell type.

    Returns:
        One of ``"bash"``, ``"zsh"``, ``"powershell"``, or ``"unknown"``.
    """
    if sys.platform == "win32":
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
        # Build the export line
        if shell_type in ("bash", "zsh"):
            new_line = f'export {var_name}="{var_value}"'
            pattern = re.compile(rf"^export\s+{re.escape(var_name)}=")
        else:  # powershell
            new_line = f'$env:{var_name} = "{var_value}"'
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
    PowerShell ``$env:PATH`` prepend to the profile.  Idempotent: skips if
    the path entry already appears in an existing PATH line.

    Args:
        profile_path: Path to the shell profile file.
        path_entry: Directory to prepend to PATH.
        shell_type: One of ``"bash"``, ``"zsh"``, or ``"powershell"``.
        overwrite: Replace existing PATH line if ``True``.

    Returns:
        ``True`` if the line was written (or replaced), ``False`` if skipped
        or on error.
    """
    try:
        if shell_type in ("bash", "zsh"):
            new_line = f'export PATH="{path_entry}:$PATH"'
        else:  # powershell
            new_line = f'$env:PATH = "{path_entry};$env:PATH"'

        # Read existing content
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        if profile_path.exists():
            content = profile_path.read_text(encoding="utf-8", errors="replace")
        else:
            content = ""

        # Check if the path entry is already referenced in a PATH line
        if path_entry in content and not overwrite:
            return False

        if path_entry in content and overwrite:
            # Replace the line containing the path entry
            new_lines = []
            for line in content.splitlines(keepends=True):
                if path_entry in line and ("PATH" in line):
                    new_lines.append(new_line + "\n")
                else:
                    new_lines.append(line)
            profile_path.write_text("".join(new_lines), encoding="utf-8")
            return True

        # Append
        lines = content.splitlines(keepends=True)
        if lines and not lines[-1].endswith("\n"):
            lines.append("\n")
        lines.append("# Added by agdt-setup\n")
        lines.append(new_line + "\n")
        profile_path.write_text("".join(lines), encoding="utf-8")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠ Could not persist PATH entry to {profile_path}: {exc}", file=sys.stderr)
        return False
