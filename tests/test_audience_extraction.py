#!/usr/bin/env python3
"""
Test Audience Insights data extraction from Meta API.

This script tests:
1. Demographic breakdowns (age, gender)
2. Geographic breakdowns (country, region)
3. Device/platform breakdowns
4. Data structure validation for schema design
"""

import asyncio
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import httpx


class AudienceTester:
    """Test audience insights extraction patterns from Meta API."""
    
    def __init__(self, access_tokens: List[str]):
        """Initialize with access tokens."""
        self.access_tokens = access_tokens
        self.current_token_index = 0
        self.base_url = "https://graph.facebook.com/v23.0"
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
    
    def get_next_token(self) -> str:
        """Get next token in round-robin fashion."""
        token = self.access_tokens[self.current_token_index]
        self.current_token_index = (self.current_token_index + 1) % len(self.access_tokens)
        return token
    
    async def make_api_call(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make API call with token rotation."""
        token = self.get_next_token()
        params['access_token'] = token
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ API call failed: {e}")
            if hasattr(response, 'text'):
                print(f"   Response: {response.text[:200]}")
            raise
    
    async def test_demographic_breakdown(
        self,
        account_id: str,
        start_date: str,
        end_date: str,
        breakdown_type: str = 'age',
        level: str = 'campaign'
    ) -> List[Dict[str, Any]]:
        """
        Test demographic breakdown extraction.
        
        Args:
            account_id: Meta ad account ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            breakdown_type: 'age' or 'gender'
            level: Analysis level (campaign, adset, ad)
        """
        print(f"\n👥 Testing Demographic Breakdown: {breakdown_type}")
        print(f"   Account: {account_id}")
        print(f"   Date Range: {start_date} to {end_date}")
        print(f"   Level: {level}")
        
        params = {
            'level': level,
            'fields': 'reach,impressions,spend,clicks,cpm,ctr',
            'time_range': json.dumps({
                'since': start_date,
                'until': end_date
            }),
            'breakdowns': breakdown_type,
        }
        
        endpoint = f"{account_id}/insights"
        data = await self.make_api_call(endpoint, params)
        
        results = data.get('data', [])
        print(f"✅ Retrieved {len(results)} breakdown segments")
        
        # Show sample data structure
        if results:
            print("\n📋 Sample Data Structure:")
            sample = results[0]
            print(json.dumps(sample, indent=2)[:500])
            print("\n   Breakdown field:", sample.get(breakdown_type, 'N/A'))
            print("   Available fields:", list(sample.keys()))
            
            # Show unique breakdown values
            breakdown_values = set(r.get(breakdown_type) for r in results if r.get(breakdown_type))
            print(f"   Unique {breakdown_type} values: {sorted(breakdown_values)}")
        
        return results
    
    async def test_combined_demographic_breakdown(
        self,
        account_id: str,
        start_date: str,
        end_date: str,
        level: str = 'campaign'
    ) -> List[Dict[str, Any]]:
        """
        Test combined demographic breakdown (age + gender).
        
        Args:
            account_id: Meta ad account ID
            start_date: Start date
            end_date: End date
            level: Analysis level
        """
        print(f"\n👥 Testing Combined Demographic Breakdown: age + gender")
        print(f"   Account: {account_id}")
        print(f"   Date Range: {start_date} to {end_date}")
        
        params = {
            'level': level,
            'fields': 'reach,impressions,spend,clicks',
            'time_range': json.dumps({
                'since': start_date,
                'until': end_date
            }),
            'breakdowns': 'age,gender',  # Combined breakdown
        }
        
        endpoint = f"{account_id}/insights"
        data = await self.make_api_call(endpoint, params)
        
        results = data.get('data', [])
        print(f"✅ Retrieved {len(results)} breakdown segments")
        
        # Show sample
        if results:
            print("\n📋 Sample Combined Breakdown:")
            sample = results[0]
            print(f"   Age: {sample.get('age', 'N/A')}")
            print(f"   Gender: {sample.get('gender', 'N/A')}")
            print(f"   Reach: {sample.get('reach', 'N/A')}")
            
            # Show distribution
            age_gender_combos = set(
                (r.get('age'), r.get('gender')) 
                for r in results 
                if r.get('age') and r.get('gender')
            )
            print(f"   Total combinations: {len(age_gender_combos)}")
            print(f"   Examples: {list(age_gender_combos)[:5]}")
        
        return results
    
    async def test_geographic_breakdown(
        self,
        account_id: str,
        start_date: str,
        end_date: str,
        breakdown_type: str = 'country',
        level: str = 'campaign'
    ) -> List[Dict[str, Any]]:
        """
        Test geographic breakdown extraction.
        
        Args:
            account_id: Meta ad account ID
            start_date: Start date
            end_date: End date
            breakdown_type: 'country' or 'region'
            level: Analysis level
        """
        print(f"\n🌍 Testing Geographic Breakdown: {breakdown_type}")
        print(f"   Account: {account_id}")
        print(f"   Date Range: {start_date} to {end_date}")
        
        params = {
            'level': level,
            'fields': 'reach,impressions,spend,clicks',
            'time_range': json.dumps({
                'since': start_date,
                'until': end_date
            }),
            'breakdowns': breakdown_type,
        }
        
        endpoint = f"{account_id}/insights"
        data = await self.make_api_call(endpoint, params)
        
        results = data.get('data', [])
        print(f"✅ Retrieved {len(results)} geographic segments")
        
        # Show sample
        if results:
            print("\n📋 Sample Geographic Data:")
            sample = results[0]
            print(f"   {breakdown_type.title()}: {sample.get(breakdown_type, 'N/A')}")
            print(f"   Reach: {sample.get('reach', 'N/A')}")
            
            # Show top locations
            geo_values = [(r.get(breakdown_type), int(r.get('reach', 0))) for r in results if r.get(breakdown_type)]
            geo_values.sort(key=lambda x: x[1], reverse=True)
            print(f"   Top 5 locations by reach:")
            for loc, reach in geo_values[:5]:
                print(f"      {loc}: {reach:,}")
        
        return results
    
    async def test_device_breakdown(
        self,
        account_id: str,
        start_date: str,
        end_date: str,
        level: str = 'campaign'
    ) -> List[Dict[str, Any]]:
        """
        Test device/platform breakdown extraction.
        
        Args:
            account_id: Meta ad account ID
            start_date: Start date
            end_date: End date
            level: Analysis level
        """
        print(f"\n📱 Testing Device/Platform Breakdown")
        print(f"   Account: {account_id}")
        print(f"   Date Range: {start_date} to {end_date}")
        
        params = {
            'level': level,
            'fields': 'reach,impressions,spend,clicks',
            'time_range': json.dumps({
                'since': start_date,
                'until': end_date
            }),
            'breakdowns': 'device_platform',  # or 'publisher_platform'
        }
        
        endpoint = f"{account_id}/insights"
        data = await self.make_api_call(endpoint, params)
        
        results = data.get('data', [])
        print(f"✅ Retrieved {len(results)} device segments")
        
        # Show sample
        if results:
            print("\n📋 Device Distribution:")
            device_data = {}
            for r in results:
                device = r.get('device_platform', 'unknown')
                reach = int(r.get('reach', 0))
                device_data[device] = device_data.get(device, 0) + reach
            
            for device, reach in sorted(device_data.items(), key=lambda x: x[1], reverse=True):
                print(f"   {device}: {reach:,} reach")
        
        return results
    
    async def test_campaign_level_insights(
        self,
        account_id: str,
        start_date: str,
        end_date: str,
        campaign_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Test campaign-level insights with specific campaigns.
        
        Args:
            account_id: Meta ad account ID
            start_date: Start date
            end_date: End date
            campaign_ids: List of campaign IDs to analyze
        """
        print(f"\n📊 Testing Campaign-Level Audience Insights")
        print(f"   Campaigns: {len(campaign_ids)}")
        
        params = {
            'level': 'campaign',
            'fields': 'campaign_id,campaign_name,reach,impressions,spend',
            'time_range': json.dumps({
                'since': start_date,
                'until': end_date
            }),
            'filtering': json.dumps([{
                'field': 'campaign.id',
                'operator': 'IN',
                'value': campaign_ids
            }]),
            'breakdowns': 'age,gender',
        }
        
        endpoint = f"{account_id}/insights"
        data = await self.make_api_call(endpoint, params)
        
        results = data.get('data', [])
        print(f"✅ Retrieved {len(results)} campaign-demographic segments")
        
        # Group by campaign
        if results:
            campaigns_found = set(r.get('campaign_name') for r in results if r.get('campaign_name'))
            print(f"   Campaigns with data: {len(campaigns_found)}")
            for camp_name in list(campaigns_found)[:3]:
                print(f"      • {camp_name}")
        
        return results


async def get_campaigns(account_id: str, token: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Helper function to get campaigns for testing."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"https://graph.facebook.com/v23.0/{account_id}/campaigns"
        params = {
            'fields': 'id,name,status',
            'limit': limit,
            'access_token': token
        }
        
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('data', [])


async def test_with_recommended_account(access_tokens: List[str]):
    """Test audience extraction with a recommended account."""
    # Use Porter - BM - new as default test account (accessible)
    test_account_id = "act_547569015598645"
    test_account_name = "Porter - BM - new"
    
    # Date range: last 30 days for better demographic data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print("🧪 Audience Insights Extraction Test")
    print("=" * 60)
    print(f"Test Account: {test_account_name}")
    print(f"Account ID: {test_account_id}")
    print(f"Tokens available: {len(access_tokens)}")
    print("=" * 60)
    
    async with AudienceTester(access_tokens) as tester:
        try:
            # Get some campaigns first
            print("\n📋 Fetching campaigns for testing...")
            campaigns = await get_campaigns(test_account_id, access_tokens[0], limit=5)
            print(f"✅ Found {len(campaigns)} campaigns")
            
            # Test 1: Age Breakdown
            print("\n" + "="*60)
            print("TEST 1: Age Breakdown")
            print("="*60)
            
            age_results = await tester.test_demographic_breakdown(
                account_id=test_account_id,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                breakdown_type='age',
                level='account'
            )
            
            # Test 2: Gender Breakdown
            print("\n" + "="*60)
            print("TEST 2: Gender Breakdown")
            print("="*60)
            
            gender_results = await tester.test_demographic_breakdown(
                account_id=test_account_id,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                breakdown_type='gender',
                level='account'
            )
            
            # Test 3: Combined Age + Gender
            print("\n" + "="*60)
            print("TEST 3: Combined Age + Gender Breakdown")
            print("="*60)
            
            combined_results = await tester.test_combined_demographic_breakdown(
                account_id=test_account_id,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                level='account'
            )
            
            # Test 4: Geographic - Country
            print("\n" + "="*60)
            print("TEST 4: Country Breakdown")
            print("="*60)
            
            country_results = await tester.test_geographic_breakdown(
                account_id=test_account_id,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                breakdown_type='country',
                level='account'
            )
            
            # Test 5: Device/Platform
            print("\n" + "="*60)
            print("TEST 5: Device Platform Breakdown")
            print("="*60)
            
            device_results = await tester.test_device_breakdown(
                account_id=test_account_id,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                level='account'
            )
            
            # Test 6: Campaign-Level Demographics (if campaigns available)
            if campaigns:
                print("\n" + "="*60)
                print("TEST 6: Campaign-Level Demographics")
                print("="*60)
                
                campaign_ids = [c['id'] for c in campaigns[:3]]
                campaign_demo_results = await tester.test_campaign_level_insights(
                    account_id=test_account_id,
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d'),
                    campaign_ids=campaign_ids
                )
            
            # Final Summary
            print("\n" + "="*60)
            print("✅ TEST SUMMARY")
            print("="*60)
            print(f"Age segments: {len(age_results)}")
            print(f"Gender segments: {len(gender_results)}")
            print(f"Combined age+gender segments: {len(combined_results)}")
            print(f"Country segments: {len(country_results)}")
            print(f"Device segments: {len(device_results)}")
            if campaigns:
                print(f"Campaign demographic segments: {len(campaign_demo_results)}")
            print(f"Total API calls made: ~{tester.current_token_index}")
            
            # Data structure for schema design
            print("\n📋 Schema Design Notes:")
            print("   Audience Insights fields needed:")
            if age_results:
                print(f"   Age breakdown: {list(age_results[0].keys())}")
            if gender_results:
                print(f"   Gender breakdown: {list(gender_results[0].keys())}")
            if country_results:
                print(f"   Country breakdown: {list(country_results[0].keys())}")
            
            print("\n   Breakdown types to support:")
            print("   • age (values: 18-24, 25-34, 35-44, 45-54, 55-64, 65+)")
            print("   • gender (values: male, female, unknown)")
            print("   • country (values: US, IN, GB, etc.)")
            print("   • region (for more granular geographic data)")
            print("   • device_platform (values: mobile, desktop, etc.)")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def get_access_tokens() -> List[str]:
    """Get access tokens from environment or config."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    tokens_str = os.getenv('META_ACCESS_TOKENS', '')
    if not tokens_str:
        print("❌ No META_ACCESS_TOKENS found in environment")
        print("   Please set META_ACCESS_TOKENS in .env file")
        sys.exit(1)
    
    tokens = [t.strip() for t in tokens_str.split(',') if t.strip()]
    print(f"✅ Loaded {len(tokens)} access token(s)")
    
    return tokens


async def main():
    """Main test function."""
    print("🚀 Meta Audience Insights Extraction Test")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Get tokens
    tokens = get_access_tokens()
    
    # Run tests
    success = await test_with_recommended_account(tokens)
    
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
        import traceback
        traceback.print_exc()
        sys.exit(1)

