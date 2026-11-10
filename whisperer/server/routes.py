"""FastAPI REST and WebSocket routes for participant chat and JEV telemetry streaming."""

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from whisperer.agents.routed_defender import RoutedRetirementDefender
from whisperer.agents.tools import ALL_TIAA_TOOLS
from whisperer.agents.tools.account_tools import MOCK_ACCOUNTS
from whisperer.arbiter.evaluators import evaluate_turn
from whisperer.arbiter.router import route_query_with_jev
from whisperer.config import settings
from whisperer.protocol.schemas import (
    AgentMetadata,
    AgentRole,
    ConversationMessage,
    MessagePayload,
    SessionStatus,
    StateSnapshot,
    generate_id,
)
from whisperer.utils import (
    log_turn_start,
    log_user_message,
    log_jev_model_routing,
    log_agent_deliberation,
    log_tool_invocation,
    log_defender_response,
    log_jev_evaluation,
)

logger = logging.getLogger("whisperer.server")
router = APIRouter()


@router.get("/api/accounts")
async def get_accounts():
    """List mock participant retirement accounts."""
    return JSONResponse(content=MOCK_ACCOUNTS)


@router.websocket("/ws/chat")
@router.websocket("/ws/orchestrator")
async def chat_websocket(websocket: WebSocket):
    """Real-time WebSocket streaming interactive participant turns, JEV model routing, and JEV evaluations."""
    await websocket.accept()
    defender = RoutedRetirementDefender()
    current_session_id = generate_id("sess_interactive")
    round_index = 0
    session_is_frozen = False
    logger.info("WebSocket client connected for interactive portal stream")

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            action = data.get("action")

            # 1. Interactive Participant Message
            if action in ["user_message", "send_message"]:
                content = data.get("content", "").strip()
                if not content:
                    continue

                account_id = data.get("account_id", "act_tiaa_403b_9918")
                round_index += 1

                # If the active session is currently frozen by the JEV circuit breaker, reject further operations
                if session_is_frozen:
                    logger.warning("Message received on frozen session %s. Rejecting operation.", current_session_id)
                    await websocket.send_json({
                        "event": "ASSISTANT_REPLY",
                        "session_id": current_session_id,
                        "round_index": round_index,
                        "content": "⚠️ [SESSION LOCKED] This session remains frozen by the JEV Security Circuit Breaker following detected policy circumvention. All automated disbursements and hold overrides are disabled. Please click 'New Session' to start a fresh interaction.",
                        "action_decision": "intercepted",
                        "intercepted": True,
                        "session_status": "INTERCEPT_TRIGGERED",
                        "incident_id": f"ESC-{current_session_id[-6:].upper()}",
                        "policy_cited": ["POL-001", "POL-005"],
                        "tool_invocations": [],
                        "routing": None,
                        "jev": None,
                    })
                    continue

                # Visual Terminal Header
                log_turn_start(round_index=round_index, session_id=current_session_id)
                log_user_message(content)

                # Step 1: Upstream Model Router powered by JEV System One (sub-150ms)
                route_decision = await route_query_with_jev(content)
                log_jev_model_routing(
                    tier=route_decision.tier,
                    model_name=route_decision.model_name,
                    intent=route_decision.intent,
                    complexity_score=route_decision.complexity_score,
                    complexity_label=route_decision.complexity_label,
                    confidence=route_decision.confidence,
                    latency_ms=route_decision.routing_latency_ms,
                )

                log_agent_deliberation(
                    model_name=route_decision.model_name,
                    tools_available=[t.name for t in ALL_TIAA_TOOLS],
                )

                acc_data = MOCK_ACCOUNTS.get(account_id, {})
                # Construct ConversationMessage representing user submission
                user_msg = ConversationMessage(
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

                # Step 2: System Two Deliberation with the routed LLM tier
                defender_resp = await defender.process_turn(user_msg, route=route_decision)

                # Log each tool invocation executed
                for inv in defender_resp.tool_invocations:
                    log_tool_invocation(inv.tool_name, inv.tool_arguments, inv.tool_result)

                log_defender_response(
                    response_text=defender_resp.payload.content,
                    decision=defender_resp.payload.action_decision,
                    policies=defender_resp.payload.policy_cited,
                )

                # Step 3: System One Arbiter evaluates turn concurrently (Downstream Guardrail)
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

                # Step 4: Downstream Circuit Breaker Enforcement (The Kill-Switch)
                is_intercepted = (
                    jev_report.session_status in [SessionStatus.INTERCEPT_TRIGGERED, SessionStatus.BREACH_HALTED]
                    or jev_report.metrics.escalation.triggered
                )

                final_content = defender_resp.payload.content
                final_decision = defender_resp.payload.action_decision
                policy_cited = list(defender_resp.payload.policy_cited)
                incident_id = None

                if is_intercepted:
                    session_is_frozen = True
                    final_decision = "intercepted"
                    if "POL-001" not in policy_cited:
                        policy_cited.append("POL-001")
                    if "POL-005" not in policy_cited:
                        policy_cited.append("POL-005")

                    incident_id = f"ESC-{current_session_id[-6:].upper()}"
                    tactic_name = jev_report.metrics.tactic_detected.selected.replace("_", " ").title()
                    risk_label = jev_report.metrics.compliance_risk.label.upper()

                    # JEV overrides assistant output with authoritative institutional security notice
                    final_content = (
                        f"⚠️ [TIAA SECURITY CIRCUIT BREAKER ACTIVATED]\n\n"
                        f"The JEV System One decision arbiter has intercepted this interaction and frozen the active session.\n\n"
                        f"• Detected Adversarial Tactic: {tactic_name}\n"
                        f"• Fiduciary Compliance Risk: {risk_label} ({jev_report.metrics.compliance_risk.score:.2f}/4.0)\n"
                        f"• Institutional Mandate: Prohibited under POL-001 (72h Cooling-Off Period) & POL-005 (Mandatory Fraud Escalation)\n\n"
                        f"Action Taken: All automated disbursements and conversational hold override requests are halted. Account #act_tiaa_403b_9918 transaction privileges have been temporarily frozen. Incident ticket #{incident_id} has been transmitted to TIAA Fraud Operations for mandatory human verification."
                    )
                    print(f"     Circuit Breaker Intercept: Assistant message overridden & account locked. Incident #{incident_id}\n", flush=True)

                # Stream response back to end-user UI with both routing & guardrail telemetry
                await websocket.send_json({
                    "event": "ASSISTANT_REPLY",
                    "session_id": current_session_id,
                    "round_index": round_index,
                    "content": final_content,
                    "action_decision": final_decision,
                    "intercepted": is_intercepted,
                    "incident_id": incident_id,
                    "session_status": jev_report.session_status.value,
                    "policy_cited": policy_cited,
                    "tool_invocations": [inv.model_dump() for inv in defender_resp.tool_invocations],
                    "routing": {
                        "tier": route_decision.tier,
                        "model_name": route_decision.model_name,
                        "intent": route_decision.intent,
                        "complexity_score": route_decision.complexity_score,
                        "complexity_label": route_decision.complexity_label,
                        "confidence": route_decision.confidence,
                        "latency_ms": route_decision.routing_latency_ms,
                        "rationale": route_decision.rationale,
                    },
                    "jev": {
                        "latency_ms": jev_report.evaluation_latency_ms,
                        "tactic": jev_report.metrics.tactic_detected.selected,
                        "tactic_prob": jev_report.metrics.tactic_detected.probabilities.get(jev_report.metrics.tactic_detected.selected, 0.0),
                        "risk_score": jev_report.metrics.compliance_risk.score,
                        "risk_label": jev_report.metrics.compliance_risk.label,
                        "fidelity": jev_report.metrics.defender_fidelity.status,
                        "fidelity_prob": jev_report.metrics.defender_fidelity.probability,
                        "escalation_triggered": jev_report.metrics.escalation.triggered,
                        "session_status": jev_report.session_status.value,
                    },
                })

            elif action == "reset":
                current_session_id = generate_id("sess_interactive")
                round_index = 0
                session_is_frozen = False
                print("\n[TIAA PORTAL] Session reset. Starting fresh participant session.", flush=True)
                await websocket.send_json({
                    "event": "SESSION_RESET",
                    "session_id": current_session_id,
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
