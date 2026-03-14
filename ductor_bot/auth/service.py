"""Authorization service: role resolution, capability checks, rate limiting."""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import TYPE_CHECKING

from ductor_bot.auth.principal import Principal
from ductor_bot.auth.roles import ROLE_CAPABILITIES, Role

if TYPE_CHECKING:
    from ductor_bot.config import AgentConfig

logger = logging.getLogger(__name__)

_DEFAULT_RATE_LIMIT = 30
_RATE_WINDOW_SECONDS = 60.0


class AuthorizationService:
    """Resolves principal → role → capabilities with rate limiting.

    When ``admin_ids`` is empty the service runs in **legacy mode**:
    every principal is treated as ADMIN for full backward compatibility.
    """

    def __init__(self, config: AgentConfig) -> None:
        self._admin_ids: set[str] = set()
        self._rate_limit: int = _DEFAULT_RATE_LIMIT
        self._rate_windows: dict[str, deque[float]] = {}
        self.update_from_config(config)

    @property
    def legacy_mode(self) -> bool:
        """True when no admin_ids are configured (all users = ADMIN)."""
        return len(self._admin_ids) == 0

    def update_from_config(self, config: AgentConfig) -> None:
        """Refresh admin list and rate limit from config (hot-reload safe)."""
        self._admin_ids = set()
        for uid in config.admin_ids:
            self._admin_ids.add(f"tg:{uid}")
        for mxid in config.matrix.admin_users:
            self._admin_ids.add(f"mx:{mxid}")
        self._rate_limit = config.rate_limit_per_minute
        logger.debug(
            "AuthorizationService updated: %d admins, rate_limit=%d/min",
            len(self._admin_ids),
            self._rate_limit,
        )

    def resolve_role(self, principal: Principal) -> Role:
        """Determine the role for a principal."""
        if self.legacy_mode:
            return Role.ADMIN
        if principal.principal_id in self._admin_ids:
            return Role.ADMIN
        if principal.transport == "system":
            return Role.ADMIN
        return Role.USER

    def has_capability(self, principal: Principal, capability: str) -> bool:
        """Check if *principal* has *capability*."""
        role = self.resolve_role(principal)
        return capability in ROLE_CAPABILITIES[role]

    def check(self, principal: Principal, capability: str) -> bool:
        """Check capability and return True if allowed, False if denied."""
        allowed = self.has_capability(principal, capability)
        if not allowed:
            logger.info(
                "Access denied: principal=%s capability=%s",
                principal.principal_id,
                capability,
            )
        return allowed

    def check_rate_limit(self, principal: Principal) -> bool:
        """Return True if the request is within rate limits.

        Admins are exempt. A rate limit of 0 disables limiting entirely.
        """
        if self._rate_limit <= 0:
            return True
        if self.resolve_role(principal) == Role.ADMIN:
            return True

        now = time.monotonic()
        window = self._rate_windows.get(principal.principal_id)
        if window is None:
            window = deque()
            self._rate_windows[principal.principal_id] = window

        # Evict entries outside the window
        cutoff = now - _RATE_WINDOW_SECONDS
        while window and window[0] < cutoff:
            window.popleft()

        if len(window) >= self._rate_limit:
            logger.warning(
                "Rate limit exceeded: principal=%s count=%d limit=%d",
                principal.principal_id,
                len(window),
                self._rate_limit,
            )
            return False

        window.append(now)
        return True
