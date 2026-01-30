# EchoTeam Modern Data/AI Stack Integration Plan

## Executive Summary

Integrating the **"Magnificent Six"** stack into EchoTeam for a production-grade, observable AI system:

| Tool | Purpose | Integration Priority | Status |
|------|---------|---------------------|--------|
| **Qdrant** | Hybrid Vector + Keyword Search | P0 - Replace Graphiti memory | Ready to run |
| **Langfuse** | LLM Observability & Tracing | P0 - Trace all agent ops | Ready to run |
| **Redpanda** | Event Streaming | P1 - Async clone actions | Image installed |
| **Netdata** | Infrastructure Monitoring | P1 - Already running | Running |
| **Dagster** | Pipeline Orchestration | P2 - Data sync jobs | Image needed |
| **PostgreSQL** | Structured Data + pgvector | P2 - Replace some Neo4j | Image installed |

---

## Current Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   EchoTeam (Current)                     │
├─────────────────────────────────────────────────────────┤
│  Frontend (React) → FastAPI → LangGraph → Clones        │
│                         ↓                                │
│              Graphiti + Neo4j (Memory)                   │
│                         ↓                                │
│              Ollama (LLM + Embeddings)                   │
└─────────────────────────────────────────────────────────┘
```

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      EchoTeam (Modern Stack)                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │   Frontend   │  │   Netdata    │  │   Langfuse   │               │
│  │   (React)    │  │   Dashboard  │  │   Tracing    │               │
│  └──────┬───────┘  └──────────────┘  └──────┬───────┘               │
│         │                                     │                       │
│         ↓                                     ↓                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                      FastAPI Layer                           │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │    │
│  │  │ Redpanda    │  │ Dagster     │  │ LangGraph           │   │    │
│  │  │ (Events)    │  │ (Pipelines) │  │ (Supervisor +       │   │    │
│  │  │ Producer    │  │             │  │  3 Clone Nodes)     │   │    │
│  │  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘   │    │
│  └─────────┼────────────────┼─────────────────────┼───────────────┘    │
│            ↓                 ↓                     ↓                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐    │
│  │   Qdrant     │  │  PostgreSQL  │  │  Langfuse (Tracing)      │    │
│  │  (Hybrid     │  │  (Relational │  │  + LLM Observability     │    │
│  │   Search)    │  │   + pgvector)│  │                          │    │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Neo4j (Optional)                         │    │
│  │         Graphiti for temporal knowledge graph               │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Ollama (LLM + Embeddings)                 │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Qdrant Integration (P0)

### Why Qdrant over Graphiti/Neo4j?
- **Hybrid Search**: Dense vectors + BM25 keyword search in one query
- **Simpler setup**: No schema initialization required
- **Better RAG**: Native hybrid search for clone context retrieval
- **Rust-based**: Lower resource usage than Neo4j

### Implementation

```python
# app/memory/qdrant.py
from qdrant_client import AsyncQdrantClient, models
import numpy as np
from app.llm.ollama_client import OllamaClient

class QdrantMemory:
    """Hybrid memory with dense + sparse search."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.client = AsyncQdrantClient(url="http://localhost:6333")
        self.embedder = OllamaClient()
        self.collection = f"echoteam_{user_id}"

    async def initialize(self):
        """Create collection with hybrid index."""
        await self.client.create_collection(
            collection_name=self.collection,
            vectors_config=models.VectorParams(
                size=768,  # nomic-embed-text dimension
                distance=models.Distance.COSINE,
            ),
            sparse_vectors_config={
                "text": models.SparseVectorParams(
                    modifier=models.SparseMod.MIN,
                    optimizer=models.SparseIndexing.DENSITY,
                )
            },
        )

    async def add(self, content: str, metadata: dict):
        """Add content with both dense and sparse vectors."""
        # Generate dense embedding
        dense = await self.embedder.embed(content)

        # Add to Qdrant with payload
        await self.client.upsert(
            collection_name=self.collection,
            points=[
                models.PointStruct(
                    id=str(uuid4()),
                    vector=dense,
                    sparse_vector=self._generate_sparse_vector(content),
                    payload={
                        "content": content,
                        "user_id": self.user_id,
                        **metadata,
                    },
                )
            ],
        )

    async def search(self, query: str, limit: int = 10):
        """Hybrid search: dense + keyword."""
        query_vector = await self.embedder.embed(query)

        results = await self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            query_sparse_vector=self._generate_sparse_vector(query),
            limit=limit,
            score_threshold=0.5,
        )
        return results
```

### Docker Setup
```bash
docker run -d \
  --name echoteam-qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  qdrant/qdrant
```

---

## Phase 2: Langfuse Integration (P0)

### Why Langfuse?
- **End-to-end tracing** of all agent operations
- **Cost tracking** per clone, per user
- **Latency analysis** for optimization
- **Dataset management** for evaluation

### Implementation

```python
# app/observability/langfuse.py
from langfuse import observe, Langfuse
from langfuse.langchain import CallbackHandler
from app.config import settings

# Initialize
langfuse = Langfuse(
    public_key=settings.LANGFUSE_PUBLIC_KEY,
    secret_key=settings.LANGFUSE_SECRET_KEY,
    host=settings.LANGFUSE_HOST,  # http://localhost:3100
)

def get_langfuse_handler():
    return CallbackHandler(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_HOST,
    )

# Instrument supervisor
@observe()
async def supervisor_workflow(state: AgentState):
    """Main workflow with full tracing."""
    result = await process_clone_tasks(state)
    return result

# Instrument clone operations
@observe(as_type="generation")
async def clone_analysis(clone_type: str, context: str):
    """Trace each clone's LLM analysis."""
    return await llm.analyze(context)
```

### Docker Setup (already have image)
```bash
docker run -d \
  --name echoteam-langfuse \
  -p 3100:3000 \
  -p 3101:3001 \
  -v langfuse_data:/data \
  langfuse/langfuse:3
```

---

## Phase 3: Redpanda Integration (P1)

### Why Redpanda?
- **Kafka-compatible** but single-binary
- **No JVM/ZooKeeper** - simpler operations
- **Event sourcing** for clone actions
- **Async processing** for long-running tasks

### Use Cases in EchoTeam
1. **Action Queue Events**: Publish when clones generate actions
2. **Audit Log**: Track all clone decisions
3. **Notifications**: Async email/alert delivery
4. **Rate Limiting**: Buffer high-frequency requests

### Implementation

```python
# app/events/redpanda.py
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import json

class EchoTeamEvents:
    """Redpanda event producer/consumer."""

    def __init__(self):
        self.producer = None
        self.consumer = None

    async def publish_action(self, action: dict):
        """Publish clone action to Redpanda."""
        await self.producer.send_and_wait(
            topic="clone-actions",
            value=json.dumps(action).encode(),
            key=action["user_id"].encode(),
        )

    async def consume_actions(self):
        """Consume actions for async processing."""
        consumer = AIOKafkaConsumer(
            "clone-actions",
            bootstrap_servers="localhost:9092",
            group_id="echoteam-workers",
        )
        await consumer.start()
        async for msg in consumer:
            yield json.loads(msg.value.decode())

# Usage in clone
@observe()
async def admin_clone(state: AgentState) -> dict:
    action = generate_admin_action(state)
    await events.publish_action({
        "action": action,
        "user_id": state["user_id"],
        "timestamp": datetime.utcnow().isoformat(),
    })
    return action
```

### Docker Setup (already have image)
```bash
docker run -d \
  --name echoteam-redpanda \
  -p 9092:9092 \
  -p 9644:9644 \
  -v redpanda_data:/var/lib/redpanda \
  redpandadata/redpanda \
  redpanda start --overwrite-httpd-addr=0.0.0.0:9644,0.0.0.0:9092
```

---

## Phase 4: Netdata Integration (P1)

### Status: Already Running ✅
Netdata container is healthy and monitoring the host.

### What's Being Monitored
- CPU, Memory, Disk I/O
- Docker containers (auto-discovered)
- Network throughput

### Access Dashboard
```
http://localhost:19999
```

### Integration with EchoTeam
```python
# Export custom metrics to Netdata via statsd
from netdata_pandas import Client

def track_clone_metrics(clone_type: str, latency: float, success: bool):
    """Send custom metrics to Netdata."""
    client = Client(host='localhost', port=8125)
    client.put(f"echoteam.clone.{clone_type}.latency", latency)
    client.put(f"echoteam.clone.{clone_type}.success", int(success))
```

---

## Phase 5: Dagster Integration (P2)

### Why Dagster?
- **Python-native** for AI/ML workflows
- **Asset-based** - declare data dependencies
- **Built-in lineage** for debugging
- **Better than Airflow** for AI pipelines

### Use Cases
1. **Daily Data Sync**: Pull emails, calendar events
2. **Model Retraining**: Periodically fine-tune clones
3. **Evaluation Pipelines**: Measure clone performance
4. **Context Refresh**: Rebuild Qdrant indices

### Docker Setup (need to pull)
```bash
docker run -d \
  --name echoteam-dagster \
  -p 3000:3000 \
  -p 3001:3001 \
  -v dagster_home:/dagster/home \
  dagster/dagster:latest
```

### Example Pipeline
```python
# pipelines/sync.py
from dagster import asset, Definitions

@asset
def email_data() -> list[dict]:
    """Fetch emails from Gmail."""
    return fetch_gmail_messages()

@asset
def calendar_data() -> list[dict]:
    """Fetch calendar events."""
    return fetch_calendar_events()

@asset(deps=[email_data, calendar_data])
def memory_index(email_data, calendar_data):
    """Update Qdrant with synced data."""
    from app.memory.qdrant import QdrantMemory
    memory = QdrantMemory(user_id="system")
    for email in email_data:
        await memory.add(email["body"], {"source": "email"})
```

---

## Phase 6: PostgreSQL + pgvector (P2)

### Status: Image Available
PostgreSQL 17 image is installed but not running.

### Use Cases
1. **Structured Data**: Users, actions, audit logs
2. **pgvector**: Fallback/complement to Qdrant
3. **Metadata Storage**: Clone configurations, user settings

### Docker Setup
```bash
docker run -d \
  --name echoteam-postgres \
  -e POSTGRES_PASSWORD=echoteam123 \
  -e POSTGRES_DB=echoteam \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:17
```

---

## Integration Roadmap

### Week 1: Core Observability
| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | Start Qdrant container | Qdrant running on port 6333 |
| 2 | Implement QdrantMemory class | `app/memory/qdrant.py` |
| 3 | Start Langfuse containers | Langfuse on port 3100 |
| 4 | Add Langfuse tracing to supervisor | `@observe()` decorators |
| 5 | Write TDD tests | 20+ tests passing |

### Week 2: Event Streaming & Monitoring
| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | Start Redpanda container | Redpanda on port 9092 |
| 2 | Implement event producer | `app/events/redpanda.py` |
| 3 | Connect action queue to Redpanda | Async action publishing |
| 4 | Configure Netdata dashboards | Custom EchoTeam metrics |
| 5 | Integration testing | E2E tests passing |

### Week 3: Orchestration (Optional)
| Day | Task | Deliverable |
|-----|------|-------------|
| 1 | Start Dagster | Pipeline UI on port 3000 |
| 2 | Create sync pipeline | Daily data sync asset |
| 3 | Add evaluation pipeline | Clone performance metrics |
| 4 | Start PostgreSQL | DB on port 5432 |
| 5 | Migrate structured data | Users, actions to Postgres |

---

## Environment Variables Required

```bash
# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# Langfuse
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=http://localhost:3100

# Redpanda
REDPANDA_BOOTSTRAP_SERVERS=localhost:9092
REDPANDA_API_TOKEN=

# Dagster
DAGSTER_HOME=/dagster/home
DAGSTER_DB_URL=postgresql://echoteam:echoteam123@localhost:5432/echoteam

# Netdata (optional custom metrics)
NETDATA_HOST=localhost
NETDATA_PORT=8125
```

---

## Testing Strategy

```python
# tests/test_integration.py
import pytest

class TestQdrantIntegration:
    """Test Qdrant hybrid search."""
    async def test_add_and_search(self):
        memory = QdrantMemory("test_user")
        await memory.add("Meeting at 3pm", {"source": "calendar"})
        results = await memory.search("schedule")
        assert len(results) > 0

class TestLangfuseTracing:
    """Test Langfuse observability."""
    def test_supervisor_traced(self):
        with create_trace() as trace:
            result = supervisor_workflow(state)
            assert len(trace.spans) > 0

class TestRedpandaEvents:
    """Test event streaming."""
    async def test_action_published(self):
        events = EchoTeamEvents()
        await events.publish_action({"action": "approve"})
        consumed = await events.consume_one()
        assert consumed["action"] == "approve"
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Hybrid search latency | < 50ms | P95 of search queries |
| Langfuse traces captured | 100% | All clone operations traced |
| Redpanda throughput | 1000 msg/s | Load test |
| Netdata dashboard uptime | 99.9% | Per month |
| Dagster pipeline success | 95% | Weekly success rate |

---

## References

- [Qdrant Python Client](https://qdrant.github.io/qdrant-client/)
- [Langfuse Python SDK](https://langfuse.github.io/langfuse-python/)
- [Redpanda Python Tutorial](https://docs.redpanda.com/api/python/)
- [Dagster ML Pipelines](https://docs.dagster.io/integrations/ml)
- [Netdata Docker](https://learn.netdata.cloud/docs/collecting-metrics/containers-and-vms/docker-engine)
