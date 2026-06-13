"""Skill-freshness helpers for the installer protocol.

A tool that bundles a Claude Code skill installs it into
``~/.claude/skills/<skill_name>/``. These helpers let an installer — or the tool
itself, at ``--advertise`` time — decide whether the installed copy is up to
date with the tool's bundled version, so the installer can *take note* and
suggest an update instead of silently keeping a stale skill.

The unit of comparison is a ``{relative_posix_path: text}`` mapping. A tool
hashes what it would install; an installer hashes what is installed; equal
hashes mean "current". This keeps the comparison authoritative and free of any
cross-package version coupling — each side computes over content it can see.
"""

from __future__ import annotations

import hashlib
import os
from typing import Dict, Optional

# Names that may appear inside an installed skill dir without being part of the
# skill's content — excluded so a stray artifact can't force a false "stale".
_SKILL_IGNORE_NAMES = {".DS_Store"}


def _default_skills_dir() -> str:
    """``~/.claude/skills`` resolved at call time (honours a patched $HOME)."""
    return os.path.join(os.path.expanduser("~"), ".claude", "skills")


def skill_payload_hash(files: Dict[str, str]) -> str:
    """Stable, order-independent hash of a skill's content.

    ``files`` maps POSIX-relative paths (e.g. ``"SKILL.md"``,
    ``"scripts/send.sh"``) to their text. The same mapping always yields the
    same digest, so a tool can hash what it bundles and an installer can hash
    what is installed and compare the two.
    """
    h = hashlib.sha256()
    for rel in sorted(files):
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(files[rel].encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()


def read_installed_skill(
    skill_name: str, skills_dir: Optional[str] = None
) -> Optional[Dict[str, str]]:
    """Read an installed skill's files as ``{relpath: text}``, or ``None``.

    Returns ``None`` when the skill is not installed (no ``SKILL.md`` under its
    dir). Binary/unreadable files and obvious junk (``__pycache__``, ``*.pyc``,
    ``.DS_Store``) are skipped so the comparison stays robust.
    """
    root = os.path.join(skills_dir or _default_skills_dir(), skill_name)
    if not os.path.isfile(os.path.join(root, "SKILL.md")):
        return None
    out: Dict[str, str] = {}
    for dirpath, dirnames, names in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in names:
            if name in _SKILL_IGNORE_NAMES or name.endswith(".pyc"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            try:
                with open(path, "r", encoding="utf-8") as f:
                    out[rel] = f.read()
            except (OSError, UnicodeDecodeError):
                continue
    return out


def installed_skill_hash(
    skill_name: str, skills_dir: Optional[str] = None
) -> Optional[str]:
    """Hash of the installed skill's content, or ``None`` when not installed."""
    files = read_installed_skill(skill_name, skills_dir)
    return None if files is None else skill_payload_hash(files)


def skill_status(
    skill_name: str, bundled: Dict[str, str], skills_dir: Optional[str] = None
) -> str:
    """Return ``"absent"`` | ``"current"`` | ``"stale"``.

    Compares the installed skill against ``bundled`` (the ``{relpath: text}``
    the tool would install). ``"absent"`` if not installed, ``"current"`` if the
    content matches, ``"stale"`` otherwise — the cue for an installer to suggest
    an update.
    """
    installed = read_installed_skill(skill_name, skills_dir)
    if installed is None:
        return "absent"
    return "current" if skill_payload_hash(installed) == skill_payload_hash(bundled) else "stale"
