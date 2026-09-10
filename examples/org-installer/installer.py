#!/usr/bin/env python3
"""Installer for the Acme Tools tool tree.

Discovers every tool under this directory that answers --advertise, and lets you
install or remove its desktop entry, shell alias and Claude Code skill.

    python3 installer.py            # GUI
    python3 installer.py --list     # what was discovered
    python3 installer.py --check    # headless login reconciliation

See PROTOCOL.md in cli-tools-kit for what a tool must advertise to show up here.
"""

import os

from cli_tools_kit import InstallerIdentity
from cli_tools_kit.gui_installer import run

HERE = os.path.dirname(os.path.abspath(__file__))

# Everything this installer claims on a host derives from the slug: the config
# directory, the alias file, the icon cache, its own .desktop entry, the WM
# class, and the Keywords marker its orphan sweeper matches on. Change the slug
# and you move house — existing shortcuts keep the old names.
IDENTITY = InstallerIdentity(
    slug="acme-tools",
    title="Acme Tools",
    icon="system-software-install",
)

if __name__ == "__main__":
    run(
        identity=IDENTITY,
        root_dir=HERE,
        entry_script=__file__,
        # "capability" bands the GUI rows by each tool's advertised capability
        # word; "category" bands by whatever label your discoverer assigns.
        group_by="capability",
    )
