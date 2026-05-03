"""Unit tests for core/cascade/evaluator.py."""

import pytest

from core.cascade.evaluator import (
    _error_factor,
    _length_adequacy,
    _refusal_factor,
    _tool_usage_factor,
    _truncation_factor,
    evaluate_response,
)
from core.cascade.types import AgentResponse, Message, MessageRole, ToolDefinition, UserRequest


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def simple_request() -> UserRequest:
    return UserRequest(
        messages=[Message(role=MessageRole.USER, content="What is the capital of France?")]
    )


@pytest.fixture
def long_request() -> UserRequest:
    content = "Explain in detail the entire history of the Roman Empire." * 5
    return UserRequest(messages=[Message(role=MessageRole.USER, content=content)])


@pytest.fixture
def request_with_tools() -> UserRequest:
    return UserRequest(
        messages=[Message(role=MessageRole.USER, content="Search for recent AI news.")],
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
    )


@pytest.fixture
def empty_response() -> AgentResponse:
    return AgentResponse(content="", model_slug="deepseek/deepseek-chat")


@pytest.fixture
def refusal_response() -> AgentResponse:
    return AgentResponse(
        content="I'm not able to help with that request.",
        model_slug="deepseek/deepseek-chat",
    )


@pytest.fixture
def error_response() -> AgentResponse:
    return AgentResponse(content="", error="HTTP 429: Rate limited")


# ── _length_adequacy ──────────────────────────────────────────────────────────


class TestLengthAdequacy:
    def test_long_response_to_short_request_returns_one(self, simple_request, good_response):
        assert _length_adequacy(simple_request, good_response) == 1.0

    def test_empty_response_to_any_request_returns_low(self, simple_request, empty_response):
        score = _length_adequacy(simple_request, empty_response)
        assert score < 0.1

    def test_empty_request_with_content_response_returns_one(self, empty_response):
        req = UserRequest(messages=[Message(role=MessageRole.USER, content="")])
        resp = AgentResponse(content="This is a reply.", model_slug="x")
        assert _length_adequacy(req, resp) == 1.0

    def test_empty_request_and_empty_response_returns_half(self):
        req = UserRequest(messages=[Message(role=MessageRole.USER, content="")])
        resp = AgentResponse(content="", model_slug="x")
        assert _length_adequacy(req, resp) == pytest.approx(0.5)

    def test_score_capped_at_one(self, simple_request):
        resp = AgentResponse(content="x" * 10_000, model_slug="x")
        assert _length_adequacy(simple_request, resp) == 1.0


# ── _refusal_factor ───────────────────────────────────────────────────────────


class TestRefusalFactor:
    def test_normal_response_no_penalty(self, good_response):
        assert _refusal_factor(good_response) == 1.0

    def test_refusal_phrase_penalized(self, refusal_response):
        assert _refusal_factor(refusal_response) == pytest.approx(0.3)

    def test_as_an_ai_penalized(self):
        resp = AgentResponse(content="As an AI, I cannot...", model_slug="x")
        assert _refusal_factor(resp) == pytest.approx(0.3)

    def test_i_cannot_provide_penalized(self):
        resp = AgentResponse(content="I cannot provide that information.", model_slug="x")
        assert _refusal_factor(resp) == pytest.approx(0.3)

    def test_partial_match_does_not_trigger(self):
        resp = AgentResponse(content="The study is unable to conclude.", model_slug="x")
        assert _refusal_factor(resp) == 1.0


# ── _truncation_factor ────────────────────────────────────────────────────────


class TestTruncationFactor:
    def test_normal_response_no_penalty(self, good_response):
        assert _truncation_factor(good_response) == 1.0

    def test_ellipsis_triggers_penalty(self):
        resp = AgentResponse(content="The answer is somewhere in the text...", model_slug="x")
        assert _truncation_factor(resp) == pytest.approx(0.7)

    def test_etc_triggers_penalty(self):
        resp = AgentResponse(content="Things like dogs, cats, birds, etc.", model_slug="x")
        assert _truncation_factor(resp) == pytest.approx(0.7)

    def test_ellipsis_in_middle_no_penalty(self):
        resp = AgentResponse(content="The answer... is Paris.", model_slug="x")
        assert _truncation_factor(resp) == 1.0


# ── _tool_usage_factor ────────────────────────────────────────────────────────


class TestToolUsageFactor:
    def test_no_tools_always_full_score(self, simple_request, good_response):
        assert _tool_usage_factor(simple_request, good_response) == 1.0

    def test_tools_available_and_used_full_score(self, request_with_tools):
        from core.cascade.types import ToolCall
        resp = AgentResponse(
            content="",
            tool_calls=[ToolCall(id="1", name="web_search", arguments={"query": "AI"})],
            model_slug="x",
        )
        assert _tool_usage_factor(request_with_tools, resp) == 1.0

    def test_tools_available_not_used_long_response_mild_penalty(self, request_with_tools):
        resp = AgentResponse(content="x" * 300, model_slug="x")
        assert _tool_usage_factor(request_with_tools, resp) == pytest.approx(0.85)

    def test_tools_available_not_used_short_response_heavy_penalty(self, request_with_tools):
        resp = AgentResponse(content="Here are some news.", model_slug="x")
        assert _tool_usage_factor(request_with_tools, resp) == pytest.approx(0.70)


# ── _error_factor ─────────────────────────────────────────────────────────────


class TestErrorFactor:
    def test_no_error_returns_one(self, good_response):
        assert _error_factor(good_response) == 1.0

    def test_error_returns_zero(self, error_response):
        assert _error_factor(error_response) == 0.0


# ── evaluate_response ─────────────────────────────────────────────────────────


class TestEvaluateResponse:
    def test_always_in_valid_range(self, simple_request, good_response, empty_response):
        for resp in (good_response, empty_response):
            score = evaluate_response(simple_request, resp)
            assert 0.0 <= score <= 1.0

    def test_error_response_returns_zero(self, simple_request, error_response):
        assert evaluate_response(simple_request, error_response) == 0.0

    def test_good_response_above_threshold(self, simple_request, good_response):
        assert evaluate_response(simple_request, good_response) > 0.75

    def test_short_refusal_response_is_near_zero(self, simple_request, refusal_response):
        assert evaluate_response(simple_request, refusal_response) <= 0.10

    def test_empty_response_returns_zero(self, simple_request, empty_response):
        assert evaluate_response(simple_request, empty_response) == 0.0

    def test_score_is_deterministic(self, simple_request, good_response):
        s1 = evaluate_response(simple_request, good_response)
        s2 = evaluate_response(simple_request, good_response)
        assert s1 == s2
