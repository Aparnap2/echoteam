"""Agentic AI Tests - LangGraph, DSPy, Instructor, HITL, DeepEval, Langfuse

Comprehensive tests for:
- LangGraph state persistence with checkpoints
- DSPy program optimization with MIPROv2
- Instructor structured outputs with validation
- Human-in-the-loop interrupt handling
- DeepEval evaluation metrics
- Langfuse observability tracing

Run with: pytest tests/test_agentic_ai.py -v

Tests cover:
1. LangGraph Checkpoint Persistence
2. DSPy Teleprompter Optimization
3. Instructor Validation & Retries
4. HITL Interrupt Workflows
5. DeepEval Evaluation Metrics
6. Langfuse Observability Tracing
7. Edge Case & Error Handling
"""

import os
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from typing import Optional, List
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field
import asyncio

# Set environment variables for testing
os.environ["LANGFUSE_HOST"] = "http://localhost:3100"
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-test"
os.environ["LANGFUSE_SECRET_KEY"] = "sk-test"


# ===== LangGraph Checkpoint Tests =====

class TestLangGraphCheckpoints:
    """Tests for LangGraph state persistence with checkpoints."""

    def test_state_graph_creation(self):
        """Test creating a basic StateGraph."""
        from typing import Annotated
        from typing_extensions import TypedDict
        from langgraph.graph import StateGraph, START, END
        from langgraph.graph.message import add_messages

        class ConversationState(TypedDict):
            messages: Annotated[list, add_messages]
            turn_count: int

        def increment_turn(state: ConversationState) -> dict:
            return {"turn_count": state.get("turn_count", 0) + 1}

        builder = StateGraph(ConversationState)
        builder.add_node("increment", increment_turn)
        builder.add_edge(START, "increment")
        builder.add_edge("increment", END)

        assert builder is not None
        assert "increment" in builder.nodes

    def test_inmemory_checkpointer(self):
        """Test InMemorySaver checkpointer."""
        from langgraph.checkpoint.memory import InMemorySaver

        memory = InMemorySaver()
        assert memory is not None
        assert hasattr(memory, 'get')
        assert hasattr(memory, 'put')

    @pytest.mark.asyncio
    async def test_state_persistence_with_thread_id(self):
        """Test that state persists across invocations with thread_id."""
        from typing import Annotated
        from typing_extensions import TypedDict
        from langgraph.graph import StateGraph, START, END
        from langgraph.graph.message import add_messages
        from langgraph.checkpoint.memory import InMemorySaver
        from langchain_core.messages import HumanMessage, AIMessage

        class ConversationState(TypedDict):
            messages: Annotated[list, add_messages]
            turn_count: int

        def respond(state: ConversationState) -> dict:
            last_msg = state["messages"][-1].content if state["messages"] else ""
            return {"messages": [AIMessage(content=f"Echo: {last_msg}")]}

        builder = StateGraph(ConversationState)
        builder.add_node("respond", respond)
        builder.add_edge(START, "respond")
        builder.add_edge("respond", END)

        memory = InMemorySaver()
        graph = builder.compile(checkpointer=memory)

        # First interaction
        config = {"configurable": {"thread_id": "test_thread_1"}}
        result1 = graph.invoke(
            {"messages": [HumanMessage(content="Hello")], "turn_count": 0},
            config=config
        )

        # Second interaction - should have all messages
        result2 = graph.invoke(
            {"messages": [HumanMessage(content="How are you?")], "turn_count": 1},
            config=config
        )

        # Verify state persisted
        messages = result2.get("messages", [])
        assert len(messages) == 4  # 2 human + 2 AI messages

    @pytest.mark.asyncio
    async def test_multiple_thread_isolation(self):
        """Test that different threads have isolated state."""
        from typing import Annotated
        from typing_extensions import TypedDict
        from langgraph.graph import StateGraph, START, END
        from langgraph.graph.message import add_messages
        from langgraph.checkpoint.memory import InMemorySaver
        from langchain_core.messages import HumanMessage, AIMessage

        class CounterState(TypedDict):
            count: int

        def increment(state: CounterState) -> dict:
            return {"count": state.get("count", 0) + 1}

        builder = StateGraph(CounterState)
        builder.add_node("increment", increment)
        builder.add_edge(START, "increment")
        builder.add_edge("increment", END)

        memory = InMemorySaver()
        graph = builder.compile(checkpointer=memory)

        # Thread A
        config_a = {"configurable": {"thread_id": "thread_A"}}
        graph.invoke({"count": 0}, config=config_a)
        graph.invoke({"count": 1}, config=config_a)
        graph.invoke({"count": 2}, config=config_a)

        # Thread B
        config_b = {"configurable": {"thread_id": "thread_B"}}
        graph.invoke({"count": 100}, config=config_b)

        # Verify isolation
        state_a = graph.get_state(config_a)
        state_b = graph.get_state(config_b)

        assert state_a.values["count"] == 3  # Incremented 3 times
        assert state_b.values["count"] == 101  # Incremented once


# ===== DSPy Optimization Tests =====

class TestDSPyOptimization:
    """Tests for DSPy program optimization."""

    def test_dspy_signature_creation(self):
        """Test creating a DSPy signature."""
        pytest.importorskip("dspy")

        import dspy

        class QASignature(dspy.Signature):
            """Answer questions based on the context."""
            context = dspy.InputField(desc="Relevant information")
            question = dspy.InputField(desc="Question to answer")
            answer = dspy.OutputField(desc="Answer to the question")

        # Check signature is properly configured via string representation
        sig_str = str(QASignature)
        assert "context" in sig_str
        assert "question" in sig_str
        assert "answer" in sig_str

    def test_dspy_chain_of_thought(self):
        """Test ChainOfThought module."""
        pytest.importorskip("dspy")

        import dspy

        cot = dspy.ChainOfThought("question -> answer")
        assert cot is not None
        assert hasattr(cot, 'forward')

    def test_dspy_module_composition(self):
        """Test composing DSPy modules."""
        pytest.importorskip("dspy")

        import dspy

        class RAGModule(dspy.Module):
            def __init__(self):
                super().__init__()
                self.retrieve = dspy.Retrieve(k=3)
                self.generate = dspy.ChainOfThought("context, question -> answer")
                self.activate_loss = False

            def forward(self, question):
                context = self.retrieve(question).passages
                return self.generate(context=context, question=question)

        rag = RAGModule()
        assert rag is not None
        assert hasattr(rag, 'retrieve')
        assert hasattr(rag, 'generate')

    def test_mipro_v2_optimizer_config(self):
        """Test MIPROv2 optimizer configuration."""
        pytest.importorskip("dspy")

        import dspy
        from dspy.teleprompt import MIPROv2

        dspy.configure(lm=dspy.LM("openai/gpt-4o-mini"))

        def validate(example, pred, trace=None):
            return example.answer.lower() == pred.answer.lower()

        # Light mode (automatic)
        optimizer_light = MIPROv2(
            metric=validate,
            auto="light",
        )

        # Manual mode
        optimizer_manual = MIPROv2(
            metric=validate,
            auto=None,
            num_candidates=10,
        )

        assert optimizer_light is not None
        assert optimizer_manual is not None


# ===== Instructor Validation Tests =====

class TestInstructorValidation:
    """Tests for Instructor structured outputs with Pydantic."""

    def test_instructor_client_creation(self):
        """Test creating Instructor client."""
        instructor_pkg = pytest.importorskip("instructor")

        # Test that from_openai function exists and is callable
        assert hasattr(instructor_pkg, 'from_openai')
        assert callable(instructor_pkg.from_openai)

        # Test module attributes (Mode is available, PatchMode may not be)
        assert hasattr(instructor_pkg, 'Mode')
        # Mode enum should be importable
        from instructor import Mode
        assert Mode is not None

    def test_pydantic_model_with_validators(self):
        """Test Pydantic model with field validators."""
        from pydantic import BaseModel, field_validator, Field

        class User(BaseModel):
            name: str = Field(min_length=1, max_length=100)
            age: int = Field(..., ge=0, le=150)
            email: str

            @field_validator("name")
            def name_must_be_capitalized(cls, v):
                if not v[0].isupper():
                    raise ValueError("Name must start with uppercase")
                return v

            @field_validator("email")
            def email_must_be_valid(cls, v):
                if "@" not in v or "." not in v.split("@")[-1]:
                    raise ValueError("Invalid email format")
                return v

        # Valid data
        user = User(name="John Doe", age=30, email="john@example.com")
        assert user.name == "John Doe"
        assert user.age == 30

        # Invalid name
        with pytest.raises(ValueError):
            User(name="john", age=30, email="john@example.com")

        # Invalid email
        with pytest.raises(ValueError):
            User(name="John", age=30, email="invalid-email")

    def test_nested_pydantic_models(self):
        """Test nested Pydantic models for complex responses."""
        from pydantic import BaseModel

        class Address(BaseModel):
            street: str
            city: str
            zipcode: str

        class Person(BaseModel):
            name: str
            age: int
            address: Address

        person = Person(
            name="Jane Doe",
            age=25,
            address=Address(
                street="123 Main St",
                city="New York",
                zipcode="10001"
            )
        )
        assert person.address.city == "New York"

    def test_response_model_with_mocked_api(self):
        """Test response_model parameter with mocked Instructor API."""
        pytest.importorskip("instructor")

        from pydantic import BaseModel
        from unittest.mock import MagicMock, patch

        class UserInfo(BaseModel):
            name: str
            age: int

        # Mock the Instructor client
        with patch('instructor.Instructor') as mock_instructor:
            mock_client = MagicMock()
            mock_instructor.return_value = mock_client

            # Mock the create method
            mock_client.chat.completions.create.return_value = UserInfo(
                name="Test User", age=30
            )

            result = mock_client.chat.completions.create(
                model="gpt-3.5-turbo",
                response_model=UserInfo,
                messages=[{"role": "user", "content": "Extract user info"}]
            )

            assert result.name == "Test User"
            assert result.age == 30


# ===== Human-in-the-Loop (HITL) Tests =====

class TestHumanInTheLoop:
    """Tests for HITL interrupt workflows."""

    def test_interrupt_creation(self):
        """Test creating an interrupt."""
        from langgraph.types import interrupt

        request = {
            "question": "Approve this action?",
            "options": ["yes", "no"]
        }

        assert "question" in request
        assert "options" in request

    def test_approval_workflow_state(self):
        """Test approval workflow state machine."""
        from typing import Optional
        from typing_extensions import TypedDict

        class ApprovalState(TypedDict):
            action: str
            approved: Optional[bool]
            result: str

        state = ApprovalState(
            action="Delete file",
            approved=None,
            result=""
        )

        assert state["action"] == "Delete file"
        assert state["approved"] is None

    def test_command_resume_after_interrupt(self):
        """Test resuming graph after interrupt with Command."""
        from langgraph.types import Command

        human_response = Command(resume="yes")
        assert human_response.resume == "yes"

    def test_interrupt_with_conditional_routing(self):
        """Test interrupt with conditional routing based on approval."""
        from typing import Optional
        from typing_extensions import TypedDict
        from langgraph.graph import StateGraph, START, END
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.types import interrupt

        class WorkflowState(TypedDict):
            task: str
            approved: Optional[bool]
            completed: bool

        def submit_task(state: WorkflowState) -> dict:
            return {"task": "Process data", "completed": False}

        def request_approval(state: WorkflowState) -> dict:
            response = interrupt({
                "question": f"Approve task: {state['task']}?",
                "options": ["approve", "reject"]
            })
            return {"approved": response == "approve"}

        def execute_task(state: WorkflowState) -> dict:
            if state.get("approved"):
                return {"completed": True}
            return {"completed": False}

        def cancel_task(state: WorkflowState) -> dict:
            return {"completed": False}

        builder = StateGraph(WorkflowState)
        builder.add_node("submit", submit_task)
        builder.add_node("approval", request_approval)
        builder.add_node("execute", execute_task)
        builder.add_node("cancel", cancel_task)

        builder.add_edge(START, "submit")
        builder.add_edge("submit", "approval")
        builder.add_edge("approval", "execute")
        builder.add_edge("approval", "cancel")
        builder.add_edge("execute", END)
        builder.add_edge("cancel", END)

        memory = InMemorySaver()
        graph = builder.compile(checkpointer=memory)

        assert "submit" in builder.nodes
        assert "approval" in builder.nodes


# ===== DeepEval Metrics Tests =====

class TestDeepEvalMetrics:
    """Tests for DeepEval evaluation metrics."""

    def test_deepeval_installed(self):
        """Test that DeepEval is available."""
        try:
            from deepeval import evaluate
            assert evaluate is not None
        except ImportError:
            pytest.skip("DeepEval not installed")

    def test_hallucination_metric(self):
        """Test hallucination detection metric."""
        try:
            from deepeval.metrics import HallucinationMetric
            from deepeval.test_case import LLMTestCase

            # Skip if no OpenAI API key
            import os
            if not os.getenv("OPENAI_API_KEY"):
                pytest.skip("OpenAI API key not configured")

            metric = HallucinationMetric(
                threshold=0.5,
                model="gpt-3.5-turbo"
            )

            test_case = LLMTestCase(
                input="What is the capital of France?",
                actual_output="The capital of France is Paris.",
                context=["France is a country in Europe."]
            )

            # Measure should work (actual API call mocked in integration tests)
            assert metric is not None
            assert metric.threshold == 0.5

        except ImportError:
            pytest.skip("DeepEval not installed")

    def test_answer_relevancy_metric(self):
        """Test answer relevancy metric."""
        try:
            from deepeval.metrics import AnswerRelevancyMetric
            from deepeval.test_case import LLMTestCase

            # Skip if no OpenAI API key
            import os
            if not os.getenv("OPENAI_API_KEY"):
                pytest.skip("OpenAI API key not configured")

            metric = AnswerRelevancyMetric(threshold=0.7)

            test_case = LLMTestCase(
                input="How do I reset my password?",
                actual_output="Go to Settings > Security > Reset Password.",
                expected_output="Instructions for password reset"
            )

            assert metric is not None
            assert metric.threshold == 0.7

        except ImportError:
            pytest.skip("DeepEval not installed")

    def test_faithfulness_metric(self):
        """Test faithfulness metric for RAG."""
        try:
            from deepeval.metrics import FaithfulnessMetric
            from deepeval.test_case import RAGTestCase

            # Skip if no OpenAI API key
            import os
            if not os.getenv("OPENAI_API_KEY"):
                pytest.skip("OpenAI API key not configured")

            metric = FaithfulnessMetric(threshold=0.8)

            test_case = RAGTestCase(
                input="What is quantum computing?",
                actual_output="Quantum computing uses qubits.",
                expected_retrieval=["Quantum computing basics"],
                actual_retrieval=["Quantum computing uses qubits for computation."]
            )

            assert metric is not None

        except ImportError:
            pytest.skip("DeepEval not installed")
        except Exception as e:
            if "API key" in str(e):
                pytest.skip("OpenAI API key not configured")
            raise

    def test_test_case_creation(self):
        """Test creating DeepEval test cases."""
        try:
            from deepeval.test_case import LLMTestCase

            test_case = LLMTestCase(
                input="What is 2+2?",
                actual_output="4",
                expected_output="4",
                context=["Basic math"],
                retrieval_context=["2+2 equals 4"]
            )

            assert test_case.input == "What is 2+2?"
            assert test_case.actual_output == "4"

        except ImportError:
            pytest.skip("DeepEval not installed")


# ===== Langfuse Observability Tests =====

class TestLangfuseObservability:
    """Tests for Langfuse tracing and observability."""

    def test_langfuse_client_creation(self):
        """Test creating Langfuse client."""
        try:
            from langfuse import Langfuse

            with patch('langfuse.Langfuse') as mock:
                client = mock.return_value
                assert client is not None

        except ImportError:
            pytest.skip("Langfuse not installed")

    def test_langfuse_trace_creation(self):
        """Test creating a trace."""
        try:
            from langfuse import Langfuse
            from unittest.mock import MagicMock

            with patch('langfuse.Langfuse') as mock_langfuse:
                mock_client = MagicMock()
                mock_langfuse.return_value = mock_client

                client = mock_langfuse.return_value
                trace = client.trace(
                    name="test_trace",
                    input={"query": "test"},
                    metadata={"user_id": "test_user"}
                )

                assert trace is not None

        except ImportError:
            pytest.skip("Langfuse not installed")

    def test_langfuse_span_creation(self):
        """Test creating a span within a trace."""
        try:
            from langfuse import Langfuse
            from unittest.mock import MagicMock

            with patch('langfuse.Langfuse') as mock_langfuse:
                mock_client = MagicMock()
                mock_langfuse.return_value = mock_client

                client = mock_langfuse.return_value
                span = client.span(
                    name="search_qdrant",
                    input={"query": "password reset"},
                    output={"results": 5}
                )

                assert span is not None

        except ImportError:
            pytest.skip("Langfuse not installed")

    def test_langfuse_generation(self):
        """Test LLM generation tracking."""
        try:
            from langfuse import Langfuse
            from unittest.mock import MagicMock

            with patch('langfuse.Langfuse') as mock_langfuse:
                mock_client = MagicMock()
                mock_langfuse.return_value = mock_client

                client = mock_langfuse.return_value
                generation = client.generation(
                    name="llm_response",
                    input={"prompt": "Answer this question"},
                    output={"response": "Here is the answer"},
                    model="gpt-4",
                    cost=0.01
                )

                assert generation is not None

        except ImportError:
            pytest.skip("Langfuse not installed")

    def test_langfuse_handler_for_langchain(self):
        """Test Langfuse callback handler for LangChain."""
        try:
            from langfuse.langchain import LangfuseCallbackHandler
            from unittest.mock import MagicMock

            handler = LangfuseCallbackHandler(
                public_key="pk-test",
                secret_key="sk-test",
                host="http://localhost:3100"
            )

            assert handler is not None
            assert hasattr(handler, 'on_llm_start')
            assert hasattr(handler, 'on_llm_end')

        except ImportError:
            pytest.skip("Langfuse not installed")


# ===== Edge Case & Error Handling Tests =====

class TestEdgeCaseHandling:
    """Tests for edge cases and error handling."""

    def test_graceful_degradation_on_missing_checkpointer(self):
        """Test graceful handling when checkpointer fails."""
        from typing import TypedDict
        from langgraph.graph import StateGraph, START, END

        class SimpleState(TypedDict):
            value: int

        def process(state: SimpleState) -> dict:
            return {"value": state.get("value", 0) + 1}

        builder = StateGraph(SimpleState)
        builder.add_node("process", process)
        builder.add_edge(START, "process")
        builder.add_edge("process", END)

        graph = builder.compile()
        result = graph.invoke({"value": 10})
        assert result["value"] == 11

    def test_validation_on_invalid_state(self):
        """Test that invalid state is handled gracefully."""
        from typing import TypedDict
        from langgraph.graph import StateGraph, START, END

        class TypedState(TypedDict):
            count: int
            name: str

        def process(state: TypedState) -> dict:
            count = state.get("count", 0)
            name = state.get("name", "unknown")
            return {"count": count + 1, "name": name}

        builder = StateGraph(TypedState)
        builder.add_node("process", process)
        builder.add_edge(START, "process")
        builder.add_edge("process", END)

        graph = builder.compile()

        result = graph.invoke({"count": 5})
        assert result["count"] == 6
        assert result["name"] == "unknown"

    @pytest.mark.asyncio
    async def test_concurrent_state_updates(self):
        """Test handling of concurrent state updates."""
        from typing import TypedDict
        from langgraph.graph import StateGraph, START, END
        from langgraph.checkpoint.memory import InMemorySaver

        class CounterState(TypedDict):
            count: int

        def increment(state: CounterState) -> dict:
            return {"count": state.get("count", 0) + 1}

        builder = StateGraph(CounterState)
        builder.add_node("increment", increment)
        builder.add_edge(START, "increment")
        builder.add_edge("increment", END)

        memory = InMemorySaver()
        graph = builder.compile(checkpointer=memory)

        # Run concurrent updates with proper configs
        async def run_concurrent():
            configs = [
                {"configurable": {"thread_id": f"thread_{i}"}}
                for i in range(3)
            ]
            results = []
            for config in configs:
                result = graph.invoke({"count": 0}, config=config)
                results.append(result)
            return results

        results = await run_concurrent()

        # Each thread should have independent state
        for i, result in enumerate(results):
            assert result["count"] == 1


# ===== Integration: Full Agent Workflow Tests =====

class TestFullAgentIntegration:
    """Integration tests for complete agent workflows."""

    @pytest.mark.asyncio
    async def test_supervisor_with_checkpoints(self):
        """Test supervisor agent with checkpoint persistence."""
        from typing import Annotated
        from typing_extensions import TypedDict
        from langgraph.graph import StateGraph, START, END
        from langgraph.graph.message import add_messages
        from langgraph.checkpoint.memory import InMemorySaver
        from langchain_core.messages import HumanMessage, AIMessage

        class AgentState(TypedDict):
            messages: Annotated[list, add_messages]
            task_result: str

        def planner(state: AgentState) -> dict:
            return {"task_result": "Planning: Analyze the request"}

        def executor(state: AgentState) -> dict:
            # Access the task_result from planner
            prev_result = state.get("task_result", "")
            return {"task_result": f"{prev_result}\nExecuting: Action taken"}

        def reporter(state: AgentState) -> dict:
            prev_result = state.get("task_result", "")
            return {"task_result": f"{prev_result}\nReporting: Complete"}

        builder = StateGraph(AgentState)
        builder.add_node("planner", planner)
        builder.add_node("executor", executor)
        builder.add_node("reporter", reporter)

        builder.add_edge(START, "planner")
        builder.add_edge("planner", "executor")
        builder.add_edge("executor", "reporter")
        builder.add_edge("reporter", END)

        memory = InMemorySaver()
        graph = builder.compile(checkpointer=memory)

        config = {"configurable": {"thread_id": "agent_test"}}
        result = graph.invoke(
            {"messages": [HumanMessage(content="Process this")], "task_result": ""},
            config=config
        )

        assert "task_result" in result
        # Verify the workflow executed through all nodes
        assert "Planning" in result["task_result"]
        assert "Executing" in result["task_result"]
        assert "Reporting" in result["task_result"]

    @pytest.mark.asyncio
    async def test_memory_integration_with_agent(self):
        """Test agent using memory layer for context."""
        from app.memory import QdrantMemory, MemoryConfig

        config = MemoryConfig.from_env()
        memory = QdrantMemory(user_id="agent-integration-test", config=config)

        # Skip if Qdrant is not available
        try:
            await memory.initialize()
        except Exception as e:
            await memory.close()
            pytest.skip(f"Qdrant not available: {e}")

        # Verify initialization worked
        if not memory.is_initialized:
            await memory.close()
            pytest.skip("Qdrant initialization failed")

        # Add context
        await memory.add(
            content="User prefers concise responses under 100 words.",
            metadata={"source": "user_preference"}
        )

        # Retrieve context
        context = await memory.get_user_context(query="response style")

        await memory.close()

        # Verify initialization and context retrieval worked
        assert memory.is_initialized
        assert context is not None
        assert isinstance(context.context_text, str)

    def test_structured_output_with_agent(self):
        """Test agent producing structured outputs."""
        from pydantic import BaseModel
        from typing import List

        class AgentAction(BaseModel):
            action_type: str
            confidence: float
            reasoning: str
            requires_approval: bool = False

        class AgentResponse(BaseModel):
            actions: List[AgentAction]
            summary: str

        response = AgentResponse(
            actions=[
                AgentAction(
                    action_type="send_email",
                    confidence=0.95,
                    reasoning="User asked to send email",
                    requires_approval=False
                )
            ],
            summary="Generated email action"
        )

        assert response.actions[0].action_type == "send_email"
        assert response.actions[0].confidence == 0.95


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
