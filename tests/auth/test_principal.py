"""Tests for Principal identity value object."""

from __future__ import annotations

from ductor_bot.auth.principal import Principal


def test_telegram_factory() -> None:
    p = Principal.telegram(12345, "Alice")
    assert p.principal_id == "tg:12345"
    assert p.transport == "tg"
    assert p.raw_id == "12345"
    assert p.display_name == "Alice"


def test_matrix_factory() -> None:
    p = Principal.matrix("@user:server.com")
    assert p.principal_id == "mx:@user:server.com"
    assert p.transport == "mx"
    assert p.raw_id == "@user:server.com"


def test_api_factory() -> None:
    p = Principal.api()
    assert p.principal_id == "api:ws-client"
    assert p.transport == "api"

    p2 = Principal.api("custom")
    assert p2.principal_id == "api:custom"


def test_system_factory() -> None:
    p = Principal.system()
    assert p.principal_id == "system"
    assert p.transport == "system"


def test_parse_telegram() -> None:
    p = Principal.parse("tg:99")
    assert p.transport == "tg"
    assert p.raw_id == "99"
    assert p.principal_id == "tg:99"


def test_parse_matrix() -> None:
    p = Principal.parse("mx:@bob:example.com")
    assert p.transport == "mx"
    assert p.raw_id == "@bob:example.com"


def test_parse_system() -> None:
    p = Principal.parse("system")
    assert p.transport == "system"
    assert p.raw_id == "system"


def test_parse_unknown() -> None:
    p = Principal.parse("foobar")
    assert p.transport == "unknown"
    assert p.raw_id == "foobar"


def test_frozen_equality() -> None:
    a = Principal.telegram(1)
    b = Principal.telegram(1)
    assert a == b
    assert hash(a) == hash(b)


def test_frozen_inequality() -> None:
    a = Principal.telegram(1)
    b = Principal.telegram(2)
    assert a != b
