"""CascadeAgent — Single-Agent System (SAS) with automatic MAS escalation.

Pipeline for every request:
  1. Route → select model tier via LLMRouter + confidence score
  2. SAS call → OpenRouterClient.complete()
  3. Evaluate → quality score via evaluator
  4. Escalate → dispatcher.dispatch_to_mas() if quality < threshold
  5. Return final AgentResponse with all metrics attached
"""

import time
from dataclasses import replace
from typing import Optional

import structlog

from config.settings import get_settings
from core.router.models import AgentRequest
from core.router.router import get_router

from .dispatcher import dispatch_to_mas
from .evaluator import evaluate_response
from .openrouter import OpenRouterClient
from .types import AgentResponse, UserRequest

logger = structlog.get_logger(__name__)

_DEFAULT_SYSTEM_PROMPT = (
    "You are World AI, a personal and professional AI assistant. "
    "Be precise, helpful, and concise. Think step by step when needed. "
    "Always respond in the same language as the user."
)


class CascadeAgent:
    """Main agent: routes requests, calls LLMs, evaluates quality, escalates if needed.

    Args:
        openrouter_client: Cloud client (OpenRouter). Created from settings if omitted.
        local_client: Optional local client (xLAM-2 via llama.cpp). Used when
                      ``use_local=True`` is passed to ``process()``.
    """

    def __init__(
        self,
        openrouter_client: Optional[OpenRouterClient] = None,
        local_client: Optional[OpenRouterClient] = None,
    ) -> None:
        s = get_settings()
        self._router = get_router()
        self._quality_threshold: float = s.confidence_threshold
        self._frontier_slug: str = s.llm_frontier_model
        self._client = openrouter_client or OpenRouterClient(api_key=s.openrouter_api_key)
        self._local_client = local_client

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _pick_client(self, use_local: bool) -> OpenRouterClient:
        if use_local and self._local_client is not None:
            return self._local_client
        return self._client

    def _to_router_request(self, request: UserRequest) -> AgentRequest:
        return AgentRequest(
            content=request.last_user_content,
            required_tools=[t.name for t in request.available_tools],
            conversation_depth=request.conversation_depth,
        )

    def _ensure_system_prompt(self, request: UserRequest) -> UserRequest:
        if request.system_prompt:
            return request
        return replace(request, system_prompt=_DEFAULT_SYSTEM_PROMPT)

    # ── Public API ────────────────────────────────────────────────────────────

    async def process(
        self,
        request: UserRequest,
        use_local: bool = False,
    ) -> AgentResponse:
        """Process one user turn through the full cascade pipeline.

        Args:
            request: The current conversation turn with tools and history.
            use_local: Route to the local xLAM-2 model instead of OpenRouter
                       for the initial SAS call. Escalation always uses cloud.

        Returns:
            AgentResponse with content, tool_calls, metrics, and quality score.
        """
        pipeline_start = time.perf_counter()
        request = self._ensure_system_prompt(request)

        # 1. Routing ───────────────────────────────────────────────────────────
        decision = self._router.route(self._to_router_request(request))
        logger.info(
            "cascade_routing",
            tier=decision.tier.value,
            model=decision.model.slug,
            confidence=decision.confidence_score,
        )

        # 2. SAS call ──────────────────────────────────────────────────────────
        client = self._pick_client(use_local)
        response = await client.complete(request, decision.model)
        response.confidence_score = decision.confidence_score

        logger.info(
            "cascade_sas_complete",
            model=response.model_slug,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
            cost_eur=response.cost_eur,
            latency_ms=response.latency_ms,
            error=response.error,
        )

        # 3. Quality evaluation ────────────────────────────────────────────────
        quality = evaluate_response(request, response)
        response.quality_score = quality

        # 4. MAS escalation if quality below threshold ─────────────────────────
        if quality < self._quality_threshold:
            logger.info(
                "cascade_below_threshold",
                quality=quality,
                threshold=self._quality_threshold,
            )
            response = await dispatch_to_mas(
                request=request,
                client=self._client,   # always cloud for frontier
                frontier_slug=self._frontier_slug,
                original_response=response,
            )
            response.quality_score = evaluate_response(request, response)
            response.confidence_score = decision.confidence_score

        # 5. Final metrics ─────────────────────────────────────────────────────
        total_ms = (time.perf_counter() - pipeline_start) * 1000
        logger.info(
            "cascade_pipeline_done",
            escalated=response.escalated,
            final_quality=response.quality_score,
            total_latency_ms=round(total_ms, 1),
            cost_eur=response.cost_eur,
        )
        return response
