"""cli-tool-kit — installer protocol + helpers for self-installing Python CLI/GUI tools.

Public API:

    from cli_tool_kit import (
        ToolInstaller, ToolMetadata,   # desktop file / bash alias install/remove
        CronInstaller,                 # idempotent cron-line management
        advertise,                     # --advertise JSON helper
        skill_status,                  # is an installed Claude skill stale?
    )

See PROTOCOL.md for the full --advertise specification.
"""

from .tool_installer import ToolInstaller, ToolMetadata
from .cron_installer import CronInstaller
from .advertise import advertise
from .skills import (
    installed_skill_hash,
    read_installed_skill,
    skill_payload_hash,
    skill_status,
)

__all__ = [
    "ToolInstaller",
    "ToolMetadata",
    "CronInstaller",
    "advertise",
    "skill_status",
    "skill_payload_hash",
    "installed_skill_hash",
    "read_installed_skill",
]

__version__ = "0.1.1"
