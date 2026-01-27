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
os.environ["OPENAI_API_KEY"] = "ollama"  # Required by Graphiti's OpenAI client
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
        """Test adding content to memory.

        Note: This test requires Graphiti 0.27+ or a Neo4j version compatible with
        Graphiti's dynamic label handling. Currently fails due to Neo4j 5.x not
        supporting SET n:$(label) syntax that Graphiti 0.26.0 generates.
        """
        pytest.skip("Blocked by Graphiti 0.26.0 bug with Neo4j 5.x dynamic labels")

    @pytest.mark.asyncio
    async def test_add_and_search(self, memory):
        """Test adding content and searching for it.

        Note: This test requires Graphiti 0.27+ or a Neo4j version compatible with
        Graphiti's dynamic label handling. Currently fails due to Neo4j 5.x not
        supporting SET n:$(label) syntax that Graphiti 0.26.0 generates.
        """
        pytest.skip("Blocked by Graphiti 0.26.0 bug with Neo4j 5.x dynamic labels")

    @pytest.mark.asyncio
    async def test_get_user_context(self, memory):
        """Test getting user context for clone operations.

        Note: This test also uses add() which is blocked by Graphiti 0.26.0 bug.
        Skipped to avoid cascading failures.
        """
        pytest.skip("Blocked by Graphiti 0.26.0 bug with Neo4j 5.x dynamic labels")


class TestEpisodeSourceConversion:
    """Tests for EpisodeSource conversion function.

    These tests verify that:
    1. Graphiti EpisodeType values are correctly mapped to EpisodeSource
    2. Raw source strings are converted to EpisodeSource enum
    3. Missing/invalid sources default to SYSTEM
    """

    def test_convert_episode_source_message_to_user_interaction(self):
        """Test that 'message' EpisodeType maps to USER_INTERACTION."""
        from app.graphiti.client import _convert_to_episode_source, EpisodeSource

        result = _convert_to_episode_source("message")
        assert result == EpisodeSource.USER_INTERACTION

    def test_convert_episode_source_json_to_research(self):
        """Test that 'json' EpisodeType maps to RESEARCH."""
        from app.graphiti.client import _convert_to_episode_source, EpisodeSource

        result = _convert_to_episode_source("json")
        assert result == EpisodeSource.RESEARCH

    def test_convert_episode_source_text_to_note(self):
        """Test that 'text' EpisodeType maps to NOTE."""
        from app.graphiti.client import _convert_to_episode_source, EpisodeSource

        result = _convert_to_episode_source("text")
        assert result == EpisodeSource.NOTE

    def test_convert_episode_source_email(self):
        """Test that 'email' source is preserved."""
        from app.graphiti.client import _convert_to_episode_source, EpisodeSource

        result = _convert_to_episode_source("email")
        assert result == EpisodeSource.EMAIL

    def test_convert_episode_source_calendar(self):
        """Test that 'calendar' source is preserved."""
        from app.graphiti.client import _convert_to_episode_source, EpisodeSource

        result = _convert_to_episode_source("calendar")
        assert result == EpisodeSource.CALENDAR

    def test_convert_episode_source_task(self):
        """Test that 'task' source is preserved."""
        from app.graphiti.client import _convert_to_episode_source, EpisodeSource

        result = _convert_to_episode_source("task")
        assert result == EpisodeSource.TASK

    def test_convert_episode_source_none_defaults_to_system(self):
        """Test that None source defaults to SYSTEM."""
        from app.graphiti.client import _convert_to_episode_source, EpisodeSource

        result = _convert_to_episode_source(None)
        assert result == EpisodeSource.SYSTEM

    def test_convert_episode_source_empty_string_defaults_to_system(self):
        """Test that empty string source defaults to SYSTEM."""
        from app.graphiti.client import _convert_to_episode_source, EpisodeSource

        result = _convert_to_episode_source("")
        assert result == EpisodeSource.SYSTEM

    def test_convert_episode_source_invalid_defaults_to_system(self):
        """Test that invalid source string defaults to SYSTEM."""
        from app.graphiti.client import _convert_to_episode_source, EpisodeSource

        result = _convert_to_episode_source("invalid_source")
        assert result == EpisodeSource.SYSTEM


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-x"])
