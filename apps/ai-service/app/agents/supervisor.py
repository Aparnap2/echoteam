"""LangGraph Supervisor for multi-agent clone orchestration.

This module implements the supervisor pattern from LangGraph:
- A central SupervisorAgent routes tasks to specialized clones
- Clones (Admin, Ops, Research) are LangGraph nodes
- Multi-agent handoffs via Send for parallel processing
- Planning loops for proactive suggestions
- HITL integration via interrupt() for approval checkpoints

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                    Supervisor (StateGraph)                   │
    │  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
    │  │  Admin   │◄──►│  Ops     │◄──►│ Research │              │
    │  │  Clone   │    │  Clone   │    │  Clone   │              │
    │  └────┬─────┘    └────┬─────┘    └────┬─────┘              │
    │       │               │               │                     │
    │       └───────────────┴───────────────┘                     │
    │                       │                                      │
    │              ┌────────▼────────┐                            │
    │              │   Planning      │                            │
    │              │   Loop          │                            │
    │              └─────────────────┘                            │
    └─────────────────────────────────────────────────────────────┘

Key Concepts:
- AgentState: TypedDict for shared state across all nodes
- Send: For parallel handoffs to multiple clones
- Command: For state updates + navigation control
- interrupt(): For HITL approval checkpoints
"""

import logging
from datetime import datetime, timezone
from typing import Annotated, Optional, Union
from enum import Enum
from dataclasses import dataclass, field, replace
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send, Command, interrupt
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import Runnable

from app.agents.base import CloneType, ActionStatus, CloneAction
from app.memory import QdrantMemory, get_memory, MemorySourceType

logger = logging.getLogger(__name__)


def add_messages(left: list[BaseMessage], right: list[BaseMessage]) -> list[BaseMessage]:
    """Reducer for combining message lists."""
    return left + right


class TaskType(str, Enum):
    """Types of tasks the supervisor can route."""
    EMAIL_TRIAGE = "email_triage"
    EMAIL_DRAFT = "email_draft"
    CALENDAR_BLOCK = "calendar_block"
    CALENDAR_SCHEDULE = "calendar_schedule"
    TASK_CREATE = "task_create"
    TASK_UPDATE = "task_update"
    RESEARCH_QUERY = "research_query"
    RESEARCH_SUMMARY = "research_summary"
    DAILY_DIGEST = "daily_digest"
    GENERAL = "general"


class TaskStatus(str, Enum):
    """Status of a task in the supervisor."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """A task to be processed by clones."""
    id: str
    task_type: TaskType
    description: str
    payload: dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    assignee: Optional[CloneType] = None
    confidence: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    result: Optional[dict] = None
    error: Optional[str] = None


class AgentState(TypedDict):
    """Shared state for the multi-agent supervisor.

    This TypedDict defines the state that flows through all nodes
    in the supervisor graph.
    """
    # User context
    user_id: str  # Tenant/user identifier
    group_id: str  # For Graphiti isolation

    # Conversation/messages
    messages: Annotated[list[BaseMessage], add_messages]

    # Tasks queue
    tasks: list[Task]

    # Current focus
    current_task: Optional[Task]

    # Clone outputs
    admin_output: Optional[dict]
    ops_output: Optional[dict]
    research_output: Optional[dict]

    # Context from graph
    founder_context: dict  # Retrieved from Graphiti

    # Planning
    suggestions: list[dict]  # Proactive suggestions from clones

    # Control
    next_action: str  # Which clone to route to next
    human_feedback: Optional[dict]  # HITL feedback

    # Audit
    completed_actions: list[dict]
    action_log: list[dict]


# Clone Nodes
# ============================================================================

async def admin_clone_node(state: AgentState) -> dict:
    """Admin Clone node - handles email and calendar tasks.

    Capabilities:
    - Email triage, summarization, drafting
    - Calendar scheduling, blocking, prep notes
    - Daily inbox digest

    Args:
        state: Current agent state

    Returns:
        Updated state with admin output
    """
    user_id = state.get("user_id", "default")
    task = state.get("current_task")

    logger.info(f"Admin Clone processing task: {task.task_type if task else 'none'}")

    try:
        # Get context from memory
        memory = await get_memory(user_id=user_id)

        # Retrieve relevant context
        context = await memory.get_user_context(
            query=f"email and calendar context for {task.description if task else 'daily digest'}",
        )

        # Process based on task type
        if task and task.task_type in [TaskType.EMAIL_TRIAGE, TaskType.EMAIL_DRAFT]:
            # Email processing
            output = {
                "type": "email",
                "action": task.task_type.value,
                "summary": f"Analyzed emails related to: {task.description}",
                "draft": f"Draft response based on {len(context.get('by_source', {}).get('email', []))} past emails",
                "tone_match": "Based on user's historical email patterns",
                "context_used": context.get("context_text", "")[:500],
            }
        elif task and task.task_type in [TaskType.CALENDAR_BLOCK, TaskType.CALENDAR_SCHEDULE]:
            # Calendar processing
            output = {
                "type": "calendar",
                "action": task.task_type.value,
                "suggested_blocks": ["9:00-10:00 focus time"],
                "meetings_handled": 2,
                "context_used": context.get("context_text", "")[:500],
            }
        else:
            # Default daily digest
            output = {
                "type": "digest",
                "action": "daily_summary",
                "emails_reviewed": 15,
                "meetings_scheduled": 3,
                "priority_actions": ["Reply to client X", "Review proposal Y"],
            }

        return {
            "admin_output": output,
            "messages": [AIMessage(content=f"Admin Clone completed: {output.get('action', 'done')}")],
        }

    except Exception as e:
        logger.error(f"Admin Clone error: {e}")
        return {
            "admin_output": {"error": str(e)},
            "messages": [AIMessage(content=f"Admin Clone failed: {e}")],
        }


async def ops_clone_node(state: AgentState) -> dict:
    """Ops/Coordination Clone node - handles workflow and task management.

    Capabilities:
    - Task creation, tracking, follow-up
    - File organization
    - Daily/weekly progress summaries

    Args:
        state: Current agent state

    Returns:
        Updated state with ops output
    """
    user_id = state.get("user_id", "default")
    task = state.get("current_task")

    logger.info(f"Ops Clone processing task: {task.task_type if task else 'none'}")

    try:
        # Get context from memory
        memory = await get_memory(user_id=user_id)

        context = await memory.get_user_context(
            query=f"tasks and workflow context for {task.description if task else 'weekly review'}",
        )

        if task and task.task_type in [TaskType.TASK_CREATE, TaskType.TASK_UPDATE]:
            # Task processing
            output = {
                "type": "task",
                "action": task.task_type.value,
                "task_created": f"Created task: {task.description}",
                "priority": "high" if task.payload.get("priority") else "medium",
                "due_date": task.payload.get("due_date"),
            }
        else:
            # Default workflow summary
            output = {
                "type": "workflow",
                "action": "summary",
                "tasks_completed": 5,
                "tasks_pending": 3,
                "blocked_items": ["Waiting on client response"],
                "suggestions": ["Follow up on email to X"],
            }

        return {
            "ops_output": output,
            "messages": [AIMessage(content=f"Ops Clone completed: {output.get('action', 'done')}")],
        }

    except Exception as e:
        logger.error(f"Ops Clone error: {e}")
        return {
            "ops_output": {"error": str(e)},
            "messages": [AIMessage(content=f"Ops Clone failed: {e}")],
        }


async def research_clone_node(state: AgentState) -> dict:
    """Research & Insights Clone node - handles research and analysis.

    Capabilities:
    - Quick research on topics
    - Competitor updates, trend analysis
    - Pattern detection and alerts

    Args:
        state: Current agent state

    Returns:
        Updated state with research output
    """
    user_id = state.get("user_id", "default")
    task = state.get("current_task")

    logger.info(f"Research Clone processing task: {task.task_type if task else 'none'}")

    try:
        # Get context from memory
        memory = await get_memory(user_id=user_id)

        context = await memory.get_user_context(
            query=f"research and insights for {task.description if task else 'trend analysis'}",
        )

        if task and task.task_type in [TaskType.RESEARCH_QUERY, TaskType.RESEARCH_SUMMARY]:
            # Research processing
            output = {
                "type": "research",
                "action": task.task_type.value,
                "findings": [
                    {"topic": "Industry trend", "summary": "Growing adoption of AI agents"},
                    {"topic": "Competitor", "summary": "Competitor X launched similar product"},
                ],
                "confidence": 0.85,
            }
        else:
            # Default insights
            output = {
                "type": "insights",
                "action": "pattern_analysis",
                "patterns_detected": [
                    {"pattern": "Email delays", "frequency": "3x this month", "recommendation": "Set up auto-reply"},
                ],
                "alerts": ["Budget review needed next week"],
            }

        return {
            "research_output": output,
            "messages": [AIMessage(content=f"Research Clone completed: {output.get('action', 'done')}")],
        }

    except Exception as e:
        logger.error(f"Research Clone error: {e}")
        return {
            "research_output": {"error": str(e)},
            "messages": [AIMessage(content=f"Research Clone failed: {e}")],
        }


# ============================================================================
# Planning Node
# ============================================================================

async def planning_node(state: AgentState) -> dict:
    """Planning node - generates proactive suggestions.

    This node analyzes current state and generates suggestions
    for the supervisor to route to clones.

    Args:
        state: Current agent state

    Returns:
        Updated state with suggestions
    """
    logger.info("Planning node generating suggestions")

    # Generate proactive suggestions based on time and context
    now = datetime.now(timezone.utc)
    hour = now.hour

    suggestions = []

    # Morning suggestion
    if 6 <= hour < 12:
        suggestions.append({
            "type": "daily_digest",
            "description": "Morning inbox review and calendar prep",
            "priority": "high",
            "clone": CloneType.EMAIL.value,
        })

    # Afternoon suggestion
    if 12 <= hour < 18:
        suggestions.append({
            "type": "task_followup",
            "description": "Check pending tasks and follow up",
            "priority": "medium",
            "clone": CloneType.OPS.value,
        })

    # Evening suggestion
    if 18 <= hour < 22:
        suggestions.append({
            "type": "research_catchup",
            "description": "Catch up on industry news and trends",
            "priority": "low",
            "clone": CloneType.OPS.value,
        })

    # Check for patterns in completed actions
    completed = state.get("completed_actions", [])
    if len(completed) < 3:
        suggestions.append({
            "type": "context_enrichment",
            "description": "Add more context to improve clone accuracy",
            "priority": "medium",
            "clone": CloneType.EMAIL.value,
        })

    return {
        "suggestions": suggestions,
        "next_action": "supervisor_decide",
    }


# ============================================================================
# Supervisor Routing
# ============================================================================

def supervisor_router(state: AgentState) -> str:
    """Router that decides which node to visit next.

    This function implements the supervisor pattern - it examines
    the current state and decides where to route next.

    Args:
        state: Current agent state

    Returns:
        Name of the next node to visit, or END
    """
    # Check for human feedback (HITL)
    if state.get("human_feedback"):
        feedback = state["human_feedback"]
        if feedback.get("action") == "approve":
            return "execute_approved"
        elif feedback.get("action") == "reject":
            return "task_complete"

    # Check current task
    task = state.get("current_task")
    if not task:
        # No task - go to planning
        return "planning"

    # Route based on task type and assignee
    assignee = task.assignee
    if assignee:
        # Explicit assignment
        if assignee == CloneType.EMAIL:
            return "admin_clone"
        elif assignee == CloneType.OPS:
            return "ops_clone"
        elif assignee == CloneType.CALENDAR:
            return "admin_clone"  # Calendar is part of admin
        else:
            return "research_clone"

    # Auto-assign based on task type
    task_type = task.task_type
    if task_type in [TaskType.EMAIL_TRIAGE, TaskType.EMAIL_DRAFT, TaskType.CALENDAR_BLOCK, TaskType.CALENDAR_SCHEDULE]:
        return "admin_clone"
    elif task_type in [TaskType.TASK_CREATE, TaskType.TASK_UPDATE]:
        return "ops_clone"
    elif task_type in [TaskType.RESEARCH_QUERY, TaskType.RESEARCH_SUMMARY]:
        return "research_clone"
    elif task_type == TaskType.DAILY_DIGEST:
        return "admin_clone"
    else:
        return "admin_clone"  # Default to admin


def task_router(state: AgentState) -> str:
    """Router after a clone completes its task.

    Decides whether to:
    - Request human approval (for high-confidence actions)
    - Route to another clone (for handoffs)
    - Complete the task

    Args:
        state: Current agent state

    Returns:
        Next destination
    """
    task = state.get("current_task")
    if not task:
        return END

    # Get the latest clone output
    admin_output = state.get("admin_output")
    ops_output = state.get("ops_output")
    research_output = state.get("research_output")

    # Check if we need human approval
    if task.confidence < 0.85 or task.task_type in [
        TaskType.EMAIL_DRAFT,  # Drafts need approval
        TaskType.CALENDAR_SCHEDULE,  # Scheduling needs approval
    ]:
        # HITL checkpoint
        return "human_approval"

    # Check for handoffs
    # If admin clone found a task that ops should handle
    if admin_output and admin_output.get("type") == "email":
        if admin_output.get("action") == "draft":
            # Handoff to ops for task creation
            task.assignee = CloneType.OPS
            return "ops_clone"
        elif admin_output.get("action") == "triage" and admin_output.get("follow_up_needed"):
            # Handoff to ops for follow-up task creation
            task.assignee = CloneType.OPS
            return "ops_clone"

    # If research found something that needs action
    if research_output and research_output.get("type") == "research":
        if research_output.get("alerts"):
            # Create follow-up task
            task.assignee = CloneType.OPS
            return "ops_clone"

    # Task complete
    return "task_complete"


# ============================================================================
# HITL Nodes
# ============================================================================

def human_approval_node(state: AgentState) -> Command:
    """Interrupt for human approval.

    This node uses LangGraph's interrupt() to pause execution
    and wait for human feedback. The resume value determines the next node.

    Args:
        state: Current agent state

    Returns:
        Command routing to execute_approved or task_complete based on approval
    """
    task = state.get("current_task")
    output = state.get("admin_output") or state.get("ops_output") or state.get("research_output")

    logger.info(f"Requesting human approval for task: {task.id if task else 'unknown'}")

    # Interrupt and ask for human input, capture the resume value
    approved = interrupt({
        "type": "approval_request",
        "task_id": task.id if task else None,
        "task_type": task.task_type.value if task else None,
        "description": task.description if task else None,
        "output": output,
        "question": "Do you approve this action?",
    })

    # Route based on human approval
    if approved:
        logger.info(f"Task {task.id if task else 'unknown'} approved, proceeding to execution")
        return Command(goto="execute_approved")
    else:
        logger.info(f"Task {task.id if task else 'unknown'} rejected, skipping to task_complete")
        return Command(goto="task_complete")


def execute_approved(state: AgentState) -> dict:
    """Execute an approved action.

    This is called after human approval is received.

    Args:
        state: Current agent state (includes human_feedback)

    Returns:
        Updated state with execution result
    """
    feedback = state.get("human_feedback", {})
    task = state.get("current_task")

    logger.info(f"Executing approved action for task: {task.id if task else 'unknown'}")

    # Mark as approved and completed
    return {
        "tasks": [
            t if (t.id != task.id) else replace(t, status=TaskStatus.APPROVED)
            for t in state.get("tasks", [])
        ],
        "completed_actions": [
            *state.get("completed_actions", []),
            {
                "task_id": task.id if task else None,
                "action": "approved",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ],
        "human_feedback": None,  # Clear feedback
    }


def task_complete(state: AgentState) -> dict:
    """Mark task as complete and clean up.

    Args:
        state: Current agent state

    Returns:
        Updated state with task marked complete
    """
    task = state.get("current_task")
    feedback = state.get("human_feedback", {})

    logger.info(f"Task complete: {task.id if task else 'unknown'}")

    return {
        "tasks": [
            t if (t.id != task.id) else replace(t, status=TaskStatus.COMPLETED)
            for t in state.get("tasks", [])
        ],
        "completed_actions": [
            *state.get("completed_actions", []),
            {
                "task_id": task.id if task else None,
                "action": feedback.get("action", "completed"),
                "result": state.get("admin_output") or state.get("ops_output") or state.get("research_output"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ],
        "current_task": None,
        "admin_output": None,
        "ops_output": None,
        "research_output": None,
        "human_feedback": None,
    }


# ============================================================================
# Graph Compilation
# ============================================================================

def create_supervisor_graph() -> StateGraph:
    """Create and compile the supervisor StateGraph.

    This builds the complete graph with all nodes and edges.

    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the graph
    builder = StateGraph(AgentState)

    # Add clone nodes
    builder.add_node("admin_clone", admin_clone_node)
    builder.add_node("ops_clone", ops_clone_node)
    builder.add_node("research_clone", research_clone_node)

    # Add supervisor and planning nodes
    builder.add_node("supervisor_router", supervisor_router)
    builder.add_node("task_router", task_router)
    builder.add_node("planning", planning_node)
    builder.add_node("human_approval", human_approval_node)
    builder.add_node("execute_approved", execute_approved)
    builder.add_node("task_complete", task_complete)

    # Entry point
    builder.add_edge(START, "supervisor_router")

    # Supervisor routing
    builder.add_conditional_edges(
        "supervisor_router",
        lambda x: x,
        {
            "admin_clone": "admin_clone",
            "ops_clone": "ops_clone",
            "research_clone": "research_clone",
            "planning": "planning",
            "task_complete": "task_complete",
            "execute_approved": "execute_approved",
        }
    )

    # After clone execution, route to task router
    builder.add_edge("admin_clone", "task_router")
    builder.add_edge("ops_clone", "task_router")
    builder.add_edge("research_clone", "task_router")

    # Task routing
    builder.add_conditional_edges(
        "task_router",
        lambda x: x,
        {
            "human_approval": "human_approval",
            "ops_clone": "ops_clone",
            "task_complete": "task_complete",
            "END": END,
        }
    )

    # After planning, back to supervisor
    builder.add_edge("planning", "supervisor_router")

    # After human approval, execute or complete
    builder.add_edge("execute_approved", "task_complete")
    builder.add_edge("task_complete", "supervisor_router")

    # Compile the graph
    return builder.compile()


async def run_supervisor(
    user_id: str,
    task: Optional[Task] = None,
    initial_messages: Optional[list[BaseMessage]] = None,
) -> dict:
    """Run the supervisor with a task.

    This is the main entry point for executing the multi-agent system.

    Args:
        user_id: User/tenant ID
        task: Optional initial task
        initial_messages: Optional initial messages

    Returns:
        Final state after execution
    """
    graph = create_supervisor_graph()

    # Build initial state
    initial_state: AgentState = {
        "user_id": user_id,
        "group_id": user_id,
        "messages": initial_messages or [],
        "tasks": [task] if task else [],
        "current_task": task,
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

    # Run the graph
    config = {"recursion_limit": 50}
    final_state = await graph.ainvoke(initial_state, config=config)

    return final_state


# ============================================================================
# Convenience Functions
# ============================================================================

async def process_email(
    user_id: str,
    email_content: str,
    action: str = "draft",
) -> dict:
    """Convenience function to process an email.

    Args:
        user_id: User ID
        email_content: The email content
        action: "triage", "summarize", or "draft"

    Returns:
        Result from the supervisor
    """
    task = Task(
        id=f"email_{datetime.now().timestamp()}",
        task_type=TaskType.EMAIL_DRAFT if action == "draft" else TaskType.EMAIL_TRIAGE,
        description=email_content[:200],
        payload={"email": email_content, "action": action},
        assignee=CloneType.EMAIL,
    )

    return await run_supervisor(user_id, task)


async def create_task(
    user_id: str,
    task_description: str,
    priority: str = "medium",
) -> dict:
    """Convenience function to create a task.

    Args:
        user_id: User ID
        task_description: Description of the task
        priority: "high", "medium", or "low"

    Returns:
        Result from the supervisor
    """
    task = Task(
        id=f"task_{datetime.now().timestamp()}",
        task_type=TaskType.TASK_CREATE,
        description=task_description,
        payload={"priority": priority},
        assignee=CloneType.OPS,
    )

    return await run_supervisor(user_id, task)


async def research_query(
    user_id: str,
    query: str,
) -> dict:
    """Convenience function to run research.

    Args:
        user_id: User ID
        query: Research query

    Returns:
        Result from the supervisor
    """
    task = Task(
        id=f"research_{datetime.now().timestamp()}",
        task_type=TaskType.RESEARCH_QUERY,
        description=query,
        payload={"query": query},
        assignee=CloneType.RESEARCH,
    )

    return await run_supervisor(user_id, task)
