#!/usr/bin/env python
"""Ingest dummy chat data into Qdrant Cloud for RAG demo.

This script populates Qdrant with sample conversations so the search
actually returns results during the demo.

Usage:
    python scripts/ingest_dummy_data.py

Environment variables:
    QDRANT_URL: Qdrant Cloud URL (required)
    QDRANT_API_KEY: Qdrant Cloud API key (required)
    OLLAMA_BASE_URL: Ollama endpoint for embeddings (default: http://localhost:11434)
    EMBEDDING_MODEL: Embedding model (default: nomic-embed-text:v1.5)
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

# Add parent path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.memory import QdrantMemory, MemoryConfig, MemorySourceType


# Sample chat conversations for demo
SAMPLE_CONVERSATIONS = [
    {
        "content": "I prefer concise email replies under 3 sentences. Please keep communication brief and to the point.",
        "source": "email",
        "metadata": {"subject": "Communication preferences", "date": "2024-01-15"},
    },
    {
        "content": "The project deadline is February 28th. We need to finalize all deliverables by end of week 3.",
        "source": "calendar",
        "metadata": {"event": "Project Review", "date": "2024-01-20"},
    },
    {
        "content": "I work best in the morning. Schedule important meetings before noon if possible.",
        "source": "user_interaction",
        "metadata": {"context": "meeting preferences", "date": "2024-01-10"},
    },
    {
        "content": "Our tech stack is Python, FastAPI, Qdrant, and React. We're building an AI-powered chat system.",
        "source": "note",
        "metadata": {"project": "EchoTeam", "date": "2024-01-18"},
    },
    {
        "content": "Monthly budget for infrastructure is $500. Prefer cost-effective solutions over expensive enterprise tools.",
        "source": "research",
        "metadata": {"topic": "budget planning", "date": "2024-01-22"},
    },
    {
        "content": "I like to start the day with a quick review of pending tasks. A 15-minute morning standup works best.",
        "source": "calendar",
        "metadata": {"event": "Daily Standup", "date": "2024-01-08"},
    },
    {
        "content": "Customer feedback is important. Always include customer quotes when presenting new features.",
        "source": "email",
        "metadata": {"subject": "Product presentation guidelines", "date": "2024-01-25"},
    },
    {
        "content": "Code reviews should focus on logic and architecture first. Style issues are secondary.",
        "source": "note",
        "metadata": {"project": "Development Guidelines", "date": "2024-01-12"},
    },
    {
        "content": "The team uses Slack for quick communication and email for formal discussions.",
        "source": "user_interaction",
        "metadata": {"context": "team communication", "date": "2024-01-05"},
    },
    {
        "content": "We aim for weekly releases. Feature branches should be merged by Thursday for testing.",
        "source": "task",
        "metadata": {"sprint": "Week 4", "date": "2024-01-28"},
    },
    {
        "content": "I prefer dark mode in all applications. It reduces eye strain during long working hours.",
        "source": "user_interaction",
        "metadata": {"context": "UI preferences", "date": "2024-01-14"},
    },
    {
        "content": "Security is paramount. All API keys must be stored in environment variables, never in code.",
        "source": "note",
        "metadata": {"project": "Security Guidelines", "date": "2024-01-30"},
    },
    {
        "content": "Quarterly reviews happen in March, June, September, and December. Prepare documentation beforehand.",
        "source": "calendar",
        "metadata": {"event": "Quarterly Review Schedule", "date": "2024-02-01"},
    },
    {
        "content": "When presenting to stakeholders, focus on business value and ROI, not technical details.",
        "source": "email",
        "metadata": {"subject": "Presentation tips", "date": "2024-02-05"},
    },
    {
        "content": "The documentation is stored in Notion. Update it after any significant feature change.",
        "source": "task",
        "metadata": {"project": "Documentation", "date": "2024-02-10"},
    },
]


async def generate_embedding(text: str, endpoint: str, model: str) -> list[float]:
    """Generate embedding for text using Ollama."""
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.post(
            endpoint,
            json={"model": model, "input": text},
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()

        if "embedding" in data:
            return data["embedding"]
        elif "embeddings" in data:
            return data["embeddings"][0] if data["embeddings"] else []
        else:
            raise ValueError(f"Unexpected response format: {data}")


async def ingest_data():
    """Ingest sample conversations into Qdrant."""
    # Get configuration from environment
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    embedding_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text:v1.5")
    user_id = os.getenv("MEMORY_USER_ID", "demo_user")

    if not qdrant_url:
        print("ERROR: QDRANT_URL environment variable is required")
        print("Example: export QDRANT_URL='https://xxxxx.us-east-1.aws.cloud.qdrant.io:6333'")
        sys.exit(1)

    print(f"Connecting to Qdrant at: {qdrant_url}")
    print(f"Embedding model: {embedding_model}")
    print(f"Ollama endpoint: {ollama_base_url}")
    print("-" * 50)

    # Create memory instance
    config = MemoryConfig(
        qdrant_url=qdrant_url,
        qdrant_api_key=qdrant_api_key,
        embedding_endpoint=f"{ollama_base_url}/api/embed",
        embedding_model=embedding_model,
    )

    memory = QdrantMemory(user_id=user_id, config=config)

    try:
        await memory.initialize()
        print(f"Connected! Collection: {memory.collection}")

        # Generate embeddings and add to Qdrant
        added_count = 0
        for conv in SAMPLE_CONVERSATIONS:
            print(f"Adding: {conv['content'][:50]}...")

            # Generate embedding
            embedding = await generate_embedding(
                conv["content"],
                f"{ollama_base_url}/api/embed",
                embedding_model
            )

            # Add to memory
            result = await memory.add(
                content=conv["content"],
                metadata={
                    "source": conv["source"],
                    **conv.get("metadata", {}),
                }
            )

            if result.status.value == "success":
                added_count += 1
                print(f"  ✓ Added (status: {result.status.value})")
            else:
                print(f"  ✗ Failed: {result.error}")

        print("-" * 50)
        print(f"Successfully added {added_count}/{len(SAMPLE_CONVERSATIONS)} conversations")

        # Verify data
        print("\nVerifying data...")
        test_query = "project preferences"
        results = await memory.search(query=test_query, max_results=3)
        print(f"Search for '{test_query}' returned {len(results)} results:")
        for r in results:
            print(f"  - [{r.score:.2f}] {r.content[:60]}...")

        print("\n✓ Ingestion complete!")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await memory.close()


if __name__ == "__main__":
    print("=" * 50)
    print("EchoTeam Qdrant Data Ingestion")
    print("=" * 50)
    print()

    asyncio.run(ingest_data())
