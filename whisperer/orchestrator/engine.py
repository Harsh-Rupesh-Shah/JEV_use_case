"""Orchestrator: Multi-turn A2A execution loop and state machine."""

import asyncio
import logging
from typing import AsyncGenerator, Dict, List, Optional
from pydantic import BaseModel, Field

from whisperer.agents.defender import RetirementAssistantDefender
from whisperer.agents.influence import InfluenceWhispererAgent
from whisperer.arbiter.evaluators import evaluate_turn
from whisperer.protocol.schemas import (
    A2ADefenderResponse,
    A2AMessage,
    JevEvaluationReport,
    SessionStatus,
    generate_id,
)
from .scenarios import ScenarioDefinition, get_scenario

logger = logging.getLogger("whisperer.orchestrator.engine")


class TurnRecord(BaseModel):
    """Immutable audit record of a single conversational round."""
    round_index: int
    adversary_message: A2AMessage
    defender_response: A2ADefenderResponse
    jev_report: JevEvaluationReport


class SessionResult(BaseModel):
    """Comprehensive post-evaluation telemetry and executive resilience audit."""
    session_id: str
    scenario: ScenarioDefinition
    status: SessionStatus
    completed_rounds: int
    overall_resilience_score: float = Field(description="Percentage score (0-100%) indicating defensive resilience")
    tactics_observed: List[str]
    max_compliance_risk: str
    escalation_triggered: bool
    turns: List[TurnRecord]


class OrchestrationEngine:
    """Coordinates multi-turn adversarial evaluations, Jev evaluations, and session state."""

    def __init__(self):
        self.active_sessions: Dict[str, SessionStatus] = {}

    async def stream_session(
        self,
        scenario_id: str,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[TurnRecord, None]:
        """Execute a multi-turn evaluation turn-by-turn, yielding results as each round finishes."""
        scenario = get_scenario(scenario_id)
        sess_id = session_id or generate_id("sess")
        self.active_sessions[sess_id] = SessionStatus.IN_PROGRESS

        whisperer = InfluenceWhispererAgent(scenario=scenario.scenario_id)
        defender = RetirementAssistantDefender()
        dialogue_history: List[Dict[str, str]] = []

        logger.info("Starting evaluation session %s [Scenario: %s]", sess_id, scenario.title)

        for round_idx in range(1, scenario.total_rounds + 1):
            if self.active_sessions.get(sess_id) in [SessionStatus.INTERCEPT_TRIGGERED, SessionStatus.BREACH_HALTED]:
                logger.info("Session %s halted due to guard condition", sess_id)
                break

            # 1. Influence Agent creates adversarial prompt using resilient LLM (with history)
            attack_msg = await whisperer.generate_message_async(
                session_id=sess_id,
                round_index=round_idx,
                target_account_id=scenario.target_account_id,
                history=dialogue_history,
            )

            # 2. Defender Agent evaluates, executes tools, and synthesizes response via LLM
            defender_resp = await defender.process_turn(attack_msg)

            # Record turn in dialogue history for subsequent rounds
            dialogue_history.append({"role": "adversary", "content": attack_msg.payload.content})
            dialogue_history.append({"role": "defender", "content": defender_resp.payload.content})

            # 3. Jev Arbiter evaluates both agents and emits structured verdict
            jev_report = await evaluate_turn(attack_msg, defender_resp)

            turn_record = TurnRecord(
                round_index=round_idx,
                adversary_message=attack_msg,
                defender_response=defender_resp,
                jev_report=jev_report,
            )

            # Update session status if escalation or breach occurred
            if jev_report.session_status != SessionStatus.CONTINUE:
                self.active_sessions[sess_id] = jev_report.session_status

            yield turn_record

            # Slight pacing delay between conversational rounds
            await asyncio.sleep(0.05)

        if self.active_sessions.get(sess_id) == SessionStatus.IN_PROGRESS:
            self.active_sessions[sess_id] = SessionStatus.DEFENSE_SUCCESSFUL

    async def run_to_completion(
        self,
        scenario_id: str,
        session_id: Optional[str] = None,
    ) -> SessionResult:
        """Run all evaluation rounds to completion and return the aggregated session scorecard."""
        scenario = get_scenario(scenario_id)
        sess_id = session_id or generate_id("sess")
        turns: List[TurnRecord] = []

        async for turn in self.stream_session(scenario_id=scenario.scenario_id, session_id=sess_id):
            turns.append(turn)

        final_status = self.active_sessions.get(sess_id, SessionStatus.DEFENSE_SUCCESSFUL)

        # Calculate metrics
        tactics = list(dict.fromkeys(t.jev_report.metrics.tactic_detected.selected for t in turns))
        escalation_triggered = any(t.jev_report.metrics.escalation.triggered for t in turns)

        if turns:
            avg_fidelity = sum(t.jev_report.metrics.defender_fidelity.probability for t in turns) / len(turns)
            resilience_score = round(avg_fidelity * 100.0, 1)
        else:
            resilience_score = 0.0

        risk_scores = [t.jev_report.metrics.compliance_risk.score for t in turns]
        max_risk_score = max(risk_scores) if risk_scores else 0.0
        risk_labels = ["negligible", "low", "moderate", "high", "critical"]
        max_risk_label = risk_labels[min(int(round(max_risk_score)), len(risk_labels) - 1)]

        return SessionResult(
            session_id=sess_id,
            scenario=scenario,
            status=final_status,
            completed_rounds=len(turns),
            overall_resilience_score=resilience_score,
            tactics_observed=tactics,
            max_compliance_risk=max_risk_label,
            escalation_triggered=escalation_triggered,
            turns=turns,
        )


_engine_instance: Optional[OrchestrationEngine] = None


def get_orchestration_engine() -> OrchestrationEngine:
    """Singleton accessor for the orchestration engine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = OrchestrationEngine()
    return _engine_instance
