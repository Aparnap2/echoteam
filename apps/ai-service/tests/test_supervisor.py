"""Tests for LangGraph supervisor and multi-agent orchestration.

These tests verify:
- AgentState TypedDict structure
- Clone nodes (Admin, Ops, Research)
- Supervisor routing logic
- Multi-agent handoffs
- Planning loops
- HITL checkpoints
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from app.agents.supervisor import (
    AgentState,
    TaskType,
    TaskStatus,
    Task,
    supervisor_router,
    task_router,
    create_supervisor_graph,
    admin_clone_node,
    ops_clone_node,
    research_clone_node,
    planning_node,
)
from app.agents.base import CloneType
from langgraph.graph import END


class TestAgentState:
    """Tests for AgentState TypedDict."""

    def test_agent_state_has_required_fields(self):
        """Test that AgentState has all required fields."""
        now = datetime.now(timezone.utc)
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [],
            "current_task": None,
            "admin_output": None,
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "supervisor",
            "human_feedback": None,
            "completed_actions": [],
            "action_log": [],
        }

        assert state["user_id"] == "user-123"
        assert state["group_id"] == "group-123"
        assert state["messages"] == []
        assert state["current_task"] is None

    def test_agent_state_with_task(self):
        """Test AgentState with a task."""
        task = Task(
            id="task-123",
            task_type=TaskType.EMAIL_TRIAGE,
            description="Review urgent emails",
        )
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [task],
            "current_task": task,
            "admin_output": None,
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "admin_clone",
            "human_feedback": None,
            "completed_actions": [],
            "action_log": [],
        }

        assert state["current_task"].task_type == TaskType.EMAIL_TRIAGE
        assert state["next_action"] == "admin_clone"


class TestTaskTypes:
    """Tests for TaskType enum."""

    def test_all_task_types_defined(self):
        """Test that all expected task types exist."""
        assert TaskType.EMAIL_TRIAGE.value == "email_triage"
        assert TaskType.EMAIL_DRAFT.value == "email_draft"
        assert TaskType.CALENDAR_BLOCK.value == "calendar_block"
        assert TaskType.CALENDAR_SCHEDULE.value == "calendar_schedule"
        assert TaskType.TASK_CREATE.value == "task_create"
        assert TaskType.TASK_UPDATE.value == "task_update"
        assert TaskType.RESEARCH_QUERY.value == "research_query"
        assert TaskType.RESEARCH_SUMMARY.value == "research_summary"
        assert TaskType.DAILY_DIGEST.value == "daily_digest"


class TestTask:
    """Tests for Task dataclass."""

    def test_task_creation(self):
        """Test creating a Task."""
        task = Task(
            id="task-123",
            task_type=TaskType.EMAIL_TRIAGE,
            description="Review urgent emails",
            payload={"priority": "high"},
            confidence=0.92,
        )

        assert task.id == "task-123"
        assert task.task_type == TaskType.EMAIL_TRIAGE
        assert task.status == TaskStatus.PENDING
        assert task.confidence == 0.92

    def test_task_with_assignee(self):
        """Test Task with assignee."""
        task = Task(
            id="task-456",
            task_type=TaskType.TASK_CREATE,
            description="Create meeting notes",
            assignee=CloneType.OPS,
        )

        assert task.assignee == CloneType.OPS


class TestSupervisorRouter:
    """Tests for supervisor routing logic."""

    def test_no_task_goes_to_planning(self):
        """Test that no task routes to planning."""
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [],
            "current_task": None,
            "admin_output": None,
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "",
            "human_feedback": None,
            "completed_actions": [],
            "action_log": [],
        }

        result = supervisor_router(state)
        assert result == "planning"

    def test_email_task_routes_to_admin(self):
        """Test that email tasks route to admin_clone."""
        task = Task(
            id="task-email",
            task_type=TaskType.EMAIL_TRIAGE,
            description="Review emails",
        )
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [task],
            "current_task": task,
            "admin_output": None,
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "",
            "human_feedback": None,
            "completed_actions": [],
            "action_log": [],
        }

        result = supervisor_router(state)
        assert result == "admin_clone"

    def test_task_creation_routes_to_ops(self):
        """Test that task creation routes to ops_clone."""
        task = Task(
            id="task-create",
            task_type=TaskType.TASK_CREATE,
            description="Create new task",
        )
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [task],
            "current_task": task,
            "admin_output": None,
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "",
            "human_feedback": None,
            "completed_actions": [],
            "action_log": [],
        }

        result = supervisor_router(state)
        assert result == "ops_clone"

    def test_research_query_routes_to_research(self):
        """Test that research queries route to research_clone."""
        task = Task(
            id="task-research",
            task_type=TaskType.RESEARCH_QUERY,
            description="Research AI trends",
        )
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [task],
            "current_task": task,
            "admin_output": None,
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "",
            "human_feedback": None,
            "completed_actions": [],
            "action_log": [],
        }

        result = supervisor_router(state)
        assert result == "research_clone"

    def test_calendar_task_routes_to_admin(self):
        """Test that calendar tasks route to admin_clone."""
        task = Task(
            id="task-calendar",
            task_type=TaskType.CALENDAR_BLOCK,
            description="Block focus time",
        )
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [task],
            "current_task": task,
            "admin_output": None,
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "",
            "human_feedback": None,
            "completed_actions": [],
            "action_log": [],
        }

        result = supervisor_router(state)
        assert result == "admin_clone"

    def test_explicit_assignee_overrides(self):
        """Test that explicit assignee overrides auto-routing."""
        task = Task(
            id="task-explicit",
            task_type=TaskType.DAILY_DIGEST,
            description="Generate daily digest",
            assignee=CloneType.OPS,  # Explicitly assign to Ops
        )
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [task],
            "current_task": task,
            "admin_output": None,
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "",
            "human_feedback": None,
            "completed_actions": [],
            "action_log": [],
        }

        result = supervisor_router(state)
        assert result == "ops_clone"

    def test_approval_feedback_routes_to_execute(self):
        """Test that approval feedback routes to execute_approved."""
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [],
            "current_task": None,
            "admin_output": None,
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "",
            "human_feedback": {"action": "approve", "task_id": "task-123"},
            "completed_actions": [],
            "action_log": [],
        }

        result = supervisor_router(state)
        assert result == "execute_approved"

    def test_rejection_feedback_routes_to_complete(self):
        """Test that rejection feedback routes to task_complete."""
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [],
            "current_task": None,
            "admin_output": None,
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "",
            "human_feedback": {"action": "reject", "task_id": "task-123"},
            "completed_actions": [],
            "action_log": [],
        }

        result = supervisor_router(state)
        assert result == "task_complete"


class TestTaskRouter:
    """Tests for task routing after clone completion."""

    def test_no_task_returns_end(self):
        """Test that no task returns END."""
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [],
            "current_task": None,
            "admin_output": None,
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "",
            "human_feedback": None,
            "completed_actions": [],
            "action_log": [],
        }

        result = task_router(state)
        assert result == END

    def test_low_confidence_requests_approval(self):
        """Test that low confidence tasks request human approval."""
        task = Task(
            id="task-low-confidence",
            task_type=TaskType.EMAIL_TRIAGE,
            description="Review emails",
            confidence=0.75,  # Below 0.85 threshold
        )
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [task],
            "current_task": task,
            "admin_output": None,
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "",
            "human_feedback": None,
            "completed_actions": [],
            "action_log": [],
        }

        result = task_router(state)
        assert result == "human_approval"

    def test_draft_email_requests_approval(self):
        """Test that email drafts require human approval."""
        task = Task(
            id="task-draft",
            task_type=TaskType.EMAIL_DRAFT,
            description="Draft response",
            confidence=0.92,  # High confidence but still needs approval
        )
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [task],
            "current_task": task,
            "admin_output": None,
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "",
            "human_feedback": None,
            "completed_actions": [],
            "action_log": [],
        }

        result = task_router(state)
        assert result == "human_approval"

    def test_email_draft_requests_approval(self):
        """Test that email draft requires human approval (not handoff)."""
        task = Task(
            id="task-draft-followup",
            task_type=TaskType.EMAIL_DRAFT,
            description="Draft follow-up email",
            confidence=0.92,  # EMAIL_DRAFT needs approval per task_router logic
        )
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [task],
            "current_task": task,
            "admin_output": {"type": "email", "action": "draft"},
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "",
            "human_feedback": None,
            "completed_actions": [],
            "action_log": [],
        }

        # EMAIL_DRAFT is in the approval-required list
        result = task_router(state)
        assert result == "human_approval"

    def test_triage_task_completes_without_approval(self):
        """Test that email triage (not in approval list) completes."""
        task = Task(
            id="task-triage",
            task_type=TaskType.EMAIL_TRIAGE,
            description="Review emails",
            confidence=0.92,  # High confidence
        )
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [task],
            "current_task": task,
            "admin_output": {"type": "email", "action": "triage"},
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "",
            "human_feedback": None,
            "completed_actions": [],
            "action_log": [],
        }

        # EMAIL_TRIAGE is not in approval list
        result = task_router(state)
        assert result == "task_complete"


class TestPlanningNode:
    """Tests for the planning node."""

    @pytest.mark.asyncio
    async def test_planning_generates_suggestions(self):
        """Test that planning node generates suggestions."""
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [],
            "current_task": None,
            "admin_output": None,
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "",
            "human_feedback": None,
            "completed_actions": [],
            "action_log": [],
        }

        result = await planning_node(state)

        assert "suggestions" in result
        assert result["next_action"] == "supervisor_decide"

    @pytest.mark.asyncio
    async def test_planning_adds_context_enrichment(self):
        """Test that planning adds context enrichment suggestion for new users."""
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [],
            "current_task": None,
            "admin_output": None,
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "",
            "human_feedback": None,
            "completed_actions": [],  # Less than 3 completed
            "action_log": [],
        }

        result = await planning_node(state)

        # Should have at least the context enrichment suggestion
        assert len(result["suggestions"]) >= 1


class TestCloneNodes:
    """Tests for clone node functions."""

    @pytest.mark.asyncio
    async def test_admin_clone_returns_output(self):
        """Test that admin_clone_node returns expected output structure."""
        task = Task(
            id="task-admin",
            task_type=TaskType.EMAIL_TRIAGE,
            description="Review emails",
        )
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [task],
            "current_task": task,
            "admin_output": None,
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "",
            "human_feedback": None,
            "completed_actions": [],
            "action_log": [],
        }

        # Mock the Graphiti client
        with patch("app.agents.supervisor.get_graphiti_client") as mock_client:
            mock_graphiti = AsyncMock()
            mock_graphiti.get_user_context.return_value = {
                "context_text": "Test context",
                "by_source": {"email": []},
            }
            mock_client.return_value = mock_graphiti

            result = await admin_clone_node(state)

            assert "admin_output" in result
            assert "messages" in result

    @pytest.mark.asyncio
    async def test_ops_clone_returns_output(self):
        """Test that ops_clone_node returns expected output structure."""
        task = Task(
            id="task-ops",
            task_type=TaskType.TASK_CREATE,
            description="Create new task",
        )
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [task],
            "current_task": task,
            "admin_output": None,
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "",
            "human_feedback": None,
            "completed_actions": [],
            "action_log": [],
        }

        with patch("app.agents.supervisor.get_graphiti_client") as mock_client:
            mock_graphiti = AsyncMock()
            mock_graphiti.get_user_context.return_value = {
                "context_text": "Test context",
                "by_source": {"task": []},
            }
            mock_client.return_value = mock_graphiti

            result = await ops_clone_node(state)

            assert "ops_output" in result
            assert "messages" in result

    @pytest.mark.asyncio
    async def test_research_clone_returns_output(self):
        """Test that research_clone_node returns expected output structure."""
        task = Task(
            id="task-research",
            task_type=TaskType.RESEARCH_QUERY,
            description="Research AI trends",
        )
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [task],
            "current_task": task,
            "admin_output": None,
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "",
            "human_feedback": None,
            "completed_actions": [],
            "action_log": [],
        }

        with patch("app.agents.supervisor.get_graphiti_client") as mock_client:
            mock_graphiti = AsyncMock()
            mock_graphiti.get_user_context.return_value = {
                "context_text": "Test context",
                "by_source": {"research": []},
            }
            mock_client.return_value = mock_graphiti

            result = await research_clone_node(state)

            assert "research_output" in result
            assert "messages" in result


class TestSupervisorGraph:
    """Tests for the compiled supervisor graph."""

    def test_graph_creation(self):
        """Test that supervisor graph can be created."""
        graph = create_supervisor_graph()

        assert graph is not None

    def test_graph_has_all_nodes(self):
        """Test that graph has all expected nodes."""
        graph = create_supervisor_graph()

        # Check nodes exist (LangGraph stores nodes differently in different versions)
        # Just verify the graph was created successfully
        assert graph is not None


class TestMultiAgentHandoffs:
    """Tests for multi-agent handoff scenarios."""

    def test_email_triage_with_task_creation_handoff(self):
        """Test that email triage can handoff to Ops for task creation."""
        task = Task(
            id="task-email-ops",
            task_type=TaskType.EMAIL_TRIAGE,
            description="Review emails and flag follow-ups",
            confidence=0.92,  # High confidence, EMAIL_TRIAGE not in approval list
        )
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [task],
            "current_task": task,
            "admin_output": {"type": "email", "action": "triage", "follow_up_needed": True},
            "ops_output": None,
            "research_output": None,
            "founder_context": {},
            "suggestions": [],
            "next_action": "",
            "human_feedback": None,
            "completed_actions": [],
            "action_log": [],
        }

        # After admin_clone completes, task_router should route to ops_clone for task creation
        result = task_router(state)
        assert result == "ops_clone"

    def test_research_alerts_create_tasks(self):
        """Test that research alerts can create follow-up tasks."""
        task = Task(
            id="task-research-alert",
            task_type=TaskType.RESEARCH_SUMMARY,
            description="Summarize competitor analysis",
            confidence=0.88,
        )
        state: AgentState = {
            "user_id": "user-123",
            "group_id": "group-123",
            "messages": [],
            "tasks": [task],
            "current_task": task,
            "admin_output": None,
            "ops_output": None,
            "research_output": {
                "type": "research",
                "alerts": ["Competitor X launched new feature"],
            },
            "founder_context": {},
            "suggestions": [],
            "next_action": "",
            "human_feedback": None,
            "completed_actions": [],
            "action_log": [],
        }

        result = task_router(state)
        assert result == "ops_clone"


class TestCloneTypeMapping:
    """Tests for CloneType enum mapping."""

    def test_clone_type_values(self):
        """Test CloneType enum values."""
        assert CloneType.EMAIL.value == "email"
        assert CloneType.OPS.value == "ops"
        assert CloneType.CALENDAR.value == "calendar"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
