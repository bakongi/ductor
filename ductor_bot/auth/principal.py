"""Principal identity: frozen value object representing an authenticated actor."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Principal:
    """Immutable identity of an authenticated actor.

    ``principal_id`` is the canonical string form used for logging,
    audit, and session ownership (e.g. ``"tg:12345"``, ``"mx:@user:server"``).
    """

    principal_id: str
    transport: str
    raw_id: str
    display_name: str = ""

    # -- Factory classmethods --------------------------------------------------

    @classmethod
    def telegram(cls, user_id: int, display_name: str = "") -> Principal:
        """Create a Telegram principal."""
        return cls(
            principal_id=f"tg:{user_id}",
            transport="tg",
            raw_id=str(user_id),
            display_name=display_name,
        )

    @classmethod
    def matrix(cls, mxid: str, display_name: str = "") -> Principal:
        """Create a Matrix principal."""
        return cls(
            principal_id=f"mx:{mxid}",
            transport="mx",
            raw_id=mxid,
            display_name=display_name,
        )

    @classmethod
    def api(cls, label: str = "ws-client") -> Principal:
        """Create an API (WebSocket) principal."""
        return cls(
            principal_id=f"api:{label}",
            transport="api",
            raw_id=label,
        )

    @classmethod
    def system(cls) -> Principal:
        """Create a system principal (internal operations)."""
        return cls(
            principal_id="system",
            transport="system",
            raw_id="system",
        )

    @classmethod
    def parse(cls, principal_id_str: str) -> Principal:
        """Reconstruct a Principal from its string form.

        Handles ``"tg:12345"``, ``"mx:@user:server"``, ``"api:label"``,
        and ``"system"``.
        """
        if principal_id_str == "system":
            return cls.system()
        if ":" not in principal_id_str:
            return cls(
                principal_id=principal_id_str,
                transport="unknown",
                raw_id=principal_id_str,
            )
        transport, _, raw_id = principal_id_str.partition(":")
        return cls(
            principal_id=principal_id_str,
            transport=transport,
            raw_id=raw_id,
        )
