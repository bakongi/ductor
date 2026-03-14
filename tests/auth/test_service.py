"""Tests for AuthorizationService."""

from __future__ import annotations

import time

import pytest

from ductor_bot.auth.principal import Principal
from ductor_bot.auth.roles import Cap, Role
from ductor_bot.auth.service import AuthorizationService
from ductor_bot.config import AgentConfig


def _make_config(**overrides: object) -> AgentConfig:
    return AgentConfig(**overrides)


def test_legacy_mode_all_admin() -> None:
    """With no admin_ids, everyone is ADMIN (backward compat)."""
    config = _make_config()
    authz = AuthorizationService(config)
    assert authz.legacy_mode is True

    user = Principal.telegram(999)
    assert authz.resolve_role(user) == Role.ADMIN
    assert authz.has_capability(user, Cap.MODEL_SELECT) is True


def test_admin_resolution() -> None:
    config = _make_config(admin_ids=[100, 200])
    authz = AuthorizationService(config)
    assert authz.legacy_mode is False

    admin = Principal.telegram(100)
    assert authz.resolve_role(admin) == Role.ADMIN
    assert authz.has_capability(admin, Cap.MODEL_SELECT) is True

    user = Principal.telegram(999)
    assert authz.resolve_role(user) == Role.USER
    assert authz.has_capability(user, Cap.MODEL_SELECT) is False


def test_system_principal_is_admin() -> None:
    config = _make_config(admin_ids=[100])
    authz = AuthorizationService(config)
    sys = Principal.system()
    assert authz.resolve_role(sys) == Role.ADMIN


def test_check_logs_denial() -> None:
    config = _make_config(admin_ids=[100])
    authz = AuthorizationService(config)
    user = Principal.telegram(999)
    assert authz.check(user, Cap.MODEL_SELECT) is False


def test_matrix_admin_resolution() -> None:
    from ductor_bot.config import MatrixConfig

    config = _make_config(matrix=MatrixConfig(admin_users=["@admin:server.com"]))
    authz = AuthorizationService(config)
    assert authz.legacy_mode is False

    admin = Principal.matrix("@admin:server.com")
    assert authz.resolve_role(admin) == Role.ADMIN

    user = Principal.matrix("@random:server.com")
    assert authz.resolve_role(user) == Role.USER


def test_rate_limit_exempt_for_admins() -> None:
    config = _make_config(admin_ids=[100], rate_limit_per_minute=1)
    authz = AuthorizationService(config)
    admin = Principal.telegram(100)
    # Should never be rate limited
    for _ in range(50):
        assert authz.check_rate_limit(admin) is True


def test_rate_limit_enforced_for_users() -> None:
    config = _make_config(admin_ids=[100], rate_limit_per_minute=3)
    authz = AuthorizationService(config)
    user = Principal.telegram(999)
    assert authz.check_rate_limit(user) is True
    assert authz.check_rate_limit(user) is True
    assert authz.check_rate_limit(user) is True
    assert authz.check_rate_limit(user) is False


def test_rate_limit_disabled_when_zero() -> None:
    config = _make_config(admin_ids=[100], rate_limit_per_minute=0)
    authz = AuthorizationService(config)
    user = Principal.telegram(999)
    for _ in range(100):
        assert authz.check_rate_limit(user) is True


def test_hot_reload_updates_config() -> None:
    config1 = _make_config(admin_ids=[100])
    authz = AuthorizationService(config1)
    user = Principal.telegram(200)
    assert authz.resolve_role(user) == Role.USER

    config2 = _make_config(admin_ids=[100, 200])
    authz.update_from_config(config2)
    assert authz.resolve_role(user) == Role.ADMIN
