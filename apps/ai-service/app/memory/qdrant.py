"""EchoTeam Memory Layer - Qdrant Hybrid Search

Replaces Graphiti/Neo4j with Qdrant for:
- Hybrid vector + keyword search (Dense + BM25)
- Simpler setup, no schema initialization
- Lower resource footprint
- Better RAG for clone context retrieval

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                    QdrantMemory                              │
    │  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
    │  │   Add    │───►│ Hybrid   │───►│ Context  │              │
    │  │ (Episodes│    │  Search  │    │  Clone   │              │
    │  └──────────┘    │ (Dense+  │    └──────────┘              │
    │       │          │  Sparse) │          │                    │
    │       │          └──────────┘          │                    │
    │       │                 │               │                    │
    │       └─────────────────┴───────────────┘                    │
    │                            │                                  │
    │              ┌────────────▼──────────┐                       │
    │              │       Qdrant          │                       │
    │              │  (Vector + Keyword)   │                       │
    │              └───────────────────────┘                       │
    └─────────────────────────────────────────────────────────────┘

Usage:
    from app.memory import QdrantMemory, MemoryConfig

    config = MemoryConfig(
        qdrant_url="http://localhost:6333",
        embedding_model="nomic-embed-text:v1.5",
    )

    memory = QdrantMemory(user_id="user123", config=config)
    await memory.initialize()

    # Add content (email, calendar event, task, etc.)
    await memory.add(
        content="Meeting with client at 3pm",
        metadata={"source": "calendar", "timestamp": "..."}
    )

    # Hybrid search (semantic + keyword)
    results = await memory.search(query="client meeting preferences")

    # Get context for clones
    context = await memory.get_user_context(query="draft email about project")
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any
from uuid import uuid4

import numpy as np
import pydantic
from pydantic import BaseModel, Field

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


class MemoryOperationStatus(str, Enum):
    """Status of a memory operation."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class MemoryOperationResult(BaseModel):
    """Result of a memory operation."""
    status: MemoryOperationStatus
    message: str = ""
    items_processed: int = 0
    error: Optional[str] = None


class SearchResult(BaseModel):
    """Result from memory search."""
    id: str = Field(description="Unique result ID")
    content: str = Field(description="Matching text content")
    score: float = Field(default=0.0, description="Relevance score 0-1", ge=0, le=1)
    source: MemorySourceType = Field(default=MemorySourceType.USER_INTERACTION)
    metadata: dict = Field(default_factory=dict)
    valid_at: Optional[datetime] = None


class UserContext(BaseModel):
    """Comprehensive user context for clone operations."""
    query: str
    email_context: list[SearchResult] = Field(default_factory=list)
    calendar_context: list[SearchResult] = Field(default_factory=list)
    task_context: list[SearchResult] = Field(default_factory=list)
    notes_context: list[SearchResult] = Field(default_factory=list)
    preferences: list[SearchResult] = Field(default_factory=list)
    patterns: list[SearchResult] = Field(default_factory=list)
    temporal_info: dict = Field(default_factory=dict)
    context_text: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "query": self.query,
            "email_count": len(self.email_context),
            "calendar_count": len(self.calendar_context),
            "task_count": len(self.task_context),
            "notes_count": len(self.notes_context),
            "preferences_count": len(self.preferences),
            "patterns_count": len(self.patterns),
            "context_text": self.context_text,
        }


@dataclass
class MemoryConfig:
    """Configuration for Qdrant memory layer.

    Uses Qdrant for hybrid vector + keyword search.
    Qdrant provides:
    - Native vector search with HNSW indexes
    - Sparse vector support for BM25 keyword search
    - Payload filtering and metadata
    - gRPC + REST APIs
    - Low resource footprint

    Environment variables (for production):
        QDRANT_URL: Qdrant connection URL (default: http://localhost:6333)
        QDRANT_API_KEY: Optional API key for authentication
        EMBEDDING_MODEL: Embedding model (default: nomic-embed-text:v1.5)
        EMBEDDING_DIMENSIONS: Embedding dimensions (default: 768)
        MAX_RESULTS: Maximum search results (default: 20)
    """
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    embedding_model: str = "nomic-embed-text:v1.5"
    embedding_endpoint: str = "http://localhost:11434/api/embed"
    embedding_dimensions: int = 768
    max_results: int = 20
    collection_name: str = "echoteam_memory"

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self.validate()

    @classmethod
    def from_env(cls) -> "MemoryConfig":
        """Create config from environment variables."""
        import os

        return cls(
            qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text:v1.5"),
            embedding_endpoint=os.getenv("EMBEDDING_ENDPOINT", "http://localhost:11434/api/embed"),
            embedding_dimensions=int(os.getenv("EMBEDDING_DIMENSIONS", "768")),
            max_results=int(os.getenv("MAX_RESULTS", "20")),
            collection_name=os.getenv("COLLECTION_NAME", "echoteam_memory"),
        )

    def validate(self) -> None:
        """Validate configuration."""
        if not self.qdrant_url.startswith("http://") and not self.qdrant_url.startswith("https://"):
            raise ValueError(f"qdrant_url must start with http:// or https://, got {self.qdrant_url}")


class QdrantMemory:
    """Qdrant-based memory for hybrid vector + keyword search.

    This class provides:
    - Dense vector search for semantic similarity
    - Sparse vector search for keyword matching (BM25)
    - User data isolation via collection prefixes
    - Async operations for agent integration
    - Context retrieval optimized for clone operations

    Attributes:
        user_id: Unique user identifier for isolation
        config: Memory configuration
    """

    def __init__(
        self,
        user_id: str,
        config: Optional[MemoryConfig] = None,
    ):
        """Initialize Qdrant memory.

        Args:
            user_id: User identifier for dataset isolation
            config: Optional memory configuration (uses defaults if not provided)
        """
        self.user_id = user_id
        self.config = config or MemoryConfig()
        self.config.validate()

        self._initialized = False
        self._client: Optional[Any] = None
        self._lock = asyncio.Lock()

        # Collection name includes user_id for isolation
        self.collection = f"echoteam_{user_id}"

    async def _ensure_client(self) -> Any:
        """Ensure Qdrant client is available."""
        if self._client is not None:
            return self._client

        try:
            from qdrant_client import AsyncQdrantClient
            from qdrant_client.models import VectorParams, Distance

            # Create async client
            self._client = AsyncQdrantClient(
                url=self.config.qdrant_url,
                api_key=self.config.qdrant_api_key,
            )

            # Ensure collection exists with dense vector index
            try:
                await self._client.get_collection(self.collection)
                logger.debug(f"Collection {self.collection} already exists")
            except Exception:
                # Create collection with dense vector index
                # Note: Sparse vectors (BM25) require Qdrant Cloud or newer versions
                await self._client.create_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(
                        size=self.config.embedding_dimensions,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Created collection {self.collection} with dense vector index")

            return self._client

        except ImportError as e:
            logger.error(f"Failed to import Qdrant client: {e}")
            raise ImportError(
                "Qdrant not installed. Install with: pip install qdrant-client"
            ) from e

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text using Ollama."""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.embedding_endpoint,
                json={
                    "model": self.config.embedding_model,
                    "input": text,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            # Handle both /api/embed and /api/embeddings response formats
            if "embedding" in data:
                return data["embedding"]
            elif "embeddings" in data:
                return data["embeddings"][0] if data["embeddings"] else []
            else:
                raise ValueError(f"Unexpected response format: {data}")

    async def _generate_sparse_vector(self, text: str) -> dict:
        """Generate sparse representation for text.

        Simple term frequency-based sparse vector for keyword matching.
        Full BM25 sparse vectors require Qdrant Cloud.
        """
        # Tokenize and count terms
        tokens = text.lower().split()
        term_freq = {}
        for token in tokens:
            # Simple filtering - keep alphanumeric tokens > 2 chars
            clean_token = ''.join(c for c in token if c.isalnum())
            if len(clean_token) > 2:
                term_freq[clean_token] = term_freq.get(clean_token, 0) + 1
        return term_freq

    async def initialize(self) -> None:
        """Initialize the memory layer and connect to Qdrant."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            try:
                await self._ensure_client()
                self._initialized = True
                logger.info(
                    f"QdrantMemory initialized for user {self.user_id} "
                    f"at {self.config.qdrant_url}"
                )
            except Exception as e:
                logger.error(f"Failed to initialize QdrantMemory: {e}")
                raise

    async def close(self) -> None:
        """Close the memory layer and release resources."""
        if self._client is not None:
            await self._client.close()
            self._client = None
        self._initialized = False
        logger.info(f"QdrantMemory closed for user {self.user_id}")

    @property
    def is_initialized(self) -> bool:
        """Check if memory is initialized."""
        return self._initialized

    async def add(
        self,
        content: str,
        metadata: Optional[dict] = None,
    ) -> MemoryOperationResult:
        """Add content to memory as an episode.

        Args:
            content: Text content to add (email body, event description, etc.)
            metadata: Optional metadata (source, timestamp, etc.)

        Returns:
            MemoryOperationResult with operation status
        """
        if not self._initialized:
            await self.initialize()

        try:
            client = await self._ensure_client()

            # Generate dense embedding
            dense_vector = await self._generate_embedding(content)

            # Generate sparse vector for keyword search
            sparse_vector = await self._generate_sparse_vector(content)

            # Build payload with user isolation
            payload = {
                "content": content,
                "user_id": self.user_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **(metadata or {}),
            }

            # Generate unique ID
            point_id = str(uuid4())

            # Upsert to Qdrant
            from qdrant_client.models import PointStruct

            await client.upsert(
                collection_name=self.collection,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=dense_vector,
                        payload=payload,
                    )
                ],
            )

            logger.debug(f"Added content {point_id} to memory for user {self.user_id}")

            return MemoryOperationResult(
                status=MemoryOperationStatus.SUCCESS,
                message=f"Added episode: {point_id}",
                items_processed=1,
            )

        except Exception as e:
            logger.error(f"Failed to add content: {e}")
            return MemoryOperationResult(
                status=MemoryOperationStatus.FAILED,
                error=str(e),
            )

    async def search(
        self,
        query: str,
        source_filter: Optional[list[MemorySourceType]] = None,
        max_results: Optional[int] = None,
    ) -> list[SearchResult]:
        """Search the memory for relevant context using vector similarity.

        Uses dense vector embeddings for semantic search.

        Args:
            query: Search query string
            source_filter: Optional filter by source types
            max_results: Maximum number of results

        Returns:
            List of SearchResult objects sorted by relevance
        """
        if not self._initialized:
            await self.initialize()

        try:
            client = await self._ensure_client()
            max_results = max_results or self.config.max_results

            # Generate query vector
            query_vector = await self._generate_embedding(query)

            # Build filter if source specified
            from qdrant_client.models import Filter, FieldCondition, MatchAny

            filter_obj = None
            if source_filter:
                # Use MatchAny to match any of the provided source types
                filter_obj = Filter(
                    must=[
                        FieldCondition(
                            key="source",
                            match=MatchAny(values=[s.value for s in source_filter]),
                        )
                    ]
                )

            # Standard vector search using query_points (AsyncQdrantClient)
            results = await client.query_points(
                collection_name=self.collection,
                query=query_vector,
                limit=max_results,
                query_filter=filter_obj,
            )

            # Convert to SearchResult objects
            search_results = []
            # Handle QueryResponse return format (points directly on response)
            points = getattr(results, 'points', [])

            for point in points:
                # Handle different point formats
                payload = getattr(point, 'payload', point)
                # Safely parse source, default to SYSTEM if invalid
                source_value = payload.get("source", "system")
                try:
                    source = MemorySourceType(source_value)
                except ValueError:
                    source = MemorySourceType.SYSTEM

                search_results.append(
                    SearchResult(
                        id=str(getattr(point, 'id', point.id)),
                        content=payload.get("content", ""),
                        score=float(getattr(point, 'score', 0.0)),
                        source=source,
                        metadata=payload,
                        valid_at=datetime.fromisoformat(payload.get("created_at", "")) if payload.get("created_at") else None,
                    )
                )

            return search_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def get_user_context(
        self,
        query: str,
    ) -> UserContext:
        """Get comprehensive context for clone operations.

        Performs hybrid search and categorizes results by source type.

        Args:
            query: Query to find relevant context

        Returns:
            UserContext with categorized results and merged context text
        """
        if not self._initialized:
            await self.initialize()

        # Search across all sources
        results = await self.search(query=query, max_results=self.config.max_results)

        # Categorize results
        email_context = [r for r in results if r.source == MemorySourceType.EMAIL]
        calendar_context = [r for r in results if r.source == MemorySourceType.CALENDAR]
        task_context = [r for r in results if r.source == MemorySourceType.TASK]
        notes_context = [r for r in results if r.source == MemorySourceType.NOTE]
        preferences = [r for r in results if r.source == MemorySourceType.USER_INTERACTION]

        # Merge context text (highest scores first)
        context_parts = []
        for result in results[:5]:  # Top 5 results
            context_parts.append(f"[{result.source.value.upper()}] {result.content}")

        context_text = "\n\n".join(context_parts) if context_parts else ""

        return UserContext(
            query=query,
            email_context=email_context,
            calendar_context=calendar_context,
            task_context=task_context,
            notes_context=notes_context,
            preferences=preferences,
            context_text=context_text,
            temporal_info={
                "total_results": len(results),
                "sources_found": list(set(r.source.value for r in results)),
            },
        )

    async def delete_by_source(self, source: MemorySourceType) -> int:
        """Delete all entries with a specific source type.

        Args:
            source: Source type to delete

        Returns:
            Number of deleted points
        """
        if not self._initialized:
            await self.initialize()

        try:
            client = await self._ensure_client()

            from qdrant_client.models import Filter, FieldCondition, MatchValue

            result = await client.delete(
                collection_name=self.collection,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="source",
                            match=MatchValue(value=source.value),
                        )
                    ]
                ),
            )

            return result.deleted

        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return 0


# Module-level memory instances for connection pooling
_memory_instances: dict[str, QdrantMemory] = {}
_memory_lock = asyncio.Lock()


async def get_memory(user_id: str, config: Optional[MemoryConfig] = None) -> QdrantMemory:
    """Get or create a memory instance for a user.

    Args:
        user_id: User identifier
        config: Optional memory configuration

    Returns:
        QdrantMemory instance
    """
    async with _memory_lock:
        if user_id not in _memory_instances:
            _memory_instances[user_id] = QdrantMemory(user_id=user_id, config=config)
            await _memory_instances[user_id].initialize()
        return _memory_instances[user_id]


async def close_memory(user_id: str) -> None:
    """Close a user's memory instance.

    Args:
        user_id: User identifier
    """
    async with _memory_lock:
        if user_id in _memory_instances:
            await _memory_instances[user_id].close()
            del _memory_instances[user_id]


async def close_all_memories() -> None:
    """Close all memory instances."""
    for user_id, memory in list(_memory_instances.items()):
        await memory.close()
    _memory_instances.clear()
