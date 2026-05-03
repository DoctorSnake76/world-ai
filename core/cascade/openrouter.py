"""Async HTTP client for OpenRouter API (OpenAI-compatible).

Works with both OpenRouter (cloud) and a local llama.cpp server
running xLAM-2 or any OpenAI-compatible endpoint.
"""

import json
import time
from typing import Any, Optional

import httpx
import structlog

from core.router.models import ModelDefinition

from .types import AgentResponse, MessageRole, ToolCall, ToolDefinition, UserRequest

logger = structlog.get_logger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
USD_TO_EUR = 0.92  # approximate conversion rate


# ── Message / Tool serialisation ─────────────────────────────────────────────


def _build_messages(request: UserRequest) -> list[dict[str, Any]]:
    """Convert UserRequest to OpenAI-compatible messages list."""
    msgs: list[dict[str, Any]] = []
    if request.system_prompt:
        msgs.append({"role": "system", "content": request.system_prompt})
    for msg in request.messages:
        if msg.role == MessageRole.TOOL:
            msgs.append(
                {
                    "role": "tool",
                    "content": msg.content,
                    "tool_call_id": msg.tool_call_id or "",
                }
            )
        else:
            msgs.append({"role": msg.role.value, "content": msg.content})
    return msgs


def _build_tools(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
    """Convert ToolDefinition list to OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            },
        }
        for t in tools
    ]


def _parse_tool_calls(raw: list[dict[str, Any]]) -> list[ToolCall]:
    result: list[ToolCall] = []
    for call in raw:
        fn = call.get("function", {})
        args_raw = fn.get("arguments", "{}")
        try:
            args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
        except json.JSONDecodeError:
            args = {"_raw": args_raw}
        result.append(
            ToolCall(
                id=call.get("id", ""),
                name=fn.get("name", ""),
                arguments=args,
            )
        )
    return result


def _estimate_cost_eur(model: ModelDefinition, tokens_in: int, tokens_out: int) -> float:
    cost_usd = (
        tokens_in / 1_000_000 * model.cost_input_per_million
        + tokens_out / 1_000_000 * model.cost_output_per_million
    )
    return round(cost_usd * USD_TO_EUR, 6)


# ── Client ────────────────────────────────────────────────────────────────────


class OpenRouterClient:
    """Async client for OpenAI-compatible chat completion endpoints.

    Pass ``local_url`` to target a local llama.cpp server (e.g. xLAM-2)
    instead of OpenRouter. When ``local_url`` is set, no Authorization
    header is sent.
    """

    def __init__(self, api_key: str, local_url: Optional[str] = None) -> None:
        self._api_key = api_key
        self._base_url = (local_url or OPENROUTER_BASE_URL).rstrip("/")
        self._is_local = local_url is not None

    # ── Private helpers ───────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if not self._is_local:
            headers["Authorization"] = f"Bearer {self._api_key}"
            headers["HTTP-Referer"] = "https://github.com/world-ai"
            headers["X-Title"] = "World AI"
        return headers

    def _build_payload(
        self,
        request: UserRequest,
        model: ModelDefinition,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model.slug,
            "messages": _build_messages(request),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if request.available_tools:
            payload["tools"] = _build_tools(request.available_tools)
            payload["tool_choice"] = "auto"
        return payload

    def _parse_response(
        self,
        data: dict[str, Any],
        model: ModelDefinition,
        latency_ms: float,
    ) -> AgentResponse:
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        usage = data.get("usage") or {}

        tokens_in = int(usage.get("prompt_tokens", 0))
        tokens_out = int(usage.get("completion_tokens", 0))
        tool_calls = _parse_tool_calls(msg.get("tool_calls") or [])

        return AgentResponse(
            content=msg.get("content") or "",
            tool_calls=tool_calls,
            model_slug=model.slug,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_eur=_estimate_cost_eur(model, tokens_in, tokens_out),
            latency_ms=round(latency_ms, 1),
        )

    # ── Public API ────────────────────────────────────────────────────────────

    async def complete(
        self,
        request: UserRequest,
        model: ModelDefinition,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AgentResponse:
        """Send a chat completion request; return a structured AgentResponse."""
        payload = self._build_payload(request, model, temperature, max_tokens)
        url = f"{self._base_url}/chat/completions"

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=90.0) as http:
                resp = await http.post(url, headers=self._headers(), json=payload)
                resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "openrouter_http_error",
                status=exc.response.status_code,
                model=model.slug,
            )
            return AgentResponse(
                content="",
                error=f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
            )
        except httpx.RequestError as exc:
            logger.error("openrouter_request_error", error=str(exc), model=model.slug)
            return AgentResponse(content="", error=str(exc))

        latency_ms = (time.perf_counter() - t0) * 1000
        response = self._parse_response(resp.json(), model, latency_ms)

        logger.info(
            "llm_call_complete",
            model=model.slug,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
            cost_eur=response.cost_eur,
            latency_ms=response.latency_ms,
            tool_calls=len(response.tool_calls),
        )
        return response
