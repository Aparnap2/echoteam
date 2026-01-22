#!/usr/bin/env python3
"""
EchoTeam LLM Evaluation Script
Evaluates clone responses for quality, accuracy, and safety.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any
import httpx
from app.llm.ollama_client import ollama_client
from app.config import settings


class LLMEvaluator:
    """Evaluate LLM responses for quality metrics."""

    def __init__(self):
        self.results: list[dict] = []
        self.metrics = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "avg_response_time_ms": 0,
            "avg_confidence": 0,
        }

    async def evaluate_response(
        self,
        task: str,
        prompt: str,
        expected_properties: list[str],
        model: str = "qwen2.5-coder:3b"
    ) -> dict:
        """Evaluate a single LLM response."""
        self.metrics["total_tests"] += 1
        start = time.time()

        result = {
            "task": task,
            "model": model,
            "prompt": prompt,
            "timestamp": datetime.utcnow().isoformat(),
            "passed": False,
            "properties_found": [],
            "response_time_ms": 0,
            "confidence": 0,
        }

        try:
            # Generate response
            response = await ollama_client.generate(
                model=model,
                prompt=prompt,
                system="You are a helpful assistant. Respond concisely.",
                temperature=0.7,
            )

            result["response_time_ms"] = int((time.time() - start) * 1000)
            result["response"] = response

            # Check for expected properties
            for prop in expected_properties:
                if prop.lower() in response.lower():
                    result["properties_found"].append(prop)

            # Determine pass/fail
            result["passed"] = len(result["properties_found"]) >= len(expected_properties) * 0.5

            # Calculate confidence based on response characteristics
            result["confidence"] = self._calculate_confidence(response)

            if result["passed"]:
                self.metrics["passed"] += 1
            else:
                self.metrics["failed"] += 1

        except Exception as e:
            result["error"] = str(e)
            result["passed"] = False
            self.metrics["failed"] += 1

        self.results.append(result)
        return result

    def _calculate_confidence(self, response: str) -> float:
        """Calculate confidence score for response."""
        score = 0.5  # Base score

        # Length heuristic
        if 10 < len(response) < 500:
            score += 0.2

        # Contains complete sentence
        if response.strip().endswith((".", "!", "?")):
            score += 0.1

        # Not too short or too long
        words = response.split()
        if 5 < len(words) < 100:
            score += 0.1

        return min(score, 1.0)

    def generate_report(self) -> dict:
        """Generate evaluation report."""
        total = self.metrics["total_tests"]
        if total > 0:
            self.metrics["pass_rate"] = self.metrics["passed"] / total * 100
            self.metrics["avg_response_time_ms"] = sum(
                r["response_time_ms"] for r in self.results
            ) / len(self.results) if self.results else 0
            self.metrics["avg_confidence"] = sum(
                r["confidence"] for r in self.results
            ) / len(self.results) if self.results else 0

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": self.metrics,
            "results": self.results,
        }


async def run_clone_evaluations():
    """Run evaluations for all clone types."""
    evaluator = LLMEvaluator()

    # Calendar Clone evaluations
    print("Evaluating Calendar Clone...")
    await evaluator.evaluate_response(
        task="calendar_summary",
        prompt="Summarize this schedule: 9am meeting, 2pm call, 5pm gym",
        expected_properties=["time", "meeting", "schedule"],
        model=settings.ollama_model_reasoning,
    )

    await evaluator.evaluate_response(
        task="focus_block",
        prompt="Suggest a focus time block for someone with 20 unread emails",
        expected_properties=["focus", "time", "hour"],
        model=settings.ollama_model_reasoning,
    )

    # Email Clone evaluations
    print("Evaluating Email Clone...")
    await evaluator.evaluate_response(
        task="email_draft",
        prompt="Draft a professional reply to: Thanks for your email, looking forward to the meeting",
        expected_properties=["reply", "meeting", "thanks"],
        model=settings.ollama_model_coding,
    )

    await evaluator.evaluate_response(
        task="email_categorize",
        prompt="Categorize these emails: newsletter, urgent request, automated notification",
        expected_properties=["newsletter", "urgent", "automated"],
        model=settings.ollama_model_reasoning,
    )

    # Ops Clone evaluations
    print("Evaluating Ops Clone...")
    await evaluator.evaluate_response(
        task="task_suggestion",
        prompt="Suggest 3 tasks based on: client complained about delay, code review pending, docs outdated",
        expected_properties=["task", "client", "review"],
        model=settings.ollama_model_reasoning,
    )

    await evaluator.evaluate_response(
        task="priority_ordering",
        prompt="Prioritize: fix bug (affects users), write docs, refactor old code",
        expected_properties=["priority", "fix", "bug"],
        model=settings.ollama_model_reasoning,
    )

    # HITL boundary evaluations
    print("Evaluating HITL boundaries...")
    await evaluator.evaluate_response(
        task="auto_action_detection",
        prompt="This is an internal summary of my inbox. No external action needed.",
        expected_properties=["summary", "internal"],
        model=settings.ollama_model_coding,
    )

    await evaluator.evaluate_response(
        task="approval_required_detection",
        prompt="Draft an email to send to a client about their project delay",
        expected_properties=["draft", "client", "email"],
        model=settings.ollama_model_coding,
    )

    # Generate embeddings evaluation
    print("Evaluating Embeddings...")
    try:
        embedding = await ollama_client.embed(
            model=settings.ollama_model_embedding,
            text="EchoTeam is an AI-powered clone workforce"
        )
        embed_result = {
            "task": "embedding_generation",
            "passed": len(embedding) > 0,
            "embedding_dim": len(embedding),
        }
        evaluator.results.append(embed_result)
    except Exception as e:
        evaluator.results.append({
            "task": "embedding_generation",
            "passed": False,
            "error": str(e),
        })

    return evaluator.generate_report()


async def run_health_checks() -> dict:
    """Run health checks on all services."""
    checks = {}

    # Check Ollama
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags", timeout=10.0)
            checks["ollama"] = {
                "healthy": response.status_code == 200,
                "models": response.json().get("models", []) if response.status_code == 200 else [],
            }
    except Exception as e:
        checks["ollama"] = {"healthy": False, "error": str(e)}

    # Check AI Service
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health", timeout=10.0)
            checks["ai_service"] = {
                "healthy": response.status_code == 200,
                "status": response.json().get("status") if response.status_code == 200 else None,
            }
    except Exception as e:
        checks["ai_service"] = {"healthy": False, "error": str(e)}

    # Check API Server
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:3001/health", timeout=10.0)
            checks["api_server"] = {
                "healthy": response.status_code == 200,
                "status": response.json().get("status") if response.status_code == 200 else None,
            }
    except Exception as e:
        checks["api_server"] = {"healthy": False, "error": str(e)}

    return checks


async def main():
    """Main evaluation runner."""
    print("=" * 60)
    print("EchoTeam LLM Evaluation")
    print("=" * 60)

    # Health checks
    print("\n[1/3] Running Health Checks...")
    health = await run_health_checks()
    all_healthy = all(c.get("healthy", False) for c in health.values())
    print(f"Health Status: {'✓ All healthy' if all_healthy else '✗ Some services unhealthy'}")
    for service, status in health.items():
        print(f"  {service}: {'✓' if status.get('healthy') else '✗'}")

    # Run evaluations
    print("\n[2/3] Running Clone Evaluations...")
    report = await run_clone_evaluations()
    print(f"Tests: {report['metrics']['total_tests']}")
    print(f"Passed: {report['metrics']['passed']}")
    print(f"Failed: {report['metrics']['failed']}")
    print(f"Pass Rate: {report['metrics'].get('pass_rate', 0):.1f}%")
    print(f"Avg Response Time: {report['metrics'].get('avg_response_time_ms', 0)}ms")

    # Save report
    report_path = "/home/aparna/Desktop/echoteam/tests/eval/report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to: {report_path}")

    print("\n[3/3] Summary")
    print("=" * 60)
    if report["metrics"]["pass_rate"] >= 80:
        print("✓ Evaluation PASSED - Clones performing well")
    else:
        print("⚠ Evaluation NEEDS IMPROVEMENT - Check failed tests")

    return report


if __name__ == "__main__":
    asyncio.run(main())
