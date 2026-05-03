"""Unit tests for MCPGateway — registry, routing, error handling, HTTP API."""

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from core.cascade.types import ToolCall, ToolDefinition, ToolResult
from nervous.gateway import MCPGateway, create_fastapi_app
from nervous.servers.base import BaseMCPServer
from nervous.servers.filesystem_mcp import FilesystemMCP
from nervous.servers.web_mcp import WebMCP


# ── Stub server for isolated gateway tests ────────────────────────────────────


class StubServer(BaseMCPServer):
    """Minimal server with a single 'stub_ping' tool for gateway tests."""

    def __init__(self, server_name: str = "stub", tool_name: str = "stub_ping") -> None:
        self._name = server_name
        self._tool_name = tool_name

    @property
    def name(self) -> str:
        return self._name

    def get_tool_definitions(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name=self._tool_name,
                description="Test stub.",
                parameters={"type": "object", "properties": {}, "required": []},
            )
        ]

    async def execute_tool(self, call: ToolCall) -> ToolResult:
        return ToolResult(
            tool_call_id=call.id,
            name=call.name,
            content=json.dumps({"pong": True, "server": self._name}),
        )


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def empty_gateway() -> MCPGateway:
    return MCPGateway(auto_register=False)


@pytest.fixture
def gateway_with_stub(empty_gateway: MCPGateway) -> MCPGateway:
    empty_gateway.register(StubServer())
    return empty_gateway


# ── Registration ──────────────────────────────────────────────────────────────


class TestRegistration:
    def test_register_server_appears_in_names(self, empty_gateway: MCPGateway) -> None:
        empty_gateway.register(StubServer("s1"))
        assert "s1" in empty_gateway.server_names

    def test_register_tools_indexed(self, empty_gateway: MCPGateway) -> None:
        empty_gateway.register(StubServer("s1", "tool_a"))
        assert "tool_a" in empty_gateway.tool_names

    def test_register_duplicate_server_raises(self, empty_gateway: MCPGateway) -> None:
        empty_gateway.register(StubServer("s1"))
        with pytest.raises(ValueError, match="already registered"):
            empty_gateway.register(StubServer("s1"))

    def test_register_duplicate_tool_raises(self, empty_gateway: MCPGateway) -> None:
        empty_gateway.register(StubServer("s1", "same_tool"))
        with pytest.raises(ValueError, match="already registered"):
            empty_gateway.register(StubServer("s2", "same_tool"))

    def test_unregister_removes_server(self, gateway_with_stub: MCPGateway) -> None:
        gateway_with_stub.unregister("stub")
        assert "stub" not in gateway_with_stub.server_names

    def test_unregister_removes_tools(self, gateway_with_stub: MCPGateway) -> None:
        gateway_with_stub.unregister("stub")
        assert "stub_ping" not in gateway_with_stub.tool_names

    def test_unregister_unknown_is_noop(self, empty_gateway: MCPGateway) -> None:
        empty_gateway.unregister("does_not_exist")  # must not raise


# ── Tool definitions aggregation ─────────────────────────────────────────────


class TestToolDefinitions:
    def test_empty_gateway_has_no_tools(self, empty_gateway: MCPGateway) -> None:
        assert empty_gateway.get_all_tool_definitions() == []

    def test_two_servers_tools_aggregated(self, empty_gateway: MCPGateway) -> None:
        empty_gateway.register(StubServer("a", "tool_a"))
        empty_gateway.register(StubServer("b", "tool_b"))
        names = {td.name for td in empty_gateway.get_all_tool_definitions()}
        assert names == {"tool_a", "tool_b"}

    def test_tools_sorted_by_name(self, empty_gateway: MCPGateway) -> None:
        empty_gateway.register(StubServer("z_server", "z_tool"))
        empty_gateway.register(StubServer("a_server", "a_tool"))
        tools = empty_gateway.get_all_tool_definitions()
        assert tools[0].name == "a_tool"
        assert tools[1].name == "z_tool"


# ── Tool dispatch ─────────────────────────────────────────────────────────────


class TestDispatch:
    async def test_dispatch_known_tool(self, gateway_with_stub: MCPGateway) -> None:
        call = ToolCall(id="abc", name="stub_ping", arguments={})
        result = await gateway_with_stub.execute_tool_call(call)
        assert not result.is_error
        data = json.loads(result.content)
        assert data["pong"] is True

    async def test_dispatch_unknown_tool_returns_error(
        self, empty_gateway: MCPGateway
    ) -> None:
        call = ToolCall(id="x", name="nonexistent_tool", arguments={})
        result = await empty_gateway.execute_tool_call(call)
        assert result.is_error
        data = json.loads(result.content)
        assert "Unknown tool" in data["error"]

    async def test_dispatch_to_correct_server(self, empty_gateway: MCPGateway) -> None:
        empty_gateway.register(StubServer("server_a", "tool_a"))
        empty_gateway.register(StubServer("server_b", "tool_b"))
        call = ToolCall(id="y", name="tool_b", arguments={})
        result = await empty_gateway.execute_tool_call(call)
        data = json.loads(result.content)
        assert data["server"] == "server_b"

    async def test_dispatch_propagates_tool_call_id(
        self, gateway_with_stub: MCPGateway
    ) -> None:
        call = ToolCall(id="unique-123", name="stub_ping", arguments={})
        result = await gateway_with_stub.execute_tool_call(call)
        assert result.tool_call_id == "unique-123"


# ── Auto-registration ─────────────────────────────────────────────────────────


class TestAutoRegister:
    def test_auto_register_includes_filesystem_and_web(
        self, tmp_path: Path
    ) -> None:
        # Patch sandbox root so FilesystemMCP doesn't try to create /data/user
        fs = FilesystemMCP(sandbox_root=str(tmp_path / "sandbox"))
        gw = MCPGateway(auto_register=False)
        gw.register(fs)
        gw.register(WebMCP(brave_api_key=""))
        assert "filesystem" in gw.server_names
        assert "web" in gw.server_names

    def test_auto_register_has_seven_tools(self, tmp_path: Path) -> None:
        fs = FilesystemMCP(sandbox_root=str(tmp_path / "sandbox"))
        gw = MCPGateway(auto_register=False)
        gw.register(fs)
        gw.register(WebMCP(brave_api_key=""))
        # 5 filesystem + 2 web = 7
        assert len(gw.get_all_tool_definitions()) == 7


# ── FastAPI HTTP layer ────────────────────────────────────────────────────────


class TestFastAPIApp:
    @pytest.fixture
    def client(self, tmp_path: Path) -> TestClient:
        gw = MCPGateway(auto_register=False)
        gw.register(StubServer("stub", "stub_ping"))
        app = create_fastapi_app(gateway=gw)
        return TestClient(app)

    def test_health_endpoint(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_tools_endpoint_returns_list(self, client: TestClient) -> None:
        resp = client.get("/tools")
        assert resp.status_code == 200
        tools = resp.json()
        assert isinstance(tools, list)
        assert any(t["name"] == "stub_ping" for t in tools)

    def test_execute_endpoint_known_tool(self, client: TestClient) -> None:
        payload = {"tool_call_id": "t1", "name": "stub_ping", "arguments": {}}
        resp = client.post("/execute", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_error"] is False
        assert json.loads(data["content"])["pong"] is True

    def test_execute_endpoint_unknown_tool_returns_422(
        self, client: TestClient
    ) -> None:
        payload = {"tool_call_id": "t2", "name": "nope", "arguments": {}}
        resp = client.post("/execute", json=payload)
        assert resp.status_code == 422

    def test_tools_endpoint_sorted(self, tmp_path: Path) -> None:
        gw = MCPGateway(auto_register=False)
        gw.register(StubServer("z", "z_tool"))
        gw.register(StubServer("a", "a_tool"))
        app = create_fastapi_app(gateway=gw)
        client = TestClient(app)
        resp = client.get("/tools")
        names = [t["name"] for t in resp.json()]
        assert names == sorted(names)
