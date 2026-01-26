"""
Async operation status tracking.
"""

import json
from pathlib import Path
from typing import Any, Dict

from agentic_devtools.state import get_state_dir


def write_async_status(operation_id: str, status: Dict[str, Any]) -> Path:
    """
    Write async operation status to a JSON file.

    Args:
        operation_id: Unique identifier for the operation
        status: Status dictionary

    Returns:
        Path to the status file
    """
    status_dir = get_state_dir() / "async"
    status_dir.mkdir(parents=True, exist_ok=True)
    status_file = status_dir / f"{operation_id}.json"
    status_file.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")
    return status_file
