"""
AI Agent API Routes.

HTTP endpoints that expose AI agent tool calling functionality for frontend integration.
The frontend calls these REST endpoints, which then invoke AI agent tools internally.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel

from ..tools import (
    get_health_conversation_context,
    parse_health_file,
    query_health_metrics,
    store_health_data,
)
from ..tools.health_insights_tool import generate_health_insights
from ..utils.base import ToolResult

router = APIRouter(prefix="/agent", tags=["AI Agent"])


# Request/Response Models
class ParseHealthFileRequest(BaseModel):
    file_path: str
    anonymize: bool = True


class StoreHealthDataRequest(BaseModel):
    user_id: str
    health_data: dict[str, Any]
    ttl_days: int = 7


class QueryHealthMetricsRequest(BaseModel):
    user_id: str
    metric_types: list[str]
    days_back: int = 30


class GenerateHealthInsightsRequest(BaseModel):
    user_id: str
    focus_area: str = "overall"
    include_trends: bool = True


class AgentResponse(BaseModel):
    success: bool
    data: dict[str, Any] | None = None
    message: str
    execution_time_ms: float | None = None


@router.post("/parse-health-file", response_model=AgentResponse)
async def api_parse_health_file(request: ParseHealthFileRequest):
    """
    Parse Apple Health XML file using AI agent tools.

    This endpoint provides the same functionality as the AI agent's parse_health_file tool,
    but accessible via HTTP for frontend integration.
    """
    try:
        # Call AI agent tool
        result: ToolResult = parse_health_file(
            file_path=request.file_path, anonymize=request.anonymize
        )

        return AgentResponse(
            success=result.success,
            data=result.data,
            message=result.message,
            execution_time_ms=result.execution_time_ms,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Health file parsing failed: {str(e)}"
        )


@router.post("/store-health-data", response_model=AgentResponse)
async def api_store_health_data(request: StoreHealthDataRequest):
    """
    Store health data in Redis with TTL using AI agent tools.

    Demonstrates Redis's TTL-based short-term memory for health conversations.
    """
    try:
        # Call AI agent tool
        result: ToolResult = store_health_data(
            user_id=request.user_id,
            health_data=request.health_data,
            ttl_days=request.ttl_days,
        )

        return AgentResponse(
            success=result.success,
            data=result.data,
            message=result.message,
            execution_time_ms=result.execution_time_ms,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Health data storage failed: {str(e)}"
        )


@router.post("/query-health-metrics", response_model=AgentResponse)
async def api_query_health_metrics(request: QueryHealthMetricsRequest):
    """
    Query health metrics from Redis using AI agent tools.

    Demonstrates Redis's O(1) lookup speed vs stateless file parsing.
    """
    try:
        # Call AI agent tool
        result: ToolResult = query_health_metrics(
            user_id=request.user_id,
            metric_types=request.metric_types,
            days_back=request.days_back,
        )

        return AgentResponse(
            success=result.success,
            data=result.data,
            message=result.message,
            execution_time_ms=result.execution_time_ms,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Health metrics query failed: {str(e)}"
        )


@router.get("/health-context/{user_id}", response_model=AgentResponse)
async def api_get_health_conversation_context(
    user_id: str = Path(..., description="User ID to get health context for"),
):
    """
    Get health conversation context from Redis short-term memory.

    Shows how Redis maintains conversational context across sessions.
    """
    try:
        # Call AI agent tool
        result: ToolResult = get_health_conversation_context(user_id)

        return AgentResponse(
            success=result.success,
            data=result.data,
            message=result.message,
            execution_time_ms=result.execution_time_ms,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Health context retrieval failed: {str(e)}"
        )


@router.post("/generate-health-insights", response_model=AgentResponse)
async def api_generate_health_insights(request: GenerateHealthInsightsRequest):
    """
    Generate intelligent health insights from Redis-cached data.

    This endpoint provides AI-ready health insights with focus areas like:
    - overall: Comprehensive health analysis
    - weight: BMI and weight management insights
    - activity: Exercise and movement analysis
    - nutrition: Dietary and hydration insights
    """
    try:
        # Call AI agent tool
        result: ToolResult = generate_health_insights(
            user_id=request.user_id,
            focus_area=request.focus_area,
            include_trends=request.include_trends,
        )

        return AgentResponse(
            success=result.success,
            data=result.data,
            message=result.message,
            execution_time_ms=result.execution_time_ms,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Health insights generation failed: {str(e)}"
        )


# Demonstration endpoints for Redis vs Stateless comparison
@router.post("/demo/redis-vs-stateless")
async def demo_redis_vs_stateless(user_id: str):
    """
    Demonstration endpoint showing Redis advantages over stateless approach.

    This would typically be called by an AI agent, but exposed for demo purposes.
    """
    try:
        # This would demonstrate:
        # 1. Parse file (stateless) vs Query Redis (fast)
        # 2. TTL automatic cleanup vs manual file management
        # 3. Conversation memory persistence vs loss of context

        return {
            "demo_type": "redis_vs_stateless",
            "redis_advantages": [
                "O(1) data access vs O(n) file parsing",
                "Automatic TTL expiration (7 days)",
                "Persistent conversation context",
                "Real-time health insights",
            ],
            "stateless_limitations": [
                "Must re-parse XML for every query",
                "No conversation memory",
                "Manual cleanup required",
                "Slower response times",
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Demo failed: {str(e)}")


@router.get("/tools/available")
async def get_available_tools():
    """
    List available AI agent tools for frontend discovery.

    Helps frontend understand what AI agent capabilities are available.
    """
    from ..tools import AVAILABLE_TOOLS, get_tool_schemas

    return {
        "available_tools": AVAILABLE_TOOLS,
        "tool_schemas": get_tool_schemas(),
        "description": "AI agent tools for Redis wellness conversations",
    }


@router.get("/workflow/info")
async def get_langgraph_workflow_info():
    """
    Get information about the LangGraph-powered AI agent workflow.

    Shows the sophisticated multi-step reasoning process.
    """
    return {
        "workflow_type": "LangGraph StateGraph",
        "description": "Multi-step reasoning AI agent for health conversations",
        "nodes": [
            "analyze_query - Analyze user intent and determine actions",
            "check_health_context - Check for existing Redis health context",
            "parse_health_data - Parse Apple Health XML securely",
            "query_health_metrics - Query Redis for O(1) health lookups",
            "generate_response - Generate context-aware responses",
            "handle_error - Graceful error handling and recovery",
        ],
        "features": [
            "Intelligent query analysis and intent detection",
            "Multi-tool workflow orchestration",
            "Redis-powered conversation state management",
            "Context-aware health insights generation",
            "Automatic error recovery and fallback responses",
        ],
        "advantages": {
            "vs_simple_chat": "Sophisticated reasoning vs basic pattern matching",
            "vs_stateless": "Persistent workflow state vs ephemeral processing",
            "redis_integration": "Native Redis TTL memory vs manual state management",
        },
    }
