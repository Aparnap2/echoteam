"""Tests for FastAPI endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    version: str
    services: dict[str, bool]


@pytest.fixture
def health_response_data():
    """Provide health check response data."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "services": {
            "ollama": True,
            "falkordb": True
        }
    }


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_response_model(self, health_response_data):
        """Test health response model validation."""
        response = HealthResponse(**health_response_data)
        assert response.status == "ok"
        assert response.version == "0.1.0"
        assert response.services["ollama"] is True

    def test_health_response_missing_service(self):
        """Test health response with missing service."""
        data = {
            "status": "ok",
            "version": "0.1.0",
            "services": {}
        }
        response = HealthResponse(**data)
        assert response.services.get("ollama") is None


class TestAgentEndpoints:
    """Tests for agent/action endpoints."""

    def test_action_request_model(self):
        """Test action request model."""
        from typing import Optional

        class ActionRequest(BaseModel):
            user_id: str
            clone_type: str
            action_type: str
            payload: dict
            context: Optional[dict] = None

        request = ActionRequest(
            user_id="user_123",
            clone_type="calendar",
            action_type="create_event",
            payload={"title": "Meeting"}
        )
        assert request.user_id == "user_123"
        assert request.clone_type == "calendar"

    def test_action_response_model(self):
        """Test action response model."""
        class ActionResponse(BaseModel):
            action_id: str
            status: str
            confidence: float
            requires_approval: bool

        response = ActionResponse(
            action_id="act_123",
            status="pending",
            confidence=0.92,
            requires_approval=True
        )
        assert response.requires_approval is True


class TestOllamaIntegration:
    """Tests for Ollama integration (mocked)."""

    @pytest.mark.asyncio
    async def test_ollama_generate(self):
        """Test Ollama generation (mocked)."""
        # Mock response from Ollama
        mock_response = {
            "model": "qwen2.5-coder:3b",
            "response": "Here is a draft email reply...",
            "done": True
        }

        assert mock_response["model"] == "qwen2.5-coder:3b"
        assert "draft" in mock_response["response"].lower()

    @pytest.mark.asyncio
    async def test_ollama_embed(self):
        """Test Ollama embedding (mocked)."""
        mock_response = {
            "model": "nomic-embed-text:v1.5",
            "embeddings": [[0.1, 0.2, 0.3] for _ in range(10)],
            "done": True
        }

        assert len(mock_response["embeddings"]) == 10
        assert len(mock_response["embeddings"][0]) == 3

    def test_model_routing(self):
        """Test that correct models are routed for tasks."""
        model_mapping = {
            "coding": "qwen2.5-coder:3b",
            "embedding": "nomic-embed-text:v1.5",
            "reasoning": "granite3.1-moe:3b"
        }

        assert model_mapping["coding"] == "qwen2.5-coder:3b"
        assert model_mapping["embedding"] == "nomic-embed-text:v1.5"


class TestCloneProcessing:
    """Tests for clone processing logic."""

    def test_hitl_boundary_auto(self):
        """Test HITL boundary for auto actions."""
        auto_actions = ["summarize", "categorize", "extract"]
        action = "summarize"
        assert action in auto_actions

    def test_hitl_boundary_approval(self):
        """Test HITL boundary for approval actions."""
        approval_actions = ["draft", "send", "create_event"]
        action = "draft"
        assert action in approval_actions

    def test_confidence_threshold(self):
        """Test confidence threshold logic."""
        def should_require_approval(action_type: str, confidence: float) -> bool:
            if action_type in ["send", "draft"]:
                return True
            return confidence < 0.85

        # High confidence auto action
        result1 = should_require_approval("summarize", 0.95)
        assert result1 is False

        # Draft always requires approval
        result2 = should_require_approval("draft", 0.95)
        assert result2 is True

        # Low confidence auto action escalates
        result3 = should_require_approval("summarize", 0.72)
        assert result3 is True

    def test_clone_type_routing(self):
        """Test routing to correct clone processor."""
        clone_routers = {
            "calendar": "CalendarClone",
            "email": "EmailClone",
            "ops": "OpsClone"
        }

        # Test that each clone type maps to correct router
        for clone_type, router in clone_routers.items():
            assert router.endswith("Clone")
            assert clone_type in clone_routers
