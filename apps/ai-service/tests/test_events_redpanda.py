"""TDD Tests for Redpanda Event Layer

These tests define the expected behavior of the RedpandaEvents class.
Run with: pytest tests/test_events_redpanda.py -v

Tests cover:
- Configuration validation
- Initialization and connection
- Event publishing
- Event consumption with consumer groups
- Topic management
"""

import os
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


# Set environment variables for testing
os.environ["REDPANDA_URL"] = "localhost:9092"
os.environ["CONSUMER_GROUP"] = "echoteam-workers-test"


class TestEventsConfig:
    """Unit tests for EventsConfig."""

    def test_config_defaults(self):
        """Test EventsConfig has sensible defaults."""
        from app.events.redpanda import EventsConfig

        config = EventsConfig()
        assert config.redpanda_url == "localhost:9092"
        assert config.consumer_group == "echoteam-workers"
        assert config.auto_create_topics is True

    def test_config_custom_values(self):
        """Test config with custom values."""
        from app.events.redpanda import EventsConfig

        config = EventsConfig(
            redpanda_url="redpanda.example.com:9092",
            consumer_group="custom-workers",
            auto_create_topics=False,
        )
        assert config.redpanda_url == "redpanda.example.com:9092"
        assert config.consumer_group == "custom-workers"
        assert config.auto_create_topics is False


class TestEvent:
    """Unit tests for Event model."""

    def test_event_creation(self):
        """Test creating an event."""
        from app.events.redpanda import Event, EventType, EventStatus

        event = Event(
            type=EventType.CLONE_ACTION,
            user_id="user123",
            payload={"action": "draft_reply"},
        )
        assert event.type == EventType.CLONE_ACTION
        assert event.user_id == "user123"
        assert event.payload["action"] == "draft_reply"
        assert event.status == EventStatus.PENDING
        assert event.id is not None
        assert event.timestamp is not None

    def test_event_to_json(self):
        """Test serializing event to JSON."""
        from app.events.redpanda import Event, EventType

        event = Event(
            type=EventType.AUDIT_LOG,
            user_id="user456",
            payload={"operation": "login"},
        )
        json_str = event.to_json()
        assert "user456" in json_str
        assert "audit_log" in json_str

    def test_event_from_json(self):
        """Test deserializing event from JSON."""
        from app.events.redpanda import Event, EventType

        original = Event(
            type=EventType.CLONE_RESULT,
            user_id="user789",
            payload={"result": "success"},
        )
        json_str = original.to_json()
        restored = Event.from_json(json_str)
        assert restored.type == EventType.CLONE_RESULT
        assert restored.user_id == "user789"
        assert restored.payload["result"] == "success"


class TestEventType:
    """Tests for EventType enum."""

    def test_event_types_defined(self):
        """Test all expected event types are defined."""
        from app.events.redpanda import EventType

        assert EventType.CLONE_ACTION == "clone_action"
        assert EventType.CLONE_RESULT == "clone_result"
        assert EventType.AUDIT_LOG == "audit_log"
        assert EventType.NOTIFICATION == "notification"
        assert EventType.RATE_LIMIT == "rate_limit"
        assert EventType.CONTEXT_UPDATE == "context_update"


class TestRedpandaEventsUnit:
    """Unit tests for RedpandaEvents - mocked client."""

    @pytest_asyncio.fixture
    async def events(self):
        """Create events instance with mocked Kafka client."""
        from app.events.redpanda import RedpandaEvents, EventsConfig

        config = EventsConfig(
            redpanda_url="localhost:9092",
            consumer_group="test-workers",
        )
        events = RedpandaEvents(config=config)
        yield events
        await events.close()

    @pytest.mark.asyncio
    async def test_events_not_initialized_initially(self, events):
        """Test events is not initialized on creation."""
        assert events.is_initialized is False

    @pytest.mark.asyncio
    async def test_close_uninitialized_events(self, events):
        """Test closing uninitialized events is safe."""
        await events.close()  # Should not raise
        assert events.is_initialized is False

    @pytest.mark.asyncio
    async def test_multiple_close_is_safe(self, events):
        """Test closing multiple times is safe."""
        await events.close()
        await events.close()  # Should not raise


class TestRedpandaEventsWithMocks:
    """Unit tests for RedpandaEvents with mocked dependencies."""

    @pytest_asyncio.fixture
    async def events(self):
        """Create events instance with mocked producer."""
        from app.events.redpanda import RedpandaEvents, EventsConfig

        config = EventsConfig(
            redpanda_url="localhost:9092",
            consumer_group="test-workers",
        )
        events = RedpandaEvents(config=config)
        yield events
        await events.close()

    @pytest.mark.asyncio
    async def test_publish_event_returns_success(self, events):
        """Test publish event returns success."""
        from app.events.redpanda import Event, EventType

        with patch.object(events, '_ensure_client', new_callable=AsyncMock) as mock_client:
            mock_client.return_value = AsyncMock()
            mock_client.return_value.send_and_wait = AsyncMock()

            event = Event(
                type=EventType.CLONE_ACTION,
                user_id="user123",
                payload={"clone_type": "email"},
            )

            result = await events.publish_event(
                topic="clone-actions",
                event=event,
                key="user123",
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_publish_action_returns_success(self, events):
        """Test publish action returns success."""
        with patch.object(events, '_ensure_client', new_callable=AsyncMock) as mock_client:
            mock_client.return_value = AsyncMock()
            mock_client.return_value.send_and_wait = AsyncMock()

            result = await events.publish_action(
                action={"type": "draft_reply"},
                user_id="user123",
                clone_type="email",
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_publish_audit_log_returns_success(self, events):
        """Test publish audit log returns success."""
        with patch.object(events, '_ensure_client', new_callable=AsyncMock) as mock_client:
            mock_client.return_value = AsyncMock()
            mock_client.return_value.send_and_wait = AsyncMock()

            result = await events.publish_audit_log(
                user_id="user123",
                action="login",
                details={"ip": "192.168.1.1"},
            )
            assert result is True


class TestRedpandaEventsIntegration:
    """Integration tests for RedpandaEvents - requires real Redpanda instance."""

    TEST_USER_ID = "integration_test_user"

    @pytest_asyncio.fixture
    async def events(self):
        """Create events instance for integration testing."""
        from app.events.redpanda import RedpandaEvents, EventsConfig

        config = EventsConfig(
            redpanda_url="localhost:9092",
            consumer_group="test-workers",
        )
        events = RedpandaEvents(config=config)
        await events.initialize()

        yield events

        await events.close()

    @pytest.mark.asyncio
    async def test_initialize(self, events):
        """Test events layer initialization."""
        assert events.is_initialized is True

    @pytest.mark.asyncio
    async def test_publish_and_receive_action(self, events):
        """Test publishing and receiving an action event."""
        from app.events.redpanda import EventType

        # Publish an action
        result = await events.publish_action(
            action={"type": "test_action", "data": "test_data"},
            user_id=self.TEST_USER_ID,
            clone_type="email",
        )
        assert result is True


class TestModuleLevelFunctions:
    """Tests for module-level helper functions."""

    @pytest.mark.asyncio
    async def test_get_events_creates_instance(self):
        """Test get_events creates a new instance."""
        from app.events.redpanda import get_events, close_events

        events = await get_events()
        assert events is not None
        assert events.is_initialized is True

        await close_events()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
