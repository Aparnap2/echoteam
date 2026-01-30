"""Google Calendar integration for event ingestion.

Handles:
- OAuth connection to Google Calendar
- Syncing recent events as episodes
- Meeting extraction (agenda, attendees, outcomes)

Note: Full implementation requires Google Cloud Console credentials.
Currently stubs the OAuth and sync logic.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import logging

from app.integrations.base import BaseIntegration, IntegrationConfig, SyncResult

logger = logging.getLogger(__name__)


class CalendarIntegration(BaseIntegration):
    """Calendar integration for event ingestion.

    Capabilities:
    - Read calendar events
    - Extract attendees, agenda, meeting notes
    - Detect meeting outcomes and action items
    """

    SERVICE_NAME = "calendar"
    DEFAULT_SCOPES = [
        "https://www.googleapis.com/auth/calendar.readonly",
    ]

    def __init__(self, user_id: str, group_id: str):
        config = IntegrationConfig(
            user_id=user_id,
            group_id=group_id,
        )
        super().__init__(config)
        self._events_cache: List[Dict[str, Any]] = []

    @property
    def service_name(self) -> str:
        return self.SERVICE_NAME

    @property
    def default_scopes(self) -> List[str]:
        return self.DEFAULT_SCOPES

    async def _refresh_oauth_token(self) -> bool:
        """Refresh OAuth token using refresh token."""
        logger.info(f"{self.service_name}: Token refresh would happen here")
        return True

    async def _perform_sync(self, since: Optional[datetime]) -> SyncResult:
        """Sync events from Google Calendar.

        Args:
            since: Only sync events after this time

        Returns:
            SyncResult with episode counts
        """
        result = SyncResult(success=True)

        # Clear cache at start of sync to avoid duplicates
        self._events_cache.clear()

        # Stub: Would fetch events from Calendar API
        # In production:
        #   events = self._client.events().list(
        #       calendarId='primary',
        #       timeMin=since.isoformat() if since else None,
        #       singleEvents=True,
        #       orderBy='startTime'
        #   ).execute()

        # Mock events for testing
        now = datetime.now(timezone.utc)
        mock_events = [
            {
                "id": "event_1",
                "summary": "Weekly Team Standup",
                "description": "Discuss progress on current sprint items",
                "start": now + timedelta(hours=2),
                "end": now + timedelta(hours=2, minutes=30),
                "attendees": ["team@company.com"],
                "location": "Conference Room A",
                "recurring": True,
            },
            {
                "id": "event_2",
                "summary": "1:1 with Manager",
                "description": "Career growth and feedback discussion",
                "start": now + timedelta(days=1, hours=3),
                "end": now + timedelta(days=1, hours=3, minutes=45),
                "attendees": ["manager@company.com"],
                "location": "Office Hours",
                "recurring": False,
            },
            {
                "id": "event_3",
                "summary": "Client Presentation",
                "description": "Present Q1 results to client",
                "start": now - timedelta(hours=4),
                "end": now - timedelta(hours=2),
                "attendees": ["client@company.com", "team@company.com"],
                "location": "Video Call",
                "recurring": False,
            },
        ]

        for event in mock_events:
            event_time = event["start"]
            if since and event_time < since:
                continue

            # Create episode content
            attendees = ", ".join(event.get("attendees", []))
            content = f"""
Event: {event['summary']}
Date: {event_time.strftime("%Y-%m-%d %H:%M")}
Duration: {event['end'] - event['start']}

Attendees: {attendees or 'None'}

{event.get('description', 'No description')}
            """.strip()

            metadata = {
                "event_id": event["id"],
                "start_time": event["start"].isoformat(),
                "end_time": event["end"].isoformat(),
                "attendees": event.get("attendees", []),
                "location": event.get("location"),
                "recurring": event.get("recurring", False),
                "synced_at": datetime.now(timezone.utc).isoformat(),
            }

            success = await self._create_episode(
                name=f"calendar_{event['id']}",
                content=content,
                source_type="calendar",
                metadata=metadata,
            )

            if success:
                result.episodes_created += 1
                # Populate cache for get_upcoming_events
                self._events_cache.append({
                    "id": event["id"],
                    "summary": event["summary"],
                    "start": event["start"],
                    "end": event["end"],
                    "attendees": event.get("attendees", []),
                    "location": event.get("location"),
                })
            else:
                result.errors.append(f"Failed to create episode for {event['id']}")

        logger.info(f"{self.service_name}: Synced {result.episodes_created} events")
        return result

    async def get_upcoming_events(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get upcoming events for dashboard display."""
        if not await self.is_connected():
            return []

        # Return cached events sorted by start time
        return sorted(
            [e for e in self._events_cache if e["start"] > datetime.now(timezone.utc)],
            key=lambda x: x["start"]
        )[:limit]

    async def suggest_focus_blocks(self) -> List[Dict[str, Any]]:
        """Suggest focus time blocks based on calendar patterns.

        Analyzes calendar to find gaps for focus time.
        """
        if not await self.is_connected():
            return []

        # Stub: Would analyze calendar for focus time opportunities
        return [
            {
                "suggested_time": "9:00 AM - 11:00 AM",
                "reason": "Light meeting schedule detected",
                "confidence": 0.85,
            },
            {
                "suggested_time": "2:00 PM - 4:00 PM",
                "reason": "Afternoon focus window",
                "confidence": 0.78,
            },
        ]
