"""Unit tests for the JEV Upstream Model Router."""

import pytest
from whisperer.arbiter.router import ModelRouteDecision, ROUTER_INTENT_CRITERIA, COMPLEXITY_LEVELS


def test_router_criteria_validity():
    """Verify that intent criteria and complexity levels adhere to JEV conventions."""
    assert "routine_lookup" in ROUTER_INTENT_CRITERIA
    assert "complex_advisory" in ROUTER_INTENT_CRITERIA
    assert "policy_override" in ROUTER_INTENT_CRITERIA
    assert len(COMPLEXITY_LEVELS) == 5
    assert COMPLEXITY_LEVELS[0] == "trivial"
    assert COMPLEXITY_LEVELS[-1] == "expert"


def test_model_route_decision_fast_tier():
    """Verify ModelRouteDecision structure for fast tier routing."""
    decision = ModelRouteDecision(
        tier="fast",
        model_name="gemini-flash-lite-latest",
        intent="routine_lookup",
        complexity_score=0.8,
        complexity_label="trivial",
        confidence=0.94,
        routing_latency_ms=114.5,
        rationale="Standard balance inquiry routed to fast tier.",
    )
    assert decision.tier == "fast"
    assert decision.complexity_score < 2.0
    assert decision.routing_latency_ms > 0
    assert "fast tier" in decision.rationale


def test_model_route_decision_reasoning_tier():
    """Verify ModelRouteDecision structure for reasoning tier routing."""
    decision = ModelRouteDecision(
        tier="reasoning",
        model_name="nvidia/nemotron-3.5-lightning:free",
        intent="complex_advisory",
        complexity_score=3.4,
        complexity_label="complex",
        confidence=0.89,
        routing_latency_ms=128.2,
        rationale="Complex retirement SEPP forecast routed to reasoning tier.",
    )
    assert decision.tier == "reasoning"
    assert decision.complexity_score >= 2.0
    assert decision.intent == "complex_advisory"

