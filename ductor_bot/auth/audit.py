"""Append-only JSONL audit log for authorization and command events."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AuditLog:
    """Append-only audit log writing JSONL to ``~/.ductor/logs/audit.jsonl``.

    Each entry contains: ``ts``, ``principal``, ``action``, ``target``,
    ``details``, ``result``.

    The log is best-effort: I/O failures are logged but never raised.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def log(
        self,
        *,
        principal: str,
        action: str,
        target: str = "",
        details: dict[str, Any] | None = None,
        result: str = "ok",
    ) -> None:
        """Append a single audit entry."""
        entry = {
            "ts": time.time(),
            "principal": principal,
            "action": action,
            "target": target,
            "details": details or {},
            "result": result,
        }
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, separators=(",", ":")) + "\n")
        except OSError:
            logger.warning("Audit log write failed", exc_info=True)

    def read_all(self) -> list[dict[str, Any]]:
        """Read all entries (for testing and diagnostics)."""
        if not self._path.exists():
            return []
        entries: list[dict[str, Any]] = []
        try:
            with self._path.open(encoding="utf-8") as f:
                for raw_line in f:
                    stripped = raw_line.strip()
                    if stripped:
                        entries.append(json.loads(stripped))
        except (OSError, json.JSONDecodeError):
            logger.warning("Audit log read failed", exc_info=True)
        return entries
