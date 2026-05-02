from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ModelTier(str, Enum):
    BUDGET = "budget"
    MID = "mid"
    FRONTIER = "frontier"


@dataclass(frozen=True)
class ModelDefinition:
    slug: str
    tier: ModelTier
    cost_input_per_million: float   # USD
    cost_output_per_million: float  # USD
    description: str


@dataclass
class AgentRequest:
    content: str
    required_tools: list[str] = field(default_factory=list)
    conversation_depth: int = 0
    domain_hint: str = ""


@dataclass
class RouterDecision:
    model: ModelDefinition
    tier: ModelTier
    confidence_score: float
    reason: str


# ── Model registries ──────────────────────────────────────────────────────────

BUDGET_MODELS: list[ModelDefinition] = [
    ModelDefinition(
        slug="deepseek/deepseek-chat",
        tier=ModelTier.BUDGET,
        cost_input_per_million=0.14,
        cost_output_per_million=0.28,
        description="DeepSeek V3 — défaut budget",
    ),
    ModelDefinition(
        slug="qwen/qwen3-8b",
        tier=ModelTier.BUDGET,
        cost_input_per_million=0.10,
        cost_output_per_million=0.10,
        description="Qwen 3 8B — ultra-économique",
    ),
]

MID_MODELS: list[ModelDefinition] = [
    ModelDefinition(
        slug="meta-llama/llama-4-scout",
        tier=ModelTier.MID,
        cost_input_per_million=0.11,
        cost_output_per_million=0.34,
        description="Llama 4 Scout — équilibré",
    ),
    ModelDefinition(
        slug="google/gemini-flash-1.5",
        tier=ModelTier.MID,
        cost_input_per_million=0.075,
        cost_output_per_million=0.30,
        description="Gemini Flash — rapide",
    ),
]

FRONTIER_MODELS: list[ModelDefinition] = [
    ModelDefinition(
        slug="anthropic/claude-opus-4-6",
        tier=ModelTier.FRONTIER,
        cost_input_per_million=15.0,
        cost_output_per_million=75.0,
        description="Claude Opus 4.6 — cas critiques",
    ),
    ModelDefinition(
        slug="openai/gpt-4o",
        tier=ModelTier.FRONTIER,
        cost_input_per_million=2.50,
        cost_output_per_million=10.0,
        description="GPT-4o — backup frontier",
    ),
]

ALL_MODELS: list[ModelDefinition] = BUDGET_MODELS + MID_MODELS + FRONTIER_MODELS


def get_model_by_slug(slug: str) -> Optional[ModelDefinition]:
    return next((m for m in ALL_MODELS if m.slug == slug), None)


def get_models_by_tier(tier: ModelTier) -> list[ModelDefinition]:
    return [m for m in ALL_MODELS if m.tier == tier]
