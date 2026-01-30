"""EchoTeam Memory Layer - Qdrant Hybrid Search

This module provides the Qdrant-based memory system for persistent,
hybrid vector + keyword search.

Modules:
- qdrant: Qdrant integration with hybrid search (Dense + Sparse)
"""

from app.memory.qdrant import (
    QdrantMemory,
    MemoryConfig,
    MemoryOperationResult,
    SearchResult,
    UserContext,
    MemorySourceType,
    MemoryOperationStatus,
    get_memory,
    close_memory,
    close_all_memories,
)

__all__ = [
    "QdrantMemory",
    "MemoryConfig",
    "MemoryOperationResult",
    "SearchResult",
    "UserContext",
    "MemorySourceType",
    "MemoryOperationStatus",
    "get_memory",
    "close_memory",
    "close_all_memories",
]
