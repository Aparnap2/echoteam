"""EchoTeam Memory Layer.

This module provides the Graphiti-based memory system for persistent,
temporal knowledge graph storage with Neo4j backend.

Modules:
- graphiti: Graphiti integration with Neo4j
"""

from app.memory.graphiti import (
    GraphitiMemory,
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
    "GraphitiMemory",
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
