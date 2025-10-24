"""
AI Agents for Redis Wellness Application.

Two agent types for side-by-side demo comparison:
- StatelessHealthAgent: Baseline with ZERO memory (tools only)
- StatefulRAGAgent: Full CoALA framework memory (episodic, procedural, semantic, short-term)
"""

from .stateful_rag_agent import StatefulRAGAgent
from .stateless_agent import StatelessHealthAgent

__all__ = [
    "StatelessHealthAgent",
    "StatefulRAGAgent",
]
