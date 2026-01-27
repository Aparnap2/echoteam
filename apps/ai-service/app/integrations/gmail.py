"""Gmail integration for email ingestion.

Handles:
- OAuth connection to Gmail
- Syncing recent emails as episodes
- Email metadata extraction (sender, subject, labels)

Note: Full implementation requires Google Cloud Console credentials.
Currently stubs the OAuth and sync logic.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import logging

from app.integrations.base import BaseIntegration, IntegrationConfig, SyncResult

logger = logging.getLogger(__name__)


class GmailIntegration(BaseIntegration):
    """Gmail integration for email ingestion.

    Capabilities:
    - Read emails (sync recent emails as episodes)
    - Extract sender, subject, snippets
    - Track email threads for context
    """

    SERVICE_NAME = "gmail"
    DEFAULT_SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.labels",
    ]

    def __init__(self, user_id: str, group_id: str):
        config = IntegrationConfig(
            user_id=user_id,
            group_id=group_id,
        )
        super().__init__(config)
        self._emails_cache: List[Dict[str, Any]] = []

    @property
    def service_name(self) -> str:
        return self.SERVICE_NAME

    @property
    def default_scopes(self) -> List[str]:
        return self.DEFAULT_SCOPES

    async def _refresh_oauth_token(self) -> bool:
        """Refresh OAuth token using refresh token.

        In production, this would call Google's token endpoint.
        """
        # Stub: Would exchange refresh_token for new access_token
        logger.info(f"{self.service_name}: Token refresh would happen here")
        return True

    async def _perform_sync(self, since: Optional[datetime]) -> SyncResult:
        """Sync emails from Gmail.

        Args:
            since: Only sync emails after this time

        Returns:
            SyncResult with episode counts
        """
        result = SyncResult(success=True)

        # Stub: Would fetch emails from Gmail API
        # In production:
        #   messages = self._client.users().messages().list(
        #       userId='me',
        #       q=f'after:{since.strftime("%Y/%m/%d")}' if since else None
        #   ).execute()
        #   for msg in messages.get('messages', []):
        #       msg_detail = self._client.users().messages().get(
        #           userId='me', id=msg['id']
        #       ).execute()

        # Mock emails for testing
        mock_emails = [
            {
                "id": "email_1",
                "subject": "Project Update - Q1 Goals",
                "from": "team@company.com",
                "snippet": "Here's our progress on Q1 goals...",
                "date": datetime.now(timezone.utc) - timedelta(hours=2),
                "labels": ["INBOX", "IMPORTANT"],
            },
            {
                "id": "email_2",
                "subject": "Meeting Tomorrow - 10am",
                "from": "colleague@company.com",
                "snippet": "Let's discuss the new feature...",
                "date": datetime.now(timezone.utc) - timedelta(hours=6),
                "labels": ["INBOX"],
            },
            {
                "id": "email_3",
                "subject": "Weekly Summary",
                "from": "reports@company.com",
                "snippet": "Your weekly activity report...",
                "date": datetime.now(timezone.utc) - timedelta(days=1),
                "labels": ["INBOX", "自动化"],
            },
        ]

        for email in mock_emails:
            if since and email["date"] < since:
                continue

            # Create episode content
            content = f"""
From: {email['from']}
Subject: {email['subject']}
Date: {email['date'].isoformat()}

{email['snippet']}
            """.strip()

            metadata = {
                "email_id": email["id"],
                "from_address": email["from"],
                "labels": email["labels"],
                "synced_at": datetime.now(timezone.utc).isoformat(),
            }

            success = await self._create_episode(
                name=f"email_{email['id']}",
                content=content,
                source_type="email",
                metadata=metadata,
            )

            if success:
                result.episodes_created += 1
            else:
                result.errors.append(f"Failed to create episode for {email['id']}")

        logger.info(f"{self.service_name}: Synced {result.episodes_created} emails")
        return result

    async def get_recent_emails(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent emails for display in UI."""
        if not await self.is_connected():
            return []

        # Return cached or fetch from API
        return self._emails_cache[:limit]

    async def search_emails(self, query: str) -> List[Dict[str, Any]]:
        """Search emails matching query."""
        if not await self.is_connected():
            return []

        # Stub: Would search Gmail
        # In production: self._client.users().messages().list(userId='me', q=query)
        return [
            {
                "id": "search_result_1",
                "subject": f"Results for: {query}",
                "from": "sender@example.com",
                "snippet": "Matching email snippet...",
            }
        ]
