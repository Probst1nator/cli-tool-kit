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
pip install git+https://github.com/Probst1nator/cli-tool-kit.git@v0.3.1
```

Or pin in `requirements.txt`:

```
cli-tool-kit @ git+https://github.com/Probst1nator/cli-tool-kit.git@v0.3.1
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

## Reusing the installer in your org

`cli_tool_kit.gui_installer` is a batteries-included tkinter installer that any
tool tree can reuse instead of forking. Point it at your tree and it discovers
every tool that answers `--advertise`, then installs or removes each one's
desktop entry, shell alias and Claude Code skill.

**Start here:**

```bash
cd /path/to/your/tools
python3 -m cli_tool_kit
```

That prints a brief you can paste into your coding agent (Claude Code or
similar); the agent interviews you for the handful of naming decisions and
writes the wrapper. `--interactive` answers the same questions on the command
line instead, and `--print-wrapper` just prints the skeleton. A complete
worked example — wrapper plus a tool — is in
[`examples/org-installer/`](examples/org-installer/).

### Identity: what your installer claims on a host

Several organisations' installers can share a machine, so yours needs a name of
its own. `InstallerIdentity` derives every per-host artifact from one slug:

```python
# my-org-tools/installer.py
import os
from cli_tool_kit import InstallerIdentity
from cli_tool_kit.gui_installer import run

HERE = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    run(
        identity=InstallerIdentity(slug="acme-tools", title="Acme Tools"),
        root_dir=HERE,
        entry_script=__file__,
    )
```

| Derived from `slug="acme-tools"` | Value |
|---|---|
| config + icon overrides | `~/.config/acme-tools/` |
| shell aliases | `~/.acme_tools_aliases` |
| icon cache | `~/.cache/acme-tools/` |
| the manager's own shortcut | `acme-tools-installer.desktop` |
| WM class | `acme_tools_installer` |
| login-check artifacts | `acme-tools-check.{desktop,log,json}` |
| `.desktop` marker | `Keywords=acme-tools;ai;tool;` |

That last one matters most: it is how the installer's orphan sweeper decides a
shortcut is *its* shortcut. With distinct markers, two organisations' installers
never delete each other's entries. Every derived name can be overridden with the
matching `InstallerIdentity` field (`config_dir`, `aliases_file`, `wm_class`, …).

**Passing no identity selects the historical first-party names**, so existing
installs are untouched by an upgrade. Running the engine bare — no identity, no
wrapper — stops and offers setup rather than claiming those names.

### `run()`

Keyword-only; every argument defaults to `None`, meaning "leave the default".

| Argument | Default | What it does |
|---|---|---|
| `identity` | `LEGACY_IDENTITY` | The names above. The one argument a third party should always pass. |
| `root_dir` | cwd | The tree to manage. Discovery, `.env` loading and the self-shortcut's `Path=` all anchor here. |
| `entry_script` | this module | The script the manager shortcut and the login-check autostart entry launch. Pass `__file__` so they re-enter your wrapper, not the bare engine. |
| `discoverer` | flat + `tools_*/` walk | `callable(root) -> [(entry_point_path, category), …]`. Pass your own for a differently shaped tree. |
| `discovery_roots` | `[root_dir]` | Scan these directories instead — for tools that live in a subdirectory or several. |
| `group_by` | `"capability"` | Which field bands the GUI rows: `"capability"` (the advertised word) or `"category"` (whatever your discoverer assigned). Anything else raises `ValueError`. |
| `pre_discovery` | `None` | `callable(refresh: bool)` run once before scanning, for side effects like cloning repos into a cache. Skipped on the `--check` path so a login hook never touches the network. |
| `check_reconcile_shortcuts` | `True` | Whether `--check` also reinstalls drifted shortcuts. Set `False` when your tools' `--install` has side effects unsafe for a login hook, making `--check` skill-only. |
| `skill_targets` | `[claude_target()]` | Where the text screen can register a skill — see "The text screen" below. |
| `tui_preselect` | `None` | Initial ticks on the text screen: `None` ticks everything on a host with nothing installed yet and otherwise mirrors the host; `True`/`False` force one or the other. |
| `window_title` | identity's title | GUI window title. |
| `self_desktop_file`, `self_desktop_name`, `self_desktop_icon` | identity's | The manager's own shortcut. |
| `wm_class` | identity's | `StartupWMClass` for window-manager grouping. |
| `notify_app` | identity's | `notify-send` application label on the `--check` path. |
| `autostart_check_desktop_name`, `check_log_name`, `check_state_name` | identity's | Login-check artifact filenames. |

The identity is applied first and these individual names override it, so you can
take the whole namespace from a slug and still change one thing.

`run()` owns its own `argparse` and consumes `sys.argv`: `--list`, `--check`,
`--enable-autostart-check`, `--install`, `--update-all`, `--cleanup`, `--tui`,
`--gui`, and a screen when given none of them. A wrapper that needs its own
subcommands should skip `run()` and call the primitives (`discover_tools`,
`install_tool`, `remove_tool`, `cli_check`) after applying an identity with
`_apply_identity`.

### The text screen

Without a display (`DISPLAY`/`WAYLAND_DISPLAY` unset: SSH, WSL, a server) or
without `python3-tk`, `run()` opens a curses screen instead of the tkinter
window; `--tui` and `--gui` force either. Same rows, same Apply: `Space` ticks
Install, `s` ticks Skill, `a`/`n` tick all or none, `Enter` applies, `q` quits.
On a host where none of the tools is installed yet every row starts ticked.

A skill can go to more than one place. The default target writes
`~/.claude/skills/<name>/` through the tool's `--install-skill`; a wrapper adds
others with `skill_targets`, and the screen lets the user tick which ones
Apply writes to (keys `1`..`9`):

```python
from cli_tool_kit.tui_installer import SkillTarget, claude_target

session = SkillTarget(
    key="fauclaude", label="fauclaude session plugin",
    installed=lambda tool: ...,          # bool
    install=lambda tool: (True, "..."),  # (ok, output)
    uninstall=lambda tool: (True, ""),
)
run(identity=IDENTITY, root_dir=HERE, entry_script=__file__,
    skill_targets=[claude_target(), session])
```

The screen calls the engine's `install_tool` / `remove_tool` / skill functions
by name at run time, so a wrapper that replaced them (to run each tool in its
own venv, say) is honoured there too.

### Discovering your tools

The default discoverer accepts two layouts, and a tree may mix them:

- **flat** — `<root>/<tool>/main.py` (plus `requirements.txt`). Category empty,
  so rows band by each tool's advertised `capability`.
- **nested** — `<root>/tools_<category>/<tool>/main.py`, where the folder
  supplies the category label.

Directories starting with `_` or `.` are skipped. Anything else: pass a
`discoverer`. If an expected tool does not appear, its `--advertise` is the
thing to fix — it must print JSON and exit *before* any heavy import, or it
trips the 5-second probe timeout. See [`PROTOCOL.md`](PROTOCOL.md).

### Grouping rows by meaning

`group_by="capability"` bands rows by the one word each tool advertises. Once a
tree outgrows that, `cli_tool_kit.taxonomy` reads what the tree already
documents about itself and produces a small set of named categories:

```python
from cli_tool_kit.taxonomy import ensure_groups

def discover(root):
    groups = ensure_groups(root)          # {tool_name: band label}
    return [(entry, groups.get(name, "")) for entry, name in my_walk(root)]
```

It fingerprints every `CLAUDE.md`/`README.md` in the tree and rebuilds only when
one changed (content hashes, not mtimes — a sync checkout restamps mtimes).
Three tiers, tried in order so it degrades rather than failing: an LLM naming
and filling the categories (Gemini via `GEMINI_API_KEY`, else a local LM Studio
/ Ollama server), else the advertised capability words banded into a fixed six,
else embedding + k-means. Nothing configured means tier two, which is instant
and needs no network.

### The GUI extra

Icon thumbnails need Pillow:

```bash
pip install "cli-tool-kit[gui] @ git+https://github.com/Probst1nator/cli-tool-kit.git@v0.2.2"
```

Installing the package also exposes a `cli-tool-installer` console script.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

## Used by

Consumers, each a self-installing tool that answers `--advertise`:

- [`studon-client`](https://github.com/Probst1nator/studon-client) — `ToolInstaller` + `CronInstaller` + a Claude Code skill
- [`BlogGen`](https://github.com/AutomatedAlchemy/BlogGen) — install machinery falls back gracefully when the kit is absent
- [`lernclaude`](https://github.com/Probst1nator/lernclaude) — same pattern
- [`manim-kit`](https://github.com/AutomatedAlchemy/manim-kit) — reports `skill_status`

Two parent installers built on `gui_installer` are private (a `tools_*/<tool>/main.py`
monorepo and a flat tree bootstrapped from a `repos.json` cache); a third walks a
lab-tools tree and gives each tool its own venv.

## License

MIT — see [`LICENSE`](LICENSE).
