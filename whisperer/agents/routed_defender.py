"""Dynamic Model-Routed Retirement Assistant Defender using LangChain create_agent."""

import json
import logging
import warnings
from typing import Any, Dict, List, Optional
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

warnings.filterwarnings("ignore", message=".*Deserializing unregistered type.*")

from whisperer.agents.base import BaseAgent
from whisperer.agents.defender import DEFENDER_SYSTEM_PROMPT
from whisperer.agents.llm_factory import get_fast_llm, get_reasoning_llm
from whisperer.agents.tools import ALL_TIAA_TOOLS
from whisperer.arbiter.router import ModelRouteDecision
from whisperer.protocol.schemas import (
    AgentRole,
    ConversationMessage,
    DefenderPayload,
    DefenderResponse,
    ToolInvocation,
)

logger = logging.getLogger("whisperer.agents.routed_defender")


class RoutedRetirementDefender(BaseAgent):
    """Retirement Assistant that dynamically executes via Fast or Reasoning LLM tiers based on JEV routing."""

    def __init__(
        self,
        agent_id: str = "tiaa_routed_defender",
        persona: str = "fiduciary_retirement_consultant",
    ):
        super().__init__(agent_id=agent_id, role=AgentRole.DEFENDER, persona=persona)
        self.memory = MemorySaver()

        # Tier 1: Fast LLM (Gemini Flash-Lite)
        try:
            self.fast_llm = get_fast_llm(temperature=0.2)
            self.fast_agent = create_agent(
                model=self.fast_llm,
                tools=ALL_TIAA_TOOLS,
                system_prompt=DEFENDER_SYSTEM_PROMPT,
                response_format=DefenderPayload,
                checkpointer=self.memory,
            )
        except Exception as e:
            logger.warning("Could not initialize Fast Agent: %s", e)
            self.fast_agent = None

        # Tier 2: Reasoning LLM (Nemotron 3.5 via OpenRouter with Gemini fallback)
        try:
            self.reasoning_llm = get_reasoning_llm(temperature=0.2)
            self.reasoning_agent = create_agent(
                model=self.reasoning_llm,
                tools=ALL_TIAA_TOOLS,
                system_prompt=DEFENDER_SYSTEM_PROMPT,
                response_format=DefenderPayload,
                checkpointer=self.memory,
            )
        except Exception as e:
            logger.warning("Could not initialize Reasoning Agent: %s", e)
            self.reasoning_agent = None

    async def process_turn(
        self,
        incoming_message: ConversationMessage,
        route: Optional[ModelRouteDecision] = None,
    ) -> DefenderResponse:
        """Autonomously process incoming turn with the routed LLM tier."""
        user_text = incoming_message.payload.content
        account_id = incoming_message.state_snapshot.target_account_id or "act_tiaa_403b_9918"
        session_id = incoming_message.session_id

        # Determine target agent based on JEV's upstream routing verdict
        tier = route.tier if route else "fast"
        target_agent = self.reasoning_agent if (tier == "reasoning" and self.reasoning_agent) else self.fast_agent

        tool_invocations: List[ToolInvocation] = []
        payload: Optional[DefenderPayload] = None

        if target_agent:
            try:
                config = {"configurable": {"thread_id": f"{session_id}_{tier}"}}
                prompt_with_context = f"[Participant Account ID: {account_id}] {user_text}"

                result = await target_agent.ainvoke(
                    {"messages": [{"role": "user", "content": prompt_with_context}]},
                    config=config,
                )

                # Extract structured payload if available
                structured = result.get("structured_response")
                if isinstance(structured, DefenderPayload):
                    payload = structured
                elif isinstance(structured, dict):
                    payload = DefenderPayload(**structured)

                # Extract tool invocations
                tool_args_map: Dict[str, Any] = {}
                fallback_text = ""

                for msg in result.get("messages", []):
                    if isinstance(msg, AIMessage):
                        if msg.tool_calls:
                            for tc in msg.tool_calls:
                                tool_args_map[tc["id"]] = (tc.get("name"), tc.get("args", {}))
                        if msg.content:
                            if isinstance(msg.content, str):
                                fallback_text = msg.content
                            elif isinstance(msg.content, list):
                                fallback_text = "".join(p.get("text", "") for p in msg.content if isinstance(p, dict))

                    elif isinstance(msg, ToolMessage):
                        tool_id = getattr(msg, "tool_call_id", None)
                        tool_name, args = tool_args_map.get(tool_id, (getattr(msg, "name", "tool"), {}))

                        if tool_name == "DefenderPayload":
                            continue

                        try:
                            tool_res = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                        except Exception:
                            tool_res = {"result": msg.content}

                        tool_invocations.append(ToolInvocation(
                            tool_name=tool_name,
                            tool_arguments=args,
                            tool_result=tool_res if isinstance(tool_res, dict) else {"raw": str(tool_res)},
                        ))

                if not payload:
                    policies = [p for p in ["POL-001", "POL-002", "POL-003", "POL-004", "POL-005"] if p in fallback_text]
                    is_declined = any(w in fallback_text.lower() for w in ["cannot waive", "cannot override", "strictly prohibits", "declined", "hold active"])
                    payload = DefenderPayload(
                        content=fallback_text,
                        policy_cited=policies,
                        action_decision="declined" if is_declined else "approved",
                    )

            except Exception as e:
                logger.exception("Error in RoutedDefender (%s tier) execution: %s", tier, e)

        # Fallback if both primary and reasoning execution failed
        if not payload:
            payload = DefenderPayload(
                content="Under TIAA fiduciary policy POL-001, early distributions during active cooling-off holds cannot be processed through chat.",
                policy_cited=["POL-001"],
                action_decision="declined",
            )

        # Ensure blocked tool results strictly enforce declined disposition and POL-001 citation
        if any(inv.tool_result.get("status") == "blocked" or inv.tool_result.get("override_granted") is False for inv in tool_invocations):
            payload.action_decision = "declined"
            if "POL-001" not in payload.policy_cited:
                payload.policy_cited.append("POL-001")

        return DefenderResponse(
            session_id=session_id,
            round_index=incoming_message.round_index,
            sender=self.metadata,
            payload=payload,
            tool_invocations=tool_invocations,
        )

