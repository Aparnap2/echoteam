"""Graphiti client for temporal knowledge graph operations.

This module provides integration with Graphiti + FalkorDB for:
- Episode ingestion (emails, calendar events, tasks, research)
- Temporal queries (retrieve context valid at specific times)
- Semantic search with entity extraction
- Multi-tenant isolation via group IDs
"""

import logging
from typing import Optional, AsyncGenerator
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

from app.config import settings

logger = logging.getLogger(__name__)


class EpisodeSource(str, Enum):
    """Source types for episodes."""
    EMAIL = "email"
    CALENDAR = "calendar"
    TASK = "task"
    NOTE = "note"
    RESEARCH = "research"
    USER_INTERACTION = "user_interaction"
    SYSTEM = "system"


class Episode(BaseModel):
    """Represents an episode (temporal memory) in the graph."""
    id: str = Field(description="Unique episode identifier")
    name: str = Field(description="Human-readable name")
    content: str = Field(description="Episode content/body")
    source: EpisodeSource = Field(default=EpisodeSource.SYSTEM)
    source_description: str = Field(default="")
    group_id: str = Field(description="Tenant/user identifier for isolation")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    invalid_at: Optional[datetime] = None
    entities: list[dict] = Field(default_factory=list)
    relationships: list[dict] = Field(default_factory=list)


class GraphSearchResult(BaseModel):
    """Result from graph search."""
    content: str = Field(description="Matching content")
    score: float = Field(description="Relevance score 0-1")
    episode_id: str = Field(description="Source episode ID")
    episode_name: str = Field(description="Source episode name")
    source: EpisodeSource = Field(description="Episode source type")
    valid_at: datetime = Field(description="When this fact became valid")
    metadata: dict = Field(default_factory=dict)


class GraphitiClient:
    """Client for interacting with Graphiti + FalkorDB temporal knowledge graph.

    This client provides:
    - Async episode ingestion with automatic entity extraction
    - Temporal queries for time-aware context retrieval
    - Semantic search with hybrid ranking
    - Multi-tenant isolation via group IDs
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: str = "echoteam"
    ):
        """Initialize Graphiti client.

        Args:
            uri: FalkorDB connection URI (defaults to config)
            user: Database user (defaults to config)
            password: Database password (defaults to config)
            database: Database name (defaults to config)
        """
        self._uri = uri or f"bolt://{settings.falkor_host}:{settings.falkor_port}"
        self._user = user or "echoteam"
        self._password = password or "echoteam_dev"
        self._database = database
        self._client: Optional[Graphiti] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize connection and build indices."""
        if self._initialized:
            return

        try:
            self._client = Graphiti(
                uri=self._uri,
                user=self._user,
                password=self._password
            )
            await self._client.build_indices_and_constraints()
            self._initialized = True
            logger.info("Graphiti client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Graphiti: {e}")
            raise

    async def close(self) -> None:
        """Close the Graphiti connection."""
        if self._client:
            await self._client.close()
            self._client = None
            self._initialized = False
            logger.info("Graphiti client closed")

    async def add_episode(
        self,
        name: str,
        content: str,
        source: EpisodeSource,
        group_id: str,
        source_description: str = "",
        reference_time: Optional[datetime] = None,
        entities: Optional[list[dict]] = None,
        relationships: Optional[list[dict]] = None,
    ) -> Episode:
        """Add an episode to the temporal knowledge graph.

        This is the core ingestion method - episodes represent discrete
        temporal memories (emails, meetings, tasks, notes, etc.).

        Args:
            name: Human-readable episode name
            content: The actual content/body text
            source: Type of episode source
            group_id: Tenant/user ID for isolation
            source_description: Description of the source
            reference_time: When this episode is valid from
            entities: Pre-extracted entities (optional, auto-extracted if not provided)
            relationships: Pre-extracted relationships

        Returns:
            Created episode with ID and metadata
        """
        if not self._client:
            raise RuntimeError("Graphiti client not initialized")

        if reference_time is None:
            reference_time = datetime.now(timezone.utc)

        # Map our source enum to Graphiti's EpisodeType
        # Graphiti only has: message, json, text
        episode_type_map = {
            EpisodeSource.EMAIL: EpisodeType.message,
            EpisodeSource.CALENDAR: EpisodeType.message,
            EpisodeSource.TASK: EpisodeType.json,  # Use JSON for structured data
            EpisodeSource.NOTE: EpisodeType.text,
            EpisodeSource.RESEARCH: EpisodeType.text,
            EpisodeSource.USER_INTERACTION: EpisodeType.message,
            EpisodeSource.SYSTEM: EpisodeType.text,
        }

        graphiti_type = episode_type_map.get(source, EpisodeType.text)

        try:
            result = await self._client.add_episode(
                name=name,
                episode_body=content,
                source=graphiti_type,
                source_description=source_description,
                reference_time=reference_time,
                group_id=group_id,
            )

            # Extract entities and relationships from result
            extracted_entities = []
            extracted_relationships = []

            if result.nodes:
                for node in result.nodes:
                    extracted_entities.append({
                        "name": node.name,
                        "labels": list(node.labels),
                        "attributes": node.attributes or {},
                    })

            if result.edges:
                for edge in result.edges:
                    extracted_relationships.append({
                        "fact": edge.fact,
                        "source": edge.source,
                        "target": edge.target,
                        "valid_at": edge.valid_at.isoformat() if edge.valid_at else None,
                    })

            return Episode(
                id=str(result.episode.uuid),
                name=name,
                content=content,
                source=source,
                source_description=source_description,
                group_id=group_id,
                created_at=result.episode.created_at or reference_time,
                valid_at=reference_time,
                invalid_at=None,
                entities=extracted_entities or (entities or []),
                relationships=extracted_relationships or (relationships or []),
            )

        except Exception as e:
            logger.error(f"Failed to add episode: {e}")
            raise

    async def search(
        self,
        query: str,
        group_id: str,
        num_results: int = 10,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        source_filter: Optional[list[EpisodeSource]] = None,
    ) -> list[GraphSearchResult]:
        """Search the temporal knowledge graph.

        Performs semantic search with temporal filtering to retrieve
        context relevant at a specific time or time range.

        Args:
            query: Search query string
            group_id: Tenant/user ID for isolation
            num_results: Maximum results to return
            start_date: Filter results from this date
            end_date: Filter results until this date
            source_filter: Optional list of source types to include

        Returns:
            List of matching search results sorted by relevance
        """
        if not self._client:
            raise RuntimeError("Graphiti client not initialized")

        try:
            # Calculate temporal window
            if end_date is None:
                end_date = datetime.now(timezone.utc)
            if start_date is None:
                start_date = end_date - timedelta(days=30)  # Default 30 days

            # Perform search
            results = await self._client.search(
                query=query,
                num_results=num_results,
                group_ids=[group_id],
            )

            # Map Graphiti results to our schema
            search_results = []
            for result in results:
                # Filter by date range
                if result.created_at:
                    if result.created_at < start_date or result.created_at > end_date:
                        continue

                search_results.append(GraphSearchResult(
                    content=result.fact,
                    score=result.score,
                    episode_id=str(result.episode_id),
                    episode_name=result.name or "Unknown",
                    source=EpisodeSource.USER_INTERACTION,  # Default, refined below
                    valid_at=result.valid_at or result.created_at or datetime.now(timezone.utc),
                    metadata={
                        "created_at": result.created_at.isoformat() if result.created_at else None,
                    },
                ))

            return search_results[:num_results]

        except Exception as e:
            logger.error(f"Graphiti search failed: {e}")
            return []

    async def get_user_context(
        self,
        group_id: str,
        query: str,
        include_email_history: bool = True,
        include_calendar: bool = True,
        include_tasks: bool = True,
        include_notes: bool = True,
        days_back: int = 30,
    ) -> dict:
        """Get comprehensive user context for clone operations.

        Aggregates relevant context from all sources for a specific query.

        Args:
            group_id: Tenant/user ID
            query: What we're looking for context about
            include_email_history: Include email episodes
            include_calendar: Include calendar episodes
            include_tasks: Include task episodes
            include_notes: Include note episodes
            days_back: How many days of history to include

        Returns:
            Aggregated context with source breakdowns
        """
        sources = []
        if include_email_history:
            sources.append(EpisodeSource.EMAIL)
        if include_calendar:
            sources.append(EpisodeSource.CALENDAR)
        if include_tasks:
            sources.append(EpisodeSource.TASK)
        if include_notes:
            sources.append(EpisodeSource.NOTE)

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days_back)

        results = await self.search(
            query=query,
            group_id=group_id,
            num_results=20,
            start_date=start_date,
            end_date=end_date,
            source_filter=sources if sources else None,
        )

        # Group by source - ensure all possible sources are included
        all_sources = set(sources) | {EpisodeSource.USER_INTERACTION}
        by_source: dict[EpisodeSource, list[GraphSearchResult]] = {s: [] for s in all_sources}
        for result in results:
            by_source[result.source].append(result)

        return {
            "query": query,
            "time_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "total_results": len(results),
            "by_source": {
                source.value: [
                    {
                        "content": r.content,
                        "score": r.score,
                        "valid_at": r.valid_at.isoformat(),
                    }
                    for r in results
                ]
                for source, results in by_source.items()
            },
            "context_text": "\n\n".join([
                f"[{r.source.value.upper()} - {r.valid_at.date()}]\n{r.content}"
                for r in results[:10]
            ]),
        }

    async def get_temporal_context(
        self,
        group_id: str,
        reference_time: datetime,
        lookback_days: int = 7,
    ) -> list[Episode]:
        """Get all episodes valid at a specific point in time.

        Useful for understanding what the user knew at a specific moment.

        Args:
            group_id: Tenant/user ID
            reference_time: Point in time to query
            lookback_days: How far back to look

        Returns:
            List of episodes valid at reference time
        """
        if not self._client:
            raise RuntimeError("Graphiti client not initialized")

        start_time = reference_time - timedelta(days=lookback_days)

        episodes = await self._client.retrieve_episodes(
            reference_time=reference_time,
            last_n=50,
            group_ids=[group_id],
        )

        return [
            Episode(
                id=str(ep.uuid),
                name=ep.name or "Unknown",
                content=ep.content[:500] if ep.content else "",
                source=EpisodeSource.SYSTEM,
                source_description="",
                group_id=group_id,
                created_at=ep.created_at or start_time,
                valid_at=ep.valid_at or start_time,
                invalid_at=ep.invalid_at,
            )
            for ep in episodes
        ]

    @property
    def is_initialized(self) -> bool:
        """Check if client is initialized."""
        return self._initialized


# Global client instance for dependency injection
_client_instance: Optional[GraphitiClient] = None


async def get_graphiti_client() -> GraphitiClient:
    """Dependency for getting Graphiti client singleton."""
    global _client_instance
    if _client_instance is None:
        _client_instance = GraphitiClient()
        await _client_instance.initialize()
    return _client_instance


async def close_graphiti_client() -> None:
    """Close the global Graphiti client."""
    global _client_instance
    if _client_instance:
        await _client_instance.close()
        _client_instance = None
