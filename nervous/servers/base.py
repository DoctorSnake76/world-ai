"""Abstract base class shared by every MCP server."""

from abc import ABC, abstractmethod

from core.cascade.types import ToolCall, ToolDefinition, ToolResult


class BaseMCPServer(ABC):
    """Contract every MCP server must satisfy.

    Concrete servers implement:
      - ``name``                  → unique identifier used as a log/routing key
      - ``get_tool_definitions``  → JSON-Schema descriptions consumed by the LLM
      - ``execute_tool``          → async dispatch for a ``ToolCall``
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique server name (snake_case, e.g. 'filesystem', 'web')."""

    @abstractmethod
    def get_tool_definitions(self) -> list[ToolDefinition]:
        """Return all tools this server exposes to the agent."""

    @abstractmethod
    async def execute_tool(self, call: ToolCall) -> ToolResult:
        """Execute *call* and return a result.

        Must never raise — errors are encoded in ``ToolResult.is_error``.
        """
