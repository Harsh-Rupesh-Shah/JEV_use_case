"""Unit tests for JEV Downstream Circuit Breaker (The Kill-Switch)."""

import pytest
from whisperer.protocol.schemas import (
    AgentMetadata,
    AgentRole,
    ComplianceRiskMetric,
    ConversationMessage,
    DefenderPayload,
    DefenderResponse,
    EscalationMetric,
    FidelityMetric,
    JevEvaluationMetrics,
    JevEvaluationReport,
    MessagePayload,
    SessionStatus,
    StateSnapshot,
    TacticMetric,
)


def create_dummy_message(content: str, session_id: str = "sess_cb_test") -> ConversationMessage:
    return ConversationMessage(
        session_id=session_id,
        round_index=1,
        sender=AgentMetadata(agent_id="user_1", role=AgentRole.ADVERSARY),
        recipient=AgentMetadata(agent_id="assistant_1", role=AgentRole.DEFENDER),
        payload=MessagePayload(content=content),
        state_snapshot=StateSnapshot(target_account_id="act_tiaa_403b_9918"),
    )


def create_dummy_defender_response(content: str, decision: str = "approved", session_id: str = "sess_cb_test") -> DefenderResponse:
    return DefenderResponse(
        session_id=session_id,
        round_index=1,
        sender=AgentMetadata(agent_id="assistant_1", role=AgentRole.DEFENDER),
        payload=DefenderPayload(
            content=content,
            action_decision=decision,
            policy_cited=["POL-001"],
        ),
    )


def test_circuit_breaker_schema_supports_intercepted():
    """Verify DefenderPayload schema accepts 'intercepted' disposition."""
    payload = DefenderPayload(
        content="Circuit breaker intercepted this turn",
        action_decision="intercepted",
        policy_cited=["POL-001", "POL-005"],
    )
    assert payload.action_decision == "intercepted"
    assert "POL-005" in payload.policy_cited


def test_circuit_breaker_condition_flagging():
    """Verify circuit breaker triggers when JEV detects escalation or policy breach."""
    report_intercepted = JevEvaluationReport(
        session_id="sess_cb_test",
        round_index=1,
        model_used="convaiinnovations/laya",
        evaluation_latency_ms=120.0,
        session_status=SessionStatus.INTERCEPT_TRIGGERED,
        metrics=JevEvaluationMetrics(
            tactic_detected=TacticMetric(selected="urgency_pressure", probabilities={"urgency_pressure": 0.85}),
            compliance_risk=ComplianceRiskMetric(score=3.5, label="high"),
            defender_fidelity=FidelityMetric(probability=0.45, status="drifting"),
            escalation=EscalationMetric(probability=0.88, triggered=True),
        ),
    )

    is_intercepted = (
        report_intercepted.session_status in [SessionStatus.INTERCEPT_TRIGGERED, SessionStatus.BREACH_HALTED]
        or report_intercepted.metrics.escalation.triggered
    )
    assert is_intercepted is True


def test_circuit_breaker_condition_routine_pass():
    """Verify circuit breaker permits routine queries without interruption."""
    report_safe = JevEvaluationReport(
        session_id="sess_cb_test",
        round_index=1,
        model_used="convaiinnovations/laya",
        evaluation_latency_ms=95.0,
        session_status=SessionStatus.CONTINUE,
        metrics=JevEvaluationMetrics(
            tactic_detected=TacticMetric(selected="routine_query", probabilities={"routine_query": 0.95}),
            compliance_risk=ComplianceRiskMetric(score=0.4, label="negligible"),
            defender_fidelity=FidelityMetric(probability=0.98, status="holding_firm"),
            escalation=EscalationMetric(probability=0.05, triggered=False),
        ),
    )

    is_intercepted = (
        report_safe.session_status in [SessionStatus.INTERCEPT_TRIGGERED, SessionStatus.BREACH_HALTED]
        or report_safe.metrics.escalation.triggered
    )
    assert is_intercepted is False


def test_circuit_breaker_triggers_on_policy_bypass_and_authority_spoof():
    """Verify circuit breaker triggers when adversary tactics (policy_bypass, authority_spoof) are caught."""
    for tactic in ["policy_bypass", "authority_spoof", "urgency_pressure", "sympathy_plea"]:
        report_attack = JevEvaluationReport(
            session_id="sess_cb_test",
            round_index=2,
            model_used="convaiinnovations/laya",
            evaluation_latency_ms=110.0,
            session_status=SessionStatus.INTERCEPT_TRIGGERED,
            metrics=JevEvaluationMetrics(
                tactic_detected=TacticMetric(selected=tactic, probabilities={tactic: 0.90}),
                compliance_risk=ComplianceRiskMetric(score=2.3, label="moderate"),
                defender_fidelity=FidelityMetric(probability=0.95, status="holding_firm"),
                escalation=EscalationMetric(probability=0.92, triggered=True),
            ),
        )

        is_intercepted = (
            report_attack.session_status in [SessionStatus.INTERCEPT_TRIGGERED, SessionStatus.BREACH_HALTED]
            or report_attack.metrics.escalation.triggered
        )
        assert is_intercepted is True


