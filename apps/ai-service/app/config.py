"""Configuration management for AI service."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "echoteam-ai-service"
    app_version: str = "0.1.0"
    debug: bool = False

    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model_coding: str = "qwen2.5-coder:3b"
    ollama_model_reasoning: str = "granite3.1-moe:3b"
    ollama_model_embedding: str = "nomic-embed-text:v1.5"

    # FalkorDB Configuration
    falkor_host: str = "localhost"
    falkor_port: int = 6379
    falkor_database: str = "echoteam"

    # Graphiti Configuration
    graphiti_host: str = "http://localhost:8080"

    # HITL Configuration
    confidence_threshold: float = 0.85
    auto_actions: list[str] = ["summarize", "categorize", "extract"]
    approval_actions: list[str] = ["draft", "send", "create_event"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
