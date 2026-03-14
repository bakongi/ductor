"""Tests for multiagent/internal_api.py: InternalAgentAPI HTTP endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp.test_utils import TestClient

from ductor_bot.multiagent.bus import InterAgentBus
from ductor_bot.multiagent.health import AgentHealth
from ductor_bot.multiagent.internal_api import InternalAgentAPI


@pytest.fixture
def bus() -> InterAgentBus:
    return InterAgentBus()


@pytest.fixture
def api(bus: InterAgentBus) -> InternalAgentAPI:
    return InternalAgentAPI(bus, port=0)


@pytest.fixture
async def client(api: InternalAgentAPI) -> TestClient:
    """Create aiohttp test client for the internal API."""
    from aiohttp.test_utils import TestServer

    server = TestServer(api._app)
    c = TestClient(server)
    await c.start_server()
    yield c
    await c.close()


class TestHandleSend:
    """Test POST /interagent/send."""

    async def test_send_success(self, client: TestClient, bus: InterAgentBus) -> None:
        stack = MagicMock()
        stack.bot.orchestrator = MagicMock()
        stack.bot.orchestrator.handle_interagent_message = AsyncMock(
            return_value=("OK", "ia-sender", "")
        )
        bus.register("target", stack)

        resp = await client.post(
            "/interagent/send",
            json={"from": "sender", "to": "target", "message": "Hello"},
        )
        assert resp.status == 200
        data = await resp.json()
        assert data["success"] is True
        assert data["text"] == "OK"

    async def test_send_missing_fields(self, client: TestClient) -> None:
        resp = await client.post(
            "/interagent/send",
            json={"from": "sender"},
        )
        assert resp.status == 400
        data = await resp.json()
        assert data["success"] is False
        assert "Missing" in data["error"]

    async def test_send_invalid_json(self, client: TestClient) -> None:
        resp = await client.post(
            "/interagent/send",
            data=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status == 400

    async def test_send_unknown_recipient(self, client: TestClient) -> None:
        resp = await client.post(
            "/interagent/send",
            json={"from": "sender", "to": "nonexistent", "message": "Hello"},
        )
        data = await resp.json()
        assert data["success"] is False
        assert "not found" in data["error"]


class TestHandleSendAsync:
    """Test POST /interagent/send_async."""

    async def test_send_async_success(self, client: TestClient, bus: InterAgentBus) -> None:
        stack = MagicMock()
        stack.bot.orchestrator = MagicMock()
        stack.bot.orchestrator.handle_interagent_message = AsyncMock(
            return_value=("OK", "ia-sender", "")
        )
        bus.register("target", stack)

        resp = await client.post(
            "/interagent/send_async",
            json={"from": "sender", "to": "target", "message": "Hello"},
        )
        assert resp.status == 200
        data = await resp.json()
        assert data["success"] is True
        assert "task_id" in data

    async def test_send_async_unknown_recipient(self, client: TestClient) -> None:
        resp = await client.post(
            "/interagent/send_async",
            json={"from": "sender", "to": "nonexistent", "message": "Hello"},
        )
        data = await resp.json()
        assert data["success"] is False
        assert "not found" in data["error"]

    async def test_send_async_missing_fields(self, client: TestClient) -> None:
        resp = await client.post(
            "/interagent/send_async",
            json={"from": "sender"},
        )
        assert resp.status == 400


class TestNewSessionFlag:
    """Test new_session flag in /interagent/send and /interagent/send_async."""

    async def test_send_passes_new_session_true(
        self, client: TestClient, bus: InterAgentBus
    ) -> None:
        stack = MagicMock()
        stack.bot.orchestrator = MagicMock()
        stack.bot.orchestrator.handle_interagent_message = AsyncMock(
            return_value=("OK", "ia-sender", "")
        )
        bus.register("target", stack)

        resp = await client.post(
            "/interagent/send",
            json={
                "from": "sender",
                "to": "target",
                "message": "Hello",
                "new_session": True,
            },
        )
        assert resp.status == 200
        stack.bot.orchestrator.handle_interagent_message.assert_awaited_once_with(
            "sender",
            "Hello",
            new_session=True,
        )

    async def test_send_defaults_new_session_false(
        self, client: TestClient, bus: InterAgentBus
    ) -> None:
        stack = MagicMock()
        stack.bot.orchestrator = MagicMock()
        stack.bot.orchestrator.handle_interagent_message = AsyncMock(
            return_value=("OK", "ia-sender", "")
        )
        bus.register("target", stack)

        resp = await client.post(
            "/interagent/send",
            json={"from": "sender", "to": "target", "message": "Hello"},
        )
        assert resp.status == 200
        stack.bot.orchestrator.handle_interagent_message.assert_awaited_once_with(
            "sender",
            "Hello",
            new_session=False,
        )

    async def test_send_async_passes_new_session(
        self, client: TestClient, bus: InterAgentBus
    ) -> None:
        stack = MagicMock()
        stack.bot.orchestrator = MagicMock()
        stack.bot.orchestrator.handle_interagent_message = AsyncMock(
            return_value=("OK", "ia-sender", "")
        )
        bus.register("target", stack)

        resp = await client.post(
            "/interagent/send_async",
            json={
                "from": "sender",
                "to": "target",
                "message": "Hello",
                "new_session": True,
            },
        )
        assert resp.status == 200
        data = await resp.json()
        assert data["success"] is True


class TestHandleList:
    """Test GET /interagent/agents."""

    async def test_list_empty(self, client: TestClient) -> None:
        resp = await client.get("/interagent/agents")
        assert resp.status == 200
        data = await resp.json()
        assert data["agents"] == []

    async def test_list_with_agents(self, client: TestClient, bus: InterAgentBus) -> None:
        bus.register("main", MagicMock())
        bus.register("sub1", MagicMock())

        resp = await client.get("/interagent/agents")
        data = await resp.json()
        assert set(data["agents"]) == {"main", "sub1"}


class TestHandleHealth:
    """Test GET /interagent/health."""

    async def test_health_no_ref(self, client: TestClient) -> None:
        resp = await client.get("/interagent/health")
        data = await resp.json()
        assert data["agents"] == {}

    async def test_health_with_agents(self, client: TestClient, api: InternalAgentAPI) -> None:
        h = AgentHealth(name="main")
        h.mark_running()
        api.set_health_ref({"main": h})

        resp = await client.get("/interagent/health")
        data = await resp.json()
        assert "main" in data["agents"]
        assert data["agents"]["main"]["status"] == "running"
        assert data["agents"]["main"]["restart_count"] == 0

    async def test_health_crashed_agent(self, client: TestClient, api: InternalAgentAPI) -> None:
        h = AgentHealth(name="sub1")
        h.mark_crashed("OOM")
        api.set_health_ref({"sub1": h})

        resp = await client.get("/interagent/health")
        data = await resp.json()
        assert data["agents"]["sub1"]["status"] == "crashed"
        assert data["agents"]["sub1"]["last_crash_error"] == "OOM"
        assert data["agents"]["sub1"]["restart_count"] == 1


class TestLifecycle:
    """Test InternalAgentAPI lifecycle return values."""

    async def test_start_returns_false_on_bind_error(self, api: InternalAgentAPI) -> None:
        from unittest.mock import patch

        with patch(
            "aiohttp.web.TCPSite.start",
            new_callable=AsyncMock,
            side_effect=OSError("bind failed"),
        ):
            started = await api.start()

        assert started is False


class TestDockerAuth:
    """Test Docker-mode token auth on InternalAgentAPI."""

    @pytest.fixture
    def docker_api(self, bus: InterAgentBus) -> InternalAgentAPI:
        return InternalAgentAPI(bus, port=0, docker_mode=True, token="secret-token")

    @pytest.fixture
    async def docker_client(self, docker_api: InternalAgentAPI) -> TestClient:
        from aiohttp.test_utils import TestServer

        server = TestServer(docker_api._app)
        c = TestClient(server)
        await c.start_server()
        yield c
        await c.close()

    async def test_no_token_returns_401(self, docker_client: TestClient) -> None:
        resp = await docker_client.get("/interagent/health")
        assert resp.status == 401
        data = await resp.json()
        assert data["error"] == "Unauthorized"

    async def test_wrong_token_returns_401(self, docker_client: TestClient) -> None:
        resp = await docker_client.get(
            "/interagent/health",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status == 401

    async def test_correct_token_succeeds(self, docker_client: TestClient) -> None:
        resp = await docker_client.get(
            "/interagent/health",
            headers={"Authorization": "Bearer secret-token"},
        )
        assert resp.status == 200

    async def test_localhost_api_no_auth_needed(self, client: TestClient) -> None:
        """Localhost-bound API (no docker_mode) does not require token."""
        resp = await client.get("/interagent/health")
        assert resp.status == 200
