"""
Data module for static knowledge bases and datasets.

Contains:
- semantic_knowledge_base: Verified health facts for semantic memory
"""

from .semantic_knowledge_base import (
    MEDICAL_DISCLAIMER,
    VERIFIED_HEALTH_FACTS,
    get_facts_by_category,
    get_high_confidence_facts,
    get_verified_health_facts,
)

__all__ = [
    "VERIFIED_HEALTH_FACTS",
    "MEDICAL_DISCLAIMER",
    "get_verified_health_facts",
    "get_facts_by_category",
    "get_high_confidence_facts",
]
