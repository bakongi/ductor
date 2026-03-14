"""Role and capability definitions for authorization."""

from __future__ import annotations

import enum


class Role(enum.Enum):
    """User roles with descending privilege."""

    ADMIN = "admin"
    USER = "user"


class Cap:
    """Capability string constants.

    Each constant maps to a specific operational permission that can be
    checked against a principal's role.
    """

    MODEL_SELECT = "model.select"
    CRON_MANAGE = "cron.manage"
    SYSTEM_DIAGNOSE = "system.diagnose"
    CONFIG_MANAGE = "config.manage"
    SESSION_MANAGE = "session.manage"
    TASKS_MANAGE = "tasks.manage"
    AGENTS_MANAGE = "agents.manage"


ROLE_CAPABILITIES: dict[Role, frozenset[str]] = {
    Role.ADMIN: frozenset(
        {
            Cap.MODEL_SELECT,
            Cap.CRON_MANAGE,
            Cap.SYSTEM_DIAGNOSE,
            Cap.CONFIG_MANAGE,
            Cap.SESSION_MANAGE,
            Cap.TASKS_MANAGE,
            Cap.AGENTS_MANAGE,
        }
    ),
    Role.USER: frozenset(),
}
