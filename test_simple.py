#!/usr/bin/env python3
"""
Simple test to verify the service is working.
Run this after starting the FastAPI server.
"""

import asyncio
import httpx
from datetime import datetime


async def test_service():
    """Test basic service functionality."""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Meta Insights Harvester")
    print("=" * 40)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        
        # Test 1: Health check
        print("1️⃣ Testing health endpoint...")
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                health = response.json()
                print(f"   ✅ Service is {health.get('status', 'unknown')}")
            else:
                print(f"   ❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Cannot connect to service: {e}")
            print("   💡 Make sure to start the service first:")
            print("      uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
            return False
        
        # Test 2: Get accounts
        print("\n2️⃣ Testing accounts endpoint...")
        try:
            response = await client.get(f"{base_url}/api/v1/accounts")
            if response.status_code == 200:
                accounts = response.json()
                print(f"   ✅ Found {len(accounts)} accessible accounts")
                
                if accounts:
                    print("   📋 Sample accounts:")
                    for i, account in enumerate(accounts[:2]):
                        name = account.get('account_name', 'Unknown')
                        account_id = account.get('account_id', 'N/A')
                        print(f"      • {name} (ID: {account_id})")
                else:
                    print("   ⚠️  No accounts found - check your Meta API tokens")
                    return False
            else:
                print(f"   ❌ Accounts request failed: {response.status_code}")
                print(f"      Response: {response.text}")
                return False
        except Exception as e:
            print(f"   ❌ Error getting accounts: {e}")
            return False
        
        # Test 3: Metrics endpoint
        print("\n3️⃣ Testing metrics endpoint...")
        try:
            response = await client.get(f"{base_url}/api/v1/metrics")
            if response.status_code == 200:
                metrics = response.json()
                print("   ✅ Metrics endpoint working")
                
                # Show some key metrics
                if "tokens" in metrics:
                    tokens = metrics["tokens"]
                    available = tokens.get("available_tokens", 0)
                    total = tokens.get("total_tokens", 0)
                    print(f"      🔑 Tokens: {available}/{total} available")
                
                if "service" in metrics:
                    service = metrics["service"]
                    uptime = service.get("uptime_seconds", 0)
                    print(f"      ⏱️  Uptime: {uptime:.1f} seconds")
            else:
                print(f"   ❌ Metrics request failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error getting metrics: {e}")
        
        print("\n🎉 Basic service test completed successfully!")
        print("\n📖 Next steps:")
        print("   • Run full connectivity test: python run_test.py")
        print("   • Access API docs: http://localhost:8000/docs")
        print("   • Use the API endpoints to extract data to CSV files")
        
        return True


if __name__ == "__main__":
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        success = asyncio.run(test_service())
        if not success:
            print("\n❌ Some tests failed. Check the output above.")
            exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted")
        exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        exit(1)