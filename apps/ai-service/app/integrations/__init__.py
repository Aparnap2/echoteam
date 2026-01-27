"""Integration stubs for external services.

These modules provide OAuth-based connections to:
- Gmail (email ingestion)
- Google Calendar (calendar events)
- Notion (tasks and notes)
- Google Drive (files)

Currently stubs - full implementation requires OAuth credentials.
"""

from app.integrations.base import IntegrationConfig, IntegrationStatus
from app.integrations.gmail import GmailIntegration
from app.integrations.calendar import CalendarIntegration
from app.integrations.notion import NotionIntegration

__all__ = [
    "IntegrationConfig",
    "IntegrationStatus",
    "GmailIntegration",
    "CalendarIntegration",
    "NotionIntegration",
]
