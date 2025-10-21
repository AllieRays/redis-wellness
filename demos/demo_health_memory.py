#!/usr/bin/env python3
"""
Redis Health Memory Demo

Demonstrates why Redis memory is crucial for health conversations:
1. Stateless: Each health question answered independently
2. Redis: Maintains context about your health data across conversation

This shows how Redis enables better health insights through conversation memory.
"""
import requests
import time

API_BASE = "http://localhost:8000/api/chat"

def demo_health_conversation_memory():
    """Demonstrate health conversation memory advantages."""

    print("🏥 REDIS HEALTH MEMORY DEMONSTRATION")
    print("=" * 60)
    print("📊 Your Health Data: 255,672 records, BMI: 22.5 kg/m², 985 step measurements")
    print("🎯 Goal: Show why Redis memory improves health conversations")
    print()

    # Health conversation flow that demonstrates memory benefits
    health_conversation = [
        "What can you tell me about my overall health?",
        "What's my current BMI?",
        "Is that BMI level healthy for me?",
        "Based on what we discussed, what should I focus on improving?"
    ]

    session_id = f"health-memory-demo-{int(time.time())}"

    for i, question in enumerate(health_conversation, 1):
        print(f"\n🗣️ QUESTION {i}: '{question}'")
        print("-" * 60)

        # Test Stateless (No Memory)
        print(f"\n🚫 STATELESS HEALTH CHAT (No Memory)")
        try:
            stateless_response = requests.post(
                f"{API_BASE}/stateless",
                json={"message": question},
                timeout=15
            )

            if stateless_response.status_code == 200:
                data = stateless_response.json()
                response = data["response"]
                # Show truncated response
                print(f"📝 Response: {response[:150]}...")
                if len(response) > 150:
                    print(f"    [Response truncated - total length: {len(response)} chars]")
            else:
                print(f"❌ Error: {stateless_response.status_code}")

        except Exception as e:
            print(f"❌ Failed: {e}")

        # Test Redis (With Memory)
        print(f"\n🧠 REDIS HEALTH CHAT (With Memory)")
        try:
            redis_response = requests.post(
                f"{API_BASE}/redis",
                json={"message": question, "session_id": session_id},
                timeout=15
            )

            if redis_response.status_code == 200:
                data = redis_response.json()
                response = data["response"]
                # Show truncated response
                print(f"📝 Response: {response[:150]}...")
                if len(response) > 150:
                    print(f"    [Response truncated - total length: {len(response)} chars]")
                print(f"🔑 Session: {data['session_id']}")
            else:
                print(f"❌ Error: {redis_response.status_code}")

        except Exception as e:
            print(f"❌ Failed: {e}")

        # Add pause between questions
        if i < len(health_conversation):
            print(f"\n⏳ Pausing 3 seconds before next question...")
            time.sleep(3)

    # Show Redis conversation history
    print("\n" + "=" * 60)
    print("🧠 REDIS CONVERSATION MEMORY")
    print("=" * 60)

    try:
        history_response = requests.get(f"{API_BASE}/history/{session_id}")
        if history_response.status_code == 200:
            history = history_response.json()
            print(f"📊 Session: {history['session_id']}")
            print(f"💬 Total Messages: {history['total_messages']}")

            print(f"\n📜 Conversation History:")
            for msg in history['messages']:
                role = "👤 USER" if msg['role'] == 'user' else "🤖 ASSISTANT"
                content = msg['content'][:100]
                print(f"{role}: {content}{'...' if len(msg['content']) > 100 else ''}")

        else:
            print(f"❌ History Error: {history_response.status_code}")

    except Exception as e:
        print(f"❌ History Failed: {e}")

    # Show the key differences
    print("\n" + "=" * 60)
    print("🎯 KEY DIFFERENCES DEMONSTRATED")
    print("=" * 60)

    print("\n🚫 STATELESS HEALTH CHAT:")
    print("  ❌ Each question answered independently")
    print("  ❌ Cannot reference previous health discussions")
    print("  ❌ Must repeat health context for every query")
    print("  ❌ Cannot build upon previous health insights")
    print("  ❌ Limited follow-up capability")

    print("\n🧠 REDIS HEALTH CHAT:")
    print("  ✅ Maintains full health conversation context")
    print("  ✅ Can reference previous health metrics discussed")
    print("  ✅ Builds upon earlier health insights")
    print("  ✅ Enables natural health conversation flow")
    print("  ✅ Remembers your health goals and concerns")
    print("  ✅ TTL-based automatic cleanup (24 hours)")

    print("\n💡 REDIS MEMORY ADVANTAGES FOR HEALTH:")
    print("  🏥 Personalized health coaching across sessions")
    print("  📈 Track health progress over time")
    print("  🎯 Context-aware health recommendations")
    print("  💊 Remember health goals and medication reminders")
    print("  📊 Build comprehensive health conversation history")

def main():
    """Run the health memory demonstration."""
    try:
        demo_health_conversation_memory()

        print("\n" + "=" * 60)
        print("✅ HEALTH MEMORY DEMO COMPLETE!")
        print("=" * 60)

        print("\n🏥 This demonstrates why Redis memory is crucial for health AI:")
        print("  • Health conversations build on previous context")
        print("  • Follow-up questions require conversation memory")
        print("  • Personal health insights improve with conversational state")
        print("  • Redis TTL provides automatic cleanup without data loss")

        print(f"\n🌐 Try it yourself at: http://localhost:3000")
        print(f"💡 Ask both chats the same health questions to see the difference!")

    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Make sure the system is running:")
        print("   docker-compose up -d")
    except Exception as e:
        print(f"❌ Demo failed: {e}")

if __name__ == "__main__":
    main()
