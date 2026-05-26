"""cli-tool-kit — installer protocol + helpers for self-installing Python CLI/GUI tools.

Public API:

    from cli_tool_kit import (
        ToolInstaller, ToolMetadata,   # desktop file / bash alias install/remove
        CronInstaller,                 # idempotent cron-line management
        advertise,                     # --advertise JSON helper
    )

See PROTOCOL.md for the full --advertise specification.
"""

from .tool_installer import ToolInstaller, ToolMetadata
from .cron_installer import CronInstaller
from .advertise import advertise

__all__ = [
    "ToolInstaller",
    "ToolMetadata",
    "CronInstaller",
    "advertise",
]

__version__ = "0.1.1"
