"""Scheduler for automated tasks.

Handles:
- Daily planning trigger (morning digest)
- Periodic sync of integrations
- Pattern alert generation
- Cleanup tasks

Uses APScheduler for cron-like scheduling.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """A scheduled task configuration."""
    id: str
    name: str
    cron_expression: str  # Simplified cron (minute hour day month)
    enabled: bool
    last_run: Optional[datetime] = None
    last_result: Optional[Dict[str, Any]] = None


class Scheduler:
    """Simple scheduler for automated EchoTeam tasks.

    In production, would use APScheduler or similar.
    Currently implements basic interval-based scheduling.
    """

    def __init__(self, user_id: str, group_id: str):
        self.user_id = user_id
        self.group_id = group_id
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._task_results: Dict[str, Any] = {}

    def add_task(self, task: ScheduledTask) -> None:
        """Add a scheduled task."""
        self._tasks[task.id] = task
        logger.info(f"Scheduler: Added task {task.id}")

    def remove_task(self, task_id: str) -> None:
        """Remove a scheduled task."""
        self._tasks.pop(task_id, None)
        logger.info(f"Scheduler: Removed task {task_id}")

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler: Already running")
            return

        self._running = True
        logger.info(f"Scheduler: Started for user {self.user_id}")

        # Start the main loop
        asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        logger.info("Scheduler: Stopped")

    async def _run_loop(self) -> None:
        """Main scheduler loop - checks tasks every minute."""
        while self._running:
            now = datetime.now(timezone.utc)

            for task_id, task in self._tasks.items():
                if not task.enabled:
                    continue

                if self._should_run(task, now):
                    task.last_run = now
                    result = await self._execute_task(task)
                    task.last_result = result
                    self._task_results[task_id] = result

            await asyncio.sleep(60)  # Check every minute

    def _should_run(self, task: ScheduledTask, now: datetime) -> bool:
        """Check if a task should run now based on its schedule."""
        if task.last_run and task.last_run > now - timedelta(minutes=1):
            return False

        # Simplified cron-like scheduling
        # Format: "minute hour day month" (all optional)
        parts = task.cron_expression.split()
        while len(parts) < 4:
            parts.append("*")

        minute, hour, day, month = parts

        if minute != "*" and now.minute != int(minute):
            return False
        if hour != "*" and now.hour != int(hour):
            return False
        if day != "*" and now.day != int(day):
            return False
        if month != "*" and now.month != int(month):
            return False

        return True

    async def _execute_task(self, task: ScheduledTask) -> Dict[str, Any]:
        """Execute a scheduled task."""
        logger.info(f"Scheduler: Executing task {task.id}")

        try:
            if task.id == "daily_digest":
                return await self._run_daily_digest()
            elif task.id == "integration_sync":
                return await self._run_integration_sync()
            elif task.id == "pattern_alerts":
                return await self._run_pattern_alerts()
            elif task.id == "planning_loop":
                return await self._run_planning_loop()
            else:
                logger.warning(f"Unknown task: {task.id}")
                return {"error": "Unknown task"}
        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}")
            return {"error": str(e)}

    async def _run_daily_digest(self) -> Dict[str, Any]:
        """Generate daily digest - Admin Clone."""
        from app.agents.supervisor import run_supervisor, Task, TaskType

        task = Task(
            id=f"daily_digest_{datetime.now().timestamp()}",
            task_type=TaskType.DAILY_DIGEST,
            description="Generate daily inbox and calendar digest",
        )

        result = await run_supervisor(self.user_id, task)
        return {
            "success": True,
            "task_type": "daily_digest",
            "result_summary": result.get("admin_output"),
        }

    async def _run_integration_sync(self) -> Dict[str, Any]:
        """Sync all connected integrations."""
        from app.integrations import (
            GmailIntegration,
            CalendarIntegration,
            NotionIntegration,
        )

        results = {}
        total_episodes = 0

        for IntegrationClass in [GmailIntegration, CalendarIntegration, NotionIntegration]:
            integration = IntegrationClass(self.user_id, self.group_id)

            # Check if connected (in production, would check stored tokens)
            if await integration.is_connected():
                sync_result = await integration.sync()
                results[integration.service_name] = {
                    "success": sync_result.success,
                    "episodes_created": sync_result.episodes_created,
                }
                total_episodes += sync_result.episodes_created
            else:
                results[integration.service_name] = {
                    "success": False,
                    "message": "Not connected",
                }

        return {
            "success": True,
            "total_episodes": total_episodes,
            "results": results,
        }

    async def _run_pattern_alerts(self) -> Dict[str, Any]:
        """Generate pattern alerts - Research Clone."""
        from app.agents.supervisor import run_supervisor, Task, TaskType

        task = Task(
            id=f"pattern_alerts_{datetime.now().timestamp()}",
            task_type=TaskType.RESEARCH_SUMMARY,
            description="Analyze patterns and generate alerts",
        )

        result = await run_supervisor(self.user_id, task)
        return {
            "success": True,
            "task_type": "pattern_alerts",
            "alerts_generated": len(result.get("research_output", {}).get("alerts", [])),
        }

    async def _run_planning_loop(self) -> Dict[str, Any]:
        """Run proactive planning - generate suggestions."""
        from app.agents.supervisor import run_supervisor, Task, TaskType

        task = Task(
            id=f"planning_{datetime.now().timestamp()}",
            task_type=TaskType.GENERAL,
            description="Generate proactive suggestions based on time and context",
        )

        result = await run_supervisor(self.user_id, task)
        return {
            "success": True,
            "task_type": "planning",
            "suggestions_count": len(result.get("suggestions", [])),
        }

    def get_task_status(self) -> List[Dict[str, Any]]:
        """Get status of all tasks for UI."""
        return [
            {
                "id": task.id,
                "name": task.name,
                "enabled": task.enabled,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "last_result": task.last_result,
            }
            for task in self._tasks.values()
        ]


def create_default_scheduler(user_id: str, group_id: str) -> Scheduler:
    """Create a scheduler with default EchoTeam tasks."""
    scheduler = Scheduler(user_id, group_id)

    # Add default tasks
    scheduler.add_task(ScheduledTask(
        id="daily_digest",
        name="Daily Digest",
        cron_expression="0 8 * *",  # 8am daily
        enabled=True,
    ))

    scheduler.add_task(ScheduledTask(
        id="integration_sync",
        name="Integration Sync",
        cron_expression="0 */4 * *",  # Every 4 hours
        enabled=True,
    ))

    scheduler.add_task(ScheduledTask(
        id="pattern_alerts",
        name="Pattern Alerts",
        cron_expression="0 9 * *",  # 9am daily
        enabled=True,
    ))

    scheduler.add_task(ScheduledTask(
        id="planning_loop",
        name="Proactive Planning",
        cron_expression="0 */6 * *",  # Every 6 hours
        enabled=True,
    ))

    return scheduler


# Convenience function for quick actions
async def trigger_daily_digest(user_id: str, group_id: str) -> Dict[str, Any]:
    """Trigger daily digest immediately (for manual quick action)."""
    scheduler = create_default_scheduler(user_id, group_id)
    return await scheduler._run_daily_digest()


async def trigger_integration_sync(user_id: str, group_id: str) -> Dict[str, Any]:
    """Trigger integration sync immediately."""
    scheduler = create_default_scheduler(user_id, group_id)
    return await scheduler._run_integration_sync()
