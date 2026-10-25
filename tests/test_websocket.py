"""Test WebSocket streaming and real-time event dispatch."""

import json
from fastapi.testclient import TestClient
from whisperer.server.app import app


def test_websocket_orchestrator_stream():
    """Stream live evaluation through FastAPI WebSocket in-memory using TestClient."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/orchestrator") as ws:
            ws.send_json({
                "action": "start",
                "scenario_id": "hardship_override",
            })

            # Read first event: SESSION_STARTED
            start_event = ws.receive_json()
            assert start_event.get("event") == "SESSION_STARTED"
            assert start_event.get("scenario_id") == "hardship_override"

            # Read at least one turn event
            turn_event = ws.receive_json()
            assert turn_event.get("event") == "TURN_COMPLETED"
            assert turn_event.get("round_index") == 1
            turn_data = turn_event.get("turn", {})
            assert "jev_report" in turn_data
            assert "adversary_message" in turn_data
            assert "defender_response" in turn_data
