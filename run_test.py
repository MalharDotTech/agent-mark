#!/usr/bin/env python3
"""
Simple test runner for Meta Insights Harvester.

This script provides an easy way to test the service with different scenarios.
"""

import asyncio
import sys
from datetime import datetime
import httpx


class SimpleMetaTester:
    """Simple tester for Meta API functionality."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the tester with base URL."""
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
    
    async def test_health_check(self) -> bool:
        """Test if the service is healthy and accessible."""
        print("🔍 Testing health check...")
        
        try:
            response = await self.client.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                health_data = response.json()
                status = health_data.get("status", "unknown")
                print(f"✅ Service is {status}")
                
                # Print some health details
                if "details" in health_data:
                    details = health_data["details"]
                    if "token_stats" in details:
                        token_stats = details["token_stats"]
                        print(f"   📊 Available tokens: {token_stats.get('available_tokens', 0)}")
                        print(f"   📊 Total tokens: {token_stats.get('total_tokens', 0)}")
                
                return status in ["healthy", "degraded"]
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    async def get_accounts(self) -> list:
        """Get available Meta ad accounts."""
        print("📋 Getting available accounts...")
        
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/accounts")
            
            if response.status_code == 200:
                accounts = response.json()
                print(f"✅ Found {len(accounts)} accounts")
                
                for i, account in enumerate(accounts[:3]):  # Show first 3
                    print(f"   {i+1}. {account.get('account_name', 'Unknown')} (ID: {account.get('account_id', 'N/A')})")
                
                if len(accounts) > 3:
                    print(f"   ... and {len(accounts) - 3} more accounts")
                
                return accounts
            else:
                print(f"❌ Failed to get accounts: {response.status_code}")
                print(f"   Response: {response.text}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting accounts: {e}")
            return []
    
    async def test_metrics(self) -> bool:
        """Test metrics endpoint."""
        print("📊 Testing metrics endpoint...")
        
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/metrics")
            
            if response.status_code == 200:
                metrics = response.json()
                print("✅ Metrics endpoint working")
                
                # Show some key metrics
                if "tokens" in metrics:
                    tokens = metrics["tokens"]
                    available = tokens.get("available_tokens", 0)
                    total = tokens.get("total_tokens", 0)
                    print(f"   🔑 Tokens: {available}/{total} available")
                
                if "service" in metrics:
                    service = metrics["service"]
                    uptime = service.get("uptime_seconds", 0)
                    print(f"   ⏱️  Uptime: {uptime:.1f} seconds")
                
                return True
            else:
                print(f"❌ Metrics request failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error getting metrics: {e}")
            return False


async def quick_test():
    """Run a quick connectivity test."""
    print("🏃‍♂️ Running Quick Connectivity Test")
    print("-" * 40)
    
    async with SimpleMetaTester() as tester:
        # Health check
        if not await tester.test_health_check():
            return False
        
        print()
        
        # Get accounts
        accounts = await tester.get_accounts()
        if not accounts:
            return False
        
        print()
        
        # Test metrics
        return await tester.test_metrics()


async def full_test():
    """Run the complete connectivity test."""
    print("🔬 Running Full Connectivity Test")
    print("-" * 40)
    
    async with SimpleMetaTester() as tester:
        # Health check
        if not await tester.test_health_check():
            print("❌ Health check failed - service may not be running")
            return False
        
        print()
        
        # Get accounts
        accounts = await tester.get_accounts()
        if not accounts:
            print("❌ No accounts available - check your Meta API tokens")
            return False
        
        print()
        
        # Test metrics
        if not await tester.test_metrics():
            print("❌ Metrics test failed")
            return False
        
        print()
        print("🎉 All connectivity tests passed!")
        return True


async def health_only():
    """Just check if the service is healthy."""
    print("🏥 Health Check Only")
    print("-" * 20)
    
    async with SimpleMetaTester() as tester:
        healthy = await tester.test_health_check()
        
        if healthy:
            print()
            # Also get metrics
            await tester.test_metrics()
        
        return healthy


async def accounts_only():
    """Just list available accounts."""
    print("📋 Available Accounts")
    print("-" * 20)
    
    async with SimpleMetaTester() as tester:
        if await tester.test_health_check():
            print()
            accounts = await tester.get_accounts()
            return len(accounts) > 0
        return False


def print_usage():
    """Print usage information."""
    print("🧪 Meta Insights Harvester Test Runner")
    print("=" * 40)
    print()
    print("Usage: python run_test.py [command]")
    print()
    print("Commands:")
    print("  quick     - Quick connectivity test (default)")
    print("  full      - Complete connectivity test")
    print("  health    - Health check and metrics only")
    print("  accounts  - List available accounts only")
    print("  help      - Show this help message")
    print()
    print("Examples:")
    print("  python run_test.py")
    print("  python run_test.py quick")
    print("  python run_test.py full")
    print("  python run_test.py health")
    print()
    print("Prerequisites:")
    print("  1. Start the service: uv run uvicorn app.main:app --reload")
    print("  2. Configure .env with valid Meta API tokens")
    print()


async def main():
    """Main function."""
    command = sys.argv[1] if len(sys.argv) > 1 else "quick"
    
    if command in ["help", "-h", "--help"]:
        print_usage()
        return 0
    
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = False
    
    try:
        if command == "quick":
            success = await quick_test()
        elif command == "full":
            success = await full_test()
        elif command == "health":
            success = await health_only()
        elif command == "accounts":
            success = await accounts_only()
        else:
            print(f"❌ Unknown command: {command}")
            print()
            print_usage()
            return 1
        
        print()
        if success:
            print("✅ Connectivity test completed successfully!")
            print("🌐 Access the API docs at: http://localhost:8000/docs")
            print("📊 Use the API endpoints to extract data to CSV files")
        else:
            print("❌ Connectivity test failed!")
            print()
            print("🔧 Troubleshooting:")
            print("  • Make sure FastAPI service is running on port 8000")
            print("  • Check .env file has valid Meta API tokens")
            print("  • Verify tokens have access to ad accounts")
            print("  • Check service logs for detailed errors")
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)