"""Command registry and OrchestratorResult."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel

from ductor_bot.orchestrator.selectors.models import ButtonGrid

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ductor_bot.auth.audit import AuditLog
    from ductor_bot.auth.principal import Principal
    from ductor_bot.auth.service import AuthorizationService
    from ductor_bot.orchestrator.core import Orchestrator
    from ductor_bot.session.key import SessionKey

CommandHandler = Callable[
    ["Orchestrator", "SessionKey", str], Awaitable["OrchestratorResult | None"]
]


class OrchestratorResult(BaseModel):
    """Structured return from handle_message."""

    text: str
    stream_fallback: bool = False
    buttons: ButtonGrid | None = None
    model_name: str | None = None
    total_tokens: int = 0
    input_tokens: int = 0
    cost_usd: float = 0.0
    duration_ms: float | None = None


@dataclass(frozen=True, slots=True)
class _CommandEntry:
    name: str
    handler: CommandHandler
    match_prefix: bool
    required_capability: str | None


class CommandRegistry:
    """Registry of slash commands with async dispatch."""

    def __init__(
        self,
        *,
        authz: AuthorizationService | None = None,
        audit_log: AuditLog | None = None,
    ) -> None:
        self._commands: list[_CommandEntry] = []
        self._authz = authz
        self._audit_log = audit_log

    def register_async(
        self,
        name: str,
        handler: CommandHandler,
        *,
        capability: str | None = None,
    ) -> None:
        self._commands.append(
            _CommandEntry(
                name=name,
                handler=handler,
                match_prefix=name.endswith(" "),
                required_capability=capability,
            )
        )

    async def dispatch(
        self,
        cmd: str,
        orch: Orchestrator,
        key: SessionKey,
        text: str,
        *,
        principal: Principal | None = None,
    ) -> OrchestratorResult | None:
        """Dispatch *cmd* to a registered handler. Returns None if unknown.

        Strips ``@botname`` suffixes so group commands like
        ``/status@mybot`` match the registered ``/status`` entry.
        """
        # Normalize: "/status@mybot args" -> "/status args"
        parts = cmd.split(None, 1)
        if parts and "@" in parts[0]:
            parts[0] = parts[0].split("@", 1)[0]
            cmd = " ".join(parts)

        for entry in self._commands:
            if entry.match_prefix:
                if not cmd.startswith(entry.name):
                    continue
            elif cmd != entry.name:
                continue

            logger.debug("Command matched cmd=%s", entry.name)

            # Capability enforcement
            if (
                entry.required_capability
                and self._authz is not None
                and principal is not None
                and not self._authz.check(principal, entry.required_capability)
            ):
                if self._audit_log:
                    self._audit_log.log(
                        principal=principal.principal_id,
                        action="access_denied",
                        target=entry.name,
                        details={"capability": entry.required_capability},
                        result="denied",
                    )
                return OrchestratorResult(text="This command requires admin access.")

            if self._audit_log and principal is not None:
                self._audit_log.log(
                    principal=principal.principal_id,
                    action="command_executed",
                    target=entry.name,
                )

            return await entry.handler(orch, key, text)
        return None
