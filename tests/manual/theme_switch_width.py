#!/usr/bin/env python3
"""Manual check: the tool table keeps the window width across a theme switch.

The tkinter window cannot be opened from the pytest suite, so this stays a
script. It opens the installer on two fake tools, measures the table, clicks a
theme button through the same handler the buttons call, and measures again. It
prints both measurements and exits non-zero if the table shrank.

    DISPLAY=:0 python3 tests/manual/theme_switch_width.py [--shots DIR]

With ``--shots DIR`` it also saves a screenshot of the whole screen before and
after the switch (needs ImageMagick's ``import``).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

# A sandbox HOME, so the run does not touch the real config, aliases or
# shortcuts of whoever is testing.
os.environ.setdefault("CLI_TOOLS_KIT_MANUAL_HOME", tempfile.mkdtemp(prefix="kit-manual-"))
os.environ["HOME"] = os.environ["CLI_TOOLS_KIT_MANUAL_HOME"]

import tkinter as tk  # noqa: E402

from cli_tools_kit import gui_installer as engine  # noqa: E402


def _tool(name: str, capability: str) -> engine.ToolEntry:
    return engine.ToolEntry(
        name=name, desktop_file=f"{name}.desktop",
        script_path=f"/nonexistent/{name}/main.py", args=[], icon="utilities-terminal",
        description=f"{name} does something", terminal=False, category="Demo",
        capability=capability, tags=["CLI"], alias=name,
    )


def _measure(app) -> dict:
    # scrollable_frame -> header container -> border wrapper -> the header row,
    # whose third child is the stretching "Tool" column.
    container = app.scrollable_frame.winfo_children()[0]
    header_row = container.winfo_children()[0].winfo_children()[0]
    return {
        "window": app.root.winfo_width(),
        "canvas": app.canvas.winfo_width(),
        "canvas item": int(float(app.canvas.itemcget(app.canvas_window, "width"))),
        "table": header_row.winfo_width(),
        "tool column": header_row.winfo_children()[2].winfo_width(),
    }


def _shot(path: str) -> None:
    try:
        subprocess.run(["import", "-window", "root", path], check=True)
        print(f"screenshot: {path}")
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"no screenshot ({exc})")


def main() -> int:
    shots = None
    if "--shots" in sys.argv:
        shots = sys.argv[sys.argv.index("--shots") + 1]
        os.makedirs(shots, exist_ok=True)

    root = tk.Tk(className="cli-tools-kit-manual")
    app = engine.InstallerApp(root, [_tool("alpha", "scrape"), _tool("beta", "convert")])
    root.geometry("900x600+80+80")
    for _ in range(3):
        root.update_idletasks()
        root.update()

    before = _measure(app)
    print("before:", before)
    if shots:
        _shot(os.path.join(shots, "before-theme-switch.png"))

    other = next(name for name in app.THEMES if name != app.current_theme)
    print(f"switching {app.current_theme} -> {other}")
    app._select_theme(other)
    for _ in range(3):
        root.update_idletasks()
        root.update()

    after = _measure(app)
    print("after: ", after)
    if shots:
        _shot(os.path.join(shots, "after-theme-switch.png"))

    root.destroy()

    ok = after["tool column"] >= before["tool column"] and after["table"] >= before["table"]
    print("PASS: the table kept its width" if ok else
          "FAIL: the table shrank on the theme switch")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
