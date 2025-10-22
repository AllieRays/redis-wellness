#!/usr/bin/env python
"""
Demo script: Token-Aware Context Management

This script demonstrates how token-aware context management works in redis-wellness.
It shows:
1. How token counting works
2. When trimming is triggered
3. How old messages are removed to stay under limits
4. Token usage statistics

Run with: python backend/test_token_management.py
"""

import asyncio
import sys
from pathlib import Path

from src.config import get_settings
from src.utils.token_manager import TokenManager

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))


async def demo_token_management():
    """Demonstrate token counting and trimming."""

    print("=" * 70)
    print("TOKEN-AWARE CONTEXT MANAGEMENT DEMO")
    print("=" * 70)

    # Initialize token manager
    settings = get_settings()
    token_manager = TokenManager()

    print("\n📊 Configuration:")
    print(f"   Max context tokens: {token_manager.max_tokens}")
    print(
        f"   Trim threshold: {token_manager.threshold} tokens ({settings.token_usage_threshold * 100}%)"
    )
    print(f"   Min messages to keep: {token_manager.min_messages}")

    # Create sample messages
    sample_messages = [
        {"role": "user", "content": "What is my average heart rate?"},
        {
            "role": "assistant",
            "content": "Your average heart rate over the last week was 72 bpm, which is normal.",
        },
        {"role": "user", "content": "What about my step count?"},
        {
            "role": "assistant",
            "content": "You averaged 8,234 steps per day, which is healthy.",
        },
        {"role": "user", "content": "How's my sleep quality?"},
        {
            "role": "assistant",
            "content": "Your sleep score was 87/100, excellent. You got 7.5 hours average.",
        },
        {"role": "user", "content": "Tell me about my workouts last month."},
        {
            "role": "assistant",
            "content": "You completed 18 workouts totaling 45 hours of exercise.",
        },
        {"role": "user", "content": "What's my current weight?"},
        {
            "role": "assistant",
            "content": "Your current weight is 165 lbs, down 2 lbs from last month.",
        },
    ]

    print(f"\n📝 Sample conversation ({len(sample_messages)} messages):")
    for i, msg in enumerate(sample_messages, 1):
        print(f"   {i}. {msg['role'].upper()}: {msg['content'][:50]}...")

    # Count tokens
    total_tokens = token_manager.count_message_tokens(sample_messages)
    print(f"\n🔢 Token count: {total_tokens} / {token_manager.max_tokens}")
    print(f"   Usage: {(total_tokens / token_manager.max_tokens * 100):.1f}%")

    # Check if trimming is needed
    should_trim = token_manager.should_trim(total_tokens)
    print(f"   Trimming needed: {'YES' if should_trim else 'NO'}")

    if should_trim:
        print("\n✂️  TRIMMING MESSAGES...")
        trimmed, original_tokens, trimmed_tokens = token_manager.trim_messages(
            sample_messages
        )

        print(
            f"\n   Original: {len(sample_messages)} messages, {original_tokens} tokens"
        )
        print(f"   Trimmed:  {len(trimmed)} messages, {trimmed_tokens} tokens")
        print(f"   Removed: {len(sample_messages) - len(trimmed)} messages")
        print(
            f"\n   ✅ Now under threshold: {trimmed_tokens} / {token_manager.threshold} tokens"
        )

        print("\n   Trimmed conversation (kept recent messages):")
        for i, msg in enumerate(trimmed, 1):
            print(f"      {i}. {msg['role'].upper()}: {msg['content'][:50]}...")

    # Show usage stats
    print("\n📈 Usage Statistics:")
    stats = token_manager.get_usage_stats(
        sample_messages if not should_trim else trimmed
    )
    print(f"   Message count: {stats['message_count']}")
    print(f"   Token count: {stats['token_count']}")
    print(f"   Usage: {stats['usage_percent']}% of max")
    print(f"   Threshold usage: {stats['threshold_percent']}% of threshold")
    print(f"   Over threshold: {stats['is_over_threshold']}")

    # Simulate conversation growing
    print("\n\n📊 SIMULATION: Conversation Growing Over Time")
    print("=" * 70)

    growing_messages = []
    for i, msg in enumerate(sample_messages, 1):
        growing_messages.append(msg)
        token_count = token_manager.count_message_tokens(growing_messages)
        usage_percent = (token_count / token_manager.max_tokens) * 100
        should_trim_now = token_manager.should_trim(token_count)

        status = "🔴 TRIM!" if should_trim_now else "🟢"
        print(
            f"   Message {i:2d}: {token_count:5d} tokens ({usage_percent:5.1f}%) {status}"
        )

    print("\n" + "=" * 70)
    print("✅ Demo complete!")
    print("\nKey takeaways:")
    print("  • Tokens are counted using tiktoken (same as OpenAI)")
    print("  • Trimming removes oldest messages first")
    print("  • Recent messages are always kept for context")
    print("  • This prevents LLM context window overflow")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(demo_token_management())
