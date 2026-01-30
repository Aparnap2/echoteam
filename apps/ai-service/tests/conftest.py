"""Pytest configuration and fixtures for AI service tests."""

# Set environment variables BEFORE any imports that use Graphiti
import os

# Neo4j configuration
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USER"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "echoteam123"

# LLM configuration for Ollama
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["LLM_MODEL"] = "granite3.1-moe:3b"
os.environ["LLM_ENDPOINT"] = "http://localhost:11434"
os.environ["LLM_API_KEY"] = "ollama"

# Embedding configuration for Ollama
os.environ["EMBEDDING_MODEL"] = "nomic-embed-text:v1.5"
os.environ["EMBEDDING_ENDPOINT"] = "http://localhost:11434/api/embed"
os.environ["EMBEDDING_DIMENSIONS"] = "768"

# Qdrant configuration
os.environ["QDRANT_URL"] = "http://localhost:6333"

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch


def pytest_configure(config):
    """Configure pytest to skip integration tests by default."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring external service"
    )


def pytest_collection_modifyitems(session, config, items):
    """Skip integration tests unless --integration flag is provided."""
    if not config.getoption("--integration", default=False):
        skip_marker = pytest.mark.skip(reason="Run with --integration to execute")
        for item in items:
            if item.get_closest_marker("integration"):
                item.add_marker(skip_marker)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_graphiti_client():
    """Mock Graphiti client for testing."""
    mock = MagicMock()
    mock.initialize = AsyncMock()
    mock.close = AsyncMock()
    mock.add_episode = AsyncMock(return_value="episode_123")
    mock.search = AsyncMock(return_value=[
        {"content": "Test result", "score": 0.9, "metadata": {}}
    ])
    return mock


@pytest.fixture
def sample_user_context():
    """Sample user context for testing."""
    return {
        "user_id": "user_123",
        "email": "test@example.com",
        "timezone": "America/New_York",
        "integrations": {
            "gmail": True,
            "calendar": True,
            "notion": False
        }
    }


@pytest.fixture
def sample_clone_config():
    """Sample clone configuration for testing."""
    return {
        "type": "calendar",
        "name": "My Calendar Clone",
        "settings": {
            "auto_create_focus_blocks": True,
            "meeting_buffer_minutes": 10,
            "confidence_threshold": 0.85
        },
        "enabled": True
    }
