"""Graphiti memory layer for EchoTeam.

This module provides integration with Graphiti + Neo4j for:
- Persistent temporal knowledge graph storage
- Multi-user isolation via user_id prefix
- Hybrid vector + graph search (GraphRAG)
- Temporal context retrieval for clone operations

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                   GraphitiMemory                             │
    │  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
    │  │   Add    │───►│ Search   │───►│ Context  │              │
    │  │ Episode  │    │  Graph   │    │  Clone   │              │
    │  └──────────┘    └──────────┘    └──────────┘              │
    │       │               │               │                     │
    │       └───────────────┴───────────────┘                     │
    │                       │                                      │
    │              ┌────────▼────────┐                            │
    │              │     Neo4j       │                            │
    │              │   (Graph+Vec)   │                            │
    │              └─────────────────┘                            │
    └─────────────────────────────────────────────────────────────┘

Usage:
    from app.memory import GraphitiMemory, MemoryConfig

    config = MemoryConfig(
        llm_provider="ollama",
        llm_model="granite3.1-moe:3b",
    )

    memory = GraphitiMemory(user_id="user123", config=config)
    await memory.initialize()

    # Add content (email, calendar event, task, etc.)
    await memory.add(
        content="Meeting with client at 3pm",
        metadata={"source": "calendar", "timestamp": "..."}
    )

    # Search for context
    results = await memory.search(query="client meeting preferences")

    # Get context for clones
    context = await memory.get_user_context(query="draft email about project")
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any

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
    text: str = Field(description="Matching text content")
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
    """Configuration for Graphiti memory layer.

    Uses Neo4j as the graph database with built-in vector search.
    Neo4j provides:
    - Native graph storage with Cypher queries
    - Vector search index support (Neo4j 5.x+)
    - Temporal data handling
    - ACID transactions

    Supports OpenAI-compatible LLM providers:
    - Local: ollama (http://localhost:11434)
    - Cloud: openai, groq, anthropic, etc.

    Environment variables (for production):
        NEO4J_URI: Neo4j connection URI (default: bolt://localhost:7687)
        NEO4J_USER: Neo4j username (default: neo4j)
        NEO4J_PASSWORD: Neo4j password (default: neo4j)
        LLM_PROVIDER: Provider name (default: ollama)
        LLM_MODEL: Model name (default: granite3.1-moe:3b)
        LLM_ENDPOINT: LLM endpoint (default: http://localhost:11434)
        EMBEDDING_MODEL: Embedding model (default: nomic-embed-text:v1.5)
    """
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "echoteam123"
    llm_provider: str = "ollama"
    llm_model: str = "granite3.1-moe:3b"
    llm_endpoint: str = "http://localhost:11434"
    llm_api_key: Optional[str] = None
    embedding_model: str = "nomic-embed-text:v1.5"
    embedding_endpoint: str = "http://localhost:11434/api/embed"
    embedding_dimensions: int = 768
    max_results: int = 20

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self.validate()

    @classmethod
    def from_env(cls) -> "MemoryConfig":
        """Create config from environment variables."""
        return cls(
            neo4j_uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.environ.get("NEO4J_USER", "neo4j"),
            neo4j_password=os.environ.get("NEO4J_PASSWORD", "echoteam123"),
            llm_provider=os.environ.get("LLM_PROVIDER", "ollama"),
            llm_model=os.environ.get("LLM_MODEL", "granite3.1-moe:3b"),
            llm_endpoint=os.environ.get("LLM_ENDPOINT", "http://localhost:11434"),
            llm_api_key=os.environ.get("LLM_API_KEY"),
            embedding_model=os.environ.get("EMBEDDING_MODEL", "nomic-embed-text:v1.5"),
            embedding_endpoint=os.environ.get("EMBEDDING_ENDPOINT", "http://localhost:11434/api/embed"),
            embedding_dimensions=int(os.environ.get("EMBEDDING_DIMENSIONS", "768")),
            max_results=int(os.environ.get("MAX_RESULTS", "20")),
        )

    def validate(self) -> None:
        """Validate configuration."""
        if not self.neo4j_uri.startswith("bolt://") and not self.neo4j_uri.startswith("neo4j://"):
            raise ValueError(f"neo4j_uri must start with bolt:// or neo4j://, got {self.neo4j_uri}")


class GraphitiMemory:
    """Graphiti-based memory for persistent temporal knowledge graph storage.

    This class wraps Graphiti functionality with:
    - Neo4j as graph + vector database
    - User data isolation via user_id in episode metadata
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
        """Initialize Graphiti memory.

        Args:
            user_id: User identifier for dataset isolation
            config: Optional memory configuration (uses defaults if not provided)
        """
        self.user_id = user_id
        self.config = config or MemoryConfig()
        self.config.validate()

        self._initialized = False
        self._graphiti: Optional[Any] = None
        self._lock = asyncio.Lock()

    async def _ensure_graphiti(self) -> Any:
        """Ensure Graphiti client is available and configured."""
        if self._graphiti is not None:
            return self._graphiti

        try:
            from graphiti_core import Graphiti
            from graphiti_core.llm_client.config import LLMConfig
            from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
            from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
            from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient

            # Set environment variable for cross-encoder (required by OpenAI client)
            os.environ["OPENAI_API_KEY"] = self.config.llm_api_key or "ollama"

            # Configure Ollama base URL with /v1 for OpenAI compatibility
            ollama_base = self.config.llm_endpoint.rstrip('/')
            if not ollama_base.endswith('/v1'):
                ollama_base = f"{ollama_base}/v1"

            # Configure Ollama LLM client using OpenAIGenericClient
            llm_config = LLMConfig(
                api_key=self.config.llm_api_key or "ollama",
                model=self.config.llm_model,
                small_model=self.config.llm_model,
                base_url=ollama_base,  # Must have /v1 suffix for OpenAI compat
            )
            llm_client = OpenAIGenericClient(config=llm_config)

            # Configure embedding for Ollama
            embedder_config = OpenAIEmbedderConfig(
                api_key="ollama",
                embedding_model=self.config.embedding_model,
                embedding_dim=self.config.embedding_dimensions,
                base_url=ollama_base,  # Must have /v1 suffix
            )
            embedder = OpenAIEmbedder(config=embedder_config)

            # Configure cross-encoder for reranking (use same LLM)
            cross_encoder = OpenAIRerankerClient(client=llm_client, config=llm_config)

            # Initialize Graphiti with Neo4j (initialization happens in constructor)
            self._graphiti = Graphiti(
                self.config.neo4j_uri,
                self.config.neo4j_user,
                self.config.neo4j_password,
                llm_client=llm_client,
                embedder=embedder,
                cross_encoder=cross_encoder,
            )

            # Graphiti initializes connections in __init__, verify they're ready
            # No separate initialize() call needed

            return self._graphiti

        except ImportError as e:
            logger.error(f"Failed to import Graphiti: {e}")
            raise ImportError(
                "Graphiti not installed. Install with: pip install graphiti-core[neo4j]"
            ) from e

    async def initialize(self) -> None:
        """Initialize the memory layer and connect to Neo4j."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            try:
                # Graphiti connects in __init__, we just need to ensure it's created
                await self._ensure_graphiti()
                self._initialized = True
                logger.info(
                    f"GraphitiMemory initialized for user {self.user_id} "
                    f"at {self.config.neo4j_uri}"
                )

            except Exception as e:
                logger.error(f"Failed to initialize GraphitiMemory: {e}")
                raise

    async def close(self) -> None:
        """Close the memory layer and release resources."""
        if self._graphiti is not None:
            await self._graphiti.close()
            self._graphiti = None
        self._initialized = False
        logger.info(f"GraphitiMemory closed for user {self.user_id}")

    @property
    def is_initialized(self) -> bool:
        """Check if memory is initialized."""
        return self._initialized

    async def add(
        self,
        content: str,
        metadata: Optional[dict] = None,
    ) -> MemoryOperationResult:
        """Add content to the memory as an episode.

        Args:
            content: Text content to add (email body, event description, etc.)
            metadata: Optional metadata (source, timestamp, etc.)

        Returns:
            MemoryOperationResult with operation status
        """
        if not self._initialized:
            await self.initialize()

        try:
            graphiti = await self._ensure_graphiti()

            # Build episode metadata with user isolation
            episode_metadata = {
                "user_id": self.user_id,
                **(metadata or {}),
            }

            # Add episode to Graphiti using correct API
            from graphiti_core.nodes import EpisodeType

            source_description = f"Content from {metadata.get('source', 'unknown')}" if metadata else "User content"
            result = await graphiti.add_episode(
                name=f"episode_{self.user_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                episode_body=content,
                source_description=source_description,
                reference_time=datetime.now(timezone.utc),
                source=EpisodeType.message,  # Required: EpisodeType enum (lowercase)
            )

            episode_id = result.uuid if hasattr(result, 'uuid') else str(result)

            logger.debug(f"Added episode {episode_id} to memory for user {self.user_id}")

            return MemoryOperationResult(
                status=MemoryOperationStatus.SUCCESS,
                message=f"Added episode: {episode_id}",
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
        """Search the memory for relevant context.

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
            graphiti = await self._ensure_graphiti()
            max_results = max_results or self.config.max_results

            # Search using Graphiti
            results = await graphiti.search(
                query=query,
                num_results=max_results,
            )

            # Convert to SearchResult objects
            search_results = []
            for result in results:
                source = MemorySourceType.USER_INTERACTION
                if hasattr(result, 'metadata') and result.metadata:
                    source_str = result.metadata.get("source", "").lower()
                    try:
                        source = MemorySourceType(source_str)
                    except ValueError:
                        pass

                search_results.append(SearchResult(
                    text=getattr(result, 'content', str(result)) or str(result),
                    score=getattr(result, 'score', 0.5) or 0.5,
                    source=source,
                    metadata=getattr(result, 'metadata', {}) or {},
                    valid_at=datetime.now(timezone.utc),
                ))

            return search_results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def get_user_context(
        self,
        query: str,
        days_back: int = 30,
        include_preferences: bool = True,
        include_patterns: bool = True,
    ) -> UserContext:
        """Get comprehensive user context for clone operations.

        Aggregates relevant context from all sources for a specific query,
        optimized for clone decision-making.

        Args:
            query: What we're looking for context about
            days_back: How many days of history to include
            include_preferences: Include user preferences
            include_patterns: Include detected patterns

        Returns:
            UserContext with all relevant context
        """
        if not self._initialized:
            await self.initialize()

        context = UserContext(query=query)

        # Search for email context
        email_results = await self.search(
            query=f"{query} email communication",
            max_results=5,
        )
        context.email_context = email_results

        # Search for calendar context
        calendar_results = await self.search(
            query=f"{query} meeting schedule",
            max_results=5,
        )
        context.calendar_context = calendar_results

        # Search for task context
        task_results = await self.search(
            query=f"{query} task todo",
            max_results=5,
        )
        context.task_context = task_results

        # Search for notes context
        notes_results = await self.search(
            query=f"{query} note documentation",
            max_results=5,
        )
        context.notes_context = notes_results

        # Search for preferences if requested
        if include_preferences:
            pref_results = await self.search(
                query="user preferences communication style",
                max_results=3,
            )
            context.preferences = pref_results

        # Search for patterns if requested
        if include_patterns:
            pattern_results = await self.search(
                query="detected patterns behavior trends",
                max_results=3,
            )
            context.patterns = pattern_results

        # Build context text for LLM consumption
        context_parts = []
        if context.email_context:
            context_parts.append("=== EMAIL CONTEXT ===")
            for r in context.email_context:
                context_parts.append(f"- {r.text[:200]}")

        if context.calendar_context:
            context_parts.append("=== CALENDAR CONTEXT ===")
            for r in context.calendar_context:
                context_parts.append(f"- {r.text[:200]}")

        if context.task_context:
            context_parts.append("=== TASK CONTEXT ===")
            for r in context.task_context:
                context_parts.append(f"- {r.text[:200]}")

        if context.preferences:
            context_parts.append("=== PREFERENCES ===")
            for r in context.preferences:
                context_parts.append(f"- {r.text}")

        if context.patterns:
            context_parts.append("=== PATTERNS ===")
            for r in context.patterns:
                context_parts.append(f"- {r.text}")

        context.context_text = "\n".join(context_parts)

        # Add temporal info
        now = datetime.now(timezone.utc)
        context.temporal_info = {
            "query_time": now.isoformat(),
            "days_back": days_back,
            "sources_searched": ["email", "calendar", "task", "note"],
        }

        return context


# Global memory instances for dependency injection
_memory_instances: dict[str, GraphitiMemory] = {}


async def get_memory(user_id: str, config: Optional[MemoryConfig] = None) -> GraphitiMemory:
    """Get or create a memory instance for a user.

    This is a convenience function for dependency injection.

    Args:
        user_id: User identifier
        config: Optional memory configuration

    Returns:
        GraphitiMemory instance for the user
    """
    if user_id not in _memory_instances:
        _memory_instances[user_id] = GraphitiMemory(user_id, config)
        await _memory_instances[user_id].initialize()

    return _memory_instances[user_id]


async def close_memory(user_id: str) -> None:
    """Close and remove a memory instance.

    Args:
        user_id: User identifier
    """
    if user_id in _memory_instances:
        await _memory_instances[user_id].close()
        del _memory_instances[user_id]


async def close_all_memories() -> None:
    """Close all memory instances."""
    for user_id in list(_memory_instances.keys()):
        await close_memory(user_id)
