import pytest

from core.router.confidence import (
    _complexity_factor,
    _domain_risk_factor,
    _history_factor,
    _normalize_inverse,
    _tools_factor,
    compute_confidence_score,
)
from core.router.models import AgentRequest, ModelTier
from core.router.router import BUDGET_THRESHOLD, MID_THRESHOLD, LLMRouter


# ── _normalize_inverse ────────────────────────────────────────────────────────

class TestNormalizeInverse:
    def test_at_lo_returns_one(self):
        assert _normalize_inverse(0, 0, 100) == 1.0

    def test_at_hi_returns_zero(self):
        assert _normalize_inverse(100, 0, 100) == 0.0

    def test_midpoint(self):
        assert _normalize_inverse(50, 0, 100) == pytest.approx(0.5)

    def test_clamp_above_hi(self):
        assert _normalize_inverse(200, 0, 100) == 0.0

    def test_clamp_below_lo(self):
        assert _normalize_inverse(-10, 0, 100) == 1.0

    def test_equal_lo_hi(self):
        assert _normalize_inverse(50, 100, 100) == 1.0


# ── _complexity_factor ────────────────────────────────────────────────────────

class TestComplexityFactor:
    def test_simple_greeting(self):
        assert _complexity_factor("What time is it?") > 0.8

    def test_single_complex_keyword(self):
        score = _complexity_factor("Can you analyze this?")
        assert score < 1.0

    def test_saturates_at_five_keywords(self):
        msg = "Please analyze, critique, optimize, refactor, and audit this."
        assert _complexity_factor(msg) == pytest.approx(0.0)

    def test_empty_content(self):
        assert _complexity_factor("") == 1.0


# ── _domain_risk_factor ───────────────────────────────────────────────────────

class TestDomainRiskFactor:
    def test_safe_domain(self):
        assert _domain_risk_factor("Tell me a fun fact about cats.") == 1.0

    def test_high_risk_finance(self):
        assert _domain_risk_factor("Best investment strategy for 2025?") == 0.2

    def test_high_risk_medical(self):
        assert _domain_risk_factor("What is the drug dosage for this diagnosis?") == 0.2

    def test_medium_risk_security(self):
        assert _domain_risk_factor("How do I store my credentials securely?") == 0.5


# ── _tools_factor / _history_factor ──────────────────────────────────────────

class TestSimpleFactors:
    def test_no_tools_returns_one(self):
        assert _tools_factor(0) == 1.0

    def test_ten_tools_returns_zero(self):
        assert _tools_factor(10) == 0.0

    def test_five_tools_returns_half(self):
        assert _tools_factor(5) == pytest.approx(0.5)

    def test_zero_depth_returns_one(self):
        assert _history_factor(0) == 1.0

    def test_twenty_depth_returns_zero(self):
        assert _history_factor(20) == 0.0


# ── compute_confidence_score ──────────────────────────────────────────────────

class TestComputeConfidenceScore:
    def test_always_in_valid_range(self):
        cases = [
            AgentRequest(content="Hi"),
            AgentRequest(content="x" * 5000),
            AgentRequest(content="analyze the legal and medical investment strategy"),
            AgentRequest(content="", required_tools=["a"] * 15, conversation_depth=30),
        ]
        for req in cases:
            score = compute_confidence_score(req)
            assert 0.0 <= score <= 1.0, f"Out of range for: {req.content!r}"

    def test_simple_request_routes_budget(self):
        req = AgentRequest(content="What is the capital of France?")
        assert compute_confidence_score(req) >= BUDGET_THRESHOLD

    def test_complex_critical_routes_frontier(self):
        req = AgentRequest(
            content=(
                "Analyze, critique, and optimize the legal and medical investment "
                "strategy. Audit the security architecture thoroughly."
            ),
            required_tools=["file", "email", "calendar", "db", "web", "shell"],
            conversation_depth=18,
        )
        assert compute_confidence_score(req) < MID_THRESHOLD


# ── LLMRouter ─────────────────────────────────────────────────────────────────

class TestLLMRouter:
    def setup_method(self):
        self.router = LLMRouter()

    def test_simple_request_is_budget(self):
        req = AgentRequest(content="Remind me to call mom tomorrow.")
        decision = self.router.route(req)
        assert decision.tier == ModelTier.BUDGET
        assert decision.confidence_score >= BUDGET_THRESHOLD

    def test_complex_request_is_frontier(self):
        req = AgentRequest(
            content=(
                "Analyze, audit, and optimize the security and legal architecture. "
                "Critique the medical investment strategy."
            ),
            required_tools=["a", "b", "c", "d", "e", "f"],
            conversation_depth=16,
        )
        decision = self.router.route(req)
        assert decision.tier == ModelTier.FRONTIER

    def test_select_model_budget(self):
        assert self.router.select_model(0.90).tier == ModelTier.BUDGET

    def test_select_model_mid(self):
        assert self.router.select_model(0.70).tier == ModelTier.MID

    def test_select_model_frontier(self):
        assert self.router.select_model(0.50).tier == ModelTier.FRONTIER

    def test_decision_reason_contains_score(self):
        req = AgentRequest(content="Hello!")
        decision = self.router.route(req)
        assert str(round(decision.confidence_score, 3)) in decision.reason

    def test_decision_reason_mentions_tier(self):
        req = AgentRequest(content="Hello!")
        decision = self.router.route(req)
        tier_label = decision.tier.value.upper()
        assert tier_label in decision.reason
