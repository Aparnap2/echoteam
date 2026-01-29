#!/usr/bin/env python
"""Chat Processor Consumer Entrypoint

Long-lived process that starts the chat processor and keeps it running.
"""
import asyncio
import signal
import sys

from app.consumers import get_chat_processor


async def run_forever():
    """Run the chat processor until stopped."""
    processor = None
    stop_event = asyncio.Event()

    def signal_handler():
        """Handle shutdown signals."""
        print("\nReceived shutdown signal, stopping...")
        stop_event.set()

    # Register signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda s, f=signal_handler: f())

    try:
        print("Starting Chat Processor Consumer...")
        processor = await get_chat_processor()
        print("Chat Processor is running. Press Ctrl+C to stop.")

        # Wait indefinitely for stop signal
        await stop_event.wait()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        if processor:
            await processor.stop()
            print("Chat Processor stopped")


if __name__ == "__main__":
    asyncio.run(run_forever())
