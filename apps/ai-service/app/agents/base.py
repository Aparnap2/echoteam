"""Base clone agent using LangGraph."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Literal
from pydantic import BaseModel, Field
from enum import Enum
from app.config import settings


class CloneType(str, Enum):
    """Types of clones in EchoTeam."""
    CALENDAR = "calendar"
    EMAIL = "email"
    OPS = "ops"


class ActionStatus(str, Enum):
    """Status of an action in the HITL flow."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


class CloneAction(BaseModel):
    """Represents an action to be taken by a clone."""
    id: str
    clone_type: CloneType
    action_type: str
    payload: dict
    confidence: float = Field(ge=0, le=1)
    status: ActionStatus = ActionStatus.PENDING

    def requires_approval(self) -> bool:
        """Determine if this action requires human approval."""
        # Outbound actions always require approval
        if self.action_type in settings.approval_actions:
            return True
        # Auto actions require approval if below confidence threshold
        if self.confidence < settings.confidence_threshold:
            return True
        return False


class CloneState(BaseModel):
    """State for a clone agent."""
    user_id: str
    clone_type: CloneType
    context: dict = Field(default_factory=dict)
    pending_actions: list[CloneAction] = Field(default_factory=list)
    memory: list[dict] = Field(default_factory=list)
    current_step: str = "analyze"


T = TypeVar("T", bound=CloneState)


class BaseCloneAgent(ABC, Generic[T]):
    """Base class for all clone agents using LangGraph."""

    def __init__(self, user_id: str, clone_type: CloneType):
        self.user_id = user_id
        self.clone_type = clone_type
        self.state = self.create_initial_state(user_id, clone_type)

    @abstractmethod
    def create_initial_state(self, user_id: str, clone_type: CloneType) -> T:
        """Create initial state for the agent."""
        pass

    @abstractmethod
    async def analyze_context(self) -> list[CloneAction]:
        """Analyze current context and generate potential actions."""
        pass

    @abstractmethod
    async def execute_action(self, action: CloneAction) -> dict:
        """Execute an approved action."""
        pass

    async def process(self) -> list[CloneAction]:
        """Main processing loop for the agent."""
        actions = await self.analyze_context()
        self.state.pending_actions.extend(actions)
        return actions

    def get_auto_actions(self) -> list[CloneAction]:
        """Get actions that can auto-execute."""
        return [
            action for action in self.state.pending_actions
            if not action.requires_approval() and action.status == ActionStatus.PENDING
        ]

    def get_approval_actions(self) -> list[CloneAction]:
        """Get actions that require human approval."""
        return [
            action for action in self.state.pending_actions
            if action.requires_approval()
        ]
