"""Read the stored tool grouping back.

``data/tool_groups.json`` is written by regroup.py, or by
:func:`ensure_groups` when the installer starts and the file no longer matches
the tools on disk. It is a build artifact: it is regenerated on demand and
tracked in git, so every host reads the same groups. Entries in "overrides"
beat the computed assignment.
"""

import json
import os
from typing import Dict

GROUPS_FILE = os.path.join("data", "tool_groups.json")
UNGROUPED = "Ungrouped"


def groups_path(root: str) -> str:
    """Absolute path of the groups file for a repo root."""
    return os.path.join(root, GROUPS_FILE)


def read_groups_file(root: str) -> dict:
    """Return the raw JSON, or {} when it is missing or unreadable."""
    path = groups_path(root)
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def load_groups(root: str) -> Dict[str, str]:
    """Map each tool directory name to its group label.

    Tools absent from the file are not in the result; callers treat a missing
    tool as UNGROUPED.
    """
    data = read_groups_file(root)
    mapping: Dict[str, str] = {}

    labels = data.get("labels")
    if isinstance(labels, dict):
        for label, members in labels.items():
            if not isinstance(members, list):
                continue
            for tool in members:
                if isinstance(tool, str):
                    mapping[tool] = str(label)

    overrides = data.get("overrides")
    if isinstance(overrides, dict):
        for tool, label in overrides.items():
            if isinstance(tool, str) and isinstance(label, str):
                mapping[tool] = label

    return mapping


def group_of(root: str, tool: str) -> str:
    """Group label for one tool, UNGROUPED when it has none."""
    return load_groups(root).get(tool, UNGROUPED)


def is_stale(root: str, k: int) -> bool:
    """True when the stored grouping no longer matches the corpus on disk.

    Stale means: no labels yet, a different k, or a corpus fingerprint that has
    moved — a tool added or removed, or a CLAUDE.md/README.md edited.
    """
    from .corpus import corpus_fingerprint

    data = read_groups_file(root)
    if not data.get("labels"):
        return True
    if data.get("k") != k:
        return True
    return data.get("fingerprint") != corpus_fingerprint(root)


# The installer calls ensure_groups on its way to opening a window, so the LLM
# tier gets a wall-clock cap. Gemini answers well inside it; a local model on a
# busy host may not, and then the capability tier takes over — instantly, and
# without disturbing bands that are already there.
STARTUP_BUDGET_SECONDS = 60.0


def ensure_groups(
    root: str, k: int = None, budget: float = STARTUP_BUDGET_SECONDS
) -> Dict[str, str]:
    """Groups for the installer, recomputed first if the corpus has changed.

    Falls back to whatever is stored when the rebuild cannot run at all (read-
    only tree, no tools): a stale grouping beats no grouping, and the GUI must
    still open.
    """
    from .build import DEFAULT_K

    k = DEFAULT_K if k is None else k
    try:
        if is_stale(root, k):
            from .build import build_groups

            build_groups(root, k=k, budget=budget)
    except Exception:
        pass
    return load_groups(root)
