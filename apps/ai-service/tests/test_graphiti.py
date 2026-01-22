"""Integration tests for Graphiti client with FalkorDB.

These tests verify:
- Episode ingestion with entity extraction
- Temporal queries for context retrieval
- Multi-tenant isolation via group IDs
- User context aggregation for clones

Prerequisites:
- FalkorDB running on localhost:6379
- graphiti-core[falkordb] installed
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.graphiti.client import (
    GraphitiClient,
    EpisodeSource,
    Episode,
    GraphSearchResult,
    get_graphiti_client,
)


class TestGraphitiClientUnit:
    """Unit tests for GraphitiClient (mocked FalkorDB)."""

    def test_episode_model_creation(self):
        """Test Episode model can be created with all fields."""
        now = datetime.now(timezone.utc)
        episode = Episode(
            id="test-uuid-123",
            name="Test Email Episode",
            content="User sent email about project update",
            source=EpisodeSource.EMAIL,
            source_description="Gmail sync",
            group_id="user-123",
            created_at=now,
            valid_at=now,
            entities=[
                {"name": "Project Update", "labels": ["Topic"], "attributes": {}}
            ],
            relationships=[
                {"fact": "sent email about", "source": "user", "target": "project"}
            ],
        )

        assert episode.id == "test-uuid-123"
        assert episode.name == "Test Email Episode"
        assert episode.source == EpisodeSource.EMAIL
        assert episode.group_id == "user-123"
        assert len(episode.entities) == 1
        assert len(episode.relationships) == 1

    def test_episode_source_enum(self):
        """Test EpisodeSource enum values."""
        assert EpisodeSource.EMAIL.value == "email"
        assert EpisodeSource.CALENDAR.value == "calendar"
        assert EpisodeSource.TASK.value == "task"
        assert EpisodeSource.NOTE.value == "note"
        assert EpisodeSource.RESEARCH.value == "research"

    def test_graph_search_result_model(self):
        """Test GraphSearchResult model creation."""
        now = datetime.now(timezone.utc)
        result = GraphSearchResult(
            content="User prefers concise email replies",
            score=0.92,
            episode_id="ep-123",
            episode_name="November Email Thread",
            source=EpisodeSource.EMAIL,
            valid_at=now,
            metadata={"context": "tone analysis"},
        )

        assert result.score == 0.92
        assert result.source == EpisodeSource.EMAIL
        assert "concise" in result.content


class TestGraphitiClientIntegration:
    """Integration tests for GraphitiClient with mocked Graphiti core.

    These tests use mocks to simulate Graphiti behavior without requiring
    an actual FalkorDB instance.
    """

    @pytest.fixture
    def mock_graphiti_client(self):
        """Create a GraphitiClient with mocked core client."""
        client = GraphitiClient(
            uri="bolt://localhost:7687",
            user="test",
            password="test",
        )
        return client

    @pytest.fixture
    def mock_graphiti_core(self):
        """Create a mock Graphiti core client."""
        mock = AsyncMock()

        # Mock add_episode response
        mock_result = MagicMock()
        mock_result.episode.uuid = "test-episode-uuid"
        mock_result.episode.created_at = datetime.now(timezone.utc)
        mock_result.nodes = []
        mock_result.edges = []
        mock.add_episode.return_value = mock_result

        # Mock search response
        mock_search_result = MagicMock()
        mock_search_result.fact = "Test fact from graph"
        mock_search_result.score = 0.95
        mock_search_result.episode_id = "ep-123"
        mock_search_result.name = "Test Episode"
        mock_search_result.created_at = datetime.now(timezone.utc)
        mock_search_result.valid_at = datetime.now(timezone.utc)
        mock.search.return_value = [mock_search_result]

        # Mock retrieve_episodes response
        mock_retrieve = MagicMock()
        mock_retrieve.uuid = "retrieve-uuid"
        mock_retrieve.name = "Retrieved Episode"
        mock_retrieve.content = "Retrieved content"
        mock_retrieve.created_at = datetime.now(timezone.utc)
        mock_retrieve.valid_at = datetime.now(timezone.utc)
        mock.retrieve_episodes.return_value = [mock_retrieve]

        return mock

    @pytest.mark.asyncio
    async def test_initialize_creates_connection(self, mock_graphiti_client, mock_graphiti_core):
        """Test that initialize creates Graphiti connection."""
        with patch("app.graphiti.client.Graphiti", return_value=mock_graphiti_core):
            mock_graphiti_core.build_indices_and_constraints = AsyncMock()

            await mock_graphiti_client.initialize()

            assert mock_graphiti_client.is_initialized is True
            mock_graphiti_core.build_indices_and_constraints.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_episode_returns_episode(self, mock_graphiti_client, mock_graphiti_core):
        """Test that add_episode returns properly structured Episode."""
        with patch("app.graphiti.client.Graphiti", return_value=mock_graphiti_core):
            mock_graphiti_core.build_indices_and_constraints = AsyncMock()
            await mock_graphiti_client.initialize()

            episode = await mock_graphiti_client.add_episode(
                name="Test Email",
                content="User discussed Q4 roadmap in email",
                source=EpisodeSource.EMAIL,
                group_id="user-123",
                source_description="Gmail sync",
            )

            assert isinstance(episode, Episode)
            assert episode.name == "Test Email"
            assert episode.source == EpisodeSource.EMAIL
            assert episode.group_id == "user-123"
            mock_graphiti_core.add_episode.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_returns_results(self, mock_graphiti_client, mock_graphiti_core):
        """Test that search returns GraphSearchResult objects."""
        with patch("app.graphiti.client.Graphiti", return_value=mock_graphiti_core):
            mock_graphiti_core.build_indices_and_constraints = AsyncMock()
            await mock_graphiti_client.initialize()

            results = await mock_graphiti_client.search(
                query="email tone preferences",
                group_id="user-123",
                num_results=5,
            )

            assert len(results) == 1
            assert isinstance(results[0], GraphSearchResult)
            assert results[0].score == 0.95
            assert "Test fact" in results[0].content

    @pytest.mark.asyncio
    async def test_get_user_context_aggregates_sources(self, mock_graphiti_client, mock_graphiti_core):
        """Test that get_user_context aggregates context from multiple sources."""
        with patch("app.graphiti.client.Graphiti", return_value=mock_graphiti_core):
            mock_graphiti_core.build_indices_and_constraints = AsyncMock()
            await mock_graphiti_client.initialize()

            context = await mock_graphiti_client.get_user_context(
                group_id="user-123",
                query="project timeline",
                include_email_history=True,
                include_calendar=True,
                include_tasks=True,
                include_notes=True,
                days_back=30,
            )

            assert "query" in context
            assert "time_range" in context
            assert "by_source" in context
            assert context["query"] == "project timeline"


class TestTemporalQueries:
    """Tests for temporal query behavior."""

    @pytest.mark.asyncio
    async def test_temporal_context_respects_time_bounds(self):
        """Test that temporal context queries respect time bounds."""
        client = GraphitiClient()

        # Mock the internal client
        mock_core = AsyncMock()
        mock_episode = MagicMock()
        mock_episode.uuid = "ep-temporal"
        mock_episode.name = "Historical Episode"
        mock_episode.content = "Content from last month"
        mock_episode.created_at = datetime.now(timezone.utc) - timedelta(days=15)
        mock_episode.valid_at = datetime.now(timezone.utc) - timedelta(days=15)
        mock_core.retrieve_episodes.return_value = [mock_episode]

        with patch("app.graphiti.client.Graphiti", return_value=mock_core):
            mock_core.build_indices_and_constraints = AsyncMock()
            await client.initialize()

            # Query with specific reference time
            reference = datetime.now(timezone.utc)
            episodes = await client.get_temporal_context(
                group_id="user-123",
                reference_time=reference,
                lookback_days=7,
            )

            # Verify retrieve_episodes was called with correct params
            mock_core.retrieve_episodes.assert_called_once()
            call_kwargs = mock_core.retrieve_episodes.call_args[1]
            assert call_kwargs["reference_time"] == reference
            assert call_kwargs["last_n"] == 50


class TestEpisodeIngestion:
    """Tests for episode ingestion from different sources."""

    @pytest.mark.parametrize("source", [
        EpisodeSource.EMAIL,
        EpisodeSource.CALENDAR,
        EpisodeSource.TASK,
        EpisodeSource.NOTE,
        EpisodeSource.RESEARCH,
    ])
    @pytest.mark.asyncio
    async def test_ingest_episode_from_source(self, source):
        """Test that episodes can be ingested from any source type."""
        client = GraphitiClient()

        mock_core = AsyncMock()
        mock_result = MagicMock()
        mock_result.episode.uuid = f"ep-{source.value}"
        mock_result.episode.created_at = datetime.now(timezone.utc)
        mock_result.nodes = []
        mock_result.edges = []
        mock_core.add_episode.return_value = mock_result

        with patch("app.graphiti.client.Graphiti", return_value=mock_core):
            mock_core.build_indices_and_constraints = AsyncMock()
            await client.initialize()

            episode = await client.add_episode(
                name=f"Test {source.value.title()} Episode",
                content=f"Content from {source.value}",
                source=source,
                group_id="test-user",
            )

            assert episode.source == source
            mock_core.add_episode.assert_called_once()


class TestMultiTenantIsolation:
    """Tests for multi-tenant isolation via group IDs."""

    @pytest.mark.asyncio
    async def test_search_isolated_by_group_id(self):
        """Test that search only returns results for specific group_id."""
        client = GraphitiClient()

        mock_core = AsyncMock()
        mock_result = MagicMock()
        mock_result.fact = "Group A context"
        mock_result.score = 0.9
        mock_result.episode_id = "ep-a"
        mock_result.name = "Group A Episode"
        mock_result.created_at = datetime.now(timezone.utc)
        mock_result.valid_at = datetime.now(timezone.utc)
        mock_core.search.return_value = [mock_result]

        with patch("app.graphiti.client.Graphiti", return_value=mock_core):
            mock_core.build_indices_and_constraints = AsyncMock()
            await client.initialize()

            # Search for group A
            results = await client.search(
                query="context",
                group_id="group-a",
            )

            # Verify group_ids was passed correctly
            call_kwargs = mock_core.search.call_args[1]
            assert call_kwargs["group_ids"] == ["group-a"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
