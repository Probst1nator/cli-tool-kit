"""``python3 -m cli_tool_kit`` — set up an installer for your organisation.

Two surfaces:

    python3 -m cli_tool_kit                       first-run setup (the default)
    python3 -m cli_tool_kit install FILE [flags]  run the installer for a
                                                  sources file (see sources.py)

``install`` takes the path of an ``installer.toml`` and passes every remaining
flag to the installer engine. It uses the default installer identity, so an
organisation that wants its own namespace on the host writes the short
``installer.py`` in README § Sources instead and runs that.
"""

import os
import sys

from .onboarding import main

USAGE = "usage: python3 -m cli_tool_kit install <installer.toml> [engine flags]"


def _install(argv):
    """The ``install`` subcommand: run the installer for one sources file."""
    if not argv or argv[0].startswith("-"):
        print(USAGE, file=sys.stderr)
        return 2
    config = argv[0]
    if not os.path.isfile(config):
        print(f"{config}: no such file\n{USAGE}", file=sys.stderr)
        return 2
    from .sources import run_installer  # noqa: PLC0415 — imports the engine
    # ENTRY_SCRIPT is what the manager shortcut and the login check re-enter.
    # The wrapper next to the sources file is the right one when there is one.
    wrapper = os.path.join(os.path.dirname(os.path.abspath(config)), "installer.py")
    entry = wrapper if os.path.isfile(wrapper) else os.path.abspath(sys.argv[0])
    return run_installer(config, argv=argv[1:], entry_script=entry)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "install":
        sys.exit(_install(sys.argv[2:]))
    sys.exit(main())
