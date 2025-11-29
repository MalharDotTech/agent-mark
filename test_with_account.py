#!/usr/bin/env python3
"""
Test Meta Insights Harvester with a specific account.

This script allows you to choose from available accounts and test Meta API connectivity
and basic functionality.
"""

import asyncio
import sys
from datetime import datetime
import httpx


class MetaAPITester:
    """Simple tester for Meta API functionality without job processing."""
    
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


# Available accounts from your Meta API
AVAILABLE_ACCOUNTS = [
    {"account_id": "act_66395971", "account_name": "Porter - old"},
    {"account_id": "act_272178626", "account_name": "Stahl Cookware Ad Account (Active)"},
    {"account_id": "act_547569015598645", "account_name": "Porter - BM - new"},
    {"account_id": "act_2153562184916418", "account_name": "NATHABIT Main"},
    {"account_id": "act_816491348940413", "account_name": "Porter Partnerships"},
    {"account_id": "act_401102658292256", "account_name": "Pink Fort"},
    {"account_id": "act_1252337455509087", "account_name": "Porter Partner"},
    {"account_id": "act_742443313975022", "account_name": "Novology - Aristok"},
    {"account_id": "act_1237435520110000", "account_name": "Careers at Torrins"},
    {"account_id": "act_250361314465016", "account_name": "NAT Habit New"},
    {"account_id": "act_189321610853222", "account_name": "Porter 2.0"},
    {"account_id": "act_1089593289023657", "account_name": "Liquid IV - Aristok"},
    {"account_id": "act_901032431399316", "account_name": "Porter UAE"},
    {"account_id": "act_1333986183941458", "account_name": "The Gift Studio"},
    {"account_id": "act_2197673197282548", "account_name": "NatHabit 3"},
    {"account_id": "act_971702507620832", "account_name": "Stahl Cookware Ad Account - 2"},
    {"account_id": "act_758730662807705", "account_name": "Chinmay Raibagkar"},
    {"account_id": "act_1041243560976896", "account_name": "PinkFort_New2"}
]

# Recommended accounts that are likely to have recent data
RECOMMENDED_ACCOUNTS = [
    "act_272178626",  # Stahl Cookware Ad Account (Active)
    "act_2153562184916418",  # NATHABIT Main
    "act_250361314465016",  # NAT Habit New
    "act_547569015598645",  # Porter - BM - new
    "act_189321610853222",  # Porter 2.0
]


def print_accounts():
    """Print available accounts with recommendations."""
    print("📋 Available Meta Ad Accounts:")
    print("=" * 60)
    
    for i, account in enumerate(AVAILABLE_ACCOUNTS, 1):
        account_id = account["account_id"]
        account_name = account["account_name"]
        
        # Mark recommended accounts
        if account_id in RECOMMENDED_ACCOUNTS:
            print(f"  {i:2d}. ⭐ {account_name}")
            print(f"      ID: {account_id}")
        else:
            print(f"  {i:2d}.    {account_name}")
            print(f"      ID: {account_id}")
        print()


async def test_specific_account(account_id: str, account_name: str):
    """Test Meta API connectivity with a specific account."""
    print(f"🧪 Testing Meta API connectivity for: {account_name}")
    print(f"📊 Account ID: {account_id}")
    print("-" * 60)
    
    async with MetaAPITester() as tester:
        # Health check
        if not await tester.test_health_check():
            print("❌ Service health check failed")
            return False
        
        print()
        
        # Get accounts and verify the specific account is accessible
        accounts = await tester.get_accounts()
        if not accounts:
            print("❌ No accounts available")
            return False
        
        # Check if the specific account is in the list
        account_found = any(acc.get("account_id") == account_id for acc in accounts)
        if account_found:
            print(f"✅ Account {account_name} is accessible via Meta API")
        else:
            print(f"⚠️  Account {account_name} not found in accessible accounts")
            print("   This may be due to token permissions or account status")
        
        print()
        
        # Test metrics
        await tester.test_metrics()
        
        return True


async def test_recommended_accounts_connectivity():
    """Test Meta API connectivity with recommended accounts."""
    print("🔍 Testing Meta API Connectivity (recommended accounts)")
    print("=" * 60)
    
    successful_tests = []
    
    for account_id in RECOMMENDED_ACCOUNTS:
        # Find account name
        account_name = next(
            (acc["account_name"] for acc in AVAILABLE_ACCOUNTS if acc["account_id"] == account_id),
            "Unknown"
        )
        
        print(f"\n🧪 Testing connectivity: {account_name} ({account_id})")
        print("-" * 40)
        
        try:
            success = await test_specific_account(account_id, account_name)
            
            if success:
                successful_tests.append((account_id, account_name))
                print(f"✅ {account_name}: Meta API connectivity successful!")
            else:
                print(f"❌ {account_name}: Meta API connectivity failed")
                
        except Exception as e:
            print(f"❌ {account_name}: Error during test - {e}")
        
        print()
    
    print("📊 Connectivity Test Summary:")
    print("=" * 40)
    if successful_tests:
        print(f"✅ Successful connections: {len(successful_tests)}")
        for account_id, account_name in successful_tests:
            print(f"   • {account_name}")
    else:
        print("❌ No successful connections - check Meta API tokens and permissions")
    
    return len(successful_tests) > 0

async def test_all_accounts_connectivity():
    """Test Meta API connectivity with all available accounts."""
    print("🔍 Testing All Accounts Connectivity")
    print("=" * 60)
    
    async with MetaAPITester() as tester:
        # Health check first
        if not await tester.test_health_check():
            print("❌ Service health check failed")
            return False
        
        print()
        
        # Get all accessible accounts
        accounts = await tester.get_accounts()
        if not accounts:
            print("❌ No accounts available")
            return False
        
        print()
        
        # Test metrics
        await tester.test_metrics()
        
        print()
        print("📊 Account Access Summary:")
        print("=" * 30)
        print(f"✅ Total accessible accounts: {len(accounts)}")
        
        # Show which of our known accounts are accessible
        accessible_known = []
        for known_account in AVAILABLE_ACCOUNTS:
            if any(acc.get("account_id") == known_account["account_id"] for acc in accounts):
                accessible_known.append(known_account["account_name"])
        
        if accessible_known:
            print(f"✅ Known accounts accessible: {len(accessible_known)}")
            for name in accessible_known[:5]:  # Show first 5
                print(f"   • {name}")
            if len(accessible_known) > 5:
                print(f"   • ... and {len(accessible_known) - 5} more")
        
        return True


def get_user_choice():
    """Get user's account choice."""
    while True:
        try:
            choice = input("\nEnter account number (1-18), 'r' for recommended test, or 'a' for all accounts: ").strip().lower()
            
            if choice == 'r':
                return 'recommended'
            elif choice == 'a':
                return 'all'
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(AVAILABLE_ACCOUNTS):
                return choice_num - 1  # Convert to 0-based index
            else:
                print(f"❌ Please enter a number between 1 and {len(AVAILABLE_ACCOUNTS)}")
                
        except ValueError:
            print("❌ Please enter a valid number, 'r', or 'a'")


async def main():
    """Main function."""
    print("🚀 Meta Insights Harvester - Account Connectivity Test")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check if account ID/name was provided as command line argument
    if len(sys.argv) > 1:
        account_arg = sys.argv[1]
        
        # Check for special commands
        if account_arg.lower() == "recommended":
            print("📅 Testing Meta API connectivity with recommended accounts...")
            return 0 if await test_recommended_accounts_connectivity() else 1
        elif account_arg.lower() == "all":
            print("📅 Testing Meta API connectivity with all accounts...")
            return 0 if await test_all_accounts_connectivity() else 1
        
        # Find account by ID or name (partial matching)
        selected_account = None
        for account in AVAILABLE_ACCOUNTS:
            if (account_arg.lower() in account["account_id"].lower() or 
                account_arg.lower() in account["account_name"].lower()):
                selected_account = account
                break
        
        if selected_account:
            print(f"🎯 Testing Meta API connectivity with: {selected_account['account_name']}")
            success = await test_specific_account(
                selected_account["account_id"], 
                selected_account["account_name"]
            )
            return 0 if success else 1
        else:
            print(f"❌ Account '{account_arg}' not found")
            print("\n💡 Available account names (partial matching supported):")
            for account in AVAILABLE_ACCOUNTS[:5]:
                print(f"   • {account['account_name']}")
            print("   • ...")
            return 1
    
    # Interactive mode
    print_accounts()
    
    print("💡 Usage Options:")
    print("   ⭐ Starred accounts are more likely to have recent data")
    print("   📊 'r' will test recommended accounts automatically")
    print("   📊 'a' will test all accounts connectivity")
    print("   🎯 Choose a specific number to test one account")
    print()
    print("💡 Command Line Usage:")
    print("   python test_with_account.py 'stahl'        # Test Stahl account")
    print("   python test_with_account.py recommended    # Test recommended accounts")
    print("   python test_with_account.py all           # Test all accounts")
    
    choice = get_user_choice()
    
    if choice == 'recommended':
        print("\n🔄 Running connectivity test on recommended accounts...")
        success = await test_recommended_accounts_connectivity()
        return 0 if success else 1
    elif choice == 'all':
        print("\n🔄 Running connectivity test on all accounts...")
        success = await test_all_accounts_connectivity()
        return 0 if success else 1
    else:
        selected_account = AVAILABLE_ACCOUNTS[choice]
        print(f"\n🎯 Testing selected account: {selected_account['account_name']}")
        
        success = await test_specific_account(
            selected_account["account_id"], 
            selected_account["account_name"]
        )
        return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)