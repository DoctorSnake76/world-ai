import re
from .models import AgentRequest

# Keywords that signal high cognitive complexity → lower confidence
_HIGH_COMPLEXITY_KW = [
    "analyse", "analyze", "critique", "compare", "synthesize",
    "strategy", "architecture", "design", "optimize", "debug",
    "implement", "refactor", "security", "audit", "evaluate",
    "diagnose", "investigate", "negotiate",
]

# Domains where errors are costly → lower confidence to escalate tier
_HIGH_RISK_DOMAINS = [
    "finance", "financial", "invest", "investment", "tax",
    "legal", "law", "court", "contract",
    "medical", "medicine", "health", "drug", "diagnosis",
]
_MEDIUM_RISK_DOMAINS = [
    "security", "privacy", "credential", "confidential", "personal",
    "password", "authentication", "permission",
]


def _normalize_inverse(value: float, lo: float, hi: float) -> float:
    """Map value in [lo, hi] → [1.0, 0.0]. Values outside range are clamped."""
    if hi <= lo:
        return 1.0
    clamped = max(lo, min(hi, value))
    return 1.0 - (clamped - lo) / (hi - lo)


def _complexity_factor(content: str) -> float:
    """
    Return [0.0, 1.0]. High complexity keywords drive this toward 0.0.
    Uses keyword density so long texts aren't unfairly penalised.
    """
    words = content.lower().split()
    if not words:
        return 1.0
    hit_count = sum(1 for kw in _HIGH_COMPLEXITY_KW if kw in content.lower())
    # Density cap: 5+ hits saturates to 0.0 confidence
    density = hit_count / 5.0
    return max(0.0, 1.0 - min(1.0, density))


def _domain_risk_factor(content: str) -> float:
    """Return 0.2 (high-risk domain), 0.5 (medium-risk), or 1.0 (safe)."""
    lower = content.lower()
    if any(kw in lower for kw in _HIGH_RISK_DOMAINS):
        return 0.2
    if any(kw in lower for kw in _MEDIUM_RISK_DOMAINS):
        return 0.5
    return 1.0


def _tools_factor(tool_count: int) -> float:
    """More tools required → more complex → lower score. Cap at 10."""
    return max(0.0, 1.0 - tool_count / 10.0)


def _history_factor(depth: int) -> float:
    """Deeper conversation → more context needed → lower score. Cap at 20."""
    return max(0.0, 1.0 - depth / 20.0)


def compute_confidence_score(request: AgentRequest) -> float:
    """
    Compute routing confidence for a request in [0.0, 1.0].

    ≥ 0.80 → BUDGET model
    0.60–0.79 → MID model
    < 0.60 → FRONTIER model
    """
    factors = {
        "length":      _normalize_inverse(len(request.content), lo=0, hi=2000),
        "complexity":  _complexity_factor(request.content),
        "domain":      _domain_risk_factor(request.content),
        "tools":       _tools_factor(len(request.required_tools)),
        "history":     _history_factor(request.conversation_depth),
    }
    weights = {
        "length":     0.10,
        "complexity": 0.35,
        "domain":     0.25,
        "tools":      0.20,
        "history":    0.10,
    }
    raw = sum(factors[k] * weights[k] for k in factors)
    return round(max(0.0, min(1.0, raw)), 4)
