"""Shared VS Code ``tasks.json`` manipulation helpers.

This module provides utilities for reading and modifying ``.vscode/tasks.json``
files that are used by the Copilot auto-start workflow.  Keeping the logic
here — rather than duplicated across ``worktree_setup.py`` and
``copilot/auto_start.py`` — avoids drift between the two callers.
"""

from __future__ import annotations

import json
import os


def remove_auto_start_task(
    tasks_path: str,
    vscode_dir: str,
    task_label: str,
    *,
    delete_if_empty: bool = False,
) -> None:
    """Remove an auto-start task from ``tasks.json``.

    Reads ``tasks_path``, removes any task whose ``"label"`` field matches
    *task_label*, then writes the result back.

    Deletion / rewrite rules when no tasks remain after removal:

    * ``delete_if_empty=True`` and **no extra top-level keys** (i.e. only
      ``"version"`` and ``"tasks"`` are present): delete ``tasks_path`` and
      attempt to ``rmdir`` *vscode_dir*.
    * ``delete_if_empty=True`` but **extra keys are present** (e.g.
      ``"inputs"``, ``"options"``): rewrite the file with an empty tasks
      array, preserving those keys.
    * ``delete_if_empty=False``: always rewrite the file, even when the
      resulting tasks array is empty.

    All errors are silently caught so this function never prevents the caller
    from proceeding.

    Args:
        tasks_path: Absolute path to ``.vscode/tasks.json``.
        vscode_dir: Absolute path to the ``.vscode/`` directory (used for
            optional ``rmdir`` when deleting the file).
        task_label: The ``"label"`` value of the task to remove.
        delete_if_empty: When ``True``, attempt to delete ``tasks_path`` (and
            ``vscode_dir``) when no tasks remain and there are no extra
            top-level keys.  Defaults to ``False``.
    """
    if not os.path.isfile(tasks_path):
        return
    try:
        with open(tasks_path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return
        tasks_list = data.get("tasks")
        if not isinstance(tasks_list, list):
            return
        original_count = len(tasks_list)
        data["tasks"] = [t for t in tasks_list if not isinstance(t, dict) or t.get("label") != task_label]
        if len(data["tasks"]) == original_count:
            return  # Task was not present — nothing to clean up
        if data["tasks"]:
            # Other tasks remain — rewrite the file.
            with open(tasks_path, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(data, indent=2) + "\n")
        elif delete_if_empty:
            # No tasks remain.  Only delete the file when it contains no other
            # top-level keys besides "version" and "tasks" (i.e. the file was
            # likely created solely for auto-start).  If other keys exist (e.g.
            # "inputs", "options") the file belongs to the user — rewrite it
            # preserving those keys.
            extra_keys = set(data.keys()) - {"version", "tasks"}
            if extra_keys:
                data["tasks"] = []
                with open(tasks_path, "w", encoding="utf-8") as fh:
                    fh.write(json.dumps(data, indent=2) + "\n")
            else:
                os.remove(tasks_path)
                # Derive the expected .vscode directory from tasks_path and
                # only attempt to remove it when it matches the supplied
                # vscode_dir. This makes accidental misuse (passing an
                # unrelated directory) a no-op rather than deleting an
                # unexpected path.
                derived_vscode_dir = os.path.dirname(tasks_path)
                try:
                    if os.path.abspath(vscode_dir) == os.path.abspath(derived_vscode_dir):
                        os.rmdir(derived_vscode_dir)
                except OSError:
                    pass
        else:
            # No tasks remain but caller does not want file deletion — rewrite
            # with empty tasks array, preserving any extra top-level keys.
            with open(tasks_path, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(data, indent=2) + "\n")
    except Exception:
        pass  # Best-effort — silently ignore errors
