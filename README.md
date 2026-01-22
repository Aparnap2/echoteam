# EchoTeam - AI Clone Workforce

> **⚠️ Portfolio Project Only** - This is a demonstration project for portfolio purposes. Not for production use.

EchoTeam is an AI-powered clone workforce that eliminates context rot for solopreneurs. It uses Graphiti/FalkorDB for persistent temporal memory and LangGraph for agentic, proactive workflows.

![EchoTeam Dashboard](./docs/ui-screenshot.png)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React + Vite)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Dashboard │  │  Clones     │  │      Action Queue       │  │
│  │   Analytics │  │  Settings   │  │      (HITL)             │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │ tRPC
┌────────────────────────┴────────────────────────────────────────┐
│                  Backend (Hono + tRPC + JWT)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Auth      │  │   Clones    │  │      Actions            │  │
│  │   (JWT)     │  │   Router    │  │      Router             │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │ REST Proxy
┌────────────────────────┴────────────────────────────────────────┐
│              AI Service (FastAPI + LangGraph)                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              StateGraph (Supervisor Pattern)             │    │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │    │
│  │  │  START      │───►│ Supervisor  │───►│   END       │ │    │
│  │  │             │    │   Router    │    │             │ │    │
│  │  └─────────────┘    └──────┬──────┘    └─────────────┘ │    │
│  │                            │                            │    │
│  │         ┌──────────────────┼──────────────────┐         │    │
│  │         ▼                  ▼                  ▼         │    │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │    │
│  │  │ Admin Clone │    │ Ops Clone   │    │Research Clone│ │    │
│  │  │ (Email/Cal) │    │ (Tasks/Org) │    │(Research)   │ │    │
│  │  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘ │    │
│  │         │                  │                  │        │    │
│  │         └──────────────────┼──────────────────┘        │    │
│  │                            │                            │    │
│  │         ┌──────────────────┼──────────────────┐         │    │
│  │         ▼                  ▼                  ▼         │    │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │    │
│  │  │  Planning   │    │    HITL     │    │  Task       │ │    │
│  │  │   Node      │    │  Approval   │    │  Complete   │ │    │
│  │  └─────────────┘    └─────────────┘    └─────────────┘ │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────────┐
│                   Data Layer (PostgreSQL + FalkorDB)              │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐    │
│  │  Prisma ORM         │  │  Graphiti + FalkorDB            │    │
│  │  (Users, Actions)   │  │  (Temporal Knowledge Graph)     │    │
│  └─────────────────────┘  └─────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19 + Vite + TypeScript + shadcn/ui |
| Backend | Hono + tRPC v11 + JWT Auth |
| AI Service | Python 3.12 + FastAPI + LangGraph |
| Database | PostgreSQL + Prisma ORM |
| Memory | Graphiti + FalkorDB (temporal knowledge graph) |
| LLM | Ollama (local) with OpenAI SDK compatibility |
| Testing | Pytest (AI), Playwright (E2E), Chrome MCP |
| CI/CD | GitHub Actions |

## Prebuilt Clones

### Admin Clone (Inbox & Calendar Guardian)
- Email triage: Summarize inbox, flag priorities, draft replies
- Calendar optimization: Suggest blocks, reschedules, prep notes
- Proactive: Daily inbox digest + suggested actions

### Ops/Coordination Clone (Workflow Orchestrator)
- Task management: Create/track/follow-up tasks across tools
- File/data organization: Sort Drive/Notion items your way
- Proactive: "Chase pending items" or "Remind about recurring tasks"

### Research & Insights Clone (Knowledge Synthesizer)
- Quick research: Web scans, competitor updates, trend summaries
- Pattern alerts: "This matches your past high-priority trends"
- Proactive: Flag opportunities/risks based on history

## Project Structure

```
echoteam/
├── .github/
│   └── workflows/
│       └── ci.yml                    # GitHub Actions CI
├── apps/
│   └── ai-service/                   # Python AI service
│       ├── app/
│       │   ├── agents/               # LangGraph multi-agent system
│       │   │   ├── base.py           # BaseCloneAgent, CloneType, ActionStatus
│       │   │   └── supervisor.py     # LangGraph StateGraph with 3 clones
│       │   ├── graphiti/             # Graphiti + FalkorDB client
│       │   │   └── client.py         # Episode ingestion, temporal queries
│       │   ├── llm/                  # LLM wrappers (Ollama)
│       │   ├── main.py               # FastAPI app
│       │   └── settings.py           # Configuration
│       ├── tests/                    # Unit tests
│       │   ├── test_graphiti.py      # Graphiti client tests (14 tests)
│       │   └── test_supervisor.py    # Supervisor tests (28 tests)
│       ├── pyproject.toml
│       └── requirements.txt
├── fullstack/                        # React + Hono fullstack
│   ├── server/
│   │   ├── index.ts                  # Hono server entry
│   │   ├── auth.ts                   # JWT authentication
│   │   ├── router.ts                 # tRPC root router
│   │   ├── routers/
│   │   │   ├── clones.ts             # Clone management API
│   │   │   ├── actions.ts            # Action queue API
│   │   │   └── user.ts               # User API
│   │   └── trpc.ts                   # tRPC configuration
│   ├── src/
│   │   ├── App.tsx                   # Main dashboard UI
│   │   ├── App.css                   # Dashboard styles
│   │   ├── lib/
│   │   │   ├── auth.tsx              # Auth context & hooks
│   │   │   ├── trpc.ts               # tRPC client
│   │   │   ├── hooks.ts              # React Query hooks
│   │   │   └── providers.tsx         # React Query + Auth providers
│   │   └── main.tsx                  # React entry
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── prisma/
│   └── schema.prisma                 # Database schema
├── docker/
│   ├── postgres.Dockerfile
│   └── falkordb.Dockerfile
├── prd.md                            # Product Requirements Doc
├── README.md                         # This file
└── docker-compose.yml                # Local dev services
```

## Setup

### Prerequisites
- Node.js 20+ with pnpm
- Python 3.12+ with uv
- PostgreSQL 15+
- FalkorDB (or Docker)
- Ollama with models: `qwen2.5-coder:3b`, `granite3.1-moe:3b`, `nomic-embed-text:v1.5`

### Local Development

1. **Clone and install dependencies:**
```bash
cd echoteam

# Frontend
cd fullstack
pnpm install

# AI Service
cd ../apps/ai-service
uv sync
```

2. **Start infrastructure (Docker):**
```bash
docker compose up -d postgres falkordb
```

3. **Configure environment:**
```bash
# fullstack/.env
DATABASE_URL="postgresql://echoteam:echoteam_dev@localhost:5432/echoteam"
JWT_SECRET="your-secret-key-change-in-production"
AI_SERVICE_URL="http://localhost:8000"

# apps/ai-service/.env
OLLAMA_BASE_URL="http://localhost:11434"
OLLAMA_MODEL_CODING="qwen2.5-coder:3b"
OLLAMA_MODEL_REASONING="granite3.1-moe:3b"
FALKORDB_URL="redis://localhost:6379"
```

4. **Run development servers:**
```bash
# Terminal 1: Fullstack (frontend + API)
cd fullstack
pnpm run dev

# Terminal 2: AI Service
cd apps/ai-service
uv run uvicorn app.main:app --reload --port 8000
```

5. **Access the app:**
- Frontend: http://localhost:5173
- API: http://localhost:3001
- AI Service: http://localhost:8000/docs

## Tests

### Unit Tests (AI Service)
```bash
cd apps/ai-service
uv run pytest tests/ -v --tb=short
```

**Results:**
```
tests/test_graphiti.py ............ [14 passed]
tests/test_supervisor.py .......... [28 passed]
=================================== 68 passed in 0.68s ===
```

**Test Coverage:**
- Graphiti client: Episode ingestion, temporal queries, multi-tenant isolation
- LangGraph supervisor: AgentState, routing logic, clone nodes, multi-agent handoffs
- Planning loops: Proactive suggestions based on time and context
- HITL: Human-in-the-loop approval checkpoints

### E2E Tests (Playwright + Chrome MCP)
```bash
cd fullstack
pnpm run test:e2e
```

**Verified Flows:**
- [x] Login screen renders
- [x] Email authentication works
- [x] Dashboard loads with stats
- [x] Clone cards display
- [x] Navigation between views
- [x] Action queue shows pending items

### LLM Evaluations
```bash
cd apps/ai-service
uv run python tests/eval/evaluate_clones.py
```

Evaluates:
- Faithfulness: Does output stick to graph context?
- Personalization: Embedding similarity to user tone
- Anti-Rot: Context carries across multi-step flows

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Demo login with email |
| POST | `/api/auth/verify` | Verify JWT token |
| POST | `/api/auth/logout` | Client-side logout |

### Clones
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/clones` | List all clones |
| GET | `/trpc/clones.getAll` | tRPC: Get all clones |
| POST | `/trpc/clones.create` | tRPC: Create clone |

### Actions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/actions/pending` | List pending actions |
| GET | `/trpc/actions.getPending` | tRPC: Get pending |
| POST | `/trpc/actions.approve` | Approve action |
| POST | `/trpc/actions.reject` | Reject action |

### AI Service
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ollama/models` | List available models |
| POST | `/api/ollama/generate` | Generate text |
| POST | `/api/clones/{id}/execute` | Execute clone action |

## HITL (Human-in-the-Loop)

Actions require approval when:
- Confidence < 85%
- Action type is sensitive (email, payment)
- First interaction with a new tool

Auto-execute for safe, reversible actions:
- Creating internal task drafts
- Organizing files
- Generating research summaries

## GitHub Actions CI

```yaml
# On PR:
- Run lint (ESLint + mypy)
- Run unit tests (34 tests)
- Run type check

# On merge to main:
- Run E2E tests (Playwright)
- Run LLM evaluations
- Build verification
```

## Development Notes

### Portfolio Project Disclaimer
This is a **portfolio project** demonstrating:
- Full-stack TypeScript development (React + Hono + tRPC)
- Python AI service with LangGraph
- Agentic AI architecture patterns
- Temporal knowledge graphs (Graphiti/FalkorDB)
- Multi-agent collaboration

**Not intended for:**
- Production use
- Real user data processing
- Sensitive transactions

### Key Patterns Demonstrated
1. **tRPC end-to-end type safety** between React and Hono
2. **LangGraph StateGraph with supervisor pattern** for multi-agent orchestration
   - AgentState TypedDict for shared state across all nodes
   - 3 clone nodes: Admin (email/calendar), Ops (tasks/org), Research
   - Multi-agent handoffs via conditional routing
   - Planning loops for proactive suggestions
3. **Temporal knowledge graphs** (Graphiti/FalkorDB) for persistent context
   - Episode ingestion with entity extraction
   - Temporal queries for time-aware context retrieval
   - Multi-tenant isolation via group IDs
4. **HITL boundaries** for safe autonomous actions
   - Confidence-based approval thresholds (85%)
   - Action-type approval (email drafts, calendar scheduling)
   - Interrupt-based checkpoints with human feedback
5. **JWT auth** with protected procedures

## License

MIT - See LICENSE file for details.

---

Built with React, Hono, tRPC, FastAPI, LangGraph, Graphiti, and ❤️
