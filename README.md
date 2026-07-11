# cli-tool-kit

A small library for self-installing Python CLI/GUI tools on Linux desktops.
Provides:

- **`ToolInstaller`** — install/remove `.desktop` shortcuts or bash aliases
  for a Python script, including auto-sourcing `~/.tools_aliases` from
  `~/.bashrc`.
- **`CronInstaller`** — idempotent cron-line management with marker comments
  so each tool's entries can be installed/removed without disturbing others.
- **`advertise()`** — a one-line helper for the `--advertise` JSON probe
  convention that lets parent installers discover and configure your tools.
- **`skill_status()`** — detect whether a tool's installed Claude Code skill
  (`~/.claude/skills/<name>/`) is `absent`, `current`, or `stale` vs. its
  bundled version, so an installer can suggest updates (`skill_payload_hash`,
  `installed_skill_hash`, `read_installed_skill` alongside).
- **`gui_installer`** — a full, reusable tkinter GUI installer *engine*: it
  discovers every tool in a project tree that speaks `--advertise`, and offers
  batch install/remove, per-row skill toggles, themes, orphan cleanup, and an
  opt-in login update-check. A thin wrapper points it at its own tree via
  `gui_installer.run(root_dir=..., entry_script=...)`; everything else
  (discovery layout, repo-cache bootstrap, login-check policy, window/desktop
  identities) is configurable. See [§ GUI installer engine](#gui-installer-engine).

See [`PROTOCOL.md`](PROTOCOL.md) for the full `--advertise` specification.

## Install

```bash
pip install git+https://github.com/Probst1nator/cli-tool-kit.git@v0.1.1
```

Or pin in `requirements.txt`:

```
cli-tool-kit @ git+https://github.com/Probst1nator/cli-tool-kit.git@v0.1.1
```

Requires Python ≥ 3.10. Optional runtime dep: `termcolor` (colored
install/remove output; falls back to plain text if absent).

## Minimal example

```python
#!/usr/bin/env python3
import sys
from cli_tool_kit import ToolMetadata, ToolInstaller, advertise

# MUST come before any heavy imports!
if "--advertise" in sys.argv:
    advertise(ToolMetadata(
        name="My Tool",
        desktop_file="my_tool.desktop",
        icon="utilities-terminal",
        desc="Does the thing",
        tags=["CLI"],
        alias="mytool",
    ))

import argparse

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--remove", action="store_true")
    args = parser.parse_args()

    installer = ToolInstaller(
        script_path=__file__,
        metadata=ToolMetadata(
            name="My Tool",
            desktop_file="my_tool.desktop",
            icon="utilities-terminal",
            desc="Does the thing",
            tags=["CLI"],
            alias="mytool",
        ),
    )
    if args.install:
        installer.install()
    elif args.remove:
        installer.remove()

if __name__ == "__main__":
    main()
```

After `python my_tool.py --install`, the `mytool` alias is available in new
shells (run `source ~/.bashrc` to pick it up immediately).

## Cron entries

```python
from cli_tool_kit import CronInstaller

cron = CronInstaller("my-tool")   # unique marker for this tool's entries

cron.install([
    f"@reboot cd {SCRIPT_DIR} && python {SCRIPT} --daemon",
    f"0 6 * * * cd {SCRIPT_DIR} && python {SCRIPT} --daily",
])

# Later:
cron.remove()                     # strips only lines bearing this marker
```

Each managed line gets a trailing `# cli-tool-kit:<marker>` comment.
Re-installing the same lines is a no-op; other tools' cron entries are
untouched.

## GUI installer engine

`cli_tool_kit.gui_installer` is a batteries-included tkinter installer that any
project tree can reuse instead of forking. A wrapper is a few lines:

```python
# my-project/installer.py
import os, sys
from cli_tool_kit.gui_installer import run

HERE = os.path.dirname(os.path.abspath(__file__))
if __name__ == "__main__":
    run(root_dir=HERE, entry_script=__file__)   # GUI default; --list/--check/... too
```

`run(...)` (and the bare module-level config globals it sets) take everything a
tree might differ on: `discoverer` (how to find entry points — defaults to the
`tools_*/<tool>/main.py` layout), `pre_discovery` (a hook to bootstrap/clone
repos before scanning; skipped on the login-check path so a login hook never
touches the network), `check_reconcile_shortcuts` (set `False` for a tree whose
`--install` has login-unsafe side effects, making `--check` skill-only), and the
window title / desktop-file / WM-class / autostart-name identities so several
installers coexist on one host.

The GUI needs Pillow for icon thumbnails — install the extra:

```bash
pip install "cli-tool-kit[gui]"
```

Installing the package also exposes a `cli-tool-installer` console script that
runs the engine against the current working directory.

### Used by

- [`tools/installer.py`](https://github.com/Probst1nator) — the `tools/` root
  installer (`tools_*/<tool>/` layout).
- `AutomatedAlchemy/installer.py` — flat FAU-tooling tree with a `repos.json`
  repo cache and a skill-only, network-free login check.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT — see [`LICENSE`](LICENSE).
