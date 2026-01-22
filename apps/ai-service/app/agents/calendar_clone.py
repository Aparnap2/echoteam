"""Calendar clone agent for managing calendar operations."""

import uuid
from datetime import datetime
from typing import Optional
from app.agents.base import (
    BaseCloneAgent,
    CloneAction,
    CloneState,
    CloneType,
    ActionStatus
)
from app.llm.ollama_client import ollama_client


class CalendarState(CloneState):
    """State for calendar clone agent."""
    events: list[dict] = []
    conflicts: list[dict] = []


class CalendarClone(BaseCloneAgent[CalendarState]):
    """Clone agent for calendar operations."""

    def create_initial_state(self, user_id: str, clone_type: CloneType) -> CalendarState:
        """Create initial state for calendar clone."""
        return CalendarState(
            user_id=user_id,
            clone_type=CloneType.CALENDAR,
            context={"timezone": "UTC"}
        )

    async def analyze_context(self) -> list[CloneAction]:
        """Analyze calendar context and generate potential actions."""
        actions = []

        # Simulate context analysis
        inbox_count = self.state.context.get("inbox_count", 0)
        meeting_conflicts = len(self.state.conflicts)

        # Generate focus block suggestion
        if inbox_count > 10:
            action = CloneAction(
                id=f"action_{uuid.uuid4().hex[:8]}",
                clone_type=CloneType.CALENDAR,
                action_type="create_focus_block",
                payload={"duration": 60, "reason": "High inbox volume"},
                confidence=0.92
            )
            actions.append(action)

        # Generate meeting prep action
        if len(self.state.events) > 0:
            action = CloneAction(
                id=f"action_{uuid.uuid4().hex[:8]}",
                clone_type=CloneType.CALENDAR,
                action_type="generate_meeting_prep",
                payload={"event_count": len(self.state.events)},
                confidence=0.88
            )
            actions.append(action)

        return actions

    async def execute_action(self, action: CloneAction) -> dict:
        """Execute an approved calendar action."""
        if action.action_type == "create_focus_block":
            return await self._create_focus_block(action.payload)
        elif action.action_type == "generate_meeting_prep":
            return await self._generate_meeting_prep(action.payload)
        else:
            return {"status": "unknown_action", "action": action.action_type}

    async def _create_focus_block(self, payload: dict) -> dict:
        """Create a focus time block."""
        duration = payload.get("duration", 60)
        return {
            "status": "success",
            "action": "create_focus_block",
            "details": {
                "duration_minutes": duration,
                "created_at": datetime.utcnow().isoformat()
            }
        }

    async def _generate_meeting_prep(self, payload: dict) -> dict:
        """Generate meeting preparation notes."""
        model = ollama_client.get_model_for_task("reasoning")
        prompt = "Generate brief meeting preparation notes based on the agenda."

        notes = await ollama_client.generate(
            model=model,
            prompt=prompt,
            system="You are a helpful assistant that creates meeting prep notes."
        )

        return {
            "status": "success",
            "action": "generate_meeting_prep",
            "details": {"notes": notes}
        }

    async def sync_calendar(self, events: list[dict]) -> None:
        """Sync calendar events from external source."""
        self.state.events = events

    async def detect_conflicts(self) -> list[dict]:
        """Detect calendar conflicts."""
        conflicts = []
        # Simple conflict detection
        for i, event1 in enumerate(self.state.events):
            for event2 in self.state.events[i + 1:]:
                if self._events_overlap(event1, event2):
                    conflicts.append({
                        "event1": event1.get("id"),
                        "event2": event2.get("id"),
                        "type": "overlap"
                    })
        self.state.conflicts = conflicts
        return conflicts

    def _events_overlap(self, event1: dict, event2: dict) -> bool:
        """Check if two events overlap in time."""
        start1 = datetime.fromisoformat(event1.get("start", ""))
        end1 = datetime.fromisoformat(event1.get("end", ""))
        start2 = datetime.fromisoformat(event2.get("start", ""))
        end2 = datetime.fromisoformat(event2.get("end", ""))

        return start1 < end2 and start2 < end1
