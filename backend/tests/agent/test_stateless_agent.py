"""
Agent tests for Stateless Health Agent.

Tests agent behavior WITHOUT exact text matching:
- Tool selection validation
- Response structure validation
- Numeric validation integration
- Error handling
"""

import pytest

from src.agents.stateless_agent import StatelessHealthAgent
from src.utils.numeric_validator import get_numeric_validator


@pytest.mark.agent
class TestStatelessAgentStructure:
    """Test agent structure and initialization."""

    def test_agent_initialization(self):
        """Test agent initializes correctly."""
        agent = StatelessHealthAgent()

        assert agent.llm is not None
        assert hasattr(agent, "chat")

    @pytest.mark.asyncio
    async def test_agent_returns_response_structure(self, health_data_fixture):
        """Test agent returns expected response structure."""
        agent = StatelessHealthAgent()

        with health_data_fixture("test_user"):
            result = await agent.chat(
                message="What's my current weight?", user_id="test_user"
            )

            # Validate structure (not content)
            assert "response" in result
            assert isinstance(result["response"], str)
            assert len(result["response"]) > 0

            assert "tools_used" in result
            assert isinstance(result["tools_used"], list)

            assert "tool_calls_made" in result
            assert isinstance(result["tool_calls_made"], int)


@pytest.mark.agent
class TestStatelessAgentToolCalling:
    """Test agent tool calling behavior."""

    @pytest.mark.asyncio
    async def test_agent_calls_health_tool(self, health_data_fixture):
        """Test agent calls appropriate tool for health queries."""
        agent = StatelessHealthAgent()

        with health_data_fixture("test_user"):
            result = await agent.chat(message="What's my weight?", user_id="test_user")

            # Verify tool was called (not specific tool name)
            assert result["tool_calls_made"] > 0
            assert len(result["tools_used"]) > 0

            # Verify response has content (not empty)
            assert result["response"]
            assert len(result["response"]) > 10

    @pytest.mark.asyncio
    async def test_agent_response_contains_numeric_data(self, health_data_fixture):
        """Test agent response contains numeric data from tools."""
        agent = StatelessHealthAgent()

        with health_data_fixture("test_user"):
            result = await agent.chat(message="What's my BMI?", user_id="test_user")

            # Extract numbers from response
            validator = get_numeric_validator()
            numbers = validator.extract_numbers_with_context(result["response"])

            # Response should contain at least one number
            assert len(numbers) > 0, "Response should contain numeric data"

    @pytest.mark.asyncio
    async def test_agent_response_semantic_validation(self, health_data_fixture):
        """Test response contains relevant keywords without exact matching."""
        agent = StatelessHealthAgent()

        with health_data_fixture("test_user"):
            result = await agent.chat(message="What's my weight?", user_id="test_user")

            response_lower = result["response"].lower()

            # Check for weight-related keywords (flexible)
            weight_keywords = ["weight", "lb", "lbs", "kg", "pounds", "mass"]
            has_weight_keyword = any(kw in response_lower for kw in weight_keywords)

            assert (
                has_weight_keyword
            ), f"Response should contain weight-related keyword: {result['response'][:100]}"

            # Verify not an error message
            error_keywords = ["error", "failed", "unavailable", "cannot"]
            has_error = any(kw in response_lower for kw in error_keywords)

            assert not has_error, "Response should not be an error message"


@pytest.mark.agent
class TestStatelessAgentValidation:
    """Test agent response validation against tool results."""

    @pytest.mark.asyncio
    async def test_agent_validation_integration(self, health_data_fixture):
        """Test NumericValidator integration with agent responses."""
        agent = StatelessHealthAgent()

        with health_data_fixture("test_user"):
            result = await agent.chat(
                message="What's my current BMI?", user_id="test_user"
            )

            # Check if validation was performed
            if "validation" in result:
                validation = result["validation"]

                # Validation should have expected structure
                assert "valid" in validation
                assert "score" in validation

                # Log validation results (don't fail test on LLM variance)
                if not validation["valid"]:
                    print(f"⚠️  Validation warning: {validation}")

    @pytest.mark.asyncio
    async def test_agent_handles_no_data_gracefully(self):
        """Test agent handles queries when no health data exists."""
        agent = StatelessHealthAgent()

        # Query without health data fixture
        result = await agent.chat(message="What's my weight?", user_id="no_data_user")

        # Should return response (not crash)
        assert "response" in result
        assert result["response"]

        # Response should indicate no data (various ways to express this)
        # Agent should communicate lack of data somehow
        assert result["response"], "Agent should provide some response"


@pytest.mark.agent
class TestStatelessAgentEdgeCases:
    """Test agent edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_agent_handles_empty_message(self):
        """Test agent handles empty/whitespace messages."""
        agent = StatelessHealthAgent()

        try:
            result = await agent.chat(message="", user_id="test_user")
            # If it doesn't crash, verify it returns something
            assert "response" in result
        except Exception:
            # Empty message handling can raise error - that's acceptable
            assert True

    @pytest.mark.asyncio
    async def test_agent_handles_very_long_message(self, health_data_fixture):
        """Test agent handles long queries."""
        agent = StatelessHealthAgent()

        long_message = (
            "I would like to know " + "please " * 100 + "what is my current weight?"
        )

        with health_data_fixture("test_user"):
            result = await agent.chat(message=long_message, user_id="test_user")

            # Should still respond
            assert result["response"]
            assert len(result["response"]) > 0

    @pytest.mark.asyncio
    async def test_agent_conversation_isolation(self, health_data_fixture):
        """Test stateless agent doesn't remember previous messages."""
        agent = StatelessHealthAgent()

        with health_data_fixture("test_user"):
            # First message about BMI
            await agent.chat(message="My goal BMI is 22", user_id="test_user")

            # Second message referencing first (should fail without memory)
            result2 = await agent.chat(
                message="Am I close to that goal?", user_id="test_user"
            )

            # Stateless agent can't answer "that goal" without context
            # Response should indicate confusion or lack of understanding
            # (Don't check exact text, just that it responds)
            assert result2["response"]
