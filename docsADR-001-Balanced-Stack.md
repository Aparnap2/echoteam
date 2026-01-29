# ADR-001: EchoTeam Modern Data/AI Stack Selection

## Status

**Accepted** - January 2025

## Context

EchoTeam needed to select modern infrastructure components for a production-grade AI system with:
- Hybrid vector + keyword search (RAG)
- Event streaming for async processing
- LLM observability and tracing
- Low resource footprint (local development)

## Decisions

### 1. Vector Database: Qdrant vs OpenSearch vs Neo4j

| Criteria | Qdrant | OpenSearch | Neo4j |
|----------|--------|------------|-------|
| Setup Complexity | Low | Medium | High |
| Resource Usage | ~100MB | ~1GB | ~500MB |
| Hybrid Search | Native | Native | Plugin |
| Local Dev | Easy | Medium | Hard |

**Decision: Qdrant**

**Rationale:**
- **Simplicity**: No schema initialization required, works out of the box
- **Hybrid Search**: Native dense vector + sparse vector (BM25) support
- **Resource Footprint**: Rust-based, uses ~100MB vs ~1GB for OpenSearch
- **Local Dev**: Docker single command, no JVM requirements like Neo4j
- **API**: Clean REST + gRPC, better Python client than Neo4j

### 2. Event Streaming: Redpanda vs Kafka vs RabbitMQ

| Criteria | Redpanda | Kafka | RabbitMQ |
|----------|----------|-------|----------|
| Setup Complexity | Low | High | Medium |
| No JVM | Yes | No | Yes |
| Kafka Compatible | Yes | Native | No |
| Resource Usage | ~200MB | ~1GB | ~100MB |
| Consumer Groups | Native | Native | Plugin |

**Decision: Redpanda**

**Rationale:**
- **Kafka Compatibility**: Drop-in replacement, same client libraries
- **No JVM**: Single binary, no ZooKeeper required
- **Developer Experience**: Easier local setup, faster startup
- **Resource Efficiency**: ~200MB vs ~1GB for Kafka
- **Future Proof**: Can migrate to Confluent if needed, same code works

### 3. LLM Observability: Langfuse vs Weights & Biases vs MLflow

| Criteria | Langfuse | W&B | MLflow |
|----------|----------|-----|--------|
| LLM Tracing | Native | Generic | Generic |
| Cost Tracking | Native | Generic | No |
| Dataset Management | Native | Yes | Limited |
| Self-Hosted | Yes | No | Yes |
| Python SDK | Excellent | Good | Good |

**Decision: Langfuse**

**Rationale:**
- **LLM-Native**: Designed specifically for LLM observability
- **Tracing**: Automatic span tracking for prompts, completions, retrievals
- **Cost Tracking**: Built-in token and cost monitoring per model
- **Datasets**: Create evaluation datasets directly from traces
- **Self-Hosted**: Free self-hosted option available

### 4. Embeddings: Ollama vs OpenAI vs HuggingFace

| Criteria | Ollama | OpenAI | HuggingFace |
|----------|--------|--------|-------------|
| Local | Yes | No | Yes |
| Cost | Free | Pay | Free |
| Model Selection | Curated | Large | Massive |
| GPU Support | Yes | N/A | Yes |

**Decision: Ollama**

**Rationale:**
- **Local Processing**: No data leaves your machine
- **Free**: No API costs during development
- **Curated Models**: nomic-embed-text optimized for hybrid search
- **Simple API**: Same format as OpenAI for easy migration

## Architecture Diagram

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
│  │                    Ollama (LLM + Embeddings)                 │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Trade-offs Considered

### What We Gained
- **Faster Development**: Qdrant + Redpanda setup in minutes vs hours
- **Lower Costs**: All self-hosted, no vendor lock-in
- **Better Observability**: Langfuse provides end-to-end tracing
- **Local Testing**: All services run on developer machines

### What We Sacrificed
- **Enterprise Features**: Missing some Neo4j graph algorithms
- **Managed Service**: No vendor SLA, self-maintenance required
- **Scale Limits**: Qdrant less tested at massive scale

## Related ADRs

- ADR-002: LangGraph Supervisor Pattern
- ADR-003: Event Sourcing with Redpanda

## References

- [Qdrant Documentation](https://qdrant.github.io/qdrant/)
- [Redpanda Documentation](https://docs.redpanda.com/)
- [Langfuse Documentation](https://langfuse.com/docs/)
