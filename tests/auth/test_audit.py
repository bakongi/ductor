"""Tests for AuditLog JSONL output."""

from __future__ import annotations

from pathlib import Path

from ductor_bot.auth.audit import AuditLog


def test_log_and_read(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "audit.jsonl")
    log.log(
        principal="tg:123",
        action="command_executed",
        target="/status",
    )
    log.log(
        principal="tg:456",
        action="access_denied",
        target="/model",
        details={"capability": "model.select"},
        result="denied",
    )
    entries = log.read_all()
    assert len(entries) == 2
    assert entries[0]["principal"] == "tg:123"
    assert entries[0]["action"] == "command_executed"
    assert entries[0]["target"] == "/status"
    assert entries[0]["result"] == "ok"
    assert "ts" in entries[0]

    assert entries[1]["principal"] == "tg:456"
    assert entries[1]["result"] == "denied"
    assert entries[1]["details"]["capability"] == "model.select"


def test_read_empty(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "missing.jsonl")
    assert log.read_all() == []


def test_creates_parent_dirs(tmp_path: Path) -> None:
    log = AuditLog(tmp_path / "sub" / "dir" / "audit.jsonl")
    log.log(principal="tg:1", action="test")
    assert (tmp_path / "sub" / "dir" / "audit.jsonl").exists()


def test_jsonl_format(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    log = AuditLog(path)
    log.log(principal="tg:1", action="a")
    log.log(principal="tg:2", action="b")

    lines = path.read_text().strip().split("\n")
    assert len(lines) == 2
    # Each line should be valid JSON (verified by read_all)
    entries = log.read_all()
    assert len(entries) == 2
