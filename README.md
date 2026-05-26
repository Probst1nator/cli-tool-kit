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

## Tests

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT — see [`LICENSE`](LICENSE).
