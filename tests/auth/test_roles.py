"""Tests for Role enum and capability mappings."""

from __future__ import annotations

from ductor_bot.auth.roles import ROLE_CAPABILITIES, Cap, Role


def test_admin_has_all_capabilities() -> None:
    admin_caps = ROLE_CAPABILITIES[Role.ADMIN]
    assert Cap.MODEL_SELECT in admin_caps
    assert Cap.CRON_MANAGE in admin_caps
    assert Cap.SYSTEM_DIAGNOSE in admin_caps
    assert Cap.CONFIG_MANAGE in admin_caps
    assert Cap.SESSION_MANAGE in admin_caps
    assert Cap.TASKS_MANAGE in admin_caps
    assert Cap.AGENTS_MANAGE in admin_caps


def test_user_has_no_capabilities() -> None:
    user_caps = ROLE_CAPABILITIES[Role.USER]
    assert len(user_caps) == 0
    assert Cap.MODEL_SELECT not in user_caps


def test_role_values() -> None:
    assert Role.ADMIN.value == "admin"
    assert Role.USER.value == "user"


def test_capabilities_are_frozensets() -> None:
    for role in Role:
        assert isinstance(ROLE_CAPABILITIES[role], frozenset)
