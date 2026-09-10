"""Sources — one installer offering tools that live in several repos.

An organisation's tools rarely sit in one checkout. This module lets the
installer read a list of repos from a TOML file next to it, put each one on
disk, and hand the engine one discovery root per repo.

``installer.toml`` is tracked and shared by everyone:

    [[source]]
    name = "acme/tools"
    path = "."                                    # relative to this file

    [[source]]
    name = "acme/lab"
    url = "https://github.com/acme/lab-tools"     # cloned into <root>/acme/lab

``installer.local.toml`` next to it is optional and belongs to one machine, so
it is gitignored by convention. It sets ``root`` and adds or replaces a ``path``
for a source matched by ``name``:

    root = "/home/me/checkouts"

    [[source]]
    name = "acme/lab"
    path = "/home/me/work/lab-tools"

A source resolves in this order: the path from the local file, then the ``path``
from the tracked file, then an existing ``<root>/<name>``, then a clone of
``url`` into ``<root>/<name>``. Only ``https://`` URLs are cloned, the clone is
full rather than shallow, and a clone that fails prints one line and drops that
source, so the other repos' tools still install.

A resolved repo may carry its own ``installer.toml``. Its ``[[source]]`` entries
are resolved too, one nested level deep and no further. Paths in a nested file
are relative to that file, clones still go under the same root, a path already
resolved is not visited twice, and duplicates are dropped.

The whole feature is three calls:

    sources = load_sources("installer.toml")
    roots = resolve_sources(sources, root="~/acme-tools")

or, for a wrapper that just wants the installer:

    run_installer(os.path.join(HERE, "installer.toml"),
                  identity=InstallerIdentity(slug="acme-tools"),
                  entry_script=__file__)
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Sequence

__all__ = ["Source", "load_sources", "resolve_sources", "run_installer"]

# How far below the top-level installer.toml a nested one is still read.
MAX_NESTING = 1

# Neutralise the ext:: and file:// transports and any hook, so fetching a repo
# cannot turn into running code from it.
GIT_SAFE = ("-c", "protocol.ext.allow=never",
            "-c", "protocol.file.allow=never",
            "-c", "core.hooksPath=/dev/null")


@dataclass(frozen=True)
class Source:
    """One repo an installer offers tools from.

    ``path`` is already absolute: ``load_sources`` resolves it against the TOML
    file it was written in. ``url`` is used only when no path is on disk.
    """

    name: str
    url: Optional[str] = None
    path: Optional[str] = None


# --- TOML -------------------------------------------------------------------

def _toml_module():
    """``tomllib`` (Python 3.11+), ``tomli`` if it is installed, else None."""
    try:
        import tomllib  # noqa: PLC0415
        return tomllib
    except ImportError:
        pass
    try:
        import tomli  # noqa: PLC0415
        return tomli
    except ImportError:
        return None


def _read_toml(path: Path, log: Callable = print) -> dict:
    """One TOML file as a dict, empty if it is absent or does not parse."""
    toml = _toml_module()
    if toml is None:
        log(f"{path.name}: not read (needs Python 3.11 or `pip install tomli`)")
        return {}
    if not path.is_file():
        return {}
    try:
        with open(path, "rb") as fh:
            return toml.load(fh)
    except (OSError, ValueError) as exc:
        log(f"{path.name}: not read ({exc})")
        return {}


def _local_path_for(config_path: Path) -> Path:
    """``installer.toml`` -> ``installer.local.toml`` in the same directory."""
    return config_path.with_name(config_path.stem + ".local" + config_path.suffix)


def _absolute(base: Path, raw: str) -> str:
    return os.path.abspath(os.path.join(str(base), os.path.expanduser(raw)))


def local_root(config_path, local_path=None) -> Optional[str]:
    """The top-level ``root`` of the local file next to ``config_path``, or None."""
    config_path = Path(config_path)
    local = Path(local_path) if local_path is not None else _local_path_for(config_path)
    value = _read_toml(local).get("root")
    if isinstance(value, str) and value:
        return str(Path(os.path.expanduser(value)).absolute())
    return None


def load_sources(config_path, local_path=None, log: Callable = print) -> List[Source]:
    """The ``[[source]]`` entries of one TOML file, local overrides applied.

    ``local_path`` defaults to ``installer.local.toml`` next to ``config_path``.
    A ``path`` is taken relative to the file it is written in. An entry without
    a name is reported and dropped.
    """
    config_path = Path(config_path)
    local_path = Path(local_path) if local_path is not None else _local_path_for(config_path)
    data = _read_toml(config_path, log)
    local = _read_toml(local_path, log)

    overrides = {entry["name"]: entry
                 for entry in local.get("source") or []
                 if isinstance(entry, dict) and entry.get("name")}

    sources: List[Source] = []
    for entry in data.get("source") or []:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not name:
            log(f"{config_path.name}: a [[source]] without a name, skipped")
            continue
        override = overrides.get(name, {}).get("path")
        raw = override or entry.get("path")
        base = local_path.parent if override else config_path.parent
        path = _absolute(base, raw) if raw else None
        sources.append(Source(name=name, url=entry.get("url"), path=path))
    return sources


# --- resolution -------------------------------------------------------------

def _git(*args):
    try:
        result = subprocess.run(["git", *GIT_SAFE, *args], capture_output=True, text=True)
    except OSError as exc:
        return False, str(exc)
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def _clone_reason(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return next((line for line in lines if line.startswith("fatal:")),
                lines[-1] if lines else "git clone failed")


def _resolve_one(source: Source, root: Path, refresh: bool, log: Callable,
                 clone: bool) -> Optional[Path]:
    """Where one source sits on disk, cloning it if that is the only way."""
    if source.path and Path(source.path).is_dir():
        return Path(source.path).resolve()

    target = root.joinpath(*source.name.split("/"))
    if target.is_dir():
        if refresh and clone and (target / ".git").is_dir() and source.url:
            ok, _ = _git("-C", str(target), "pull", "--ff-only")
            log(f"{source.name}: pulled" if ok else
                f"{source.name}: left as is, local changes or diverged history")
        return target.resolve()

    if not source.url:
        if clone:
            log(f"{source.name}: no checkout at {target} and no url, skipped")
        return None
    if not source.url.lower().startswith("https://"):
        if clone:
            log(f"{source.name}: {source.url} is not an https:// URL, skipped")
        return None
    if not clone:
        return None
    if not (root.is_dir() and os.access(str(root), os.W_OK)):
        log(f"{source.name}: not cloned, skipped ({root} does not exist or cannot be"
            " written to; pass --root DIR to clone somewhere else)")
        return None

    log(f"Cloning {source.url} -> {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    ok, out = _git("clone", source.url, str(target))
    if not ok:
        log(f"{source.name}: not cloned, skipped ({_clone_reason(out)})")
        return None
    return target.resolve()


def _resolve_level(sources: Sequence[Source], root: Path, refresh: bool, log: Callable,
                   clone: bool, config_name: str, depth: int,
                   found: List[Path], seen: set) -> None:
    for source in sources:
        path = _resolve_one(source, root, refresh, log, clone)
        if path is None or path in seen:
            continue
        seen.add(path)
        found.append(path)
        if depth >= MAX_NESTING:
            continue
        nested = path / config_name
        if nested.is_file():
            _resolve_level(load_sources(nested, log=log), root, refresh, log, clone,
                           config_name, depth + 1, found, seen)


def resolve_sources(sources: Sequence[Source], root, refresh: bool = False,
                    log: Callable = print, clone: bool = True) -> List[Path]:
    """Put every source on disk and return one discovery root per repo.

    Clones the sources that are given by a URL and are not on disk yet. With
    ``refresh`` the clones are also brought up to date with ``git pull
    --ff-only``; a checkout given by ``path`` is never pulled. A source that
    cannot be resolved prints one line and is left out.

    A resolved repo that holds its own ``installer.toml`` contributes its
    sources too, one nested level deep. Clones from a nested file go under the
    same root. A path that is already in the result is not visited again, so a
    file that points back at its parent cannot loop.

    ``clone=False`` resolves from the filesystem alone and never reaches the
    network, which is what the login check needs.
    """
    root = Path(os.path.expanduser(str(root))).absolute()
    found: List[Path] = []
    _resolve_level(sources, root, refresh, log, clone, "installer.toml", 0, found, set())
    return found


# --- the convenience wrapper ------------------------------------------------

def _take_root(argv: List[str]):
    """Pull ``--root DIR`` out of ``argv``. The engine owns every other flag."""
    rest, root = [], None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--root" and i + 1 < len(argv):
            root = argv[i + 1]
            i += 2
            continue
        if arg.startswith("--root="):
            root = arg[len("--root="):]
            i += 1
            continue
        rest.append(arg)
        i += 1
    return rest, root


def default_root(config_path) -> str:
    """Two levels above the config file's directory.

    A bootstrap script clones the first repo to ``<root>/<org>/<tool tree>``, so
    the other sources belong two levels up from the file that lists them.
    """
    return str(Path(config_path).absolute().parent.parent.parent)


def run_installer(config_path, argv=None, **run_kwargs):
    """Read a sources file, wire the engine to it, and run the installer.

    ``--root DIR`` is taken from ``argv`` (``sys.argv[1:]`` by default) and the
    rest is left to the engine, so ``--list``, ``--apply``, ``--skill-target``,
    ``--check``, ``--tui`` and ``--gui`` keep working. ``--refresh`` stays the
    engine's flag: it reaches the pre-discovery hook, which then pulls every
    clone.

    The root is ``--root`` if given, else the ``root`` of the local file, else
    two levels above the config file's directory. Cloning happens in the
    pre-discovery hook, which the engine skips on the ``--check`` path, so that
    check stays network-free and sees whatever is already on disk.

    Every other keyword goes to :func:`cli_tool_kit.gui_installer.run`.
    ``discovery_roots`` and ``pre_discovery`` are this function's to set.
    """
    for reserved in ("discovery_roots", "pre_discovery"):
        if reserved in run_kwargs:
            raise TypeError(f"run_installer sets {reserved} itself")

    config_path = Path(config_path).absolute()
    argv = list(sys.argv[1:] if argv is None else argv)
    argv, root_arg = _take_root(argv)
    sys.argv = [sys.argv[0]] + argv

    root = root_arg or local_root(config_path) or default_root(config_path)
    root = str(Path(os.path.expanduser(root)).absolute())
    sources = load_sources(config_path)

    # The engine reads DISCOVERY_ROOTS after the hook has run, so the hook fills
    # this list in place with what it resolved. It is pre-filled with what is on
    # disk already, for the --check path that never calls the hook.
    roots = [str(p) for p in resolve_sources(sources, root, clone=False,
                                             log=lambda *_: None)]

    def pre_discovery(refresh):
        roots[:] = [str(p) for p in resolve_sources(sources, root, refresh=refresh)]

    from . import gui_installer  # noqa: PLC0415 — imports tkinter, keep it lazy
    run_kwargs.setdefault("root_dir", root)
    return gui_installer.run(discovery_roots=roots, pre_discovery=pre_discovery,
                             **run_kwargs)
