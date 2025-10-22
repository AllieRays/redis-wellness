"""
AI Agents for Redis Wellness Application.

Two agent types for side-by-side comparison:
- StatelessHealthAgent: Baseline with NO memory
- StatefulRAGAgent: Full Redis + RedisVL memory
"""

from ..services.memory_manager import MemoryManager, get_memory_manager
from .stateful_rag_agent import StatefulRAGAgent
from .stateless_agent import StatelessHealthAgent

__all__ = [
    # Agents for demo comparison
    "StatelessHealthAgent",
    "StatefulRAGAgent",
    # Memory management
    "MemoryManager",
    "get_memory_manager",
]
