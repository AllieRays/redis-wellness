"""
AI Agent Tools for Redis Wellness Application.

This module provides tools that AI agents can call to:
- Parse and analyze health data
- Store/retrieve data with Redis TTL features
- Generate intelligent health insights
- Compare Redis vs stateless performance

Design principles:
- Single-purpose, focused tools
- Comprehensive input validation
- Structured JSON responses
- Error handling with actionable feedback
- Privacy-first data handling
"""

from ..services.redis_health_tool import (
    get_health_conversation_context,
    query_health_metrics,
    store_health_data,
)
from ..utils.base import ToolError, ToolResult, validate_tool_input
from ..utils.performance_tool import compare_data_access_performance
from .agent_tools import create_user_bound_tools
from .health_insights_tool import generate_health_insights
from .health_parser_tool import parse_health_file

# Tool registry for AI agent discovery
AVAILABLE_TOOLS = {
    "parse_health_file": {
        "function": parse_health_file,
        "description": "Parse Apple Health XML file and extract structured health data",
        "category": "data_processing",
    },
    "store_health_data": {
        "function": store_health_data,
        "description": "Store health data in Redis with TTL for conversational memory",
        "category": "data_storage",
    },
    "query_health_metrics": {
        "function": query_health_metrics,
        "description": "Query specific health metrics from Redis for AI conversations",
        "category": "data_retrieval",
    },
    "generate_health_insights": {
        "function": generate_health_insights,
        "description": "Generate AI-ready health insights and trend analysis",
        "category": "ai_analysis",
    },
    "compare_data_access_performance": {
        "function": compare_data_access_performance,
        "description": "Compare Redis vs stateless data access performance",
        "category": "benchmarking",
    },
}


def get_tool_schemas():
    """
    Return OpenAI-compatible tool schemas for AI agents.

    Returns:
        List of tool schema dictionaries for function calling
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "parse_health_file",
                "description": "Parse Apple Health XML file and extract structured health data with privacy protection",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to Apple Health export XML file",
                        },
                        "anonymize": {
                            "type": "boolean",
                            "description": "Whether to anonymize personal data (default: true)",
                            "default": True,
                        },
                    },
                    "required": ["file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "store_health_data",
                "description": "Store parsed health data in Redis with TTL for conversational memory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "Unique user identifier",
                        },
                        "health_data": {
                            "type": "object",
                            "description": "Parsed health data from parse_health_file",
                        },
                        "ttl_days": {
                            "type": "integer",
                            "description": "TTL in days for conversational memory (default: 7)",
                            "default": 7,
                            "minimum": 1,
                            "maximum": 30,
                        },
                    },
                    "required": ["user_id", "health_data"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "query_health_metrics",
                "description": "Query specific health metrics from Redis for conversation context",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "Unique user identifier",
                        },
                        "metric_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Health metric types to query (e.g., 'BodyMassIndex', 'DietaryWater')",
                        },
                        "days_back": {
                            "type": "integer",
                            "description": "Number of days to look back (default: 30)",
                            "default": 30,
                            "minimum": 1,
                            "maximum": 365,
                        },
                    },
                    "required": ["user_id", "metric_types"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "generate_health_insights",
                "description": "Generate AI-ready health insights and trends for conversation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "Unique user identifier",
                        },
                        "focus_area": {
                            "type": "string",
                            "enum": ["weight", "activity", "nutrition", "overall"],
                            "description": "Area to focus insights on",
                            "default": "overall",
                        },
                        "include_trends": {
                            "type": "boolean",
                            "description": "Include trend analysis (default: true)",
                            "default": True,
                        },
                    },
                    "required": ["user_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "compare_data_access_performance",
                "description": "Compare Redis vs stateless data access performance to demonstrate advantages",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "User ID to test performance with",
                        },
                        "operation_type": {
                            "type": "string",
                            "enum": [
                                "query_metrics",
                                "generate_insights",
                                "trend_analysis",
                            ],
                            "description": "Type of operation to benchmark",
                        },
                        "iterations": {
                            "type": "integer",
                            "description": "Number of test iterations (default: 10)",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 100,
                        },
                    },
                    "required": ["user_id", "operation_type"],
                },
            },
        },
    ]


__all__ = [
    "ToolResult",
    "ToolError",
    "validate_tool_input",
    "parse_health_file",
    "store_health_data",
    "query_health_metrics",
    "get_health_conversation_context",
    "generate_health_insights",
    "compare_data_access_performance",
    "create_user_bound_tools",
    "AVAILABLE_TOOLS",
    "get_tool_schemas",
]
