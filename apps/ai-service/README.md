# EchoTeam AI Service - Qdrant + Redpanda Memory Layer

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   EchoTeam AI Service                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ Email Clone │    │ Ops Clone   │    │ Research    │     │
│  │             │    │             │    │ Clone       │     │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘     │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            │                                │
│                   ┌────────▼────────┐                       │
│                   │  LangGraph      │                       │
│                   │  Supervisor     │                       │
│                   │  (StateGraph)   │                       │
│                   └────────┬────────┘                       │
│                            │                                │
│         ┌──────────────────┼──────────────────┐             │
│         │                  │                  │             │
│  ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐      │
│  │ Qdrant      │   │ Human-in-   │   │ Redpanda    │      │
│  │ Memory      │   │ the-Loop    │   │ Events      │      │
│  │ (Hybrid     │   │ (interrupt) │   │ (Streaming) │      │
│  │  Search)    │   │             │   │             │      │
│  └─────────────┘   └─────────────┘   └─────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Memory Layer: Qdrant
- **Qdrant (1.12.0)**: Hybrid vector search (dense + sparse/BM25)
- **Ollama**: Local LLM provider (granite3.1-moe:3b, nomic-embed-text:v1.5)
- Simpler setup, no schema initialization, lower resource footprint

### Event Streaming: Redpanda
- **Redpanda**: Kafka-compatible event streaming
- Consumer groups for parallel processing
- Topics: `chat.events`, `clone.actions`, `audit.logs`

### Agentic AI Libraries
- **LangGraph**: State persistence with InMemory checkpoints
- **DSPy**: Declarative LLM programs with MIPROv2 optimizer
- **Instructor**: Structured outputs with Pydantic validation
- **DeepEval**: LLM evaluation metrics (hallucination, relevancy, faithfulness)
- **Langfuse**: Observability and tracing

## Quick Start

```bash
# Start services
make start

# Run API
make run

# Run tests
make test

# Run consumer
make consumer
```

## Test Suite (70 passing)

| Category | Tests | Description |
|----------|-------|-------------|
| Memory (Qdrant) | 24 | Hybrid search, user isolation, add/search |
| Events (Redpanda) | 14 | Publish/subscribe, consumer groups |
| Agentic AI | 32 | LangGraph, DSPy, Instructor, HITL, DeepEval, Langfuse |

### Running Tests

```bash
cd apps/ai-service
source .venv/bin/activate

# All tests
pytest tests/ -v

# Specific test files
pytest tests/test_memory_qdrant.py -v
pytest tests/test_events_redpanda.py -v
pytest tests/test_agentic_ai.py -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_URL` | http://localhost:6333 | Qdrant server |
| `OLLAMA_BASE_URL` | http://localhost:11434 | Ollama endpoint |
| `OLLAMA_MODEL_CODING` | granite3.1-moe:3b | Coding model |
| `OLLAMA_MODEL_REASONING` | granite3.1-moe:3b | Reasoning model |
| `OLLAMA_MODEL_EMBEDDING` | nomic-embed-text:v1.5 | Embedding model |
| `REDPANDA_HOSTS` | localhost:9092 | Redpanda brokers |
| `OPENAI_API_KEY` | - | Required for DeepEval metrics |

## File Structure

```
apps/ai-service/
├── app/
│   ├── agents/
│   │   ├── supervisor.py      # LangGraph supervisor
│   │   └── ...
│   ├── memory/
│   │   ├── qdrant.py          # QdrantMemory class
│   │   └── __init__.py
│   ├── events/
│   │   ├── redpanda.py        # RedpandaEvents class
│   │   └── __init__.py
│   ├── consumers/
│   │   ├── chat_processor.py  # RAG chat consumer
│   │   └── __init__.py
│   ├── llm/
│   │   └── ollama_client.py   # Ollama LLM client
│   └── config.py              # Settings
├── tests/
│   ├── test_memory_qdrant.py  # Qdrant memory tests (24)
│   ├── test_events_redpanda.py # Redpanda event tests (14)
│   └── test_agentic_ai.py     # Agentic AI tests (32)
├── Makefile                   # One-command operations
└── pyproject.toml
```

## Key Components

### `app/memory/qdrant.py`
- `MemoryConfig`: Qdrant + embedding configuration
- `QdrantMemory`: Main memory class for hybrid search
- `MemorySourceType`: Enum for source types (email, calendar, task, etc.)

### `app/events/redpanda.py`
- `EventsConfig`: Redpanda connection config
- `RedpandaEvents`: Publish/subscribe with consumer groups
- Event types: `CLONE_ACTION`, `CLONE_RESULT`, `AUDIT_LOG`, etc.

### `app/consumers/chat_processor.py`
- RAG consumer listening to `chat.events` topic
- Langfuse tracing for observability
- Confidence scoring for responses

## Debugging

All `print()` statements replaced with `icecream.ic()` for better debugging:

```python
from app.main import icecream

icecream.ic(f"Query: {query}")
icecream.ic(f"Results: {len(results)}")
```
