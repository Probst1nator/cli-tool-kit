#!/usr/bin/env python3
"""Greeter — a complete, minimal cli-tools-kit tool.

Everything an installer needs from a tool is here and nothing else: the
--advertise probe, --install/--remove, and the optional Claude Code skill pair.
Copy this file, change the metadata, write your actual program under main().
"""

import json
import os
import sys

# --- the probe ------------------------------------------------------------
#
# This MUST come before any heavy import. The installer runs `main.py
# --advertise` with a 5-second timeout; a tool that imports torch first is a
# tool that never appears in the installer.

METADATA = {
    "name": "Greeter",
    "capability": "notify",        # controlled word — what the tool DOES
    "domain": "shell",             # optional distinguisher within a capability
    "desktop_file": "greeter.desktop",
    "icon": "dialog-information",  # freedesktop icon name, or an absolute path
    "desc": "Greet someone by name",
    "terminal": False,
    "args": [],
    "tags": ["CLI"],               # GUI / CLI / Icon — how it installs
    "alias": "greeter",            # required without the Icon tag
    "skill_name": "greeter",       # optional: registers a Claude Code skill
}

if "--advertise" in sys.argv:
    print(json.dumps([METADATA]))
    sys.exit(0)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SKILL_MD = """---
name: greeter
description: Greet someone by name.
---

Run the greeter:

```bash
python3 {script} --name "Ada"
```
"""


def _skill_dir() -> str:
    return os.path.join(os.path.expanduser("~"), ".claude", "skills", "greeter")


def _install_skill() -> None:
    """Write SKILL.md from the copy held here — never edit the installed file."""
    os.makedirs(_skill_dir(), exist_ok=True)
    path = os.path.join(_skill_dir(), "SKILL.md")
    # Absolute paths, never the shell alias: aliases do not expand in the
    # non-interactive shells an agent runs commands in.
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(SKILL_MD.format(script=os.path.join(SCRIPT_DIR, "main.py")))
    print(f"Installed skill: {path}")


def _uninstall_skill() -> None:
    path = os.path.join(_skill_dir(), "SKILL.md")
    if os.path.isfile(path):
        os.remove(path)
    if os.path.isdir(_skill_dir()) and not os.listdir(_skill_dir()):
        os.rmdir(_skill_dir())
    print("Removed skill: greeter")


# --- install / remove -----------------------------------------------------
#
# ToolInstaller writes the .desktop file and/or the shell alias. It takes its
# identity from the installer that spawned it, so the artifacts carry that
# organisation's marker and land in its alias file.

def _installer():
    from cli_tools_kit import ToolInstaller, ToolMetadata
    return ToolInstaller(
        script_path=__file__,
        metadata=ToolMetadata(
            name=METADATA["name"],
            desktop_file=METADATA["desktop_file"],
            icon=METADATA["icon"],
            desc=METADATA["desc"],
            tags=METADATA["tags"],
            alias=METADATA["alias"],
            capability=METADATA["capability"],
            domain=METADATA["domain"],
            skill_name=METADATA["skill_name"],
        ),
    )


def main() -> int:
    if "--install" in sys.argv:
        _installer().install()
        _install_skill()          # best-effort, so direct CLI use is one-shot
        return 0
    if "--remove" in sys.argv:
        _installer().remove()
        return 0
    if "--install-skill" in sys.argv:
        _install_skill()
        return 0
    if "--uninstall-skill" in sys.argv:
        _uninstall_skill()
        return 0

    name = "world"
    if "--name" in sys.argv:
        name = sys.argv[sys.argv.index("--name") + 1]
    print(f"Hello, {name}!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
