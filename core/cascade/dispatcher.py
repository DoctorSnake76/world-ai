"""MAS dispatcher — escalates to the frontier model when SAS quality is insufficient.

The dispatcher is intentionally minimal for Phase 1: it calls the frontier
model with the original draft injected as context. Full multi-agent
orchestration will be added in later phases.
"""

from dataclasses import replace

import structlog

from core.router.models import FRONTIER_MODELS, ModelDefinition, get_model_by_slug

from .openrouter import OpenRouterClient
from .types import AgentResponse, UserRequest

logger = structlog.get_logger(__name__)

_MAX_DRAFT_CHARS = 1200  # how much of the original draft to inject


def _resolve_frontier(slug: str) -> ModelDefinition:
    model = get_model_by_slug(slug)
    if model is not None:
        return model
    logger.warning("unknown_frontier_slug", slug=slug, fallback=FRONTIER_MODELS[0].slug)
    return FRONTIER_MODELS[0]


def _enrich_system_prompt(base_prompt: str, draft: str, draft_model: str) -> str:
    """Inject the original draft into the system prompt for the frontier model."""
    if not draft:
        return base_prompt
    note = (
        f"\n\n[Context: a first attempt by {draft_model} produced the following draft "
        f"which did not meet quality standards. Review it, correct any issues, and "
        f"provide a complete, high-quality answer.]\n"
        f"Draft: {draft[:_MAX_DRAFT_CHARS]}"
    )
    return base_prompt + note


async def dispatch_to_mas(
    request: UserRequest,
    client: OpenRouterClient,
    frontier_slug: str,
    original_response: AgentResponse,
) -> AgentResponse:
    """Call the frontier model with the original draft as context.

    Always uses the cloud client (``client``) regardless of whether the
    initial SAS call used a local model.
    """
    model = _resolve_frontier(frontier_slug)
    logger.info(
        "mas_escalation_start",
        frontier_model=model.slug,
        original_model=original_response.model_slug,
        original_quality=original_response.quality_score,
        original_error=original_response.error,
    )

    enriched = replace(
        request,
        system_prompt=_enrich_system_prompt(
            request.system_prompt,
            original_response.content,
            original_response.model_slug,
        ),
    )

    response = await client.complete(enriched, model, temperature=0.5)
    response.escalated = True

    logger.info(
        "mas_escalation_complete",
        frontier_model=model.slug,
        tokens_in=response.tokens_in,
        tokens_out=response.tokens_out,
        cost_eur=response.cost_eur,
        latency_ms=response.latency_ms,
        error=response.error,
    )
    return response
