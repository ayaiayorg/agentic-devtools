"""
Cross-platform file locking utilities.

Provides file locking to prevent race conditions when multiple processes
access the state file concurrently. Uses fcntl on Unix and msvcrt on Windows.
"""

import contextlib
import sys
import time
from pathlib import Path
from typing import IO, Iterator, Optional


class FileLockError(Exception):
    """Raised when a file lock cannot be acquired."""

    pass


def _lock_file_unix(file_handle: IO, exclusive: bool = True, timeout: float = 5.0) -> None:
    """
    Lock a file on Unix systems using fcntl.

    Args:
        file_handle: Open file handle to lock
        exclusive: If True, acquire exclusive lock; otherwise shared lock
        timeout: Maximum time to wait for lock in seconds

    Raises:
        FileLockError: If lock cannot be acquired within timeout
    """
    import fcntl

    lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
    start_time = time.time()

    while True:
        try:
            fcntl.flock(file_handle.fileno(), lock_type | fcntl.LOCK_NB)
            return
        except OSError as e:
            if time.time() - start_time > timeout:
                raise FileLockError(f"Could not acquire lock within {timeout}s: {e}") from e
            time.sleep(0.01)  # 10ms retry interval


def _unlock_file_unix(file_handle: IO) -> None:
    """Unlock a file on Unix systems."""
    import fcntl

    fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)


def _lock_file_windows(file_handle: IO, exclusive: bool = True, timeout: float = 5.0) -> None:  # pragma: no cover
    """
    Lock a file on Windows systems using msvcrt.

    Args:
        file_handle: Open file handle to lock
        exclusive: If True, acquire exclusive lock; otherwise shared lock
        timeout: Maximum time to wait for lock in seconds

    Raises:
        FileLockError: If lock cannot be acquired within timeout
    """
    import msvcrt

    start_time = time.time()

    while True:
        try:
            # On Windows, we lock the first byte of the file
            # LK_NBLCK for exclusive, LK_NBRLCK for shared (read-only)
            lock_mode = msvcrt.LK_NBLCK if exclusive else msvcrt.LK_NBRLCK
            msvcrt.locking(file_handle.fileno(), lock_mode, 1)
            return
        except OSError as e:
            if time.time() - start_time > timeout:
                raise FileLockError(f"Could not acquire lock within {timeout}s: {e}") from e
            time.sleep(0.01)  # 10ms retry interval


def _unlock_file_windows(file_handle: IO) -> None:  # pragma: no cover
    """Unlock a file on Windows systems."""
    import msvcrt

    try:
        msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
    except OSError:
        # Ignore unlock errors - file may already be unlocked
        pass


def lock_file(file_handle: IO, exclusive: bool = True, timeout: float = 5.0) -> None:
    """
    Lock a file handle (cross-platform).

    Args:
        file_handle: Open file handle to lock
        exclusive: If True, acquire exclusive lock; otherwise shared lock
        timeout: Maximum time to wait for lock in seconds

    Raises:
        FileLockError: If lock cannot be acquired within timeout
    """
    if sys.platform == "win32":  # pragma: no cover
        _lock_file_windows(file_handle, exclusive, timeout)
    else:
        _lock_file_unix(file_handle, exclusive, timeout)


def unlock_file(file_handle: IO) -> None:
    """
    Unlock a file handle (cross-platform).

    Args:
        file_handle: Open file handle to unlock
    """
    if sys.platform == "win32":  # pragma: no cover
        _unlock_file_windows(file_handle)
    else:
        _unlock_file_unix(file_handle)


@contextlib.contextmanager
def locked_file(
    path: Path,
    mode: str = "r+",
    exclusive: bool = True,
    timeout: float = 5.0,
    encoding: Optional[str] = "utf-8",
) -> Iterator[IO]:
    """
    Context manager for accessing a file with locking.

    Usage:
        with locked_file(path, "r+") as f:
            data = f.read()
            f.seek(0)
            f.write(new_data)
            f.truncate()

    Args:
        path: Path to the file
        mode: File open mode (default "r+")
        exclusive: If True, acquire exclusive lock; otherwise shared lock
        timeout: Maximum time to wait for lock in seconds
        encoding: File encoding (None for binary mode)

    Yields:
        Locked file handle

    Raises:
        FileLockError: If lock cannot be acquired within timeout
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create file if it doesn't exist and mode requires it
    if not path.exists() and "r" in mode and "+" in mode:
        path.write_text("{}", encoding=encoding)

    file_handle = open(path, mode, encoding=encoding)
    try:
        lock_file(file_handle, exclusive=exclusive, timeout=timeout)
        try:
            yield file_handle
        finally:
            unlock_file(file_handle)
    finally:
        file_handle.close()


@contextlib.contextmanager
def locked_state_file(
    path: Path,
    timeout: float = 5.0,
) -> Iterator[IO]:
    """
    Context manager specifically for state file access with exclusive locking.

    Creates the file with empty JSON object if it doesn't exist.

    Args:
        path: Path to the state file
        timeout: Maximum time to wait for lock in seconds

    Yields:
        Locked file handle

    Raises:
        FileLockError: If lock cannot be acquired within timeout
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create file if it doesn't exist
    if not path.exists():
        path.write_text("{}", encoding="utf-8")

    with locked_file(path, mode="r+", exclusive=True, timeout=timeout, encoding="utf-8") as f:
        yield f
