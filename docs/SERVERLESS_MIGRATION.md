# Serverless Migration Plan: $0 Deployment Architecture

**Goal:** Migrate from self-hosted Docker infrastructure to free cloud tiers for $0 deployment on platforms like Railway/Render/Vercel.

## Current Architecture (Docker)

```
Local Docker:
├── Qdrant (localhost:6333)          → Vector DB
├── Redpanda (localhost:9092)        → Event Streaming
└── Ollama (localhost:11434)         → Local LLM
```

## Target Architecture (Serverless)

```
Cloud Services (Free Tiers):
├── Qdrant Cloud (1GB free)          → Vector DB
├── Upstash Kafka (10k msgs/day)     → Event Streaming
└── Ollama (Render dedicated)        → LLM (or cloud API)
```

---

## 1. Qdrant: Local → Qdrant Cloud

### Connection Pattern

```python
# Before: Local Docker
from qdrant_client import AsyncQdrantClient

client = AsyncQdrantClient(url="http://localhost:6333")

# After: Qdrant Cloud with API Key
from qdrant_client import AsyncQdrantClient

# Detect cloud vs local based on environment
qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
qdrant_api_key = os.getenv("QDRANT_API_KEY")  # None for local

client = AsyncQdrantClient(
    url=qdrant_url,
    api_key=qdrant_api_key,  # Pass None for local, key for cloud
)
```

### Environment Variables

```bash
# Local Development (.env)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# Production (Qdrant Cloud)
QDRANT_URL=https://xxxxx-xxxxx.us-east-1.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=your-api-key-here
```

---

## 2. Redpanda → Upstash Kafka

### Key Differences

| Feature | Redpanda (Local) | Upstash Kafka (Cloud) |
|---------|------------------|----------------------|
| Auth | None | SASL/SCRAM-SHA-256 |
| SSL | Optional | Required |
| Bootstrap | localhost:9092 | Provided by Upstash |

### Dual-Compatible Client Pattern

```python
# app/events/kafka_client.py

import os
import ssl
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.helpers import create_ssl_context


def is_cloud_kafka() -> bool:
    """Check if we're using cloud Kafka (Upstash) vs local Redpanda."""
    return os.getenv("KAFKA_USERNAME") is not None


def create_producer():
    """Create Kafka producer compatible with both local and cloud."""
    bootstrap_servers = os.getenv(
        "KAFKA_BROKERS",
        "localhost:9092"
    )

    if is_cloud_kafka():
        # Upstash Kafka requires SSL + SASL
        ssl_context = create_ssl_context(
            cafile=None,  # Upstash provides CA in endpoint
            certfile=None,
            keyfile=None,
        )
        # For Upstash, we use the endpoint's certs via system certs
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED

        return AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            security_protocol="SASL_SSL",
            ssl_context=ssl_context,
            sasl_mechanism="SCRAM-SHA-256",
            sasl_plain_username=os.getenv("KAFKA_USERNAME"),
            sasl_plain_password=os.getenv("KAFKA_PASSWORD"),
        )
    else:
        # Local Redpanda - no auth
        return AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
        )


def create_consumer(topic: str, group_id: str):
    """Create Kafka consumer compatible with both local and cloud."""
    bootstrap_servers = os.getenv(
        "KAFKA_BROKERS",
        "localhost:9092"
    )

    if is_cloud_kafka():
        ssl_context = create_ssl_context()
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED

        return AIOKafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            security_protocol="SASL_SSL",
            ssl_context=ssl_context,
            sasl_mechanism="SCRAM-SHA-256",
            sasl_plain_username=os.getenv("KAFKA_USERNAME"),
            sasl_plain_password=os.getenv("KAFKA_PASSWORD"),
            auto_offset_reset="earliest",
        )
    else:
        # Local Redpanda - no auth
        return AIOKafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset="earliest",
        )
```

### Environment Variables

```bash
# Local Development (.env)
KAFKA_BROKERS=localhost:9092
KAFKA_USERNAME=
KAFKA_PASSWORD=

# Production (Upstash Kafka)
KAFKA_BROKERS=global-leading-midge-7845.us-east-1.kafka.upstash.io:9092
KAFKA_USERNAME=global-leading-midge-7845
KAFKA_PASSWORD=your-scram-password-here
```

---

## 3. Updated Redpanda Events Module

```python
# app/events/redpanda.py (updated)

import os
import logging
from typing import Optional, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Event types for the system."""
    CLONE_ACTION = "clone_action"
    CLONE_RESULT = "clone_result"
    AUDIT_LOG = "audit_log"
    NOTIFICATION = "notification"
    RATE_LIMIT = "rate_limit"
    CONTEXT_UPDATE = "context_update"


class EventStatus(str, Enum):
    """Event processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Event:
    """Event model for Redpanda/Upstash messaging."""
    type: EventType
    user_id: str
    payload: dict
    status: EventStatus = EventStatus.PENDING
    id: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.id is None:
            import uuid
            self.id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_json(self) -> str:
        return json.dumps({
            "id": self.id,
            "type": self.type.value,
            "user_id": self.user_id,
            "payload": self.payload,
            "status": self.status.value,
            "timestamp": self.timestamp,
        })

    @classmethod
    def from_json(cls, data: str) -> "Event":
        obj = json.loads(data)
        return cls(
            id=obj["id"],
            type=EventType(obj["type"]),
            user_id=obj["user_id"],
            payload=obj["payload"],
            status=EventStatus(obj["status"]),
            timestamp=obj["timestamp"],
        )


@dataclass
class EventsConfig:
    """Configuration for Redpanda/Upstash events."""
    redpanda_url: str = "localhost:9092"
    consumer_group: str = "echoteam-workers"
    auto_create_topics: bool = True

    @classmethod
    def from_env(cls) -> "EventsConfig":
        import os
        return cls(
            redpanda_url=os.getenv("KAFKA_BROKERS", "localhost:9092"),
            consumer_group=os.getenv(
                "CONSUMER_GROUP",
                "echoteam-workers"
            ),
            auto_create_topics=os.getenv(
                "AUTO_CREATE_TOPICS", "true"
            ).lower() == "true",
        )


class RedpandaEvents:
    """Redpanda-compatible events using aiokafka.

    Supports both local Redpanda and Upstash Kafka.
    """

    def __init__(self, config: Optional[EventsConfig] = None):
        self.config = config or EventsConfig.from_env()
        self._producer: Optional[AIOKafkaProducer] = None
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._initialized = False

    def _is_cloud(self) -> bool:
        """Check if using cloud Kafka (Upstash)."""
        return os.getenv("KAFKA_USERNAME") is not None

    async def initialize(self) -> None:
        """Initialize the events layer."""
        from aiokafka import AIOKafkaProducer

        if self._initialized:
            return

        try:
            if self._is_cloud():
                # Upstash Kafka - requires SSL + SASL
                import ssl
                from aiokafka.helpers import create_ssl_context

                ssl_context = create_ssl_context()
                ssl_context.check_hostname = True
                ssl_context.verify_mode = ssl.CERT_REQUIRED

                self._producer = AIOKafkaProducer(
                    bootstrap_servers=self.config.redpanda_url,
                    security_protocol="SASL_SSL",
                    ssl_context=ssl_context,
                    sasl_mechanism="SCRAM-SHA-256",
                    sasl_plain_username=os.getenv("KAFKA_USERNAME"),
                    sasl_plain_password=os.getenv("KAFKA_PASSWORD"),
                    value_serializer=lambda v: json.dumps(v).encode(),
                )
            else:
                # Local Redpanda - no auth
                self._producer = AIOKafkaProducer(
                    bootstrap_servers=self.config.redpanda_url,
                    value_serializer=lambda v: json.dumps(v).encode(),
                )

            await self._producer.start()
            self._initialized = True
            logger.info(
                f"Redpanda/Upstash events initialized at "
                f"{self.config.redpanda_url}"
            )
        except ImportError as e:
            logger.error(f"Failed to import aiokafka: {e}")
            raise

    async def close(self) -> None:
        """Close the events layer."""
        if self._producer:
            await self._producer.stop()
            self._producer = None
        if self._consumer:
            await self._consumer.stop()
            self._consumer = None
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    async def publish_event(
        self,
        topic: str,
        event: Event,
        key: Optional[str] = None,
    ) -> bool:
        """Publish an event to a topic."""
        if not self._initialized:
            await self.initialize()

        try:
            await self._producer.send_and_wait(
                topic,
                value=event.to_json(),
                key=key.encode() if key else None,
            )
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
        """Publish a clone action event."""
        topic = f"{clone_type}.actions"
        event = Event(
            type=EventType.CLONE_ACTION,
            user_id=user_id,
            payload=action,
        )
        return await self.publish_event(topic, event, key=user_id)

    async def consume_events(
        self,
        topic: str,
        group_id: Optional[str] = None,
    ) -> AsyncGenerator[Event, None]:
        """Consume events from a topic."""
        if not self._initialized:
            await self.initialize()

        consumer = None
        try:
            from aiokafka import AIOKafkaConsumer

            if self._is_cloud():
                import ssl
                from aiokafka.helpers import create_ssl_context

                ssl_context = create_ssl_context()
                ssl_context.check_hostname = True
                ssl_context.verify_mode = ssl.CERT_REQUIRED

                consumer = AIOKafkaConsumer(
                    topic,
                    bootstrap_servers=self.config.redpanda_url,
                    group_id=group_id or self.config.consumer_group,
                    value_deserializer=lambda v: json.loads(v.decode()),
                    security_protocol="SASL_SSL",
                    ssl_context=ssl_context,
                    sasl_mechanism="SCRAM-SHA-256",
                    sasl_plain_username=os.getenv("KAFKA_USERNAME"),
                    sasl_plain_password=os.getenv("KAFKA_PASSWORD"),
                    auto_offset_reset="earliest",
                    enable_auto_commit=True,
                )
            else:
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
                    event = Event.from_json(message.value.decode())
                    yield event
                except Exception as e:
                    logger.error(f"Failed to deserialize event: {e}")

        finally:
            if consumer:
                await consumer.stop()


# Module-level instances for connection pooling
_events_instances = {}
_events_lock = None


async def get_events() -> RedpandaEvents:
    """Get or create a RedpandaEvents instance."""
    global _events_instances, _events_lock

    import asyncio
    if _events_lock is None:
        _events_lock = asyncio.Lock()

    async with _events_lock:
        key = "default"
        if key not in _events_instances:
            _events_instances[key] = RedpandaEvents()
            await _events_instances[key].initialize()
        return _events_instances[key]


async def close_events() -> None:
    """Close all events instances."""
    global _events_instances, _events_lock

    async with _events_lock:
        for events in list(_events_instances.values()):
            await events.close()
        _events_instances.clear()
```

---

## 4. Updated Qdrant Memory Module

```python
# app/memory/qdrant.py (updated)

import os
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)


class MemorySourceType(str, Enum):
    """Source types for memory entries."""
    EMAIL = "email"
    CALENDAR = "calendar"
    TASK = "task"
    NOTE = "note"
    RESEARCH = "research"
    USER_INTERACTION = "user_interaction"
    SYSTEM = "system"


@dataclass
class MemoryConfig:
    """Configuration for Qdrant memory layer."""
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    embedding_model: str = "nomic-embed-text:v1.5"
    embedding_endpoint: str = "http://localhost:11434/api/embed"
    embedding_dimensions: int = 768
    max_results: int = 20
    collection_name: str = "echoteam_memory"

    def __post_init__(self) -> None:
        self.validate()

    @classmethod
    def from_env(cls) -> "MemoryConfig":
        """Create config from environment variables."""
        return cls(
            qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            embedding_model=os.getenv(
                "EMBEDDING_MODEL",
                "nomic-embed-text:v1.5"
            ),
            embedding_endpoint=os.getenv(
                "EMBEDDING_ENDPOINT",
                "http://localhost:11434/api/embed"
            ),
            embedding_dimensions=int(
                os.getenv("EMBEDDING_DIMENSIONS", "768")
            ),
            max_results=int(os.getenv("MAX_RESULTS", "20")),
            collection_name=os.getenv(
                "COLLECTION_NAME",
                "echoteam_memory"
            ),
        )

    def validate(self) -> None:
        """Validate configuration."""
        if not self.qdrant_url.startswith("http"):
            raise ValueError(
                f"qdrant_url must start with http:// or https://, "
                f"got {self.qdrant_url}"
            )


class QdrantMemory:
    """Qdrant-based memory with cloud support."""

    def __init__(
        self,
        user_id: str,
        config: Optional[MemoryConfig] = None,
    ):
        self.user_id = user_id
        self.config = config or MemoryConfig.from_env()
        self.config.validate()

        self._initialized = False
        self._client: Optional[Any] = None
        self._lock = asyncio.Lock()
        self.collection = f"echoteam_{user_id}"

    async def _ensure_client(self) -> Any:
        """Ensure Qdrant client is available."""
        if self._client is not None:
            return self._client

        try:
            from qdrant_client import AsyncQdrantClient
            from qdrant_client.models import VectorParams, Distance

            self._client = AsyncQdrantClient(
                url=self.config.qdrant_url,
                api_key=self.config.qdrant_api_key,  # None for local, key for cloud
            )

            # Ensure collection exists
            try:
                await self._client.get_collection(self.collection)
            except Exception:
                await self._client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(
                        size=self.config.embedding_dimensions,
                        distance=Distance.COSINE,
                    ),
                )

            return self._client

        except ImportError as e:
            logger.error(f"Failed to import Qdrant client: {e}")
            raise ImportError(
                "Qdrant not installed. Install with: pip install qdrant-client"
            ) from e

    async def initialize(self) -> None:
        """Initialize the memory layer."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            await self._ensure_client()
            self._initialized = True
            logger.info(
                f"QdrantMemory initialized for user {self.user_id} "
                f"at {self.config.qdrant_url}"
            )

    async def close(self) -> None:
        """Close the memory layer."""
        if self._client is not None:
            await self._client.close()
            self._client = None
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    # ... rest of methods (add, search, get_user_context) unchanged
```

---

## 5. Environment Configuration

### Local Development (.env)

```bash
# Local Docker Stack
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

KAFKA_BROKERS=localhost:9092
KAFKA_USERNAME=
KAFKA_PASSWORD=

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_CODING=granite3.1-moe:3b
OLLAMA_MODEL_EMBEDDING=nomic-embed-text:v1.5

LANGFUSE_ENABLED=false
```

### Production (.env.production)

```bash
# Qdrant Cloud (Free Tier - 1GB)
QDRANT_URL=https://xxxxx-xxxxx.us-east-1.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=your-api-key-here

# Upstash Kafka (Free Tier - 10k msgs/day)
KAFKA_BROKERS=global-leading-midge-7845.us-east-1.kafka.upstash.io:9092
KAFKA_USERNAME=global-leading-midge-7845
KAFKA_PASSWORD=your-scram-password-here

# Ollama (Cloud API or Render dedicated)
OLLAMA_BASE_URL=http://your-render-service:11434
OLLAMA_MODEL_CODING=granite3.1-moe:3b
OLLAMA_MODEL_EMBEDDING=nomic-embed-text:v1.5

# Langfuse Cloud (Hobby Plan - 50k traces/mo)
LANGFUSE_ENABLED=true
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=your-public-key
LANGFUSE_SECRET_KEY=your-secret-key
```

---

## 6. Deployment Checklist

### Step 1: Create Cloud Accounts

- [ ] Sign up for [Qdrant Cloud](https://cloud.qdrant.io) (Free 1GB)
- [ ] Sign up for [Upstash Kafka](https://upstash.com) (Free 10k msgs/day)
- [ ] Sign up for [Langfuse Cloud](https://cloud.langfuse.com) (Hobby plan)

### Step 2: Configure Cloud Resources

- [ ] Create Qdrant Cloud cluster, get URL and API Key
- [ ] Create Upstash Kafka topic(s): `chat.events`, `clone.actions`
- [ ] Get Upstash Kafka credentials (bootstrap server, username, password)
- [ ] Create Langfuse project, get API keys

### Step 3: Update Code

- [ ] Update `app/events/redpanda.py` with dual-compat Kafka client
- [ ] Update `app/memory/qdrant.py` with Qdrant Cloud support
- [ ] Add environment variable loading in config

### Step 4: Deploy

- [ ] Push code to GitHub
- [ ] Create Render web service for FastAPI
- [ ] Configure environment variables in Render
- [ ] Test the deployed endpoint

---

## 7. Cost Comparison

| Resource | Local Docker | Cloud Free Tier |
|----------|-------------|-----------------|
| Vector DB | Qdrant (self-hosted) | Qdrant Cloud (1GB free) |
| Event Streaming | Redpanda (self-hosted) | Upstash Kafka (10k msgs/day) |
| Compute | Local/Railway | Render Free |
| LLM | Ollama (local/Render) | Ollama (Render) or API |
| Observability | Langfuse (self-hosted) | Langfuse Cloud (50k traces) |
| **Total/Month** | **~$0-20** | **$0** |

---

## 8. Limitations

1. **Upstash Kafka Limits:**
   - 10,000 messages per day free tier
   - 1GB data retention
   - Not suitable for high-throughput production

2. **Qdrant Cloud Limits:**
   - 1GB storage free tier
   - Limited to 1 cluster
   - No automatic backups on free tier

3. **Render Free Tier:**
   - Service spins down after 15 min inactivity
   - 500 hours/month compute
   - No persistent connections

4. **Langfuse Cloud Limits:**
   - 50,000 traces/month
   - 7-day data retention

---

## 9. Testing the Migration

```bash
# Test with local Redpanda first
export KAFKA_BROKERS=localhost:9092
export KAFKA_USERNAME=
pytest tests/test_events_redpanda.py -v

# Test with Upstash Kafka (mock credentials)
export KAFKA_BROKERS=your-upstash-endpoint.kafka.upstash.io:9092
export KAFKA_USERNAME=your-username
export KAFKA_PASSWORD=your-password
pytest tests/test_events_redpanda.py -v -k integration
```
