"""FastAPI REST and WebSocket routes for session control and telemetry streaming."""

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from whisperer.agents.tools.account_tools import MOCK_ACCOUNTS
from whisperer.orchestrator.engine import get_orchestration_engine
from whisperer.orchestrator.scenarios import list_available_scenarios

from whisperer.agents.defender import RetirementAssistantDefender
from whisperer.agents.tools import ALL_TIAA_TOOLS
from whisperer.arbiter.evaluators import evaluate_turn
from whisperer.config import settings
from whisperer.protocol.schemas import (
    A2AMessage,
    AgentMetadata,
    AgentRole,
    MessagePayload,
    StateSnapshot,
    generate_id,
)
from whisperer.utils import (
    log_turn_start,
    log_user_message,
    log_agent_deliberation,
    log_tool_invocation,
    log_defender_response,
    log_jev_evaluation,
)

logger = logging.getLogger("whisperer.server")
router = APIRouter()


@router.get("/api/scenarios")
async def get_scenarios():
    """List all available adversarial attack scenarios."""
    scenarios = list_available_scenarios()
    return JSONResponse(content=[s.model_dump() for s in scenarios])


@router.get("/api/accounts")
async def get_accounts():
    """List mock participant retirement accounts."""
    return JSONResponse(content=MOCK_ACCOUNTS)


@router.post("/api/evaluations/run/{scenario_id}")
async def run_evaluation(scenario_id: str):
    """Run full evaluation to completion and return executive scorecard."""
    engine = get_orchestration_engine()
    result = await engine.run_to_completion(scenario_id=scenario_id)
    return JSONResponse(content=result.model_dump())


@router.websocket("/ws/orchestrator")
@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    """Real-time WebSocket streaming interactive human participant turns and automated evaluations."""
    await websocket.accept()
    engine = get_orchestration_engine()
    defender = RetirementAssistantDefender()
    current_session_id = generate_id("sess_interactive")
    round_index = 0
    logger.info("WebSocket client connected for interactive portal stream")

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            action = data.get("action")

            # 1. Interactive Human Participant Message
            if action in ["user_message", "send_message"]:
                content = data.get("content", "").strip()
                if not content:
                    continue

                account_id = data.get("account_id", "act_tiaa_403b_9918")
                round_index += 1

                # Visual Terminal Header
                log_turn_start(round_index=round_index, session_id=current_session_id)
                log_user_message(content)
                log_agent_deliberation(
                    model_name=settings.GEMINI_MODEL,
                    tools_available=[t.name for t in ALL_TIAA_TOOLS],
                )

                acc_data = MOCK_ACCOUNTS.get(account_id, {})
                # Construct A2AMessage representing user submission
                user_msg = A2AMessage(
                    session_id=current_session_id,
                    round_index=round_index,
                    sender=AgentMetadata(
                        agent_id="human_participant_01",
                        role=AgentRole.ADVERSARY,
                        persona="human_participant_eleanor_vance",
                    ),
                    recipient=AgentMetadata(
                        agent_id="tiaa_retirement_assistant_01",
                        role=AgentRole.DEFENDER,
                    ),
                    payload=MessagePayload(
                        content=content,
                        urgency_level="high" if any(w in content.lower() for w in ["urgent", "surgery", "emergency", "immediately", "today", "now"]) else "medium",
                    ),
                    state_snapshot=StateSnapshot(
                        target_account_id=account_id,
                        current_balance=acc_data.get("total_balance", 284500.00),
                        vested_balance=acc_data.get("vested_balance", 284500.00),
                        plan_type=acc_data.get("plan_type", "403(b)"),
                        pending_holds=acc_data.get("active_holds", ["HOLD_72H_HARDSHIP"]),
                        mfa_verified=False,
                    ),
                )

                # System Two: Defender processes turn with bound LangChain tools
                defender_resp = await defender.process_turn(user_msg)

                # Log each tool invocation executed
                for inv in defender_resp.tool_invocations:
                    log_tool_invocation(inv.tool_name, inv.tool_arguments, inv.tool_result)

                log_defender_response(
                    response_text=defender_resp.payload.content,
                    decision=defender_resp.payload.action_decision,
                    policies=defender_resp.payload.policy_cited,
                )

                # System One: Jev Arbiter evaluates turn concurrently
                jev_report = await evaluate_turn(user_msg, defender_resp)

                log_jev_evaluation(
                    latency_ms=jev_report.evaluation_latency_ms,
                    tactic=jev_report.metrics.tactic_detected.selected,
                    tactic_prob=jev_report.metrics.tactic_detected.probabilities.get(jev_report.metrics.tactic_detected.selected, 0.0),
                    risk_score=jev_report.metrics.compliance_risk.score,
                    risk_label=jev_report.metrics.compliance_risk.label,
                    fidelity=jev_report.metrics.defender_fidelity.status,
                    fidelity_prob=jev_report.metrics.defender_fidelity.probability,
                    escalation=jev_report.metrics.escalation.triggered,
                    session_status=jev_report.session_status,
                )


                # Stream response back to end-user UI
                await websocket.send_json({
                    "event": "ASSISTANT_REPLY",
                    "session_id": current_session_id,
                    "round_index": round_index,
                    "content": defender_resp.payload.content,
                    "action_decision": defender_resp.payload.action_decision,
                    "policy_cited": defender_resp.payload.policy_cited,
                    "tool_invocations": [inv.model_dump() for inv in defender_resp.tool_invocations],
                    "jev": {
                        "latency_ms": jev_report.evaluation_latency_ms,
                        "tactic": jev_report.metrics.tactic_detected.selected,
                        "tactic_prob": jev_report.metrics.tactic_detected.probabilities.get(jev_report.metrics.tactic_detected.selected, 0.0),
                        "risk_score": jev_report.metrics.compliance_risk.score,
                        "risk_label": jev_report.metrics.compliance_risk.label,
                        "fidelity": jev_report.metrics.defender_fidelity.status,
                        "fidelity_prob": jev_report.metrics.defender_fidelity.probability,
                    },
                })

            elif action == "reset":
                current_session_id = generate_id("sess_interactive")
                round_index = 0
                print("\n[TIAA PORTAL] Session reset. Starting fresh participant session.", flush=True)
                await websocket.send_json({
                    "event": "SESSION_RESET",
                    "session_id": current_session_id,
                })

            # 2. Automated Adversarial Assessment Mode (for automated validation)
            elif action == "start":
                scenario_id = data.get("scenario_id", "hardship_override")
                logger.info("Received start signal for scenario: %s", scenario_id)

                await websocket.send_json({
                    "event": "SESSION_STARTED",
                    "scenario_id": scenario_id,
                })

                async for turn in engine.stream_session(scenario_id=scenario_id):
                    await websocket.send_json({
                        "event": "TURN_COMPLETED",
                        "round_index": turn.round_index,
                        "turn": turn.model_dump(),
                    })

                res = await engine.run_to_completion(scenario_id=scenario_id)
                await websocket.send_json({
                    "event": "SESSION_FINISHED",
                    "summary": {
                        "session_id": res.session_id,
                        "status": res.status,
                        "completed_rounds": res.completed_rounds,
                        "overall_resilience_score": res.overall_resilience_score,
                        "max_compliance_risk": res.max_compliance_risk,
                        "tactics_observed": res.tactics_observed,
                        "escalation_triggered": res.escalation_triggered,
                    },
                })

            elif action == "ping":
                await websocket.send_json({"event": "pong"})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.exception("Error in chat WebSocket: %s", e)
        try:
            await websocket.send_json({"event": "ERROR", "message": str(e)})
        except Exception:
            pass
