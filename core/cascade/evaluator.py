"""Post-response quality evaluator for the Agent Cascade.

Returns a score in [0.0, 1.0]. Scores below the configured threshold
trigger escalation to the MAS (frontier model) via the dispatcher.
"""

import re

import structlog

from .types import AgentResponse, UserRequest

logger = structlog.get_logger(__name__)

# Patterns that indicate the model refused or deflected the request
_REFUSAL_PATTERNS = [
    r"i(?:'m| am) (?:not able|unable) to",
    r"i can(?:'t| not) (?:help|assist)",
    r"as an ai(?: language model)?",
    r"i (?:don't|do not) (?:have|know)",
    r"i (?:cannot|can't) (?:provide|generate|create)",
    r"that(?:'s| is) (?:not something i can|outside my)",
]
_REFUSAL_RE = re.compile("|".join(_REFUSAL_PATTERNS), re.IGNORECASE)

# Markers that suggest the response was cut off mid-sentence
_TRUNCATION_SUFFIXES = ("...", "…", "[continued]", "[truncated]", "etc.")

# Weight map for final score computation
_WEIGHTS: dict[str, float] = {
    "length":     0.30,
    "refusal":    0.30,
    "truncation": 0.15,
    "tool_usage": 0.15,
    "error":      0.10,
}


# ── Individual factor functions ───────────────────────────────────────────────


def _length_adequacy(request: UserRequest, response: AgentResponse) -> float:
    """Penalize responses that are too short relative to the request."""
    req_len = len(request.last_user_content)
    resp_len = len(response.content)

    if req_len == 0:
        return 1.0 if resp_len > 10 else 0.5

    ratio = resp_len / req_len
    # target: response at least half the length of the request
    return min(1.0, ratio / 0.5)


def _refusal_factor(response: AgentResponse) -> float:
    """Return 0.3 if the model deflected; 1.0 otherwise."""
    if _REFUSAL_RE.search(response.content):
        return 0.3
    return 1.0


def _truncation_factor(response: AgentResponse) -> float:
    """Return 0.7 if the response looks cut off; 1.0 otherwise."""
    stripped = response.content.rstrip()
    if any(stripped.endswith(suffix) for suffix in _TRUNCATION_SUFFIXES):
        return 0.7
    return 1.0


def _tool_usage_factor(request: UserRequest, response: AgentResponse) -> float:
    """Penalize mildly when tools were available but not invoked on a short answer."""
    if not request.available_tools:
        return 1.0
    if response.tool_calls:
        return 1.0
    # Tool available, not used — acceptable only if the response is substantial
    return 0.85 if len(response.content) > 200 else 0.70


def _error_factor(response: AgentResponse) -> float:
    """Hard zero whenever the API returned an error."""
    return 0.0 if response.error else 1.0


# ── Public API ────────────────────────────────────────────────────────────────


def evaluate_response(request: UserRequest, response: AgentResponse) -> float:
    """Compute quality score [0.0, 1.0] for a completed cascade response.

    A score below the configured ``confidence_threshold`` triggers MAS
    escalation in the dispatcher.
    """
    if response.error:
        logger.warning("evaluator_error_in_response", error=response.error)
        return 0.0

    factors = {
        "length":     _length_adequacy(request, response),
        "refusal":    _refusal_factor(response),
        "truncation": _truncation_factor(response),
        "tool_usage": _tool_usage_factor(request, response),
        "error":      _error_factor(response),
    }
    score = round(
        max(0.0, min(1.0, sum(factors[k] * _WEIGHTS[k] for k in factors))),
        4,
    )
    logger.debug("evaluator_result", score=score, factors=factors)
    return score
