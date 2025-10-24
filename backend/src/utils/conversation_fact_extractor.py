"""
Conversation Fact Extractor - Extracts user-stated facts from conversation history.

This module extracts factual statements from conversation history to prevent
LLM hallucinations. It identifies goals, preferences, dates, and numerical
values stated by the user.

Use Case:
    User: "My goal is 150 lbs"
    LLM: "You're getting closer to your goal of 155 lbs"  # ❌ HALLUCINATION

    Solution: Extract "150 lbs" from conversation, validate against LLM response,
    detect mismatch, and force correction.
"""

import logging
import re
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage

logger = logging.getLogger(__name__)


class ConversationFactExtractor:
    """
    Extracts user-stated facts from conversation history.

    Identifies:
    - Goals: "My goal is X", "I want to reach Y"
    - Preferences: "I prefer X", "I like Y"
    - Personal facts: "I weigh X", "My height is Y"
    - Dates: "on October 15", "last Friday"
    - Numbers with units: "150 lbs", "6 feet", "30 years old"
    """

    # Patterns for extracting goals
    GOAL_PATTERNS = [
        r"(?:my )?goal\s*(?:weight)?\s*(?:is|was|:)\s*(?:to )?(?:reach |weigh |be |get to )?(\d+(?:\.\d+)?)\s*(?:lbs?|pounds?|kg)",
        r"(?:want|trying|aiming) to (?:reach |weigh |be |get to )?(\d+(?:\.\d+)?)\s*(?:lbs?|pounds?|kg)",
        r"(?:target|objective) (?:is|was|:) (?:to )?(?:reach |weigh |be )?(\d+(?:\.\d+)?)\s*(?:lbs?|pounds?|kg)",
    ]

    # Patterns for extracting preferences
    PREFERENCE_PATTERNS = [
        r"(?:i )?prefer (?:to )?([\w\s]+)",
        r"(?:i )?like (?:to )?([\w\s]+)",
        r"(?:i )?enjoy ([\w\s]+)",
    ]

    # Patterns for extracting numerical facts with units
    NUMERICAL_FACT_PATTERNS = [
        r"(?:i )?weigh (\d+(?:\.\d+)?)\s*(?:lbs?|pounds?|kg)",
        r"(?:my )?(?:height|weight) (?:is|was) (\d+(?:\.\d+)?)\s*(?:lbs?|pounds?|kg|feet|ft|inches?|in|cm)",
        r"(?:i am|i'm) (\d+)\s*(?:years? old|lbs?|pounds?|kg)",
    ]

    def __init__(self):
        self.goal_regex = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.GOAL_PATTERNS
        ]
        self.preference_regex = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.PREFERENCE_PATTERNS
        ]
        self.numerical_fact_regex = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.NUMERICAL_FACT_PATTERNS
        ]

    def extract_facts(self, messages: list[BaseMessage]) -> dict[str, Any]:
        """
        Extract all facts from conversation history.

        Args:
            messages: List of conversation messages (LangChain format)

        Returns:
            Dict with extracted facts:
            {
                "goals": [{"value": "150", "unit": "lbs", "raw_text": "My goal is 150 lbs"}],
                "preferences": ["workout on Mondays", "outdoor running"],
                "numerical_facts": [{"value": "138.6", "unit": "lbs", "context": "I weigh"}],
                "dates": ["October 15", "last Friday"],
                "all_numbers": ["150", "138.6"]  # For validation
            }
        """
        facts = {
            "goals": [],
            "preferences": [],
            "numerical_facts": [],
            "dates": [],
            "all_numbers": [],
        }

        # Only process user messages (not system or assistant messages)
        user_messages = [
            msg
            for msg in messages
            if isinstance(msg, HumanMessage) and hasattr(msg, "content")
        ]

        for msg in user_messages:
            text = str(msg.content)

            # Extract goals
            for pattern in self.goal_regex:
                matches = pattern.finditer(text)
                for match in matches:
                    goal_value = match.group(1)
                    # Extract unit (look for lbs, kg, etc. in the match)
                    unit_match = re.search(
                        r"(lbs?|pounds?|kg)",
                        text[match.start() : match.end()],
                        re.IGNORECASE,
                    )
                    unit = unit_match.group(1) if unit_match else "unknown"

                    facts["goals"].append(
                        {
                            "value": goal_value,
                            "unit": unit,
                            "raw_text": text[match.start() : match.end()],
                            "full_message": text,
                        }
                    )
                    facts["all_numbers"].append(goal_value)
                    logger.info(f"📊 Extracted goal: {goal_value} {unit}")

            # Extract preferences
            for pattern in self.preference_regex:
                matches = pattern.finditer(text)
                for match in matches:
                    preference = match.group(1).strip()
                    facts["preferences"].append(preference)
                    logger.info(f"💡 Extracted preference: {preference}")

            # Extract numerical facts
            for pattern in self.numerical_fact_regex:
                matches = pattern.finditer(text)
                for match in matches:
                    value = match.group(1)
                    unit_match = re.search(
                        r"(lbs?|pounds?|kg|feet|ft|inches?|in|cm|years?)",
                        text[match.start() : match.end()],
                        re.IGNORECASE,
                    )
                    unit = unit_match.group(1) if unit_match else "unknown"

                    facts["numerical_facts"].append(
                        {
                            "value": value,
                            "unit": unit,
                            "context": text[
                                max(0, match.start() - 20) : match.start()
                            ].strip(),
                            "raw_text": text[match.start() : match.end()],
                        }
                    )
                    facts["all_numbers"].append(value)
                    logger.info(f"🔢 Extracted fact: {value} {unit}")

            # Extract dates (simple patterns for now)
            date_patterns = [
                r"(?:on |in )?(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?",
                r"(?:on |in )?\d{1,2}/\d{1,2}(?:/\d{2,4})?",
                r"(?:last |next |this )?(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)",
            ]

            for date_pattern in date_patterns:
                matches = re.finditer(date_pattern, text, re.IGNORECASE)
                for match in matches:
                    date_text = match.group(0)
                    facts["dates"].append(date_text)
                    logger.info(f"📅 Extracted date: {date_text}")

        # Deduplicate while preserving order
        facts["all_numbers"] = list(dict.fromkeys(facts["all_numbers"]))
        facts["preferences"] = list(dict.fromkeys(facts["preferences"]))
        facts["dates"] = list(dict.fromkeys(facts["dates"]))

        logger.info(
            f"✅ Extracted facts: {len(facts['goals'])} goals, {len(facts['numerical_facts'])} facts, {len(facts['dates'])} dates"
        )
        return facts

    def validate_response_against_facts(
        self, response_text: str, facts: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Validate LLM response against extracted facts to detect hallucinations.

        Args:
            response_text: LLM-generated response
            facts: Extracted facts from conversation history

        Returns:
            Validation result:
            {
                "valid": bool,
                "mismatches": [{"type": "goal", "expected": "150", "found": "155", ...}],
                "warnings": ["LLM stated goal as 155 lbs but user said 150 lbs"]
            }
        """
        mismatches = []
        warnings = []

        # Extract numbers from response
        response_numbers = re.findall(r"\d+(?:\.\d+)?", response_text)

        # Check if any goals are mentioned incorrectly
        for goal in facts.get("goals", []):
            goal_value = goal["value"]
            goal_unit = goal["unit"]

            # Look for goal mentions in response (e.g., "goal of X lbs")
            goal_mentions = re.finditer(
                rf"goal\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*{goal_unit}",
                response_text,
                re.IGNORECASE,
            )

            for mention in goal_mentions:
                mentioned_value = mention.group(1)
                if mentioned_value != goal_value:
                    mismatch = {
                        "type": "goal",
                        "expected": goal_value,
                        "expected_unit": goal_unit,
                        "found": mentioned_value,
                        "context": response_text[
                            max(0, mention.start() - 30) : mention.end() + 30
                        ],
                    }
                    mismatches.append(mismatch)
                    warnings.append(
                        f"LLM stated goal as {mentioned_value} {goal_unit} but user said {goal_value} {goal_unit}"
                    )
                    logger.warning(
                        f"⚠️ Goal mismatch: expected {goal_value}, found {mentioned_value}"
                    )

        # Check for approximate numbers (common LLM hallucination)
        for goal in facts.get("goals", []):
            goal_float = float(goal["value"])
            for resp_num in response_numbers:
                try:
                    resp_float = float(resp_num)
                    # If response number is within 10% of goal but not exact, flag it
                    if (
                        abs(resp_float - goal_float) <= goal_float * 0.1
                        and resp_float != goal_float
                        and resp_num
                        not in [
                            fact["value"] for fact in facts.get("numerical_facts", [])
                        ]
                    ):
                        warnings.append(
                            f"LLM used approximate number {resp_num} (close to user's stated {goal['value']})"
                        )
                        logger.warning(
                            f"⚠️ Approximate number detected: {resp_num} vs {goal['value']}"
                        )
                except ValueError:
                    pass

        valid = len(mismatches) == 0

        if not valid:
            logger.error(f"❌ Validation failed: {len(mismatches)} mismatches found")
        else:
            logger.info("✅ Response matches conversation facts")

        return {
            "valid": valid,
            "mismatches": mismatches,
            "warnings": warnings,
            "facts_checked": {
                "goals": len(facts.get("goals", [])),
                "numerical_facts": len(facts.get("numerical_facts", [])),
                "dates": len(facts.get("dates", [])),
            },
        }


# Singleton instance
_fact_extractor = None


def get_fact_extractor() -> ConversationFactExtractor:
    """Get or create singleton fact extractor instance."""
    global _fact_extractor
    if _fact_extractor is None:
        _fact_extractor = ConversationFactExtractor()
    return _fact_extractor
