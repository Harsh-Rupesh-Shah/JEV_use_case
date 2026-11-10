"""Upstream Model Router powered by TypeSafe JEV System One.

Dynamically classifies participant queries by intent and cognitive complexity in a single
parallel forward pass (sub-150ms), routing tasks to the optimal LLM tier (Fast vs Reasoning)
as detailed in the JEV architecture.
"""

import logging
import time
from typing import Dict, Optional
from pydantic import BaseModel, Field
from typesafe_sdk import Choice, Score

from whisperer.arbiter.jev_client import get_jev_client
from whisperer.config import settings

logger = logging.getLogger("whisperer.arbiter.router")

# Intent classification taxonomy for retirement workflows
ROUTER_INTENT_CRITERIA: Dict[str, str] = {
    "routine_lookup": "Basic account balance, standard IRS 403b/IRA contribution limits, general policy FAQs, or 1099 form requests",
    "complex_advisory": "Multi-scenario retirement modeling, tax bracket optimization, IRS 72t SEPP rules, compound projection, or actuarial calculations",
    "policy_override": "Requests to waive 72-hour fraud cooling-off holds, claim supervisor overrides, or bypass multi-factor authentication",
}

# Ordered cognitive complexity rubric (0.0 to 4.0)
COMPLEXITY_LEVELS = ["trivial", "simple", "moderate", "complex", "expert"]


class ModelRouteDecision(BaseModel):
    """Decision emitted by the upstream JEV System One model router."""
    tier: str = Field(description="'fast' (low-latency, free) or 'reasoning' (frontier deep thinking)")
    model_name: str = Field(description="Name of the selected LLM model")
    intent: str = Field(description="Detected primary intent category")
    complexity_score: float = Field(description="Expected continuous complexity value (0.0 to 4.0)")
    complexity_label: str = Field(description="Mapped categorical complexity level name")
    confidence: Optional[float] = Field(default=None, description="JEV confidence score (0.0 to 1.0)")
    intent_probabilities: Dict[str, float] = Field(default_factory=dict, description="Full probability distribution over intents")
    routing_latency_ms: float = Field(description="Latency of the JEV classification in milliseconds")
    rationale: str = Field(description="Human-readable justification for the routing decision")


async def route_query_with_jev(user_text: str) -> ModelRouteDecision:
    """Classify user query using JEV in a single parallel forward pass and select optimal model tier.
    
    Fast Tier: Gemini Flash-Lite (low latency, sub-second, zero-cost)
    Reasoning Tier: Nemotron 3.5 / OpenRouter (deep multi-step financial logic)
    """
    client = get_jev_client()
    start_time = time.perf_counter()

    # Lean state trimming to prevent context rot
    trimmed_text = user_text.strip()
    if len(trimmed_text) > 250:
        trimmed_text = trimmed_text[:247] + "..."

    # Define parallel questions evaluated concurrently on the query state
    router_questions = {
        "intent": Choice(
            instructions="Identify the primary category of this participant inquiry",
            criteria=ROUTER_INTENT_CRITERIA,
        ),
        "complexity": Score(
            instructions="Rate the cognitive and analytical complexity required to answer this inquiry",
            criteria=COMPLEXITY_LEVELS,
        ),
    }

    try:
        response, latency_ms = await client.evaluate_async(
            state=trimmed_text,
            questions=router_questions,
        )

        # 1. Extract Intent Choice
        intent_ans = response.answers.get("intent")
        intent_selected = getattr(intent_ans, "choice", "routine_lookup")
        intent_conf = getattr(intent_ans, "confidence", None)
        intent_probs = getattr(intent_ans, "probabilities", {}) or {}

        # 2. Extract Complexity Score
        complexity_ans = response.answers.get("complexity")
        complexity_score = float(getattr(complexity_ans, "score", 1.0))
        level_idx = min(max(int(round(complexity_score)), 0), len(COMPLEXITY_LEVELS) - 1)
        complexity_label = COMPLEXITY_LEVELS[level_idx]

        # 3. Decision Logic: High complexity or complex advisory requires the Reasoning Tier
        is_complex = intent_selected == "complex_advisory" or complexity_score >= 2.0

        if is_complex:
            tier = "reasoning"
            model_name = settings.OPENROUTER_MODEL
            rationale = (
                f"Multi-step advisory inquiry (complexity: {complexity_label}, score: {complexity_score:.1f}). "
                f"Routed to frontier reasoning tier ({settings.OPENROUTER_MODEL})."
            )
        else:
            tier = "fast"
            model_name = settings.GEMINI_MODEL
            rationale = (
                f"Standard inquiry (complexity: {complexity_label}, score: {complexity_score:.1f}). "
                f"Optimized for sub-second execution via fast tier ({settings.GEMINI_MODEL})."
            )

        logger.info(
            "JEV Upstream Router: intent=%s, complexity=%.2f (%s) -> tier=%s [%.1f ms]",
            intent_selected,
            complexity_score,
            complexity_label,
            tier,
            latency_ms,
        )

        return ModelRouteDecision(
            tier=tier,
            model_name=model_name,
            intent=str(intent_selected),
            complexity_score=complexity_score,
            complexity_label=complexity_label,
            confidence=intent_conf,
            intent_probabilities={str(k): float(v) for k, v in intent_probs.items()},
            routing_latency_ms=round(latency_ms, 2),
            rationale=rationale,
        )

    except Exception as e:
        # Fail-safe: Always ensure uninterrupted operation regardless of external network issues
        total_lat = (time.perf_counter() - start_time) * 1000.0
        logger.warning("JEV router fallback triggered: %s", e)

        # Basic deterministic keyword heuristic for fallback
        lower_q = user_text.lower()
        if any(w in lower_q for w in ["simulate", "forecast", "actuarial", "bracket", "72(t)", "sepp", "optimize"]):
            tier = "reasoning"
            model_name = settings.OPENROUTER_MODEL
            intent = "complex_advisory"
            comp_score = 3.0
            comp_label = "complex"
        else:
            tier = "fast"
            model_name = settings.GEMINI_MODEL
            intent = "routine_lookup"
            comp_score = 1.0
            comp_label = "simple"

        return ModelRouteDecision(
            tier=tier,
            model_name=model_name,
            intent=intent,
            complexity_score=comp_score,
            complexity_label=comp_label,
            confidence=0.85,
            intent_probabilities={intent: 0.85},
            routing_latency_ms=round(total_lat, 2),
            rationale=f"Routed via resilient fallback to {tier} tier ({model_name}).",
        )

