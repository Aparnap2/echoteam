"""EchoTeam Chat Processor - Redpanda Consumer with RAG

Listens to chat.events topic and triggers RAG lookup for questions.
Traces entire decision process in Langfuse.

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                   ChatProcessor                              │
    │  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
    │  │ Consume  │───►│  RAG     │───►│ Reply    │              │
    │  │ Events   │    │  Lookup  │    │ (If >    │              │
    │  └──────────┘    │ (Qdrant) │    │  0.8)    │              │
    │       │          └──────────┘    └──────────┘              │
    │       │                 │                 │                 │
    │       └─────────────────┴─────────────────┘                 │
    │                         │                                   │
    │              ┌──────────▼──────────┐                        │
    │              │    Langfuse         │                        │
    │              │    (Tracing)        │                        │
    │              └─────────────────────┘                        │
    └─────────────────────────────────────────────────────────────┘

Usage:
    from app.consumers import ChatProcessor

    processor = ChatProcessor()
    await processor.start()
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Any
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field

from app.events.redpanda import RedpandaEvents, EventsConfig, Event, EventType
from app.memory import QdrantMemory, MemoryConfig, get_memory, SearchResult

logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    """Chat message model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    room_id: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_question: bool = False


class RAGResult(BaseModel):
    """RAG lookup result."""
    query: str
    retrieved_docs: list[SearchResult]
    confidence: float
    should_reply: bool
    reply_content: Optional[str] = None


@dataclass
class ChatProcessorConfig:
    """Configuration for chat processor.

    Environment variables:
        CHAT_EVENTS_TOPIC: Topic to consume (default: chat.events)
        RAG_CONFIDENCE_THRESHOLD: Min confidence to reply (default: 0.8)
        LANGFUSE_ENABLED: Enable tracing (default: True)
        LANGFUSE_HOST: Langfuse server URL (default: http://localhost:3100)
    """
    chat_events_topic: str = "chat.events"
    rag_confidence_threshold: float = 0.8
    langfuse_enabled: bool = True
    langfuse_host: str = "http://localhost:3100"

    @classmethod
    def from_env(cls) -> "ChatProcessorConfig":
        """Create config from environment variables."""
        import os

        return cls(
            chat_events_topic=os.getenv("CHAT_EVENTS_TOPIC", "chat.events"),
            rag_confidence_threshold=float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.8")),
            langfuse_enabled=os.getenv("LANGFUSE_ENABLED", "true").lower() == "true",
            langfuse_host=os.getenv("LANGFUSE_HOST", "http://localhost:3100"),
        )


class ChatProcessor:
    """Chat processor that listens to Redpanda and triggers RAG.

    Features:
    - Consumes chat events from Redpanda
    - Detects questions (ends with ?)
    - Performs RAG lookup in Qdrant
    - Traces decisions in Langfuse
    - Posts replies if confidence > threshold
    """

    def __init__(
        self,
        config: Optional[ChatProcessorConfig] = None,
    ):
        """Initialize chat processor.

        Args:
            config: Optional configuration
        """
        self.config = config or ChatProcessorConfig()
        self._events: Optional[RedpandaEvents] = None
        self._memory: Optional[QdrantMemory] = None
        self._running = False
        self._consumer_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize processor components."""
        logger.info("Initializing ChatProcessor...")

        # Initialize events consumer
        self._events = RedpandaEvents(
            config=EventsConfig(
                redpanda_url="localhost:9092",
                consumer_group="chat-processor",
            )
        )
        await self._events.initialize()

        # Initialize memory for RAG
        self._memory = await get_memory(user_id="chat-processor")

        logger.info("ChatProcessor initialized")

    async def start(self) -> None:
        """Start consuming chat events."""
        if self._running:
            logger.warning("ChatProcessor already running")
            return

        await self.initialize()
        self._running = True

        # Start consumer in background
        self._consumer_task = asyncio.create_task(self._consume_events())

        logger.info(f"ChatProcessor started, listening to {self.config.chat_events_topic}")

    async def stop(self) -> None:
        """Stop consuming chat events."""
        self._running = False

        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass

        if self._events:
            await self._events.close()

        logger.info("ChatProcessor stopped")

    async def _consume_events(self) -> None:
        """Consume chat events from Redpanda."""
        try:
            async for event in self._events.consume_events(self.config.chat_events_topic):
                if not self._running:
                    break

                try:
                    await self._process_event(event)
                except Exception as e:
                    logger.error(f"Failed to process event: {e}")

        except asyncio.CancelledError:
            logger.info("Event consumer cancelled")
        except Exception as e:
            logger.error(f"Event consumer error: {e}")

    async def _process_event(self, event: Event) -> None:
        """Process a single chat event.

        Args:
            event: Event to process
        """
        if event.type != EventType.CLONE_ACTION:
            return

        payload = event.payload
        chat_message = payload.get("message", {})

        if not isinstance(chat_message, dict):
            return

        # Check if message is a question
        content = chat_message.get("content", "")
        if not content.endswith("?"):
            return

        logger.info(f"Detected question: {content[:50]}...")

        # Create chat message
        message = ChatMessage(
            user_id=chat_message.get("user_id", "unknown"),
            room_id=chat_message.get("room_id", "general"),
            content=content,
            is_question=True,
        )

        # Perform RAG lookup with tracing
        await self._rag_lookup(message)

    async def _rag_lookup(self, message: ChatMessage) -> RAGResult:
        """Perform RAG lookup for a chat message.

        Traces the entire decision process in Langfuse.

        Args:
            message: Chat message to look up

        Returns:
            RAGResult with lookup results
        """
        # Start Langfuse trace
        trace_id = await self._start_trace(message)

        try:
            # Step 1: Generate embedding and search Qdrant
            async with await self._span("search_qdrant", trace_id):
                results = await self._memory.search(
                    query=message.content,
                    max_results=5,
                )

            # Calculate confidence based on top result score
            confidence = results[0].score if results else 0.0

            # Step 2: Decision logic
            should_reply = confidence >= self.config.rag_confidence_threshold

            result = RAGResult(
                query=message.content,
                retrieved_docs=results,
                confidence=confidence,
                should_reply=should_reply,
            )

            # Step 3: Generate reply if confident
            if should_reply:
                async with await self._span("generate_reply", trace_id):
                    result.reply_content = await self._generate_reply(
                        message, results[0]
                    )

                # Post reply (would go to another topic)
                await self._post_reply(message, result)

            # End trace with result
            await self._end_trace(trace_id, result)

            logger.info(
                f"RAG lookup: confidence={confidence:.2f}, "
                f"should_reply={should_reply}, docs_found={len(results)}"
            )

            return result

        except Exception as e:
            await self._end_trace(trace_id, None, error=str(e))
            raise

    async def _generate_reply(
        self, message: ChatMessage, top_result: SearchResult
    ) -> str:
        """Generate a reply based on retrieved document.

        Args:
            message: Original message
            top_result: Top retrieved document

        Returns:
            Reply content
        """
        # Simple template reply - could use LLM for more sophisticated responses
        return (
            f"Similar question was asked before! "
            f"Answer: {top_result.content[:200]}..."
        )

    async def _post_reply(self, message: ChatMessage, result: RAGResult) -> None:
        """Post a reply to the chat.

        Args:
            message: Original message
            result: RAG result
        """
        reply_event = Event(
            type=EventType.CLONE_ACTION,
            user_id=message.user_id,
            payload={
                "action": "rag_reply",
                "original_message_id": message.id,
                "reply_content": result.reply_content,
                "confidence": result.confidence,
                "source_doc_id": result.retrieved_docs[0].id if result.retrieved_docs else None,
            },
        )

        await self._events.publish_event(
            topic="chat.replies",
            event=reply_event,
            key=message.room_id,
        )

        logger.info(f"Posted reply to room {message.room_id}")

    # ===== Langfuse Tracing Methods =====

    async def _start_trace(self, message: ChatMessage) -> str:
        """Start a Langfuse trace for the RAG lookup.

        Args:
            message: Chat message being processed

        Returns:
            Trace ID
        """
        trace_id = str(uuid4())

        if not self.config.langfuse_enabled:
            return trace_id

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.config.langfuse_host}/api/traces",
                    json={
                        "id": trace_id,
                        "name": "rag_lookup",
                        "input": {"query": message.content},
                        "metadata": {
                            "user_id": message.user_id,
                            "room_id": message.room_id,
                        },
                    },
                    timeout=5.0,
                )
        except Exception as e:
            logger.debug(f"Langfuse trace start failed: {e}")

        return trace_id

    async def _span(self, name: str, trace_id: str) -> "Span":
        """Create a Langfuse span.

        Args:
            name: Span name
            trace_id: Trace ID to associate with this span

        Returns:
            Span context manager
        """
        return Span(name, self.config, trace_id)

    async def _end_trace(
        self, trace_id: str, result: Optional[RAGResult], error: Optional[str] = None
    ) -> None:
        """End a Langfuse trace.

        Args:
            trace_id: Trace ID
            result: RAG result
            error: Optional error message
        """
        if not self.config.langfuse_enabled:
            return

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.config.langfuse_host}/api/traces/{trace_id}",
                    json={
                        "output": {
                            "confidence": result.confidence if result else None,
                            "should_reply": result.should_reply if result else None,
                            "docs_found": len(result.retrieved_docs) if result else 0,
                        },
                        "error": error,
                    },
                    timeout=5.0,
                )
        except Exception as e:
            logger.debug(f"Langfuse trace end failed: {e}")


class Span:
    """Langfuse span context manager."""

    def __init__(self, name: str, config: ChatProcessorConfig, trace_id: str):
        self.name = name
        self.config = config
        self.trace_id = trace_id
        self.start_time = None
        self.start_time_iso = None

    async def __aenter__(self):
        """Capture start time on entry."""
        import time

        self.start_time = time.time()
        self.start_time_iso = datetime.now(timezone.utc).isoformat()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Send span to Langfuse on exit."""
        import time

        duration_ms = (time.time() - self.start_time) * 1000

        if self.config.langfuse_enabled:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{self.config.langfuse_host}/api/spans",
                        json={
                            "traceId": self.trace_id,
                            "id": str(uuid4()),
                            "name": self.name,
                            "startTime": self.start_time_iso,
                            "endTime": datetime.now(timezone.utc).isoformat(),
                            "duration": duration_ms,
                        },
                        timeout=5.0,
                    )
            except Exception as e:
                logger.error(
                    f"Failed to send span to Langfuse: {e} "
                    f"(trace_id={self.trace_id}, name={self.name})"
                )


# Convenience function
async def get_chat_processor() -> ChatProcessor:
    """Get or create a chat processor.

    Returns:
        ChatProcessor instance
    """
    processor = ChatProcessor()
    await processor.start()
    return processor
