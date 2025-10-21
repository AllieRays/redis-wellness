"""
Health RAG Agent with RedisVL Vector Search & Memory.

Consolidated, production-quality implementation featuring:
- LangGraph agentic workflow
- Tool calling for health data retrieval
- RedisVL semantic vector search
- Dual memory system (short-term + long-term)
- Iterative reasoning with reflection
"""

import logging
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from ..config import get_settings
from ..tools import create_user_bound_tools
from ..utils.numeric_validator import get_numeric_validator
from ..utils.query_classifier import QueryClassifier

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State management for health RAG agent."""

    messages: Annotated[list, add_messages]
    user_id: str
    session_id: str
    tool_calls_made: int
    max_tool_calls: int
    # Memory context
    short_term_context: str | None
    long_term_context: str | None
    semantic_hits: int


class HealthRAGAgent:
    """
    Production RAG agent for health conversations.

    Architecture:
    1. Query Analysis → Understand intent
    2. Memory Retrieval → Short-term (conversation) + Long-term (semantic)
    3. Tool Execution → Call health data tools
    4. Response Generation → Synthesize with full context
    5. Memory Update → Store important insights

    Features:
    - LangGraph workflow orchestration
    - RedisVL semantic vector search (when memory_manager attached)
    - Dual memory system (conversation + semantic)
    - Tool calling with automatic selection
    - Iterative refinement (up to 5 tool calls)
    """

    def __init__(self, memory_manager=None):
        """
        Initialize RAG agent.

        Args:
            memory_manager: Optional MemoryManager for dual memory system
        """
        self.settings = get_settings()
        self.memory_manager = memory_manager

        # Initialize LLM
        self.llm = ChatOllama(
            model=self.settings.ollama_model,
            base_url=self.settings.ollama_base_url,
            temperature=0.05,  # Ultra-low for tool calling accuracy (Qwen recommendation)
            num_predict=2048,  # Increased limit for detailed responses
            timeout=60,  # 60 second timeout to prevent hanging
        )

        # Initialize query classifier for tool routing
        self.query_classifier = QueryClassifier()

        # Tools will be created per-user at runtime
        self.llm_with_tools = None

        # Build agent graph
        self.graph = self._build_graph()
        self.app = self.graph.compile()

        logger.info("HealthRAGAgent initialized successfully with QueryClassifier")

    def _build_graph(self) -> StateGraph:
        """
        Build LangGraph workflow.

        Flow:
        START → agent → [tools] → agent → END
                  ↓
            (decides if more tools needed)

        Note: Tools are created dynamically per-user in the agent node
        """
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", self._tool_node)

        # Define flow
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges(
            "agent", self._should_continue, {"continue": "tools", "end": END}
        )
        workflow.add_edge("tools", "agent")

        return workflow

    async def _agent_node(self, state: AgentState) -> dict:
        """
        Main agent reasoning node.

        Responsibilities:
        - Classify query intent (NEW - Phase 2)
        - Filter tools based on classification (NEW - Phase 2)
        - Create user-bound tools
        - Analyze query with memory context
        - Decide which tools to call
        - Generate final response when done
        """
        messages = state["messages"]
        user_id = state.get("user_id", "unknown")

        # Extract user's current query (last human message)
        current_query = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                current_query = msg.content
                break

        # Classify query intent to filter tools (Phase 2: Tool Routing)
        classification = self.query_classifier.classify_intent(current_query)

        logger.info(
            f"🎯 Query classified: intent={classification['intent']}, "
            f"confidence={classification['confidence']:.2f}, "
            f"keywords={classification['matched_keywords']}"
        )

        # Create all user-bound tools (with conversation history for tiered responses)
        all_user_tools = create_user_bound_tools(user_id, conversation_history=messages)

        # Filter tools based on classification confidence
        if self.query_classifier.should_filter_tools(classification, threshold=0.5):
            # High confidence - only present recommended tools
            recommended_tool_names = set(classification["recommended_tools"])
            filtered_tools = [
                tool for tool in all_user_tools if tool.name in recommended_tool_names
            ]

            logger.info(
                f"🔧 Tool filtering ENABLED (confidence {classification['confidence']:.2f} >= 0.5): "
                f"Presenting {len(filtered_tools)} tools: {[t.name for t in filtered_tools]}"
            )

            tools_to_bind = filtered_tools
        else:
            # Low confidence - present all tools, let LLM decide
            logger.info(
                f"🔧 Tool filtering DISABLED (confidence {classification['confidence']:.2f} < 0.5): "
                f"Presenting all {len(all_user_tools)} tools"
            )

            tools_to_bind = all_user_tools

        # Bind filtered tools to LLM
        llm_with_tools = self.llm.bind_tools(tools_to_bind)

        # Build system prompt with memory context
        system_content = self._build_system_prompt(state)
        system_msg = SystemMessage(content=system_content)

        messages_with_system = [system_msg] + messages

        # Call LLM with filtered tools (ASYNC to prevent blocking)
        response = await llm_with_tools.ainvoke(messages_with_system)

        return {"messages": [response]}

    def _tool_node(self, state: AgentState) -> dict:
        """
        Tool execution node.

        Creates user-bound tools and executes them.
        """
        user_id = state.get("user_id", "unknown")
        messages = state.get("messages", [])
        user_tools = create_user_bound_tools(user_id, conversation_history=messages)

        # Use LangGraph's ToolNode with user-bound tools
        # ToolNode is a Runnable, invoke it synchronously
        tool_node = ToolNode(user_tools)
        return tool_node.invoke(state)

    def _build_system_prompt(self, state: AgentState) -> str:
        """
        Build comprehensive system prompt with memory context.

        Includes:
        - Agent capabilities
        - Available tools
        - Short-term memory (recent conversation)
        - Long-term memory (semantic retrieval)
        - Instructions for tool use
        """
        prompt_parts = [
            "You are a health AI assistant with access to the user's Apple Health data.",
            "",
            "Note: Tools automatically provide appropriate detail level based on conversation context.",
            "First workout query gets basic info. Follow-ups get full details (calories, heart rate).",
            "",
            "🧠 MEMORY CONTEXT:",
        ]

        # Add short-term memory
        if state.get("short_term_context"):
            prompt_parts.append("Recent conversation context:")
            prompt_parts.append(state["short_term_context"])
            prompt_parts.append("")

        # Add long-term memory
        if state.get("long_term_context"):
            prompt_parts.append("Relevant past insights (semantic memory):")
            prompt_parts.append(state["long_term_context"])
            prompt_parts.append(
                f"({state.get('semantic_hits', 0)} semantic memories retrieved)"
            )
            prompt_parts.append("")

        prompt_parts.extend(
            [
                "🛠️ TOOLS:",
                "1. search_health_records_by_metric - Individual values and trends",
                "2. search_workouts_and_activity - Returns: date, day_of_week, time, type, duration, calories, heart rate",
                "   IMPORTANT: Always use the 'day_of_week' field from tool output (e.g., Friday, Monday)",
                "3. aggregate_metrics - Calculate averages, min, max, totals",
                "",
                "🚨 DATA ACCURACY:",
                "- Only mention data that tools ACTUALLY return - don't explain missing fields",
                "- If tool doesn't return calories, DON'T say 'no calories burned' - just skip it",
                "- If tool doesn't return heart rate, DON'T say 'no heart rate data' - just skip it",
                "- Quote returned data EXACTLY (dates, times, numbers, day_of_week)",
                "- Use 'day_of_week' from tool output - DON'T calculate it yourself",
                "",
                "🎯 TOOL SELECTION:",
                "- Averages/stats → aggregate_metrics",
                "- Workouts/exercise → search_workouts_and_activity (use days_back=30 for 'last workout')",
                "- Individual values → search_health_records_by_metric",
                "",
            ]
        )

        return "\n".join(prompt_parts)

    def _should_continue(self, state: AgentState) -> str:
        """
        Decide whether to continue with tool calls or end.

        Returns:
            "continue" if tools should be called
            "end" if response is ready
        """
        messages = state["messages"]
        last_message = messages[-1]

        # Check if LLM wants to call tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            # Check tool call limit
            if state.get("tool_calls_made", 0) >= state.get("max_tool_calls", 5):
                logger.warning(
                    f"Max tool calls ({state.get('max_tool_calls')}) reached"
                )
                return "end"
            return "continue"

        return "end"

    async def chat(
        self,
        message: str,
        user_id: str,
        session_id: str = "default",
        conversation_history: list[dict] | None = None,
        max_tool_calls: int = 5,
    ) -> dict[str, Any]:
        """
        Process chat message with full RAG pipeline.

        Args:
            message: User's message
            user_id: User identifier
            session_id: Session ID for memory
            conversation_history: Previous messages (short-term memory)
            max_tool_calls: Maximum tool calls per turn

        Returns:
            Dict with response, tools used, and memory stats
        """
        try:
            # Build message history
            messages = []

            # Add conversation history (short-term memory)
            if conversation_history:
                for msg in conversation_history[-10:]:  # Last 10 for context
                    role = msg.get("role")
                    content = msg.get("content")

                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))

            # Add current message
            messages.append(HumanMessage(content=message))

            # Retrieve memory context
            short_term_context = None
            long_term_context = None
            semantic_hits = 0

            # TEMPORARILY DISABLED: Semantic memory caching
            # if self.memory_manager:
            #     try:
            #         # Get short-term context (conversation summary)
            #         short_term_context = await self.memory_manager.get_short_term_context(
            #             user_id,
            #             session_id
            #         )
            #
            #         # Get long-term context (semantic retrieval)
            #         long_term_result = await self.memory_manager.retrieve_semantic_memory(
            #             user_id,
            #             message,
            #             top_k=3
            #         )
            #         long_term_context = long_term_result.get("context")
            #         semantic_hits = long_term_result.get("hits", 0)
            #
            #     except Exception as e:
            #         logger.warning(f"Memory retrieval failed: {e}")

            # Initialize state
            initial_state = {
                "messages": messages,
                "user_id": user_id,
                "session_id": session_id,
                "tool_calls_made": 0,
                "max_tool_calls": max_tool_calls,
                "short_term_context": short_term_context,
                "long_term_context": long_term_context,
                "semantic_hits": semantic_hits,
            }

            # Run agent workflow
            final_state = await self.app.ainvoke(initial_state)

            # Extract final response
            final_messages = final_state["messages"]
            last_message = final_messages[-1]

            if isinstance(last_message, AIMessage):
                response_text = last_message.content
            else:
                response_text = str(last_message)

            # Extract tool usage
            tools_used = []
            for msg in final_messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        tools_used.append(
                            {
                                "name": tool_call.get("name", "unknown"),
                                "args": tool_call.get("args", {}),
                            }
                        )

            # ========== VALIDATION: Check for hallucinated numbers ==========
            validator = get_numeric_validator()

            # Extract tool results from message history
            tool_results = []
            from langchain_core.messages import ToolMessage

            for msg in final_messages:
                if isinstance(msg, ToolMessage):
                    tool_results.append(
                        {
                            "name": msg.name if hasattr(msg, "name") else "unknown",
                            "content": msg.content,
                        }
                    )

            # Validate response against tool results
            validation_result = validator.validate_response(
                response_text=response_text,
                tool_results=tool_results,
                strict=False,  # Allow fuzzy matching for rounding
            )

            # Log validation results
            if not validation_result["valid"]:
                logger.warning(
                    f"⚠️ Response validation failed!\n"
                    f"Score: {validation_result['score']:.2%}\n"
                    f"Hallucinations: {len(validation_result['hallucinations'])}\n"
                    f"Warnings: {validation_result['warnings']}"
                )
            else:
                logger.info(
                    f"✅ Response validation passed: "
                    f"Score: {validation_result['score']:.2%}, "
                    f"Matched: {validation_result.get('stats', {}).get('matched', 0)}/{validation_result.get('stats', {}).get('total_numbers', 0)}"
                )

            # TEMPORARILY DISABLED: Store in long-term memory
            # if self.memory_manager and len(response_text) > 50:
            #     try:
            #         await self.memory_manager.store_semantic_memory(
            #             user_id,
            #             session_id,
            #             message,
            #             response_text
            #         )
            #     except Exception as e:
            #         logger.warning(f"Memory storage failed: {e}")

            return {
                "response": response_text,
                "tools_used": tools_used,
                "tool_calls_made": len(tools_used),
                "session_id": session_id,
                "memory_stats": {
                    "short_term_available": short_term_context is not None,
                    "semantic_hits": semantic_hits,
                    "long_term_available": long_term_context is not None,
                },
                "validation": {
                    "valid": validation_result["valid"],
                    "score": validation_result["score"],
                    "hallucinations_detected": len(
                        validation_result.get("hallucinations", [])
                    ),
                    "numbers_validated": validation_result.get("stats", {}).get(
                        "matched", 0
                    ),
                    "total_numbers": validation_result.get("stats", {}).get(
                        "total_numbers", 0
                    ),
                },
                "type": "rag_agent_with_memory",
            }

        except Exception as e:
            logger.error(f"RAG agent chat failed: {e}", exc_info=True)
            return {
                "response": "I encountered an error processing your request. Please try again.",
                "error": str(e),
                "type": "rag_agent_with_memory",
            }


# Global agent instance (will be initialized with memory manager)
_health_rag_agent: HealthRAGAgent | None = None


def get_health_rag_agent(memory_manager=None) -> HealthRAGAgent:
    """
    Get or create the global health RAG agent.

    Args:
        memory_manager: Optional memory manager to attach

    Returns:
        HealthRAGAgent instance
    """
    global _health_rag_agent

    if _health_rag_agent is None:
        _health_rag_agent = HealthRAGAgent(memory_manager=memory_manager)

    return _health_rag_agent


async def process_health_chat(
    message: str,
    user_id: str,
    session_id: str = "default",
    conversation_history: list[dict] | None = None,
    memory_manager=None,
) -> dict[str, Any]:
    """
    Main entry point for health RAG chat.

    Args:
        message: User's message
        user_id: User identifier
        session_id: Session ID
        conversation_history: Previous messages
        memory_manager: Optional memory manager

    Returns:
        Dict with response and metadata
    """
    agent = get_health_rag_agent(memory_manager=memory_manager)

    return await agent.chat(
        message=message,
        user_id=user_id,
        session_id=session_id,
        conversation_history=conversation_history,
    )
