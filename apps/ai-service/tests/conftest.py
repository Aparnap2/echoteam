"""Pytest configuration and fixtures for AI service tests."""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client for testing."""
    mock = MagicMock()
    mock.generate = AsyncMock(returned_value={
        "model": "qwen2.5-coder:3b",
        "response": "Test response",
        "done": True
    })
    mock.embed = AsyncMock(return_value={
        "model": "nomic-embed-text:v1.5",
        "embeddings": [[0.1, 0.2, 0.3]],
        "done": True
    })
    return mock


@pytest.fixture
def mock_falkordb_client():
    """Mock FalkorDB client for testing."""
    mock = MagicMock()
    mock.connect = MagicMock()
    mock.query = AsyncMock(return_value=[])
    mock.close = MagicMock()
    return mock


@pytest.fixture
def mock_graphiti_client(mock_falkordb_client):
    """Mock Graphiti client for testing."""
    mock = MagicMock()
    mock.initialize = AsyncMock()
    mock.close = AsyncMock()
    mock.add_episode = AsyncMock(return_value="episode_123")
    mock.search = AsyncMock(return_value=[
        {"content": "Test result", "score": 0.9}
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
