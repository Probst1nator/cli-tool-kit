# The `--advertise` Installer Protocol

This document specifies the convention that lets a parent installer discover,
display, and install/remove a tree of self-describing Python tools.

A consuming repository (the "parent") scans for entry-point scripts that
respond to `--advertise` with a JSON list of metadata records. Each record
describes how that tool wants to be installed.

## The probe contract

The parent installer invokes each candidate script as:

```bash
python <script_path> --advertise
```

The script MUST:

1. Print a JSON list of one or more metadata dicts to stdout.
2. Exit with status 0.
3. Do this **before any heavy imports** — the parent enforces a 5-second
   timeout on the probe. Tools that import `requests`, `pandas`, or any other
   slow module before answering the probe will time out and disappear from
   the parent's listing.

## Metadata schema

Each dict in the list describes one installable variant of the tool.

| Field | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `name` | str | yes | — | Human-readable label shown in the GUI / list. |
| `desktop_file` | str | yes | — | Filename for the `.desktop` shortcut (e.g. `"my_tool.desktop"`). Also used as alias name if `alias` is unset. |
| `icon` | str | yes | — | Icon name (freedesktop name like `"utilities-terminal"`) or absolute path. |
| `desc` | str | yes | — | Short description shown under the name. |
| `terminal` | bool | no | `False` | If true, launches under `konsole -e`. |
| `args` | list[str] | no | `[]` | Extra CLI args appended to the entry-point invocation. |
| `tags` | list[str] | no | `["GUI", "Icon"]` | Capability tags — see below. |
| `alias` | str | conditional | (derived from `desktop_file`) | Bash alias name. Required when `Icon` is not in tags. |
| `categories` | str | no | `"Utility;"` | `.desktop` Categories field. |
| `skill_name` | str | no | — | Opt into Claude Code skill registration — see "Optional `skill_name`" below. |

## Tags

Tools declare their capabilities via `tags`:

- **`GUI`** — has a graphical window (tkinter / Qt / GTK / etc.)
- **`CLI`** — runs in the terminal
- **`Icon`** — gets a `.desktop` shortcut in `~/.local/share/applications/`

Without `Icon`, the tool is installed as a bash alias in `~/.tools_aliases`
(which the installer auto-sources from `~/.bashrc` on first install).

| Tool type | Tags | `alias` field | Resulting install |
|---|---|---|---|
| GUI app with desktop icon | `["GUI", "Icon"]` | omit | `.desktop` file |
| Terminal app with desktop icon | `["CLI", "Icon"]` | omit | `.desktop` file |
| CLI-only (bash alias) | `["CLI"]` | required | bash alias |
| GUI + CLI with desktop icon | `["GUI", "CLI", "Icon"]` | omit | `.desktop` file |
| GUI + CLI without icon | `["GUI", "CLI"]` | required | bash alias |
| Desktop icon **and** shell alias | `["GUI", "CLI", "Icon"]` | set | `.desktop` file **and** bash alias |

The `alias` field is independent of `Icon`: set it to also install a bash
alias alongside a `.desktop` file (handy for GUI tools you also want to launch
from the terminal).

## Minimal example

```python
#!/usr/bin/env python3
import sys
from cli_tool_kit import ToolMetadata, ToolInstaller, advertise

# MUST be before any heavy imports!
if "--advertise" in sys.argv:
    advertise(ToolMetadata(
        name="Git Commit Suggester",
        desktop_file="cg.desktop",
        icon="git",
        desc="AI-powered commit message suggestions",
        tags=["CLI"],
        alias="cg",
    ))

# Heavy imports AFTER the advertise guard
import argparse
from somewhere_slow import HeavyThing

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--remove", action="store_true")
    args = parser.parse_args()

    installer = ToolInstaller(
        script_path=__file__,
        metadata=ToolMetadata(
            name="Git Commit Suggester",
            desktop_file="cg.desktop",
            icon="git",
            desc="AI-powered commit message suggestions",
            tags=["CLI"],
            alias="cg",
        ),
    )

    if args.install:
        installer.install()
    elif args.remove:
        installer.remove()

if __name__ == "__main__":
    main()
```

## Install output hints (recommended for CLI tools)

When `--install` prints a command the user should run next, prefix it with
`Run: ` on a single line. Compliant parent installer GUIs parse this and
surface a copy button:

```python
# Single command
print("Run: source ~/.bashrc")

# Multiple commands — join with &&
print("Run: source ~/.bashrc && cg --help")
```

`ToolInstaller` does this automatically for tools without an `Icon` tag.

## Cron lines (`CronInstaller`)

Tools that run on a schedule should use `CronInstaller` for idempotent, atomic
cron-line management:

```python
from cli_tool_kit import CronInstaller

cron = CronInstaller("my-tool")  # unique marker for this tool's lines

if args.install:
    installer.install()  # alias / desktop shortcut
    cron.install([
        f"@reboot cd {SCRIPT_DIR} && {sys.executable} {SCRIPT} --daemon",
        f"0 6 * * * cd {SCRIPT_DIR} && {sys.executable} {SCRIPT} --daily",
    ])
elif args.remove:
    installer.remove()
    cron.remove()
```

Each managed line gets a trailing `# cli-tool-kit:<marker>` comment so that:
- Re-installing the same lines is a no-op (idempotent).
- Removing strips only lines bearing this marker — other tools' cron entries
  are untouched.
- Multiple tools (each with their own marker) coexist in one user's crontab
  without colliding.

## Optional `skill_name` — Claude Code skill registration

If a tool can register a Claude Code skill (a `~/.claude/skills/<name>/SKILL.md`),
add `"skill_name": "<name>"` to its advertise dict. Compliant parent installer
GUIs then show a per-row **Skill** checkbox; checking it runs the tool's
`--install-skill`, unchecking runs `--uninstall-skill`. The Install checkbox
auto-checks Skill when toggled on.

Contract the tool must satisfy:

- Expose `--install-skill` and `--uninstall-skill` CLI flags, both idempotent.
- `--install-skill` writes `~/.claude/skills/<skill_name>/SKILL.md` from an
  inline `SKILL_MD_CONTENT` constant (single source of truth — never edit the
  on-disk file directly).
- `--uninstall-skill` removes that file and the empty dir.
- The tool's existing `--install` may call `_install_skill()` as a best-effort
  final step so direct CLI use stays one-shot.

The skill name is the directory under `~/.claude/skills/` and can differ from
the tool name (e.g. tool `studon-client` registers skill `studon`).

## When reinstallation is required

`.desktop` files contain hardcoded absolute paths. After certain changes you
must `--remove` then `--install` to update them.

| Change | Reinstall? | Reason |
|---|---|---|
| Tool directory renamed/moved | **yes** | Path in `.desktop` file is now invalid |
| `.desktop` filename changed | **yes** | Old file remains, new one not created |
| New entry points added | **yes** | New shortcuts don't exist yet |
| Icon or display name changed | **yes** | Stored in `.desktop` file |
| New dependencies in `requirements.txt` | **yes** | Need `pip install` |
| Code changes in `.py` files | no | Script re-read on each launch |
| Internal module changes | no | Python reloads on each run |
| Data directory changes | no | Paths resolved dynamically in code |
