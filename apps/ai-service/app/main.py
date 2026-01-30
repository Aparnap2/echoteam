"""FastAPI application for EchoTeam AI Service."""

from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import httpx
import icecream
from app.config import settings
from app.memory import QdrantMemory, MemoryConfig, get_memory, MemorySourceType
from app.agents import CalendarClone, EmailClone, OpsClone, CloneType


# Configure icecream for debugging
icecream.install()

# Global memory instance
memory: Optional[QdrantMemory] = None
ollama_healthy: bool = False

# Source type mapping (module-level to avoid recreation on each request)
SOURCE_ENUM_MAP = {
    "email": MemorySourceType.EMAIL,
    "calendar": MemorySourceType.CALENDAR,
    "task": MemorySourceType.TASK,
    "note": MemorySourceType.NOTE,
    "research": MemorySourceType.RESEARCH,
    "user_interaction": MemorySourceType.USER_INTERACTION,
    "system": MemorySourceType.SYSTEM,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global memory, ollama_healthy

    # Check Ollama health
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags", timeout=10.0)
            ollama_healthy = response.status_code == 200
    except Exception:
        ollama_healthy = False

    # Initialize memory
    config = MemoryConfig.from_env()
    memory = await get_memory(user_id="default", config=config)
    icecream.ic(f"Started {settings.app_name} v{settings.app_version}")
    icecream.ic(f"Ollama: {'healthy' if ollama_healthy else 'unhealthy'}")
    icecream.ic(f"Qdrant: {'connected' if memory.is_initialized else 'disconnected'}")
    yield
    if memory:
        await memory.close()
    icecream.ic("Shutting down AI service")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)


# ============ Models ============

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    services: dict[str, bool]


class ActionRequest(BaseModel):
    """Request to process an action through a clone."""
    user_id: str
    clone_type: str
    action_type: str
    payload: dict = Field(default_factory=dict)
    context: Optional[dict] = None


class ActionResponse(BaseModel):
    """Response from processing an action."""
    action_id: str
    status: str
    confidence: float
    requires_approval: bool
    result: Optional[dict] = None


class CloneProcessRequest(BaseModel):
    """Request to run a clone's full processing loop."""
    user_id: str
    clone_type: str
    context: Optional[dict] = None


class CloneProcessResponse(BaseModel):
    """Response from clone processing."""
    user_id: str
    clone_type: str
    actions: list[dict]
    auto_actions: list[dict]
    approval_actions: list[dict]


# ============ Endpoints ============

@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        services={
            "ollama": ollama_healthy,
            "qdrant": memory.is_initialized if memory else False
        }
    )


class OllamaModelsResponse(BaseModel):
    """Response containing available Ollama models."""
    models: list[dict]
    configured_models: dict[str, str]


@app.get("/api/ollama/models", response_model=OllamaModelsResponse)
async def get_ollama_models() -> OllamaModelsResponse:
    """Get available Ollama models."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags", timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
            else:
                models = []
    except Exception:
        models = []

    return OllamaModelsResponse(
        models=[
            {"name": m["name"], "size": m["size"], "digest": m["digest"][:8]}
            for m in models
        ],
        configured_models={
            "coding": settings.ollama_model_coding,
            "reasoning": settings.ollama_model_reasoning,
            "embedding": settings.ollama_model_embedding
        }
    )


class GenerateRequest(BaseModel):
    """Request to generate text."""
    prompt: str
    model: Optional[str] = None
    system: Optional[str] = None
    temperature: float = 0.7


class GenerateResponse(BaseModel):
    """Response from text generation."""
    response: str
    model: str
    duration_ms: int


@app.post("/api/ollama/generate", response_model=GenerateResponse)
async def generate_text(request: GenerateRequest) -> GenerateResponse:
    """Generate text using Ollama."""
    import time
    from app.llm.ollama_client import ollama_client

    model = request.model or settings.ollama_model_coding
    start = time.time()

    response = await ollama_client.generate(
        model=model,
        prompt=request.prompt,
        system=request.system,
        temperature=request.temperature
    )

    duration_ms = int((time.time() - start) * 1000)

    return GenerateResponse(
        response=response,
        model=model,
        duration_ms=duration_ms
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs"
    }


@app.post("/api/actions", response_model=ActionResponse)
async def process_action(request: ActionRequest) -> ActionResponse:
    """Process a single action through the appropriate clone."""
    # Validate clone type
    try:
        clone_type_enum = CloneType(request.clone_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid clone_type: {request.clone_type}")

    # Create appropriate clone
    if clone_type_enum == CloneType.CALENDAR:
        clone = CalendarClone(request.user_id, clone_type_enum)
    elif clone_type_enum == CloneType.EMAIL:
        clone = EmailClone(request.user_id, clone_type_enum)
    elif clone_type_enum == CloneType.OPS:
        clone = OpsClone(request.user_id, clone_type_enum)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported clone type: {request.clone_type}")

    # Create action
    from app.agents import CloneAction, ActionStatus
    action = CloneAction(
        id=f"action_{id(clone)}",
        clone_type=clone_type_enum,
        action_type=request.action_type,
        payload=request.payload,
        confidence=0.90
    )

    # Check if approval is required
    requires_approval = action.requires_approval()

    # Execute if auto
    result = None
    if not requires_approval:
        result = await clone.execute_action(action)

    return ActionResponse(
        action_id=action.id,
        status=ActionStatus.PENDING.value if requires_approval else ActionStatus.EXECUTED.value,
        confidence=action.confidence,
        requires_approval=requires_approval,
        result=result
    )


@app.post("/api/clones/process", response_model=CloneProcessResponse)
async def process_clone(request: CloneProcessRequest) -> CloneProcessResponse:
    """Run a clone's full processing loop."""
    # Validate clone type
    try:
        clone_type_enum = CloneType(request.clone_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid clone_type: {request.clone_type}")

    # Create appropriate clone
    if clone_type_enum == CloneType.CALENDAR:
        clone = CalendarClone(request.user_id, clone_type_enum)
    elif clone_type_enum == CloneType.EMAIL:
        clone = EmailClone(request.user_id, clone_type_enum)
    elif clone_type_enum == CloneType.OPS:
        clone = OpsClone(request.user_id, clone_type_enum)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported clone type: {request.clone_type}")

    # Set context if provided
    if request.context:
        clone.state.context.update(request.context)

    # Process
    actions = await clone.process()

    # Separate auto and approval actions
    auto_actions = clone.get_auto_actions()
    approval_actions = clone.get_approval_actions()

    return CloneProcessResponse(
        user_id=request.user_id,
        clone_type=request.clone_type,
        actions=[a.model_dump() for a in actions],
        auto_actions=[a.model_dump() for a in auto_actions],
        approval_actions=[a.model_dump() for a in approval_actions]
    )


@app.post("/api/memory/search")
async def search_memory(query: str, num_results: int = 5):
    """Search the memory store using hybrid vector search."""
    if not memory:
        raise HTTPException(status_code=503, detail="Memory not initialized")

    results = await memory.search(query=query, max_results=num_results)
    return {"results": [r.model_dump() for r in results]}


@app.post("/api/memory/episode")
async def add_episode(
    content: str,
    source: str = "user_interaction",
    metadata: Optional[dict] = None,
):
    """Add an episode to the memory store."""
    if not memory:
        raise HTTPException(status_code=503, detail="Memory not initialized")

    # Map source string to MemorySourceType
    source_type = SOURCE_ENUM_MAP.get(source.lower(), MemorySourceType.USER_INTERACTION)

    # Merge metadata, ensuring computed source is authoritative (source last wins)
    merged_metadata = {**(metadata or {}), "source": source_type.value}

    result = await memory.add(
        content=content,
        metadata=merged_metadata,
    )
    return {"status": result.status.value, "message": result.message}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
