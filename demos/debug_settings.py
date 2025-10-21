#!/usr/bin/env python3
"""Debug script to test settings loading"""

import sys
sys.path.append('./backend/src')

from config import get_settings

def main():
    settings = get_settings()
    
    print("=== Current Settings ===")
    print(f"redis_host: {settings.redis_host}")
    print(f"redis_port: {settings.redis_port}")
    print(f"redis_session_ttl_seconds: {settings.redis_session_ttl_seconds}")
    print(f"redis_health_data_ttl_seconds: {settings.redis_health_data_ttl_seconds}")
    print(f"redis_default_ttl_days: {settings.redis_default_ttl_days}")
    
    print("\n=== Expected Values ===")
    print(f"7 months in seconds: 18144000")
    print(f"7 months in days: 210")

if __name__ == "__main__":
    main()