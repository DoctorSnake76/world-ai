"""Unit tests for core/cascade/agent.py.

The OpenRouterClient is mocked so no real HTTP calls are made.
"""

import pytest
from dataclasses import replace
from unittest.mock import AsyncMock, patch

from core.cascade.agent import CascadeAgent, _DEFAULT_SYSTEM_PROMPT
from core.cascade.types import (
    AgentResponse,
    Message,
    MessageRole,
    ToolCall,
    ToolDefinition,
    UserRequest,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def simple_request() -> UserRequest:
    return UserRequest(
        messages=[Message(role=MessageRole.USER, content="What is the capital of France?")]
    )


@pytest.fixture
def request_with_tools() -> UserRequest:
    return UserRequest(
        messages=[Message(role=MessageRole.USER, content="Search for AI news today.")],
        available_tools=[
            ToolDefinition(
                name="web_search",
                description="Search the web",
                parameters={"type": "object", "properties": {"query": {"type": "string"}}},
            )
        ],
    )


@pytest.fixture
def good_response() -> AgentResponse:
    return AgentResponse(
        content="Paris is the capital of France. It has been the capital since 987 AD.",
        model_slug="deepseek/deepseek-chat",
        tokens_in=15,
        tokens_out=20,
    )


@pytest.fixture
def poor_response() -> AgentResponse:
    """A short refusal — evaluator will score this near 0."""
    return AgentResponse(
        content="I'm not able to help with that.",
        model_slug="deepseek/deepseek-chat",
        tokens_in=5,
        tokens_out=8,
    )


@pytest.fixture
def error_response() -> AgentResponse:
    return AgentResponse(content="", error="HTTP 429: Rate limited")


@pytest.fixture
def frontier_response() -> AgentResponse:
    return AgentResponse(
        content=(
            "Paris is the capital and most populous city of France, "
            "with a population of over 2 million in the city proper."
        ),
        model_slug="anthropic/claude-opus-4-6",
        tokens_in=30,
        tokens_out=40,
        escalated=True,
    )


def make_agent(mock_complete) -> CascadeAgent:
    """Create a CascadeAgent with a mocked OpenRouterClient."""
    mock_client = AsyncMock()
    mock_client.complete = mock_complete
    return CascadeAgent(openrouter_client=mock_client)


# ── Basic pipeline ────────────────────────────────────────────────────────────


class TestCascadeAgentBasic:
    @pytest.mark.asyncio
    async def test_returns_agent_response(self, simple_request, good_response):
        agent = make_agent(AsyncMock(return_value=good_response))
        result = await agent.process(simple_request)
        assert isinstance(result, AgentResponse)

    @pytest.mark.asyncio
    async def test_response_content_preserved(self, simple_request, good_response):
        agent = make_agent(AsyncMock(return_value=good_response))
        result = await agent.process(simple_request)
        assert result.content == good_response.content

    @pytest.mark.asyncio
    async def test_confidence_score_attached(self, simple_request, good_response):
        agent = make_agent(AsyncMock(return_value=good_response))
        result = await agent.process(simple_request)
        assert 0.0 <= result.confidence_score <= 1.0

    @pytest.mark.asyncio
    async def test_quality_score_attached(self, simple_request, good_response):
        agent = make_agent(AsyncMock(return_value=good_response))
        result = await agent.process(simple_request)
        assert 0.0 <= result.quality_score <= 1.0

    @pytest.mark.asyncio
    async def test_good_response_not_escalated(self, simple_request, good_response):
        agent = make_agent(AsyncMock(return_value=good_response))
        result = await agent.process(simple_request)
        assert not result.escalated


# ── System prompt injection ───────────────────────────────────────────────────


class TestSystemPromptInjection:
    @pytest.mark.asyncio
    async def test_default_system_prompt_injected_when_none(self, simple_request, good_response):
        captured: list[UserRequest] = []

        async def capture(req: UserRequest, model, **_):
            captured.append(req)
            return good_response

        agent = make_agent(capture)
        await agent.process(simple_request)

        assert captured[0].system_prompt == _DEFAULT_SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_existing_system_prompt_not_overwritten(self, simple_request, good_response):
        request = replace(simple_request, system_prompt="Custom prompt.")
        captured: list[UserRequest] = []

        async def capture(req: UserRequest, model, **_):
            captured.append(req)
            return good_response

        agent = make_agent(capture)
        await agent.process(request)

        assert captured[0].system_prompt == "Custom prompt."


# ── Escalation logic ──────────────────────────────────────────────────────────


class TestMASEscalation:
    @pytest.mark.asyncio
    async def test_poor_quality_triggers_escalation(
        self, simple_request, poor_response, frontier_response
    ):
        mock_complete = AsyncMock(side_effect=[poor_response, frontier_response])
        agent = make_agent(mock_complete)
        result = await agent.process(simple_request)

        assert result.escalated
        assert mock_complete.call_count == 2

    @pytest.mark.asyncio
    async def test_error_response_triggers_escalation(
        self, simple_request, error_response, frontier_response
    ):
        mock_complete = AsyncMock(side_effect=[error_response, frontier_response])
        agent = make_agent(mock_complete)
        result = await agent.process(simple_request)

        assert result.escalated

    @pytest.mark.asyncio
    async def test_good_response_no_escalation(self, simple_request, good_response):
        mock_complete = AsyncMock(return_value=good_response)
        agent = make_agent(mock_complete)
        await agent.process(simple_request)

        assert mock_complete.call_count == 1

    @pytest.mark.asyncio
    async def test_escalated_response_has_quality_score(
        self, simple_request, poor_response, frontier_response
    ):
        mock_complete = AsyncMock(side_effect=[poor_response, frontier_response])
        agent = make_agent(mock_complete)
        result = await agent.process(simple_request)

        assert result.quality_score > 0.0

    @pytest.mark.asyncio
    async def test_escalated_response_retains_confidence_score(
        self, simple_request, poor_response, frontier_response
    ):
        mock_complete = AsyncMock(side_effect=[poor_response, frontier_response])
        agent = make_agent(mock_complete)
        result = await agent.process(simple_request)

        assert result.confidence_score > 0.0


# ── Tool-calling pass-through ─────────────────────────────────────────────────


class TestToolCalling:
    @pytest.mark.asyncio
    async def test_tool_calls_returned_in_response(
        self, request_with_tools, good_response
    ):
        response_with_tool = replace(
            good_response,
            tool_calls=[ToolCall(id="tc1", name="web_search", arguments={"query": "AI news"})],
        )
        agent = make_agent(AsyncMock(return_value=response_with_tool))
        result = await agent.process(request_with_tools)

        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "web_search"

    @pytest.mark.asyncio
    async def test_no_escalation_when_tool_calls_present(
        self, request_with_tools, good_response
    ):
        response_with_tool = replace(
            good_response,
            content="",
            tool_calls=[ToolCall(id="tc1", name="web_search", arguments={"query": "AI"})],
        )
        mock_complete = AsyncMock(return_value=response_with_tool)
        agent = make_agent(mock_complete)
        await agent.process(request_with_tools)

        assert mock_complete.call_count == 1
