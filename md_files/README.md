# 🕵️ The Retirement Whisperer
### Adversarial Multi-Agent Resilience Platform for TIAA Retirement Systems

---

## Executive Summary

**The Retirement Whisperer** is an institutional-grade multi-agent adversarial resilience platform designed for **TIAA**. It tests and validates participant-facing AI retirement assistants against complex conversational social engineering, psychological manipulation, and policy circumvention before deployment.

The platform pairs **LangChain** conversational agents communicating over a strongly-typed **Agent-to-Agent (A2A) Protocol** with TypeSafe AI's **Jev** System One decision engine, providing sub-250ms deterministic compliance evaluations and fraud escalation triggers.

---

## 📚 Specification & Architecture Documents

The pre-implementation documentation suite is organized across four foundational specifications:

1. [ARCHITECTURE.md](file:///Users/harshshah/Projects/JEV/ARCHITECTURE.md)
   - High-level system architecture and separation of concerns.
   - Dual-agent interaction topology and the A2A protocol layer.
   - Jev System One arbiter integration, fan-out evaluation, and fail-safe policies.
   - Sequence diagrams and security boundary definitions.

2. [SYSTEM_SPEC.md](file:///Users/harshshah/Projects/JEV/SYSTEM_SPEC.md)
   - Core objectives, business drivers, and stakeholder personas at TIAA.
   - Three detailed adversarial attack playbooks (Emergency Hardship, Beneficiary Tampering, Market Panic).
   - TIAA fiduciary guardrails and compliance policy matrix (`POL-001` through `POL-005`).
   - Jev scoring rubric (`Choice`, `Score`, `Noul`) and performance SLAs.

3. [A2A_PROTOCOL.md](file:///Users/harshshah/Projects/JEV/A2A_PROTOCOL.md)
   - Formal JSON/Pydantic schemas for `A2AMessage`, `A2ADefenderResponse`, and `JevEvaluationReport`.
   - Finite State Machine (FSM) defining evaluation lifecycles and transition guard conditions.
   - Pacing, turn telemetry, and automatic fraud interception triggers.

4. [TECH_STACK.md](file:///Users/harshshah/Projects/JEV/TECH_STACK.md)
   - Complete technology stack manifest (`typesafe-ai`, `langchain`, `pydantic`, `fastapi`, modern web UI).
   - Module directory tree and architecture layout (`whisperer/`).
   - `requirements.txt` manifest and environment configuration details.
   - Step-by-step phased development roadmap.

---

## Key System Components

```
                   +---------------------------------------------+
                   |          The Retirement Whisperer           |
                   |           Adversarial Resilience            |
                   +---------------------------------------------+
                                          |
                     +--------------------+--------------------+
                     |                                         |
                     v                                         v
       +----------------------------+            +----------------------------+
       |       The Whisperer        |    A2A     |    Retirement Assistant    |
       |      (Influence Agent)     | <========> |         (Defender)         |
       |  - Social engineering      |  Protocol  |  - TIAA retirement tools   |
       |  - Pressure escalation     |            |  - Fiduciary policy checks |
       +----------------------------+            +----------------------------+
                     \                                         /
                      \                                       /
                       +------------------+------------------+
                                          |
                                          v
                            +---------------------------+
                            |       TypeSafe Jev        |
                            |   (System One Arbiter)    |
                            |   - Tactic classification |
                            |   - Compliance risk score |
                            |   - Defender resilience   |
                            |   - Immediate escalation  |
                            +---------------------------+
                                          |
                                          v
                            +---------------------------+
                            |     Live Command UI       |
                            |  - Turn-by-turn dialogue  |
                            |  - Calibrated risk meters |
                            |  - Vulnerability reports  |
                            +---------------------------+
```
