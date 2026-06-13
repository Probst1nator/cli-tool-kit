"""Tests for skill-freshness helpers (skill_status / skill_payload_hash)."""

from __future__ import annotations

from pathlib import Path

from cli_tool_kit import installed_skill_hash, skill_payload_hash, skill_status


def _install(home: Path, name: str, files: dict[str, str]) -> None:
    """Write a fake installed skill into $HOME/.claude/skills/<name>/."""
    root = home / ".claude" / "skills" / name
    for rel, body in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")


def test_absent_when_not_installed(sandbox_home: Path) -> None:
    assert skill_status("ghost", {"SKILL.md": "x"}) == "absent"
    assert installed_skill_hash("ghost") is None


def test_current_when_content_matches(sandbox_home: Path) -> None:
    _install(sandbox_home, "demo", {"SKILL.md": "hello"})
    assert skill_status("demo", {"SKILL.md": "hello"}) == "current"


def test_stale_when_content_differs(sandbox_home: Path) -> None:
    _install(sandbox_home, "demo", {"SKILL.md": "old body"})
    assert skill_status("demo", {"SKILL.md": "new body"}) == "stale"


def test_multifile_current_and_stale(sandbox_home: Path) -> None:
    bundled = {"SKILL.md": "a", "scripts/run.sh": "echo hi"}
    _install(sandbox_home, "ms", bundled)
    assert skill_status("ms", bundled) == "current"
    assert skill_status("ms", {"SKILL.md": "a", "scripts/run.sh": "echo bye"}) == "stale"


def test_stray_junk_is_ignored(sandbox_home: Path) -> None:
    _install(sandbox_home, "demo", {"SKILL.md": "x", ".DS_Store": "junk"})
    # The .DS_Store must not make an otherwise-matching skill look stale.
    assert skill_status("demo", {"SKILL.md": "x"}) == "current"


def test_payload_hash_is_order_independent() -> None:
    a = skill_payload_hash({"SKILL.md": "x", "b.txt": "y"})
    b = skill_payload_hash({"b.txt": "y", "SKILL.md": "x"})
    assert a == b


def test_payload_hash_distinguishes_path_from_body() -> None:
    # Moving content between the path key and the body must change the hash,
    # so a rename is detected as stale.
    assert skill_payload_hash({"ab": ""}) != skill_payload_hash({"a": "b"})
