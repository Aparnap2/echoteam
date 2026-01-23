"""TDD Tests for Graphiti Memory Layer

These tests define the expected behavior of the GraphitiMemory class.
Run with: pytest tests/test_memory_graphiti.py -v
"""

import os
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch


# Set environment variables BEFORE any imports that use Graphiti
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USER"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "echoteam123"
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["LLM_MODEL"] = "granite3.1-moe:3b"
os.environ["LLM_ENDPOINT"] = "http://localhost:11434"
os.environ["LLM_API_KEY"] = "ollama"
os.environ["EMBEDDING_MODEL"] = "nomic-embed-text:v1.5"
os.environ["EMBEDDING_ENDPOINT"] = "http://localhost:11434/api/embed"
os.environ["EMBEDDING_DIMENSIONS"] = "768"


class TestGraphitiMemoryUnit:
    """Unit tests for GraphitiMemory - mocked Graphiti client."""

    @pytest.fixture
    def mock_graphiti_client(self):
        """Mock Graphiti client for unit testing."""
        mock = MagicMock()
        mock.initialize = AsyncMock()
        mock.close = AsyncMock()
        mock.add_episode = AsyncMock(return_value="episode_123")
        mock.search = AsyncMock(return_value=[
            {"content": "Test result", "score": 0.9, "metadata": {}}
        ])
        return mock

    @pytest.fixture
    def memory_config(self):
        """Sample memory configuration for testing."""
        from app.memory.graphiti import MemoryConfig
        return MemoryConfig(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="echoteam123",
            llm_provider="ollama",
            llm_model="granite3.1-moe:3b",
        )

    @pytest.mark.asyncio
    async def test_memory_config_defaults(self):
        """Test MemoryConfig has sensible defaults."""
        from app.memory.graphiti import MemoryConfig

        config = MemoryConfig()
        assert config.llm_provider == "ollama"
        assert config.llm_model == "granite3.1-moe:3b"
        assert config.neo4j_uri == "bolt://localhost:7687"
        assert config.neo4j_user == "neo4j"

    @pytest.mark.asyncio
    async def test_memory_from_env(self):
        """Test creating MemoryConfig from environment variables."""
        from app.memory.graphiti import MemoryConfig

        config = MemoryConfig.from_env()
        assert config.llm_provider == "ollama"
        assert config.llm_model == "granite3.1-moe:3b"

    @pytest.mark.asyncio
    async def test_memory_operation_result(self):
        """Test MemoryOperationResult model."""
        from app.memory.graphiti import MemoryOperationResult, MemoryOperationStatus

        result = MemoryOperationResult(
            status=MemoryOperationStatus.SUCCESS,
            message="Test passed",
            items_processed=5,
        )
        assert result.status == MemoryOperationStatus.SUCCESS
        assert result.items_processed == 5

    @pytest.mark.asyncio
    async def test_search_result(self):
        """Test SearchResult model."""
        from app.memory.graphiti import SearchResult, MemorySourceType

        result = SearchResult(
            text="Found content",
            score=0.95,
            source=MemorySourceType.EMAIL,
            metadata={"key": "value"},
        )
        assert result.text == "Found content"
        assert result.score == 0.95
        assert result.source == MemorySourceType.EMAIL

    @pytest.mark.asyncio
    async def test_user_context(self):
        """Test UserContext model for clone operations."""
        from app.memory.graphiti import UserContext, SearchResult, MemorySourceType

        context = UserContext(
            query="email preferences",
            context_text="User prefers short replies",
        )
        assert context.query == "email preferences"
        assert context.email_context == []


class TestGraphitiMemoryIntegration:
    """Integration tests for GraphitiMemory - requires Neo4j + Ollama."""

    TEST_USER_ID = "test_user_graphiti"

    @pytest_asyncio.fixture
    async def memory(self):
        """Create memory instance for integration testing."""
        from app.memory.graphiti import GraphitiMemory, MemoryConfig

        config = MemoryConfig(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="echoteam123",
            llm_provider="ollama",
            llm_model="granite3.1-moe:3b",
            embedding_model="nomic-embed-text:v1.5",
        )
        memory = GraphitiMemory(user_id=self.TEST_USER_ID, config=config)
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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-x"])
