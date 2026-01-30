"""Notion integration for tasks and notes ingestion.

Handles:
- OAuth connection to Notion
- Syncing pages and databases as episodes
- Task extraction with status, due dates, assignees

Note: Full implementation requires Notion OAuth credentials.
Currently stubs the OAuth and sync logic.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import logging

from app.integrations.base import BaseIntegration, IntegrationConfig, SyncResult

logger = logging.getLogger(__name__)


class NotionIntegration(BaseIntegration):
    """Notion integration for tasks and notes.

    Capabilities:
    - Read pages and databases
    - Extract tasks with status and due dates
    - Sync meeting notes and project documentation
    """

    SERVICE_NAME = "notion"
    # Notion OAuth scopes - see https://developers.notion.com/reference/scopes
    DEFAULT_SCOPES = [
        # TODO: Add actual Notion scopes for production:
        # "read_content", "read_userinfo", "read_database_content", etc.
    ]

    def __init__(self, user_id: str, group_id: str):
        config = IntegrationConfig(
            user_id=user_id,
            group_id=group_id,
        )
        super().__init__(config)
        self._pages_cache: List[Dict[str, Any]] = []

    @property
    def service_name(self) -> str:
        return self.SERVICE_NAME

    @property
    def default_scopes(self) -> List[str]:
        return self.DEFAULT_SCOPES

    async def _refresh_oauth_token(self) -> bool:
        """Notion tokens don't expire, so no refresh needed."""
        return True

    async def _perform_sync(self, since: Optional[datetime]) -> SyncResult:
        """Sync pages and tasks from Notion.

        Args:
            since: Only sync pages modified after this time

        Returns:
            SyncResult with episode counts
        """
        result = SyncResult(success=True)

        # Stub: Would fetch from Notion API
        # In production:
        #   pages = self._client.search(
        #       filter={"property": "object", "value": "page"}
        #   )
        #   databases = self._client.search(
        #       filter={"property": "object", "value": "database"}
        #   )

        # Mock pages/tasks for testing
        now = datetime.now(timezone.utc)
        mock_pages = [
            {
                "id": "page_1",
                "title": "Q1 Project Tracker",
                "content": "Tracking progress on Q1 deliverables",
                "last_edited": now - timedelta(hours=3),
                "type": "database",
                "properties": {
                    "Status": {"select": {"name": "In Progress"}},
                    "Due Date": {"date": {"start": (now + timedelta(days=5)).strftime("%Y-%m-%d")}},
                },
            },
            {
                "id": "page_2",
                "title": "Meeting Notes - Jan 20",
                "content": """Discussion points:
- Reviewed Q1 goals progress
- Assigned action items
- Next steps: Follow up with client

Action Items:
- [ ] Send follow-up email
- [ ] Update project tracker
- [ ] Schedule next meeting""",
                "last_edited": now - timedelta(days=1),
                "type": "page",
                "properties": {},
            },
            {
                "id": "page_3",
                "title": "Research - Competitor Analysis",
                "content": "Analysis of competitor products and pricing",
                "last_edited": now - timedelta(days=2),
                "type": "page",
                "properties": {
                    "Status": {"select": {"name": "Completed"}},
                },
            },
        ]

        for page in mock_pages:
            if since and page["last_edited"] < since:
                continue

            # Create episode content
            page_type = page.get("type", "page")
            content = f"""
Title: {page['title']}
Type: {page_type}
Last Edited: {page['last_edited'].strftime("%Y-%m-%d %H:%M")}

{page['content']}
            """.strip()

            metadata = {
                "page_id": page["id"],
                "page_type": page_type,
                "last_edited": page["last_edited"].isoformat(),
                "properties": page.get("properties", {}),
                "synced_at": datetime.now(timezone.utc).isoformat(),
            }

            # Determine source type based on content
            source_type = "task" if "Status" in page.get("properties", {}) else "note"

            success = await self._create_episode(
                name=f"notion_{page['id']}",
                content=content,
                source_type=source_type,
                metadata=metadata,
            )

            if success:
                result.episodes_created += 1
            else:
                result.errors.append(f"Failed to create episode for {page['id']}")

        logger.info(f"{self.service_name}: Synced {result.episodes_created} pages")
        return result

    async def get_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get tasks from Notion databases.

        Args:
            status: Filter by task status (e.g., 'In Progress', 'Completed')
        """
        if not await self.is_connected():
            return []

        # Stub: Would filter pages by status
        tasks = [p for p in self._pages_cache if "Status" in p.get("properties", {})]
        if status:
            tasks = [
                t for t in tasks
                if t.get("properties", {}).get("Status", {}).get("select", {}).get("name") == status
            ]
        return tasks

    async def create_task(self, title: str, content: str,
                          due_date: Optional[str] = None) -> Optional[str]:
        """Create a new task in Notion."""
        if not await self.is_connected():
            return None

        # Stub: Would create page in Notion
        task_id = f"task_{datetime.now().timestamp()}"
        logger.info(f"{self.service_name}: Would create task: {title}")
        return task_id
