"""End-to-end integration tests for multi-round adversarial evaluation execution."""

import pytest
from whisperer.orchestrator.engine import get_orchestration_engine
from whisperer.orchestrator.scenarios import list_available_scenarios


def test_list_scenarios():
    """Verify pre-configured attack scenarios are loaded properly."""
    scenarios = list_available_scenarios()
    assert len(scenarios) >= 2
    scenario_ids = [s.scenario_id for s in scenarios]
    assert "hardship_override" in scenario_ids
    assert "beneficiary_substitution" in scenario_ids


@pytest.mark.asyncio
async def test_run_evaluation_to_completion():
    """Verify running a full multi-round adversarial evaluation session through Jev and scoring resilience."""
    engine = get_orchestration_engine()

    result = await engine.run_to_completion(
        scenario_id="hardship_override",
        session_id="sess_integration_run_01",
    )

    assert result.session_id == "sess_integration_run_01"
    assert result.completed_rounds >= 1
    assert result.overall_resilience_score > 0
    assert len(result.turns) == result.completed_rounds
    assert len(result.tactics_observed) > 0

    print(
        f"\n[Evaluation Complete] Scenario: {result.scenario.title}"
        f"\n  Final Status: {result.status}"
        f"\n  Completed Rounds: {result.completed_rounds}"
        f"\n  Resilience Score: {result.overall_resilience_score}%"
        f"\n  Max Compliance Risk: {result.max_compliance_risk}"
        f"\n  Tactics Observed: {result.tactics_observed}"
    )

    for turn in result.turns:
        print(
            f"  Round {turn.round_index} | Tactic: {turn.jev_report.metrics.tactic_detected.selected:<18} "
            f"| Risk: {turn.jev_report.metrics.compliance_risk.label:<10} "
            f"| Fidelity: {turn.jev_report.metrics.defender_fidelity.probability:.2f} "
            f"| Latency: {turn.jev_report.evaluation_latency_ms:.0f}ms"
        )
