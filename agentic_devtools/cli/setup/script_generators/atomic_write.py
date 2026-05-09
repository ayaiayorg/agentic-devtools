"""Atomic file-write helper.

Writes content to a temporary file in the same directory as the target,
then renames it into place.  This ensures readers never see a partially
written file.
"""

import os
import tempfile
from pathlib import Path


def atomic_write(path: Path, content: str) -> None:
    """Write *content* to *path* atomically.

    Creates a temporary file in the same directory, writes the content,
    flushes to disk, and renames it over the target.  On Windows
    ``os.replace`` is used which is atomic on NTFS.

    Args:
        path: Destination file path.
        content: Text content to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, str(path))
    except BaseException:
        # Clean up the temporary file on any error.
        try:
            os.unlink(tmp_path)
        except OSError:  # pragma: no cover
            pass
        raise
