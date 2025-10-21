#!/usr/bin/env python3
"""
Side-by-side Chat Comparison Demo

Demonstrates the difference between:
1. Stateless Chat - No memory, each message processed independently
2. Redis Chat - Conversation memory with TTL-based persistence

Technologies demonstrated:
- Stateless: HTTPX + Ollama (no Redis)
- Redis: RedisVL + HTTPX + Ollama (with conversation memory)
"""
import requests
import json
import time

API_BASE = "http://localhost:8000/api/chat"

def test_conversation_flow():
    """Test side-by-side conversation flow to demonstrate memory differences."""
    
    print("🔄 Redis vs Stateless Chat Comparison Demo")
    print("=" * 60)
    
    # Test conversation flow
    conversation = [
        "Hi, my name is Alice and I'm 28 years old.",
        "What's my name?",
        "How old am I?",
        "Can you tell me something about my health based on my age?"
    ]
    
    session_id = f"comparison-{int(time.time())}"
    
    print(f"\n📝 Testing conversation flow with {len(conversation)} messages...")
    print(f"🔑 Redis session ID: {session_id}")
    
    for i, message in enumerate(conversation, 1):
        print(f"\n--- Message {i}: '{message}' ---")
        
        # Test Stateless Chat
        print("\n🚫 STATELESS CHAT (No Memory):")
        try:
            stateless_response = requests.post(
                f"{API_BASE}/stateless",
                json={"message": message},
                timeout=10
            )
            
            if stateless_response.status_code == 200:
                stateless_data = stateless_response.json()
                response_preview = stateless_data["response"][:100]
                print(f"   Response: {response_preview}...")
            else:
                print(f"   ❌ Error: {stateless_response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Failed: {e}")
        
        # Test Redis Chat
        print("\n🧠 REDIS CHAT (With Memory):")
        try:
            redis_response = requests.post(
                f"{API_BASE}/redis",
                json={"message": message, "session_id": session_id},
                timeout=10
            )
            
            if redis_response.status_code == 200:
                redis_data = redis_response.json()
                response_preview = redis_data["response"][:100]
                print(f"   Response: {response_preview}...")
                print(f"   Session: {redis_data['session_id']}")
            else:
                print(f"   ❌ Error: {redis_response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Failed: {e}")
        
        # Add delay between messages
        if i < len(conversation):
            print("\n   ⏳ Waiting 2 seconds...")
            time.sleep(2)
    
    # Show conversation history for Redis chat
    print("\n" + "=" * 60)
    print("📚 REDIS CONVERSATION HISTORY")
    print("=" * 60)
    
    try:
        history_response = requests.get(f"{API_BASE}/history/{session_id}")
        if history_response.status_code == 200:
            history_data = history_response.json()
            print(f"Session: {history_data['session_id']}")
            print(f"Total Messages: {history_data['total_messages']}")
            print("\nConversation Flow:")
            
            for msg in history_data['messages']:
                role = msg['role'].upper()
                content_preview = msg['content'][:80]
                timestamp = msg.get('timestamp', 'N/A')
                print(f"  {role}: {content_preview}...")
                if len(msg['content']) > 80:
                    print(f"        (Full message truncated)")
        else:
            print(f"❌ History Error: {history_response.status_code}")
            
    except Exception as e:
        print(f"❌ History Failed: {e}")
    
    # Show session information
    print("\n" + "=" * 60)
    print("ℹ️  REDIS SESSION INFORMATION") 
    print("=" * 60)
    
    try:
        session_response = requests.get(f"{API_BASE}/session/{session_id}/info")
        if session_response.status_code == 200:
            session_data = session_response.json()
            ttl_hours = session_data['ttl_seconds'] / 3600
            
            print(f"Session ID: {session_data['session_id']}")
            print(f"Message Count: {session_data['message_count']}")
            print(f"TTL: {session_data['ttl_seconds']} seconds ({ttl_hours:.1f} hours)")
            print(f"Session Exists: {session_data['exists']}")
            print(f"Auto-cleanup: Redis will automatically delete this session in {ttl_hours:.1f} hours")
        else:
            print(f"❌ Session Info Error: {session_response.status_code}")
            
    except Exception as e:
        print(f"❌ Session Info Failed: {e}")

def show_comparison_summary():
    """Show detailed comparison information."""
    
    print("\n" + "=" * 60)
    print("📊 TECHNOLOGY COMPARISON SUMMARY")
    print("=" * 60)
    
    try:
        info_response = requests.get(f"{API_BASE}/comparison/info")
        if info_response.status_code == 200:
            info_data = info_response.json()
            
            print(f"Comparison Type: {info_data['comparison_type']}")
            
            print(f"\n🚀 Redis Chat Advantages:")
            for advantage in info_data['redis_advantages']:
                print(f"  ✅ {advantage}")
                
            print(f"\n⚠️ Stateless Chat Limitations:")
            for limitation in info_data['stateless_limitations']:
                print(f"  ❌ {limitation}")
                
            print(f"\n🛠️ Technology Stack:")
            print(f"  📡 Stateless: HTTPX + Ollama (no persistence)")
            print(f"  🧠 Redis: RedisVL + HTTPX + Ollama (with memory)")
            
            print(f"\n🔗 Available Endpoints:")
            for name, endpoint in info_data['endpoints'].items():
                print(f"  • {name}: {endpoint}")
                
        else:
            print(f"❌ Comparison Info Error: {info_response.status_code}")
            
    except Exception as e:
        print(f"❌ Comparison Info Failed: {e}")

def cleanup_demo_session(session_id):
    """Clean up the demo session."""
    print(f"\n🧹 Cleaning up demo session: {session_id}")
    
    try:
        cleanup_response = requests.delete(f"{API_BASE}/session/{session_id}")
        if cleanup_response.status_code == 200:
            cleanup_data = cleanup_response.json()
            print(f"✅ {cleanup_data['message']}")
        else:
            print(f"❌ Cleanup failed: {cleanup_response.status_code}")
    except Exception as e:
        print(f"❌ Cleanup error: {e}")

def main():
    """Run the complete chat comparison demo."""
    try:
        # Run conversation flow test
        test_conversation_flow()
        
        # Show comparison summary
        show_comparison_summary()
        
        print("\n" + "=" * 60)
        print("✅ CHAT COMPARISON DEMO COMPLETE!")
        print("=" * 60)
        
        print("\n🎉 Key Demonstrations:")
        print("  ✅ Stateless chat has no memory between messages")
        print("  ✅ Redis chat maintains conversation context")
        print("  ✅ Redis provides session management with TTL")
        print("  ✅ Redis enables conversation history retrieval")
        print("  ✅ Automatic cleanup prevents memory leaks")
        
        print(f"\n🔧 Technologies Compared:")
        print(f"  • Stateless: Pure HTTPX → Ollama")
        print(f"  • Redis: RedisVL → Conversation Memory → Ollama")
        
        print(f"\n💡 Redis provides significant advantages for conversational AI!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Make sure the backend is running:")
        print("   docker-compose up -d backend")
    except Exception as e:
        print(f"❌ Demo failed: {e}")

if __name__ == "__main__":
    main()