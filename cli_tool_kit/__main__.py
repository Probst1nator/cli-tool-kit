"""``python3 -m cli_tool_kit`` — set up an installer for your organisation.

The package has no other command-line surface: running a tool tree is the job
of the ``installer.py`` this generates.
"""

import sys

from .onboarding import main

if __name__ == "__main__":
    sys.exit(main())
