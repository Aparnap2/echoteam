"""Configuration management for AI service."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "echoteam-ai-service"
    app_version: str = "0.1.0"
    debug: bool = False

    # Qdrant Cloud Configuration
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None

    # Ollama Configuration (for local embedding generation)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model_coding: str = "qwen2.5-coder:3b"
    ollama_model_reasoning: str = "granite3.1-moe:3b"
    ollama_model_embedding: str = "nomic-embed-text:v1.5"

    # OpenAI Configuration (for cloud LLM - fallback)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"

    # Langfuse Observability (disabled by default until keys are provided)
    langfuse_enabled: bool = False
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None

    # HITL Configuration
    confidence_threshold: float = 0.85
    auto_actions: list[str] = ["summarize", "categorize", "extract"]
    approval_actions: list[str] = ["draft", "send", "create_event"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
