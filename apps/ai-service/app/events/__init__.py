"""EchoTeam Event Layer - Redpanda Event Streaming

This module provides Redpanda-based event streaming for async clone actions,
audit logging, and event-driven architecture.

Modules:
- redpanda: Redpanda integration with consumer groups
"""

from app.events.redpanda import (
    RedpandaEvents,
    EventsConfig,
    Event,
    EventType,
    EventStatus,
    get_events,
    close_events,
)

__all__ = [
    "RedpandaEvents",
    "EventsConfig",
    "Event",
    "EventType",
    "EventStatus",
    "get_events",
    "close_events",
]
