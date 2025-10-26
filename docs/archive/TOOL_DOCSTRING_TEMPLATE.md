# Tool Docstring Template for Qwen

## Standard Format

```python
@tool
def tool_name(param1: type, param2: type = default) -> dict[str, Any]:
    """
    [ONE LINE: Action verb + what it does]

    USE WHEN user asks:
    - "specific query pattern 1"
    - "specific query pattern 2"
    - "specific query pattern 3"

    DO NOT USE for:
    - Different use case → use other_tool instead

    Args:
        param1: Description with valid values
            Examples: "value1", "value2", "value3"
        param2: Description (default: value)
            Options: "option1", "option2"

    Returns:
        Dict with:
        - field1: description
        - field2: description

    Examples:
        Query: "What was my weight in September?"
        Call: tool_name(param1="BodyMass", param2="September")
        Returns: List of weight records with dates

        Query: "Average heart rate last week?"
        Call: tool_name(param1="HeartRate", param2="last week", param3=["average"])
        Returns: {"average": "87 bpm", "sample_size": 7}
    """
```

## Key Principles

1. **No emojis** - Plain text only
2. **Decision-first** - When to use comes before how
3. **Concrete examples** - Real query → real call → real return
4. **Consistent structure** - Same order every time
5. **Type hints** - All parameters fully annotated
6. **Clear alternatives** - When NOT to use + what to use instead

## Anti-Patterns to Avoid

❌ Mixing implementation details in Args section
❌ Long prose explanations
❌ Examples without showing the full call
❌ Missing return structure
❌ Emojis and formatting in docstrings (save for comments)
