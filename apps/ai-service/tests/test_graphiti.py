"""Tests for Graphiti client and temporal knowledge graph operations."""

import pytest
from unittest.mock import Mock, AsyncMock, patch


class TestGraphitiClient:
    """Mock Graphiti client for testing."""

    def __init__(self):
        self.initialized = False
        self.episodes = []

    async def initialize(self) -> None:
        self.initialized = True

    async def close(self) -> None:
        self.initialized = False

    async def add_episode(self, name: str, facts: list[str]) -> str:
        episode_id = f"episode_{len(self.episodes)}"
        self.episodes.append({"id": episode_id, "name": name, "facts": facts})
        return episode_id

    async def search(self, query: str, num_results: int = 5) -> list[dict]:
        return [
            {"content": f"Result for {query}", "score": 0.9}
            for _ in range(num_results)
        ]


class TestTemporalGraph:
    """Test temporal graph operations."""

    def __init__(self):
        self.nodes: dict[str, dict] = {}
        self.edges: list[dict] = []

    def add_node(self, node_id: str, data: dict) -> None:
        self.nodes[node_id] = {**data, "node_id": node_id}

    def add_edge(self, source: str, target: str, relation: str) -> None:
        self.edges.append({
            "source": source,
            "target": target,
            "relation": relation
        })

    def query_temporal(self, node_id: str, time_range: tuple[str, str]) -> list[dict]:
        """Query nodes within a time range."""
        return [
            self.nodes.get(node_id, {})
        ]


@pytest.fixture
def graphiti_client():
    """Provide a test Graphiti client."""
    return TestGraphitiClient()


@pytest.fixture
def temporal_graph():
    """Provide a test temporal graph."""
    return TestTemporalGraph()


class TestGraphitiClientUnit:
    """Unit tests for Graphiti client."""

    def test_client_initialization(self, graphiti_client):
        """Test that client can be initialized."""
        assert not graphiti_client.initialized

    @pytest.mark.asyncio
    async def test_client_initialize(self, graphiti_client):
        """Test client initialization async method."""
        await graphiti_client.initialize()
        assert graphiti_client.initialized

    @pytest.mark.asyncio
    async def test_client_close(self, graphiti_client):
        """Test client close async method."""
        await graphiti_client.initialize()
        await graphiti_client.close()
        assert not graphiti_client.initialized

    @pytest.mark.asyncio
    async def test_add_episode(self, graphiti_client):
        """Test adding an episode to the graph."""
        episode_id = await graphiti_client.add_episode(
            "test_episode",
            ["fact1", "fact2"]
        )
        assert episode_id == "episode_0"
        assert len(graphiti_client.episodes) == 1

    @pytest.mark.asyncio
    async def test_search(self, graphiti_client):
        """Test searching the graph."""
        results = await graphiti_client.search("test query", num_results=3)
        assert len(results) == 3
        assert all("content" in r for r in results)
        assert all("score" in r for r in results)


class TestTemporalGraphUnit:
    """Unit tests for temporal graph."""

    def test_add_node(self, temporal_graph):
        """Test adding a node to the graph."""
        temporal_graph.add_node("user_1", {"name": "John", "type": "person"})
        assert "user_1" in temporal_graph.nodes
        assert temporal_graph.nodes["user_1"]["name"] == "John"

    def test_add_edge(self, temporal_graph):
        """Test adding an edge to the graph."""
        temporal_graph.add_edge("user_1", "task_1", "owns")
        assert len(temporal_graph.edges) == 1
        assert temporal_graph.edges[0]["relation"] == "owns"

    def test_query_temporal(self, temporal_graph):
        """Test temporal query."""
        temporal_graph.add_node("event_1", {"type": "meeting"})
        results = temporal_graph.query_temporal("event_1", ("2024-01-01", "2024-12-31"))
        assert len(results) == 1
        assert results[0]["type"] == "meeting"
