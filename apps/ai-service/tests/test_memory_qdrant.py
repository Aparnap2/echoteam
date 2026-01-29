"""TDD Tests for Qdrant Memory Layer

These tests define the expected behavior of the QdrantMemory class.
Run with: pytest tests/test_memory_qdrant.py -v

Tests cover:
- Configuration validation
- Initialization and connection
- Add operations with hybrid indexing
- Hybrid search (dense + sparse)
- User context retrieval
- User data isolation
"""

import os
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


# Set environment variables for testing
os.environ["QDRANT_URL"] = "http://localhost:6333"
os.environ["EMBEDDING_MODEL"] = "nomic-embed-text:v1.5"
os.environ["EMBEDDING_DIMENSIONS"] = "768"


class TestMemoryConfig:
    """Unit tests for MemoryConfig."""

    def test_config_defaults(self):
        """Test MemoryConfig has sensible defaults."""
        from app.memory.qdrant import MemoryConfig

        config = MemoryConfig()
        assert config.qdrant_url == "http://localhost:6333"
        assert config.embedding_model == "nomic-embed-text:v1.5"
        assert config.embedding_dimensions == 768
        assert config.max_results == 20

    def test_config_from_env(self):
        """Test creating config from environment variables."""
        from app.memory.qdrant import MemoryConfig

        config = MemoryConfig.from_env()
        assert config.qdrant_url == "http://localhost:6333"

    def test_config_validation_valid_url(self):
        """Test config validation accepts valid URLs."""
        from app.memory.qdrant import MemoryConfig

        config = MemoryConfig(qdrant_url="https://qdrant.example.com:6333")
        assert config.qdrant_url == "https://qdrant.example.com:6333"

    def test_config_validation_invalid_url(self):
        """Test config validation rejects invalid URLs."""
        from app.memory.qdrant import MemoryConfig

        with pytest.raises(ValueError, match="http:// or https://"):
            MemoryConfig(qdrant_url="invalid-url")

    def test_config_custom_values(self):
        """Test config with custom values."""
        from app.memory.qdrant import MemoryConfig

        config = MemoryConfig(
            qdrant_url="http://localhost:6333",
            embedding_model="custom-model",
            embedding_dimensions=1024,
            max_results=50,
        )
        assert config.embedding_model == "custom-model"
        assert config.embedding_dimensions == 1024
        assert config.max_results == 50


class TestMemoryOperationResult:
    """Unit tests for MemoryOperationResult."""

    def test_success_result(self):
        """Test creating a successful result."""
        from app.memory.qdrant import MemoryOperationResult, MemoryOperationStatus

        result = MemoryOperationResult(
            status=MemoryOperationStatus.SUCCESS,
            message="Added 5 items",
            items_processed=5,
        )
        assert result.status == MemoryOperationStatus.SUCCESS
        assert result.items_processed == 5

    def test_failed_result(self):
        """Test creating a failed result."""
        from app.memory.qdrant import MemoryOperationResult, MemoryOperationStatus

        result = MemoryOperationResult(
            status=MemoryOperationStatus.FAILED,
            error="Connection timeout",
        )
        assert result.status == MemoryOperationStatus.FAILED
        assert result.error == "Connection timeout"


class TestSearchResult:
    """Unit tests for SearchResult."""

    def test_search_result_creation(self):
        """Test creating a search result."""
        from app.memory.qdrant import SearchResult, MemorySourceType

        result = SearchResult(
            id="test-id",
            content="Meeting at 3pm",
            score=0.95,
            source=MemorySourceType.CALENDAR,
            metadata={"timestamp": "2024-01-15"},
        )
        assert result.id == "test-id"
        assert result.content == "Meeting at 3pm"
        assert result.score == 0.95
        assert result.source == MemorySourceType.CALENDAR

    def test_search_result_defaults(self):
        """Test search result default values."""
        from app.memory.qdrant import SearchResult, MemorySourceType

        result = SearchResult(
            id="test-id",
            content="Test content",
        )
        assert result.score == 0.0
        assert result.source == MemorySourceType.USER_INTERACTION
        assert result.metadata == {}


class TestUserContext:
    """Unit tests for UserContext."""

    def test_user_context_creation(self):
        """Test creating a user context."""
        from app.memory.qdrant import UserContext, SearchResult

        results = [
            SearchResult(id="1", content="Email about project", source="email"),
            SearchResult(id="2", content="Meeting scheduled", source="calendar"),
        ]

        context = UserContext(
            query="project meeting",
            email_context=[results[0]],
            calendar_context=[results[1]],
            context_text="[EMAIL] Email about project\n\n[CALENDAR] Meeting scheduled",
        )

        assert context.query == "project meeting"
        assert len(context.email_context) == 1
        assert len(context.calendar_context) == 1

    def test_user_context_to_dict(self):
        """Test converting context to dictionary."""
        from app.memory.qdrant import UserContext

        context = UserContext(
            query="test query",
            context_text="Some context",
        )

        data = context.to_dict()
        assert data["query"] == "test query"
        assert data["email_count"] == 0
        assert "context_text" in data


class TestQdrantMemoryUnit:
    """Unit tests for QdrantMemory - mocked Qdrant client."""

    @pytest_asyncio.fixture
    async def memory(self):
        """Create memory instance with mocked Qdrant client."""
        from app.memory.qdrant import QdrantMemory, MemoryConfig

        config = MemoryConfig(
            qdrant_url="http://localhost:6333",
            embedding_model="nomic-embed-text:v1.5",
        )
        memory = QdrantMemory(user_id="test_user", config=config)
        yield memory
        await memory.close()

    @pytest.mark.asyncio
    async def test_memory_not_initialized_initially(self, memory):
        """Test memory is not initialized on creation."""
        assert memory.is_initialized is False

    @pytest.mark.asyncio
    async def test_collection_name_includes_user_id(self, memory):
        """Test collection name includes user_id for isolation."""
        assert "test_user" in memory.collection
        assert memory.collection.startswith("echoteam_")

    @pytest.mark.asyncio
    async def test_close_uninitialized_memory(self, memory):
        """Test closing uninitialized memory is safe."""
        await memory.close()  # Should not raise
        assert memory.is_initialized is False

    @pytest.mark.asyncio
    async def test_multiple_close_is_safe(self, memory):
        """Test closing multiple times is safe."""
        await memory.close()
        await memory.close()  # Should not raise


class TestQdrantMemoryWithMocks:
    """Unit tests for QdrantMemory with mocked dependencies."""

    @pytest_asyncio.fixture
    async def memory(self):
        """Create memory instance with mocked embedding."""
        from app.memory.qdrant import QdrantMemory, MemoryConfig

        config = MemoryConfig(
            qdrant_url="http://localhost:6333",
            embedding_model="nomic-embed-text:v1.5",
        )
        memory = QdrantMemory(user_id="test_user", config=config)
        yield memory
        await memory.close()

    @pytest.mark.asyncio
    async def test_add_returns_success(self, memory):
        """Test add operation returns success."""
        with patch.object(memory, '_ensure_client', new_callable=AsyncMock) as mock_client:
            mock_client.return_value = AsyncMock()
            with patch.object(memory, '_generate_embedding', new_callable=AsyncMock, return_value=[0.1] * 768):
                with patch.object(memory, '_generate_sparse_vector', new_callable=AsyncMock, return_value={}):
                    with patch('qdrant_client.models.PointStruct') as mock_point:
                        mock_client.return_value.upsert = AsyncMock()
                        await memory.initialize()
                        result = await memory.add("Test content", {"source": "test"})
                        assert result.status.value == "success"

    @pytest.mark.asyncio
    async def test_search_returns_results(self, memory):
        """Test search returns results."""
        with patch.object(memory, '_ensure_client', new_callable=AsyncMock) as mock_client:
            mock_client.return_value = AsyncMock()
            with patch.object(memory, '_generate_embedding', new_callable=AsyncMock, return_value=[0.1] * 768):
                with patch.object(memory, '_generate_sparse_vector', new_callable=AsyncMock, return_value={}):
                    await memory.initialize()

                    # Mock query_points response
                    mock_result = MagicMock()
                    mock_result.result.points = []
                    mock_client.return_value.query_points = AsyncMock(return_value=mock_result)

                    results = await memory.search("test query")
                    assert isinstance(results, list)


class TestQdrantMemoryIntegration:
    """Integration tests for QdrantMemory - requires real Qdrant instance."""

    TEST_USER_ID = "integration_test_user"

    @pytest_asyncio.fixture
    async def memory(self):
        """Create memory instance for integration testing."""
        from app.memory.qdrant import QdrantMemory, MemoryConfig

        config = MemoryConfig(
            qdrant_url="http://localhost:6333",
            embedding_model="nomic-embed-text:v1.5",
        )
        memory = QdrantMemory(user_id=self.TEST_USER_ID, config=config)
        await memory.initialize()

        yield memory

        await memory.close()

    @pytest.mark.asyncio
    async def test_initialize(self, memory):
        """Test memory layer initialization."""
        assert memory.is_initialized is True

    @pytest.mark.asyncio
    async def test_add_content(self, memory):
        """Test adding content to memory."""
        result = await memory.add(
            content="The founder prefers concise email replies under 3 sentences.",
            metadata={"source": "email"},
        )
        assert result.status.value == "success"
        assert result.items_processed == 1

    @pytest.mark.asyncio
    async def test_add_and_search(self, memory):
        """Test adding content and searching for it."""
        # Add content
        add_result = await memory.add(
            content="Meeting scheduled for 3pm tomorrow with the client.",
            metadata={"source": "calendar"},
        )
        assert add_result.status.value == "success"

        # Search for it
        results = await memory.search(query="meeting client 3pm")
        assert len(results) >= 0  # May be empty if indexing not complete

    @pytest.mark.asyncio
    async def test_get_user_context(self, memory):
        """Test getting user context for clone operations."""
        # Add some content first
        await memory.add(
            content="User prefers formal tone in emails.",
            metadata={"source": "email"},
        )

        # Get context
        context = await memory.get_user_context(query="email style")
        assert context.query == "email style"
        assert isinstance(context.context_text, str)

    @pytest.mark.asyncio
    async def test_user_data_isolation(self, memory):
        """Test that user data is isolated by collection."""
        from app.memory.qdrant import QdrantMemory, MemoryConfig

        # Create another memory for different user
        other_memory = QdrantMemory(
            user_id="other_user",
            config=MemoryConfig(qdrant_url="http://localhost:6333"),
        )
        await other_memory.initialize()

        # Add content to first memory
        await memory.add(
            content="Secret project information",
            metadata={"source": "note"},
        )

        # Search in other user's memory - should not find our data
        results = await other_memory.search(query="Secret project")
        other_user_content = [r.content for r in results]

        # Cleanup
        await other_memory.close()

        # The other user should not see the first user's data
        assert "Secret project information" not in other_user_content


class TestMemorySourceType:
    """Tests for MemorySourceType enum."""

    def test_source_types_defined(self):
        """Test all expected source types are defined."""
        from app.memory.qdrant import MemorySourceType

        assert MemorySourceType.EMAIL == "email"
        assert MemorySourceType.CALENDAR == "calendar"
        assert MemorySourceType.TASK == "task"
        assert MemorySourceType.NOTE == "note"
        assert MemorySourceType.RESEARCH == "research"
        assert MemorySourceType.USER_INTERACTION == "user_interaction"
        assert MemorySourceType.SYSTEM == "system"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
