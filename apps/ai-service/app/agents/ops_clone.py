"""Ops clone agent for managing tasks and operations."""

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


class OpsState(CloneState):
    """State for ops clone agent."""
    tasks: list[dict] = []
    projects: list[dict] = []


class OpsClone(BaseCloneAgent[OpsState]):
    """Clone agent for operations/tasks management."""

    def create_initial_state(self, user_id: str, clone_type: CloneType) -> OpsState:
        """Create initial state for ops clone."""
        return OpsState(
            user_id=user_id,
            clone_type=CloneType.OPS,
            context={"workspace": "notion"}
        )

    async def analyze_context(self) -> list[CloneAction]:
        """Analyze operations context and generate potential actions."""
        actions = []

        # Analyze overdue tasks
        overdue_tasks = [t for t in self.state.tasks if t.get("status") == "overdue"]
        today_tasks = [t for t in self.state.tasks if t.get("due_date") == datetime.utcnow().date().isoformat()]

        if len(overdue_tasks) > 0:
            # Prioritize overdue tasks (auto-execute)
            action = CloneAction(
                id=f"action_{uuid.uuid4().hex[:8]}",
                clone_type=CloneType.OPS,
                action_type="prioritize_tasks",
                payload={"count": len(overdue_tasks)},
                confidence=0.92
            )
            actions.append(action)

        # Suggest new tasks from context
        if self.state.context.get("email_count", 0) > 5:
            action = CloneAction(
                id=f"action_{uuid.uuid4().hex[:8]}",
                clone_type=CloneType.OPS,
                action_type="suggest_tasks",
                payload={"source": "email"},
                confidence=0.88
            )
            actions.append(action)

        # Create task action (auto-execute with undo)
        action = CloneAction(
            id=f"action_{uuid.uuid4().hex[:8]}",
            clone_type=CloneType.OPS,
            action_type="create_task",
            payload={"title": "Review inbox", "source": "clone_suggestion"},
            confidence=0.90
        )
        actions.append(action)

        return actions

    async def execute_action(self, action: CloneAction) -> dict:
        """Execute an approved operations action."""
        if action.action_type == "prioritize_tasks":
            return await self._prioritize_tasks(action.payload)
        elif action.action_type == "suggest_tasks":
            return await self._suggest_tasks(action.payload)
        elif action.action_type == "create_task":
            return await self._create_task(action.payload)
        elif action.action_type == "update_task":
            return await self._update_task(action.payload)
        else:
            return {"status": "unknown_action", "action": action.action_type}

    async def _prioritize_tasks(self, payload: dict) -> dict:
        """Prioritize tasks based on urgency and importance."""
        count = payload.get("count", 0)
        return {
            "status": "success",
            "action": "prioritize_tasks",
            "details": {
                "tasks_prioritized": count,
                "method": "urgency_sort"
            }
        }

    async def _suggest_tasks(self, payload: dict) -> dict:
        """Suggest tasks based on context."""
        model = ollama_client.get_model_for_task("reasoning")
        source = payload.get("source", "context")

        suggestions = await ollama_client.generate(
            model=model,
            prompt="Suggest 3 tasks based on high email volume",
            system="You are a productivity assistant. Suggest actionable tasks."
        )

        return {
            "status": "success",
            "action": "suggest_tasks",
            "details": {"source": source, "suggestions": suggestions}
        }

    async def _create_task(self, payload: dict) -> dict:
        """Create a new task."""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = {
            "id": task_id,
            "title": payload.get("title"),
            "status": "pending",
            "source": payload.get("source", "manual"),
            "created_at": datetime.utcnow().isoformat()
        }
        self.state.tasks.append(task)

        return {
            "status": "success",
            "action": "create_task",
            "details": {"task_id": task_id}
        }

    async def _update_task(self, payload: dict) -> dict:
        """Update an existing task."""
        task_id = payload.get("task_id")
        updates = payload.get("updates", {})

        for task in self.state.tasks:
            if task.get("id") == task_id:
                task.update(updates)
                break

        return {
            "status": "success",
            "action": "update_task",
            "details": {"task_id": task_id}
        }

    async def sync_tasks(self, tasks: list[dict]) -> None:
        """Sync tasks from external source."""
        self.state.tasks = tasks

    async def sync_projects(self, projects: list[dict]) -> None:
        """Sync projects from external source."""
        self.state.projects = projects

    async def get_tasks(self, status: Optional[str] = None) -> list[dict]:
        """Get tasks, optionally filtered by status."""
        if status:
            return [t for t in self.state.tasks if t.get("status") == status]
        return self.state.tasks
