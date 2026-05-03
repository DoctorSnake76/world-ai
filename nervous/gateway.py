"""MCP Gateway — central tool registry and dispatcher.

The gateway aggregates tools from every registered ``BaseMCPServer`` and
provides a single entry point for the agent to:
  1. Discover available tools  →  ``get_all_tool_definitions()``
  2. Execute a tool call       →  ``execute_tool_call(call)``

Optional FastAPI integration
────────────────────────────
Call ``create_fastapi_app()`` to get a mountable ASGI app that exposes:
  GET  /tools     → list of all tool definitions (JSON)
  POST /execute   → execute a tool call, return a ToolResult (JSON)

Usage (standalone HTTP):
  uvicorn nervous.gateway:app --host 0.0.0.0 --port 8010

Usage (in-process, tests):
  gateway = MCPGateway()
  gateway.register(FilesystemMCP())
  gateway.register(WebMCP())
  result = await gateway.execute_tool_call(call)
"""

import json
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from core.cascade.types import ToolCall, ToolDefinition, ToolResult

from .servers.base import BaseMCPServer
from .servers.filesystem_mcp import FilesystemMCP
from .servers.web_mcp import WebMCP

logger = structlog.get_logger(__name__)


# ── Pydantic models for the HTTP API ─────────────────────────────────────────


class ExecuteRequest(BaseModel):
    """Payload for POST /execute."""

    tool_call_id: str
    name: str
    arguments: dict[str, Any] = {}


class ToolDefinitionSchema(BaseModel):
    """Serialisable form of ToolDefinition for the HTTP API."""

    name: str
    description: str
    parameters: dict[str, Any]


class ToolResultSchema(BaseModel):
    """Serialisable form of ToolResult for the HTTP API."""

    tool_call_id: str
    name: str
    content: str
    is_error: bool


# ── Gateway ───────────────────────────────────────────────────────────────────


class MCPGateway:
    """Aggregates and routes tool calls across registered MCP servers.

    Args:
        auto_register: When *True* (default), automatically registers
                       ``FilesystemMCP`` and ``WebMCP`` at construction time.
    """

    def __init__(self, auto_register: bool = True) -> None:
        self._servers: dict[str, BaseMCPServer] = {}
        # tool_name → server_name for O(1) routing
        self._tool_index: dict[str, str] = {}

        if auto_register:
            self.register(FilesystemMCP())
            self.register(WebMCP())

    # ── Registry ─────────────────────────────────────────────────────────────

    def register(self, server: BaseMCPServer) -> None:
        """Add *server* to the gateway and index its tools.

        Raises ``ValueError`` on duplicate server name or duplicate tool name.
        """
        if server.name in self._servers:
            raise ValueError(f"Server '{server.name}' is already registered")

        for td in server.get_tool_definitions():
            if td.name in self._tool_index:
                existing = self._tool_index[td.name]
                raise ValueError(
                    f"Tool '{td.name}' already registered by server '{existing}'"
                )
            self._tool_index[td.name] = server.name

        self._servers[server.name] = server
        logger.info(
            "gateway_server_registered",
            server=server.name,
            tools=[td.name for td in server.get_tool_definitions()],
        )

    def unregister(self, server_name: str) -> None:
        """Remove a server and all its tools from the registry."""
        server = self._servers.pop(server_name, None)
        if server is None:
            return
        for td in server.get_tool_definitions():
            self._tool_index.pop(td.name, None)
        logger.info("gateway_server_unregistered", server=server_name)

    # ── Public API ────────────────────────────────────────────────────────────

    def get_all_tool_definitions(self) -> list[ToolDefinition]:
        """Return tool definitions from all registered servers (sorted by name)."""
        tools: list[ToolDefinition] = []
        for server in self._servers.values():
            tools.extend(server.get_tool_definitions())
        return sorted(tools, key=lambda td: td.name)

    async def execute_tool_call(self, call: ToolCall) -> ToolResult:
        """Dispatch *call* to the owning server; never raises.

        Returns a ``ToolResult`` with ``is_error=True`` if the tool is unknown
        or the owning server is no longer registered.
        """
        server_name = self._tool_index.get(call.name)
        if server_name is None:
            logger.warning("gateway_unknown_tool", tool=call.name)
            return ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps(
                    {
                        "error": f"Unknown tool '{call.name}'. "
                        f"Available: {sorted(self._tool_index.keys())}"
                    }
                ),
                is_error=True,
            )

        server = self._servers[server_name]
        logger.info("gateway_dispatch", tool=call.name, server=server_name)
        return await server.execute_tool(call)

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def server_names(self) -> list[str]:
        return list(self._servers.keys())

    @property
    def tool_names(self) -> list[str]:
        return sorted(self._tool_index.keys())


# ── FastAPI application ───────────────────────────────────────────────────────

_gateway_singleton: MCPGateway | None = None


def _get_gateway() -> MCPGateway:
    global _gateway_singleton
    if _gateway_singleton is None:
        _gateway_singleton = MCPGateway(auto_register=True)
    return _gateway_singleton


def create_fastapi_app(gateway: MCPGateway | None = None) -> FastAPI:
    """Build and return the FastAPI ASGI app.

    Args:
        gateway: Use a custom gateway (e.g. for tests). Uses the auto-configured
                 singleton when *None*.
    """
    _gw = gateway or _get_gateway()
    app = FastAPI(
        title="World AI — MCP Gateway",
        description="Central dispatcher for all MCP tool servers.",
        version="0.1.0",
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "servers": str(_gw.server_names)}

    @app.get("/tools", response_model=list[ToolDefinitionSchema])
    async def list_tools() -> list[ToolDefinitionSchema]:
        """Return all available tool definitions."""
        return [
            ToolDefinitionSchema(
                name=td.name,
                description=td.description,
                parameters=td.parameters,
            )
            for td in _gw.get_all_tool_definitions()
        ]

    @app.post("/execute", response_model=ToolResultSchema)
    async def execute(req: ExecuteRequest) -> ToolResultSchema:
        """Execute a tool call and return the result."""
        call = ToolCall(id=req.tool_call_id, name=req.name, arguments=req.arguments)
        result = await _gw.execute_tool_call(call)
        if result.is_error:
            raise HTTPException(status_code=422, detail=json.loads(result.content))
        return ToolResultSchema(
            tool_call_id=result.tool_call_id,
            name=result.name,
            content=result.content,
            is_error=result.is_error,
        )

    return app


# Mountable app instance (used by uvicorn / docker-compose)
app = create_fastapi_app()
