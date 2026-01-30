"""EchoTeam Event Layer - Redpanda Event Streaming

Replaces synchronous clone actions with async event processing:
- Event publishing for clone actions
- Consumer groups for parallel processing
- Audit logging and replayability

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                      RedpandaEvents                          │
    │  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
    │  │ Publish  │───►│  Topic   │───►│ Consume  │              │
    │  │ (Async)  │    │ (Logs)   │    │ (Groups) │              │
    │  └──────────┘    └──────────┘    └──────────┘              │
    │       │               │                 │                   │
    │       └───────────────┴─────────────────┘                   │
    │                       │                                     │
    │              ┌────────▼────────┐                            │
    │              │    Redpanda     │                            │
    │              │  (Kafka compat) │                            │
    │              └─────────────────┘                            │
    └─────────────────────────────────────────────────────────────┘

Usage:
    from app.events import RedpandaEvents, EventTypes

    events = RedpandaEvents()
    await events.initialize()

    # Publish clone action
    await events.publish_action({
        "clone_type": "email",
        "action": "draft_reply",
        "user_id": "user123",
        "payload": {...},
    })

    # Consume actions (in worker process)
    async for action in events.consume_actions("echoteam-workers"):
        await process_action(action)
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any, AsyncGenerator
from uuid import uuid4

import pydantic
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of events in the system."""
    CLONE_ACTION = "clone_action"
    CLONE_RESULT = "clone_result"
    AUDIT_LOG = "audit_log"
    NOTIFICATION = "notification"
    RATE_LIMIT = "rate_limit"
    CONTEXT_UPDATE = "context_update"


class EventStatus(str, Enum):
    """Status of an event."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Event(BaseModel):
    """Base event model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: str
    payload: dict = Field(default_factory=dict)
    status: EventStatus = EventStatus.PENDING
    error: Optional[str] = None

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> "Event":
        """Deserialize from JSON string."""
        return cls.model_validate_json(data)


@dataclass
class EventsConfig:
    """Configuration for Redpanda events layer.

    Uses Redpanda for:
    - Low-latency event streaming
    - Consumer groups for parallel processing
    - Kafka-compatible API for portability

    Environment variables (for production):
        REDPANDA_URL: Redpanda connection URL (default: localhost:9092)
        REDPANDA_API_KEY: Optional API key for authentication
        CONSUMER_GROUP: Consumer group name (default: echoteam-workers)
    """
    redpanda_url: str = "localhost:9092"
    redpanda_api_key: Optional[str] = None
    consumer_group: str = "echoteam-workers"
    auto_create_topics: bool = True

    def __post_init__(self) -> None:
        """Validate configuration."""
        pass


class RedpandaEvents:
    """Redpanda-based event layer for async clone actions.

    This class provides:
    - Async event publishing for clone operations
    - Consumer groups for parallel processing
    - Event replayability for debugging
    - Audit logging integration

    Attributes:
        config: Events configuration
    """

    def __init__(
        self,
        config: Optional[EventsConfig] = None,
    ):
        """Initialize Redpanda events layer.

        Args:
            config: Optional events configuration (uses defaults if not provided)
        """
        self.config = config or EventsConfig()
        self._initialized = False
        self._producer: Optional[Any] = None
        self._consumer: Optional[Any] = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the events layer and connect to Redpanda."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            try:
                await self._ensure_client()
                self._initialized = True
                logger.info(
                    f"RedpandaEvents initialized at {self.config.redpanda_url}"
                )
            except Exception as e:
                logger.error(f"Failed to initialize RedpandaEvents: {e}")
                raise

    async def _ensure_client(self) -> Any:
        """Ensure Redpanda client is available."""
        if self._producer is not None:
            return self._producer

        try:
            from aiokafka import AIOKafkaProducer

            # Create async producer
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.config.redpanda_url,
                value_serializer=lambda v: json.dumps(v).encode(),
                key_serializer=lambda k: k.encode() if k else None,
            )
            await self._producer.start()
            logger.info(f"Connected to Redpanda at {self.config.redpanda_url}")
            return self._producer

        except ImportError as e:
            logger.error(f"Failed to import aiokafka: {e}")
            raise ImportError(
                "aiokafka not installed. Install with: pip install aiokafka"
            ) from e

    async def close(self) -> None:
        """Close the events layer and release resources."""
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
        self._initialized = False
        logger.info("RedpandaEvents closed")

    @property
    def is_initialized(self) -> bool:
        """Check if events layer is initialized."""
        return self._initialized

    async def publish_event(
        self,
        topic: str,
        event: Event,
        key: Optional[str] = None,
    ) -> bool:
        """Publish an event to a Redpanda topic.

        Args:
            topic: Topic name to publish to
            event: Event to publish
            key: Optional partition key (user_id for ordering)

        Returns:
            True if publish succeeded
        """
        if not self._initialized:
            await self.initialize()

        try:
            producer = await self._ensure_client()
            await producer.send_and_wait(
                topic=topic,
                value=event.model_dump(mode="json"),
                key=key or event.user_id,
            )
            logger.debug(f"Published event {event.id} to {topic}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return False

    async def publish_action(
        self,
        action: dict,
        user_id: str,
        clone_type: str,
    ) -> bool:
        """Publish a clone action event.

        Args:
            action: Action details
            user_id: User identifier
            clone_type: Type of clone (email, calendar, ops)

        Returns:
            True if publish succeeded
        """
        event = Event(
            type=EventType.CLONE_ACTION,
            user_id=user_id,
            payload={
                "clone_type": clone_type,
                "action": action,
            },
        )
        return await self.publish_event(
            topic="clone-actions",
            event=event,
            key=user_id,
        )

    async def publish_audit_log(
        self,
        user_id: str,
        action: str,
        details: dict,
    ) -> bool:
        """Publish an audit log event.

        Args:
            user_id: User identifier
            action: Action performed
            details: Action details

        Returns:
            True if publish succeeded
        """
        event = Event(
            type=EventType.AUDIT_LOG,
            user_id=user_id,
            payload={
                "action": action,
                "details": details,
            },
        )
        return await self.publish_event(
            topic="audit-logs",
            event=event,
            key=user_id,
        )

    async def consume_events(
        self,
        topic: str,
        group_id: Optional[str] = None,
    ) -> AsyncGenerator[Event, None]:
        """Consume events from a Redpanda topic.

        Args:
            topic: Topic name to consume from
            group_id: Consumer group ID (uses config default if not provided)

        Yields:
            Event objects from the topic
        """
        if not self._initialized:
            await self.initialize()

        consumer = None
        try:
            from aiokafka import AIOKafkaConsumer

            consumer = AIOKafkaConsumer(
                topic,
                bootstrap_servers=self.config.redpanda_url,
                group_id=group_id or self.config.consumer_group,
                value_deserializer=lambda v: json.loads(v.decode()),
                auto_offset_reset="earliest",
                enable_auto_commit=True,
            )
            await consumer.start()

            async for message in consumer:
                try:
                    event = Event.model_validate(message.value)
                    yield event
                except Exception as e:
                    logger.error(f"Failed to deserialize event: {e}")

        except ImportError as e:
            logger.error(f"Failed to import aiokafka: {e}")
            raise ImportError(
                "aiokafka not installed. Install with: pip install aiokafka"
            ) from e
        finally:
            if consumer is not None:
                await consumer.stop()
                logger.debug("Consumer stopped")

    async def consume_actions(
        self,
        group_id: Optional[str] = None,
    ) -> AsyncGenerator[dict, None]:
        """Consume clone actions from the clone-actions topic.

        Args:
            group_id: Consumer group ID

        Yields:
            Action dictionaries from the topic
        """
        async for event in self.consume_events("clone-actions", group_id):
            if event.type == EventType.CLONE_ACTION:
                yield event.payload

    async def create_topics(self, topics: list[str]) -> None:
        """Create topics if they don't exist.

        Args:
            topics: List of topic names to create
        """
        try:
            from aiokafka import AIOKafkaAdminClient
            from aiokafka.admin import NewTopic

            admin = AIOKafkaAdminClient(
                bootstrap_servers=self.config.redpanda_url,
            )
            await admin.start()

            new_topics = [
                NewTopic(name=topic, num_partitions=3, replication_factor=1)
                for topic in topics
            ]

            try:
                await admin.create_topics(new_topics)
                logger.info(f"Created topics: {topics}")
            except Exception as e:
                # Topic already exists is OK
                if "TopicAlreadyExistsError" not in str(e):
                    logger.warning(f"Failed to create topics: {e}")

            await admin.close()

        except ImportError:
            logger.warning("aiokafka not installed, skipping topic creation")


# Module-level events instances for connection pooling
_events_instances: dict[str, RedpandaEvents] = {}
_events_lock = asyncio.Lock()


async def get_events(config: Optional[EventsConfig] = None) -> RedpandaEvents:
    """Get or create a RedpandaEvents instance.

    Args:
        config: Optional events configuration

    Returns:
        RedpandaEvents instance
    """
    async with _events_lock:
        key = "default"
        if key not in _events_instances:
            _events_instances[key] = RedpandaEvents(config=config)
            await _events_instances[key].initialize()
        return _events_instances[key]


async def close_events() -> None:
    """Close all events instances."""
    async with _events_lock:
        for events in list(_events_instances.values()):
            await events.close()
        _events_instances.clear()
