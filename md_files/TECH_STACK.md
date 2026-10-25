# 🛠️ Tech Stack & Implementation Blueprint
### The Retirement Whisperer: Multi-Agent Adversarial System

---

## 1. Core Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Decision Arbiter (System 1)** | `typesafe-ai` / TypeSafe Jev API | Sub-250ms deterministic decisions, calibrated scoring (`Choice`, `Score`, `Noul`) |
| **Agentic Framework (System 2)** | `langchain`, `langchain-core` | Autonomous agent execution, prompt chains, memory, tool orchestration |
| **Protocol & Data Modeling** | `pydantic` (v2.x) | A2A message validation, strict typed schemas, telemetry serialization |
| **Backend API & WebSockets** | `fastapi`, `uvicorn`, `websockets` | Evaluation runner, session state management, real-time event streaming |
| **Frontend Live Dashboard** | Vanilla HTML5, CSS3, Modern ES6+ | Glassmorphic executive dashboard, real-time threat radar, split-screen A2A viewer |
| **Environment & Config** | `python-dotenv` | Hermetic management of API keys (`LAYA_IMPOSSIBLE_API_KEY`, LLM keys) |

---

## 2. Directory & Project Structure

The project will follow a modular, production-grade layout:

```
JEV/
├── .env                              # Environment secrets (LAYA_IMPOSSIBLE_API_KEY, etc.)
├── .gitignore                        # Standard Python / Node gitignore
├── README.md                         # Quickstart & Executive Summary
├── ARCHITECTURE.md                   # Complete System Architecture
├── SYSTEM_SPEC.md                    # Requirements, Playbooks & Fiduciary Policies
├── A2A_PROTOCOL.md                   # Agent-to-Agent Message Envelope Specs
├── TECH_STACK.md                     # Tech Stack & Implementation Blueprint
│
├── requirements.txt                  # Python dependencies
│
├── whisperer/                        # Core Application Package
│   ├── __init__.py
│   ├── config.py                     # App settings, API keys, thresholds
│   │
│   ├── protocol/                     # A2A Protocol Implementation
│   │   ├── __init__.py
│   │   ├── schemas.py                # Pydantic models for A2AMessage, States, Verdicts
│   │   └── bus.py                    # In-memory async message event bus
│   │
│   ├── arbiter/                      # TypeSafe Jev Decision Engine
│   │   ├── __init__.py
│   │   ├── jev_client.py             # Jev SDK wrapper, connection pooling, retries
│   │   ├── evaluators.py             # Choice, Score, Noul evaluation suites
│   │   └── rules.py                  # Threshold rules & automatic escalation triggers
│   │
│   ├── agents/                       # Conversational Agents (LangChain)
│   │   ├── __init__.py
│   │   ├── base.py                   # Common Agent interface
│   │   ├── defender.py               # TIAA Retirement Assistant + Fiduciary Guardrails
│   │   ├── influence.py              # The Whisperer + Adversarial Playbooks
│   │   └── tools/                    # Defender Mock Retirement Tools
│   │       ├── __init__.py
│   │       ├── account_tools.py      # Balance, vesting, account status
│   │       ├── hardship_tools.py     # 72-hour hold, emergency qualification
│   │       └── beneficiary_tools.py  # MFA verification, beneficiary updates
│   │
│   ├── orchestrator/                 # Evaluation Runner & Lifecycle
│   │   ├── __init__.py
│   │   ├── engine.py                 # Multi-turn execution loop
│   │   └── scenarios.py              # Pre-configured adversarial scenario definitions
│   │
│   ├── server/                       # FastAPI Backend & WebSockets
│   │   ├── __init__.py
│   │   ├── app.py                    # REST endpoints & WebSocket server
│   │   └── routes.py                 # Session control APIs
│   │
│   └── web/                          # Real-Time Command & Resilience Dashboard
│       ├── index.html                # Visual interface with glassmorphic styling
│       ├── styles.css                # Polished dark mode, gradients, micro-animations
│       └── app.js                    # WebSocket client, live gauges, chat transcript
│
└── tests/                            # Test Suite
    ├── test_protocol.py              # A2A schema validation tests
    ├── test_jev_arbiter.py           # Jev evaluation unit tests
    └── test_orchestrator.py          # End-to-end multi-turn evaluation run
```

---

## 3. Dependency Manifest (`requirements.txt`)

```text
# Decision Arbiter (TypeSafe Jev)
typesafe-ai>=0.1.0

# Agentic Framework & LLM Integrations
langchain>=0.3.0
langchain-core>=0.3.0
langchain-openai>=0.2.0

# Protocol & Data Validation
pydantic>=2.8.0

# Server & Asynchronous Networking
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
websockets>=13.0
httpx>=0.27.0
python-dotenv>=1.0.0

# Testing & Utilities
pytest>=8.0.0
pytest-asyncio>=0.24.0
```

---

## 4. Environment Configuration

The application requires the following environment variables defined in `.env`:

```bash
# TypeSafe Jev API Key (Required for System One Arbiter)
LAYA_IMPOSSIBLE_API_KEY=imp-rt-...

# Primary LLM API Key (Used for Whisperer & Defender dialogue)
OPENAI_API_KEY=sk-...

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
LOG_LEVEL=INFO
```

---

## 5. Development & Execution Roadmap

1. **Phase 1: Foundation & Schemas**
   - Setup dependencies in a virtual environment.
   - Implement `whisperer/protocol/schemas.py` with strict A2A Pydantic structures.
   - Implement `whisperer/arbiter/jev_client.py` and verify connectivity with `LAYA_IMPOSSIBLE_API_KEY`.

2. **Phase 2: Agent Engineering & Tools**
   - Build Defender agent with mock TIAA retirement tools (`account_tools`, `hardship_tools`).
   - Build Influence agent with customizable red-team playbooks.
   - Test single-turn and multi-turn A2A message exchange.

3. **Phase 3: Jev Decision Engine Integration**
   - Connect Jev evaluation pipelines to analyze dialogue turns across `Choice`, `Score`, and `Noul`.
   - Wire automated escalation triggers when compliance thresholds are breached.

4. **Phase 4: Orchestration & Streaming UI**
   - Implement FastAPI WebSocket server to stream turns, Jev scores, and session verdicts.
   - Build the executive dashboard with live radar metrics, risk meters, and agent conversation viewer.
