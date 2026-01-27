# EchoTeam AI Service - Graphiti + Neo4j Memory Layer

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
│  │ Graphiti    │   │ Human-in-   │   │ HITL        │      │
│  │ Memory      │   │ the-Loop    │   │ Boundary    │      │
│  │ (Neo4j)     │   │ (interrupt) │   │             │      │
│  └─────────────┘   └─────────────┘   └─────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Memory Layer: Graphiti + Neo4j

### Technology Stack
- **Graphiti Core (0.26.0)**: Temporal knowledge graph library
- **Neo4j 5.22.0**: Graph database with vector search
- **Ollama**: Local LLM provider (granite3.1-moe:3b, nomic-embed-text)

### Key Components

#### `app/memory/graphiti.py`
- `MemoryConfig`: Configuration dataclass for Neo4j + LLM settings
- `GraphitiMemory`: Main memory class for add/search/context operations

#### `app/graphiti/client.py`
- `GraphitiClient`: Low-level Graphiti operations
- `EpisodeSource`: Enum for source types (email, calendar, task, etc.)
- `Episode` / `GraphSearchResult`: Pydantic models

### Usage

```python
from app.memory.graphiti import GraphitiMemory, MemoryConfig

# Configure
config = MemoryConfig(
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="echoteam123",
    llm_model="granite3.1-moe:3b",
    embedding_model="nomic-embed-text:v1.5",
)

# Initialize
memory = GraphitiMemory(user_id="user123", config=config)
await memory.initialize()

# Add content
await memory.add(
    content="Meeting with client at 3pm",
    metadata={"source": "calendar"}
)

# Search
results = await memory.search(query="client meeting preferences")

# Get context for clones
context = await memory.get_user_context(query="draft email")
```

## Running Services

### Start Neo4j
```bash
docker start echoteam-neo4j
# UI: http://localhost:7474
# Bolt: bolt://localhost:7687
```

### Start Ollama
```bash
# Required models:
ollama pull granite3.1-moe:3b
ollama pull nomic-embed-text:v1.5
```

### Run Tests
```bash
cd apps/ai-service
source .venv/bin/activate
pytest tests/ -v
```

## Test Results
- **91 tests passing**
- **6 tests skipped** (Graphiti 0.26.0 dynamic label bug with Neo4j 5.x)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URI` | bolt://localhost:7687 | Neo4j connection |
| `NEO4J_USER` | neo4j | Database user |
| `NEO4J_PASSWORD` | echoteam123 | Database password |
| `LLM_MODEL` | granite3.1-moe:3b | Ollama reasoning model |
| `LLM_ENDPOINT` | http://localhost:11434 | Ollama endpoint |
| `EMBEDDING_MODEL` | nomic-embed-text:v1.5 | Embedding model |
| `OPENAI_API_KEY` | ollama | Required by Graphiti |

## Known Issues

### Graphiti + Neo4j 5.x Compatibility
Some Graphiti 0.26.0 operations fail due to dynamic label syntax:
```
SET n:$(node.labels)  # Not supported in Neo4j 5.x
```

Workaround: Tests using `add()` are skipped until Graphiti 0.27+ is released.

## File Structure

```
apps/ai-service/
├── app/
│   ├── agents/
│   │   ├── supervisor.py      # LangGraph supervisor
│   │   └── ...
│   ├── graphiti/
│   │   ├── client.py          # Graphiti client wrapper
│   │   └── __init__.py
│   ├── memory/
│   │   ├── graphiti.py        # GraphitiMemory class
│   │   └── __init__.py
│   └── config.py              # Settings
├── tests/
│   ├── test_memory.py         # Memory tests
│   ├── test_memory_graphiti.py # Graphiti-specific tests
│   ├── test_supervisor.py     # Supervisor tests
│   └── test_agents.py         # Agent tests
└── pyproject.toml
```
