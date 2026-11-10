"""Base interface for conversational agents participating in evaluation turns."""

from abc import ABC, abstractmethod
from typing import Optional
from whisperer.protocol.schemas import (
    AgentMetadata,
    AgentRole,
    ConversationMessage,
    DefenderResponse,
)


class BaseAgent(ABC):
    """Abstract conversational agent operating over evaluation turns."""

    def __init__(self, agent_id: str, role: AgentRole, persona: Optional[str] = None):
        self.metadata = AgentMetadata(
            agent_id=agent_id,
            role=role,
            persona=persona,
        )

    @property
    def agent_id(self) -> str:
        return self.metadata.agent_id

    @property
    def role(self) -> AgentRole:
        return self.metadata.role

    @property
    def persona(self) -> Optional[str]:
        return self.metadata.persona

    @abstractmethod
    async def process_turn(self, incoming_message: ConversationMessage) -> DefenderResponse:
        """Process incoming turn message and generate response envelope."""
        pass
