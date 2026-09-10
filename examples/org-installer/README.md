# Example: an installer for your organisation

A complete, runnable tool tree. Copy the shape, not the names.

```
org-installer/
├── installer.py        # the wrapper — identity + run()
└── greeter/
    ├── main.py         # a tool: --advertise, --install/--remove, skill flags
    └── requirements.txt
```

Try it (nothing is installed until you ask for it):

```bash
python3 installer.py --list     # what the engine discovered
python3 installer.py            # the GUI
```

## What to change

**`installer.py`** — the slug. Everything this installer claims on a host
derives from it: `~/.config/<slug>/`, `~/.<slug>_aliases`, `~/.cache/<slug>/`,
`<slug>-installer.desktop`, the WM class, and the `Keywords=<slug>;ai;tool;`
marker that tells its orphan sweeper which shortcuts are its own. Pick it once —
changing it later orphans whatever is already installed under the old name.

**`greeter/main.py`** — the metadata dict, and the program under `main()`.

## The rule that catches people

`--advertise` must print its JSON and exit **before any heavy import**. The
installer probes each tool with a 5-second timeout, so a tool that imports
torch or a provider SDK at module level simply never appears. Keep the probe at
the top of the file, above everything.

Tools are discovered at `<root>/<tool>/main.py` (needing a `requirements.txt`
beside it), or at `<root>/tools_<category>/<tool>/main.py`. Directories starting
with `_` or `.` are skipped. For any other shape, pass your own `discoverer` —
see the repo README, "Reusing the installer in your org".

## Being set up by an agent

From your own tool tree:

```bash
python3 -m cli_tools_kit
```

prints a brief to paste into Claude Code (or any agent with a structured
question tool). It asks you the naming decisions, writes the wrapper, and
reports what it discovered. `--interactive` asks the same questions here
instead; `--print-wrapper` prints the skeleton alone.
