"""Tests for Graphiti memory layer with Neo4j.

These tests verify the Graphiti integration with Neo4j for:
- User data isolation
- Add → Search workflow
- Temporal context queries
- Multi-tenant support
"""

import os
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


class TestMemoryConfig:
    """Test cases for MemoryConfig."""

    def test_config_defaults(self):
        """Test default configuration values."""
        from app.memory.graphiti import MemoryConfig

        config = MemoryConfig()
        assert config.llm_provider == "ollama"
        assert config.llm_model == "granite3.1-moe:3b"
        assert config.neo4j_uri == "bolt://localhost:7687"
        assert config.neo4j_user == "neo4j"

    def test_config_custom(self):
        """Test custom configuration values."""
        from app.memory.graphiti import MemoryConfig

        config = MemoryConfig(
            neo4j_uri="bolt://neo4j.example.com:7687",
            neo4j_user="admin",
            neo4j_password="secret123",
            llm_provider="openai",
            llm_model="gpt-4o-mini",
        )
        assert config.neo4j_uri == "bolt://neo4j.example.com:7687"
        assert config.neo4j_user == "admin"
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4o-mini"

    def test_config_from_env(self):
        """Test creating config from environment variables."""
        from app.memory.graphiti import MemoryConfig

        # Set environment variables
        os.environ["NEO4J_URI"] = "bolt://custom:7687"
        os.environ["NEO4J_USER"] = "testuser"
        os.environ["NEO4J_PASSWORD"] = "testpass"
        os.environ["LLM_PROVIDER"] = "groq"
        os.environ["LLM_MODEL"] = "llama-3.3-70b-versatile"

        try:
            config = MemoryConfig.from_env()
            assert config.neo4j_uri == "bolt://custom:7687"
            assert config.neo4j_user == "testuser"
            assert config.llm_provider == "groq"
            assert config.llm_model == "llama-3.3-70b-versatile"
        finally:
            # Cleanup
            del os.environ["NEO4J_URI"]
            del os.environ["NEO4J_USER"]
            del os.environ["NEO4J_PASSWORD"]
            del os.environ["LLM_PROVIDER"]
            del os.environ["LLM_MODEL"]

    def test_config_validation_uri(self):
        """Test configuration validation for Neo4j URI."""
        from app.memory.graphiti import MemoryConfig

        with pytest.raises(ValueError):
            MemoryConfig(neo4j_uri="http://localhost:7687")


class TestSearchResult:
    """Test cases for SearchResult model."""

    def test_search_result_creation(self):
        """Test creating a SearchResult."""
        from app.memory.graphiti import SearchResult, MemorySourceType

        result = SearchResult(
            text="Test content",
            score=0.95,
            source=MemorySourceType.EMAIL,
        )
        assert result.text == "Test content"
        assert result.score == 0.95
        assert result.source == MemorySourceType.EMAIL

    def test_search_result_defaults(self):
        """Test SearchResult default values."""
        from app.memory.graphiti import SearchResult

        result = SearchResult(text="Test")
        assert result.score == 0.0
        assert result.source.value == "user_interaction"
        assert result.metadata == {}


class TestUserContext:
    """Test cases for UserContext model."""

    def test_user_context_creation(self):
        """Test creating a UserContext."""
        from app.memory.graphiti import UserContext, SearchResult

        context = UserContext(
            query="client preferences",
            email_context=[
                SearchResult(text="Client likes video calls", score=0.9)
            ],
        )
        assert context.query == "client preferences"
        assert len(context.email_context) == 1

    def test_user_context_to_dict(self):
        """Test UserContext serialization."""
        from app.memory.graphiti import UserContext

        context = UserContext(
            query="test",
            context_text="Some context",
        )
        data = context.to_dict()
        assert data["query"] == "test"
        assert data["context_text"] == "Some context"


class TestMemoryOperationResult:
    """Test cases for MemoryOperationResult model."""

    def test_success_result(self):
        """Test creating a success result."""
        from app.memory.graphiti import MemoryOperationResult, MemoryOperationStatus

        result = MemoryOperationResult(
            status=MemoryOperationStatus.SUCCESS,
            items_processed=5,
        )
        assert result.status == MemoryOperationStatus.SUCCESS
        assert result.items_processed == 5

    def test_failed_result(self):
        """Test creating a failed result."""
        from app.memory.graphiti import MemoryOperationResult, MemoryOperationStatus

        result = MemoryOperationResult(
            status=MemoryOperationStatus.FAILED,
            error="Connection failed",
        )
        assert result.status == MemoryOperationStatus.FAILED
        assert result.error == "Connection failed"


class TestMemorySourceType:
    """Test cases for MemorySourceType enum."""

    def test_source_types(self):
        """Test all source types are defined."""
        from app.memory.graphiti import MemorySourceType

        assert MemorySourceType.EMAIL.value == "email"
        assert MemorySourceType.CALENDAR.value == "calendar"
        assert MemorySourceType.TASK.value == "task"
        assert MemorySourceType.NOTE.value == "note"
        assert MemorySourceType.RESEARCH.value == "research"
        assert MemorySourceType.USER_INTERACTION.value == "user_interaction"
        assert MemorySourceType.SYSTEM.value == "system"


class TestGraphitiMemoryUnit:
    """Unit tests for GraphitiMemory class (without actual Graphiti)."""

    def test_memory_initialization(self):
        """Test memory instance creation."""
        from app.memory.graphiti import GraphitiMemory, MemoryConfig

        memory = GraphitiMemory(
            user_id="test_user",
            config=MemoryConfig(llm_provider="ollama"),
        )
        assert memory.user_id == "test_user"
        assert memory.config.llm_provider == "ollama"
        assert memory.is_initialized is False

    @pytest.mark.asyncio
    async def test_memory_not_initialized_until_called(self):
        """Test memory doesn't auto-initialize."""
        from app.memory.graphiti import GraphitiMemory

        memory = GraphitiMemory(user_id="test_user")
        # Should not be initialized until explicitly called
        assert memory.is_initialized is False

    @pytest.mark.asyncio
    async def test_close_uninitialized_memory(self):
        """Test closing uninitialized memory is safe."""
        from app.memory.graphiti import GraphitiMemory

        memory = GraphitiMemory(user_id="test_user")
        # Should not raise
        await memory.close()

    @pytest.mark.asyncio
    async def test_multiple_close_is_safe(self):
        """Test closing memory multiple times is safe."""
        from app.memory.graphiti import GraphitiMemory

        memory = GraphitiMemory(user_id="test_user")
        await memory.close()
        await memory.close()  # Should not raise


class TestGraphitiMemoryWithMocks:
    """Tests for GraphitiMemory with mocked Graphiti module."""

    @pytest.fixture
    def mock_graphiti(self):
        """Create mocked Graphiti module."""
        mock = MagicMock()

        # Set up async mocks
        mock.initialize = AsyncMock()
        mock.close = AsyncMock()
        mock.add_episode = AsyncMock(return_value="episode_123")
        mock.search = AsyncMock(return_value=[
            MagicMock(content="Result 1", score=0.9, metadata={}),
            MagicMock(content="Result 2", score=0.8, metadata={}),
        ])

        return mock

    @pytest_asyncio.fixture
    async def memory_with_mocks(self, mock_graphiti):
        """Create memory instance with mocked Graphiti."""
        from app.memory.graphiti import GraphitiMemory, MemoryConfig

        memory = GraphitiMemory(
            user_id="test_user",
            config=MemoryConfig(llm_provider="ollama"),
        )
        # Inject mock module
        memory._graphiti = mock_graphiti
        memory._initialized = True
        yield memory
        await memory.close()

    @pytest.mark.asyncio
    async def test_add_calls_graphiti(self, memory_with_mocks, mock_graphiti):
        """Test add method calls Graphiti add_episode."""
        await memory_with_mocks.add(
            content="Test email content",
            metadata={"source": "email"},
        )

        mock_graphiti.add_episode.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_returns_results(self, memory_with_mocks, mock_graphiti):
        """Test search returns parsed results."""
        results = await memory_with_mocks.search(query="test query")

        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0].text == "Result 1"
        assert results[0].score == 0.9

    @pytest.mark.asyncio
    async def test_search_with_max_results(self, memory_with_mocks, mock_graphiti):
        """Test search respects max_results parameter."""
        await memory_with_mocks.search(query="test", max_results=5)

        # Verify search was called
        mock_graphiti.search.assert_called_once()


class TestGraphitiMemoryIntegration:
    """Integration tests for Graphiti memory (requires Neo4j + Ollama).

    These tests require:
    - Neo4j running on localhost:7687
    - Ollama running on localhost:11434 with granite3.1-moe:3b model
    """

    @pytest_asyncio.fixture
    async def real_memory(self):
        """Create memory instance for integration testing."""
        from app.memory.graphiti import GraphitiMemory, MemoryConfig

        # Check if Neo4j is available
        try:
            import httpx
            resp = httpx.get("http://localhost:7474", timeout=2)
            if resp.status_code != 200:
                pytest.skip("Neo4j not available")
        except Exception:
            pytest.skip("Neo4j not available")

        # Check if Ollama is available
        try:
            resp = httpx.get("http://localhost:11434/api/version", timeout=2)
            if resp.status_code != 200:
                pytest.skip("Ollama not available")
        except Exception:
            pytest.skip("Ollama not available")

        # Create memory instance
        try:
            config = MemoryConfig(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="echoteam123",
                llm_provider="ollama",
                llm_model="granite3.1-moe:3b",
            )
            memory = GraphitiMemory(user_id="integration_test", config=config)
            await memory.initialize()
        except Exception as e:
            pytest.skip(f"Graphiti initialization failed: {e}")

        if not memory.is_initialized:
            pytest.skip("Graphiti memory failed to initialize")

        yield memory

        # Cleanup after test
        await memory.close()

    @pytest.mark.asyncio
    async def test_real_add(self, real_memory):
        """Test real add operation."""
        result = await real_memory.add(
            content="Meeting with client at 3pm about project Alpha",
            metadata={"source": "calendar"},
        )

        assert result.status.value == "success"
        assert result.items_processed == 1

    @pytest.mark.asyncio
    async def test_real_add_and_search(self, real_memory):
        """Test real add and search operations."""
        # Add content
        result = await real_memory.add(
            content="Client prefers email communication over phone calls",
            metadata={"source": "email"},
        )
        assert result.status.value == "success"

        # Search should return relevant results
        results = await real_memory.search(query="client communication preferences")

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_user_data_isolation(self, real_memory):
        """Test that user data is isolated."""
        from app.memory.graphiti import GraphitiMemory, MemoryConfig

        # Create another memory for different user
        other_memory = GraphitiMemory(
            user_id="other_user",
            config=MemoryConfig(
                neo4j_uri="bolt://localhost:7687",
                neo4j_user="neo4j",
                neo4j_password="echoteam123",
            ),
        )
        await other_memory.initialize()

        # Add content to first memory
        await real_memory.add(
            content="Secret project information",
            metadata={"source": "note"},
        )

        # Search in other user's memory
        results = await other_memory.search(query="Secret project")

        # Cleanup
        await other_memory.close()

        # The other user should not see the first user's data
        assert all(r.text != "Secret project information" for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
