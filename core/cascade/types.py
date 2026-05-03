"""Shared data types for the Agent Cascade pipeline."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None  # required when role == TOOL


@dataclass
class ToolDefinition:
    """Describes a tool the agent can invoke (JSON Schema format)."""

    name: str
    description: str
    parameters: dict[str, Any]  # standard JSON Schema object


@dataclass
class ToolCall:
    """A tool invocation requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolResult:
    """Result of executing a tool call."""

    tool_call_id: str
    name: str
    content: str
    is_error: bool = False


@dataclass
class UserRequest:
    """Everything the cascade needs to process one turn."""

    messages: list[Message]
    available_tools: list[ToolDefinition] = field(default_factory=list)
    system_prompt: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def last_user_content(self) -> str:
        """Return the content of the most recent user message."""
        for msg in reversed(self.messages):
            if msg.role == MessageRole.USER:
                return msg.content
        return ""

    @property
    def conversation_depth(self) -> int:
        """Number of messages in the conversation history."""
        return len(self.messages)


@dataclass
class AgentResponse:
    """Output produced by a single cascade pass."""

    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    model_slug: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_eur: float = 0.0
    latency_ms: float = 0.0
    confidence_score: float = 0.0   # routing decision score
    quality_score: float = 0.0      # post-response evaluation score
    escalated: bool = False          # True when MAS escalation was triggered
    error: Optional[str] = None
