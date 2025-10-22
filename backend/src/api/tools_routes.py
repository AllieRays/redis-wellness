"""
Apple Health Tools API - Direct HTTP Access to Individual Apple Health Tools

Provides REST endpoints for direct access to Apple Health tools:
- Parse Apple Health XML exports
- Query Apple Health metrics from Redis
- Generate Apple Health insights
- Store Apple Health data

Purpose: Direct tool access for testing/debugging, not for main chat flow.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..apple_health import (  # From processors.py
    generate_health_insights,
    parse_health_file,
)
from ..services.redis_apple_health_manager import (
    query_health_metrics,
    store_health_data,
)
from ..utils.base import ToolResult

router = APIRouter(prefix="/tools", tags=["Apple Health Tools"])


# ========== Request Models ==========


class ParseHealthFileRequest(BaseModel):
    file_path: str
    anonymize: bool = True


class StoreHealthDataRequest(BaseModel):
    user_id: str
    health_data: dict[str, Any]
    ttl_days: int = 210


class QueryHealthMetricsRequest(BaseModel):
    user_id: str
    metric_types: list[str]
    days_back: int = 30


class GenerateHealthInsightsRequest(BaseModel):
    user_id: str
    focus_area: str = "overall"
    include_trends: bool = True


# ========== Response Models ==========


class ToolResponse(BaseModel):
    """Standard response for all Apple Health tools."""

    success: bool
    data: dict[str, Any] | None = None
    message: str
    execution_time_ms: float | None = None


# ========== Helper Function ==========


def create_tool_response(result: ToolResult) -> ToolResponse:
    """Convert ToolResult to HTTP response."""
    return ToolResponse(
        success=result.success,
        data=result.data,
        message=result.message,
        execution_time_ms=result.execution_time_ms,
    )


# ========== Tool Endpoints ==========


@router.post("/parse-health-file", response_model=ToolResponse)
async def parse_health_file_endpoint(request: ParseHealthFileRequest):
    """
    Parse Apple Health XML export file.

    Direct HTTP access to the Apple Health XML parsing tool.
    """
    try:
        result: ToolResult = parse_health_file(
            file_path=request.file_path, anonymize=request.anonymize
        )
        return create_tool_response(result)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Apple Health file parsing failed: {str(e)}"
        ) from e


@router.post("/store-health-data", response_model=ToolResponse)
async def store_health_data_endpoint(request: StoreHealthDataRequest):
    """
    Store Apple Health data in Redis with TTL.

    Direct HTTP access to the Apple Health data storage tool.
    """
    try:
        result: ToolResult = store_health_data(
            user_id=request.user_id,
            health_data=request.health_data,
            ttl_days=request.ttl_days,
        )
        return create_tool_response(result)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Apple Health data storage failed: {str(e)}"
        ) from e


@router.post("/query-health-metrics", response_model=ToolResponse)
async def query_health_metrics_endpoint(request: QueryHealthMetricsRequest):
    """
    Query Apple Health metrics from Redis.

    Direct HTTP access to the Apple Health metrics query tool.
    """
    try:
        result: ToolResult = query_health_metrics(
            user_id=request.user_id,
            metric_types=request.metric_types,
            days_back=request.days_back,
        )
        return create_tool_response(result)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Apple Health metrics query failed: {str(e)}"
        ) from e


@router.post("/generate-health-insights", response_model=ToolResponse)
async def generate_health_insights_endpoint(request: GenerateHealthInsightsRequest):
    """
    Generate AI insights from Apple Health data stored in Redis.

    Direct HTTP access to the Apple Health insights generation tool.
    """
    try:
        result: ToolResult = generate_health_insights(
            user_id=request.user_id,
            focus_area=request.focus_area,
            include_trends=request.include_trends,
        )
        return create_tool_response(result)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Apple Health insights generation failed: {str(e)}"
        ) from e


# ========== Info Endpoint ==========


@router.get("/available")
async def get_available_tools():
    """
    List available Apple Health tools.

    Shows what individual Apple Health tools can be called directly.
    """
    return {
        "available_tools": [
            "parse_health_file",
            "query_health_metrics",
            "generate_health_insights",
            "store_health_data",
        ],
        "description": "Direct HTTP access to individual Apple Health tools",
        "endpoints": [
            "/tools/parse-health-file - Parse Apple Health XML export",
            "/tools/query-health-metrics - Query Apple Health data from Redis",
            "/tools/generate-health-insights - Generate AI insights from Apple Health data",
            "/tools/store-health-data - Store Apple Health data in Redis",
        ],
    }
