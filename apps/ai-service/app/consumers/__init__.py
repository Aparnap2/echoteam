"""EchoTeam Consumers - Event Processing Workers

This module provides event consumers for processing messages from Redpanda.

Modules:
- chat_processor: RAG-enabled chat message processor
"""

from app.consumers.chat_processor import (
    ChatProcessor,
    ChatProcessorConfig,
    ChatMessage,
    RAGResult,
    get_chat_processor,
)

__all__ = [
    "ChatProcessor",
    "ChatProcessorConfig",
    "ChatMessage",
    "RAGResult",
    "get_chat_processor",
]
