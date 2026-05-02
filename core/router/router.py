import logging

from .confidence import compute_confidence_score
from .models import (
    BUDGET_MODELS,
    FRONTIER_MODELS,
    MID_MODELS,
    AgentRequest,
    ModelDefinition,
    ModelTier,
    RouterDecision,
    get_model_by_slug,
)
from config.settings import get_settings

logger = logging.getLogger(__name__)

# Confidence thresholds that define tier boundaries
BUDGET_THRESHOLD: float = 0.80
MID_THRESHOLD: float = 0.60


class LLMRouter:
    """Routes AgentRequest objects to the appropriate model tier."""

    def __init__(self) -> None:
        s = get_settings()
        self._budget_slug = s.llm_budget_model
        self._mid_slug = s.llm_mid_model
        self._frontier_slug = s.llm_frontier_model

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _resolve(self, slug: str, fallback: list[ModelDefinition]) -> ModelDefinition:
        model = get_model_by_slug(slug)
        if model is not None:
            return model
        logger.warning("unknown model slug %r — falling back to %r", slug, fallback[0].slug)
        return fallback[0]

    # ── Public API ────────────────────────────────────────────────────────────

    def select_model(self, confidence: float) -> ModelDefinition:
        """Return the model that matches the confidence score tier."""
        if confidence >= BUDGET_THRESHOLD:
            return self._resolve(self._budget_slug, BUDGET_MODELS)
        if confidence >= MID_THRESHOLD:
            return self._resolve(self._mid_slug, MID_MODELS)
        return self._resolve(self._frontier_slug, FRONTIER_MODELS)

    def route(self, request: AgentRequest) -> RouterDecision:
        """Compute confidence score and return a fully-formed routing decision."""
        confidence = compute_confidence_score(request)
        model = self.select_model(confidence)

        if confidence >= BUDGET_THRESHOLD:
            reason = f"score={confidence:.3f} ≥ {BUDGET_THRESHOLD} → BUDGET ({model.slug})"
        elif confidence >= MID_THRESHOLD:
            reason = f"score={confidence:.3f} in [{MID_THRESHOLD}, {BUDGET_THRESHOLD}) → MID ({model.slug})"
        else:
            reason = f"score={confidence:.3f} < {MID_THRESHOLD} → FRONTIER ({model.slug})"

        logger.info("llm_routing", extra={"model": model.slug, "tier": model.tier, "confidence": confidence})

        return RouterDecision(
            model=model,
            tier=model.tier,
            confidence_score=confidence,
            reason=reason,
        )


# ── Module-level singleton ────────────────────────────────────────────────────

_router: LLMRouter | None = None


def get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
