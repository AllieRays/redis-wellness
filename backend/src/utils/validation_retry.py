"""
Shared validation and retry logic for both stateless and stateful agents.

Validates LLM responses for numeric and date hallucinations, with automatic retry.
"""

import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

logger = logging.getLogger(__name__)


async def validate_and_retry_response(
    response_text: str,
    tool_results: list[dict[str, Any]],
    user_query: str,
    llm,
    conversation: list,
    stream: bool = False,
) -> tuple[str, dict, dict]:
    """
    Validate response for numeric and date hallucinations, retry if needed (non-streaming).

    Args:
        response_text: LLM's response text
        tool_results: Results from tool calls
        user_query: Original user query
        llm: LLM instance (without tools bound)
        conversation: Full conversation history
        stream: Ignored (kept for backward compatibility)

    Returns:
        Tuple of (corrected_text, numeric_validation, date_validation)
    """
    from .date_validator import get_date_validator
    from .numeric_validator import get_numeric_validator

    # Validate numeric accuracy
    numeric_validator = get_numeric_validator()
    numeric_validation = numeric_validator.validate_response(
        response_text=response_text,
        tool_results=tool_results,
        strict=False,
    )

    # Validate date accuracy
    date_validator = get_date_validator()
    date_validation = date_validator.validate_response(
        user_query=user_query,
        response_text=response_text,
    )

    # Handle date validation failures first (higher priority)
    if not date_validation["valid"]:
        logger.error(f"❌ DATE MISMATCH DETECTED: {date_validation['warnings']}")

        correction_prompt = (
            f"\n\nYour response mentions the wrong date. "
            f"User asked about {date_validation['query_dates'][0]['raw_match']}, "
            f"but you mentioned {date_validation['response_dates'][0]['raw_match']}. "
            f"Please correct your response to use the date the user asked about."
        )

        # Add bad response + correction to conversation
        conversation_copy = conversation.copy()
        conversation_copy.append(AIMessage(content=response_text))
        conversation_copy.append(HumanMessage(content=correction_prompt))

        # Retry without tools (non-streaming only)
        retry_response = await llm.ainvoke(conversation_copy)
        corrected_text = retry_response.content
        logger.info("🔄 Retry response generated (date correction)")
        return corrected_text, numeric_validation, date_validation

    # Handle numeric validation failures
    elif not numeric_validation["valid"]:
        logger.warning(f"Validation failed (score: {numeric_validation['score']:.2%})")

        # Only retry if validation completely failed (score = 0) and we have tool results
        if numeric_validation["score"] == 0.0 and tool_results:
            logger.warning("⚠️ Zero validation score - retrying with correction prompt")

            correction_prompt = (
                "\n\nYour previous response contained numbers that don't match the tool data. "
                "Please provide a response using ONLY the numbers from the tool results above. "
                "Quote the exact values from the tool output."
            )

            # Add bad response + correction to conversation
            conversation_copy = conversation.copy()
            conversation_copy.append(AIMessage(content=response_text))
            conversation_copy.append(HumanMessage(content=correction_prompt))

            # Retry without tools (non-streaming only)
            retry_response = await llm.ainvoke(conversation_copy)
            corrected_text = retry_response.content
            logger.info("🔄 Retry response generated (numeric correction)")
            return corrected_text, numeric_validation, date_validation
        else:
            # Low score but not zero, or no tool results - return original
            return response_text, numeric_validation, date_validation

    else:
        # Validation passed
        logger.info(f"Validation passed (score: {numeric_validation['score']:.2%})")
        return response_text, numeric_validation, date_validation


def build_validation_result(
    numeric_validation: dict[str, Any],
    date_validation: dict[str, Any],
) -> dict[str, Any]:
    """
    Build validation result dict for response.

    Args:
        numeric_validation: Numeric validation result
        date_validation: Date validation result

    Returns:
        Validation result dict
    """
    return {
        "numeric_valid": numeric_validation["valid"],
        "numeric_score": numeric_validation["score"],
        "date_valid": date_validation["valid"],
        "hallucinations_detected": len(numeric_validation.get("hallucinations", [])),
        "date_mismatches": len(date_validation.get("date_mismatches", [])),
        "numbers_validated": numeric_validation.get("stats", {}).get("matched", 0),
        "total_numbers": numeric_validation.get("stats", {}).get("total_numbers", 0),
    }
