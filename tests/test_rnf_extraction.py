#!/usr/bin/env python3
"""
Test RNF (Reach & Frequency) data extraction from Meta API.

This script tests:
1. Cumulative reach & frequency extraction
2. Audience overlap analysis (3-API-call pattern)
3. Token rotation across multiple calls
4. Data structure validation for schema design
"""

import asyncio
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import httpx
from itertools import combinations


class RNFTester:
    """Test RNF data extraction patterns from Meta API."""
    
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
    
    async def test_cumulative_reach_frequency(
        self,
        account_id: str,
        start_date: str,
        end_date: str,
        level: str = 'account',
        time_increment: str = '1',
        entity_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Test cumulative reach & frequency extraction.
        
        Args:
            account_id: Meta ad account ID (with act_ prefix)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            level: Analysis level (account, campaign, adset, ad)
            time_increment: '1' for daily, '7' for weekly, 'monthly'
            entity_ids: Optional list of campaign/adset/ad IDs to filter
        """
        print(f"\n📊 Testing Cumulative R&F Extraction")
        print(f"   Account: {account_id}")
        print(f"   Date Range: {start_date} to {end_date}")
        print(f"   Level: {level}")
        print(f"   Time Increment: {time_increment}")
        
        params = {
            'level': level,
            'fields': 'reach,frequency,impressions,spend,clicks,cpm,cpp,ctr',
            'time_range': json.dumps({
                'since': start_date,
                'until': end_date
            }),
            'time_increment': time_increment,
        }
        
        # Add filtering if specific entities selected
        if entity_ids and level != 'account':
            params['filtering'] = json.dumps([{
                'field': f'{level}.id',
                'operator': 'IN',
                'value': entity_ids
            }])
        
        endpoint = f"{account_id}/insights"
        data = await self.make_api_call(endpoint, params)
        
        results = data.get('data', [])
        print(f"✅ Retrieved {len(results)} time periods")
        
        # Show sample data structure
        if results:
            print("\n📋 Sample Data Structure:")
            sample = results[0]
            print(json.dumps(sample, indent=2)[:500])
            print("\n   Fields received:", list(sample.keys()))
        
        return results
    
    async def get_campaigns(self, account_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get campaigns for testing overlap analysis."""
        print(f"\n📋 Fetching campaigns for {account_id}")
        
        params = {
            'fields': 'id,name,status',
            'limit': limit
        }
        
        endpoint = f"{account_id}/campaigns"
        data = await self.make_api_call(endpoint, params)
        
        campaigns = data.get('data', [])
        print(f"✅ Found {len(campaigns)} campaigns")
        for camp in campaigns[:5]:
            print(f"   • {camp['name']} ({camp['id']})")
        
        return campaigns
    
    async def calculate_overlap_for_pair(
        self,
        account_id: str,
        level: str,
        entity1_id: str,
        entity1_name: str,
        entity2_id: str,
        entity2_name: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Calculate audience overlap for a single pair using 3-API-call pattern.
        
        Pattern:
        1. Get reach for entity1
        2. Get reach for entity2
        3. Get combined reach for [entity1, entity2]
        4. Calculate overlap = reach1 + reach2 - combined_reach
        """
        print(f"\n🔄 Calculating overlap: {entity1_name} vs {entity2_name}")
        
        time_range = json.dumps({
            'since': start_date,
            'until': end_date
        })
        
        # Call 1: Reach for entity1
        print(f"   Call 1/3: Getting reach for {entity1_name}")
        params1 = {
            'level': level,
            'fields': 'reach',
            'time_range': time_range,
            'filtering': json.dumps([{
                'field': f'{level}.id',
                'operator': 'IN',
                'value': [entity1_id]
            }])
        }
        data1 = await self.make_api_call(f"{account_id}/insights", params1)
        reach1 = int(data1['data'][0].get('reach', 0)) if data1.get('data') else 0
        print(f"   ✓ Reach1: {reach1:,}")
        
        # Call 2: Reach for entity2
        print(f"   Call 2/3: Getting reach for {entity2_name}")
        params2 = {
            'level': level,
            'fields': 'reach',
            'time_range': time_range,
            'filtering': json.dumps([{
                'field': f'{level}.id',
                'operator': 'IN',
                'value': [entity2_id]
            }])
        }
        data2 = await self.make_api_call(f"{account_id}/insights", params2)
        reach2 = int(data2['data'][0].get('reach', 0)) if data2.get('data') else 0
        print(f"   ✓ Reach2: {reach2:,}")
        
        # Call 3: Combined reach for both entities
        print(f"   Call 3/3: Getting combined reach")
        params_combined = {
            'level': 'account',  # Account level to get combined reach
            'fields': 'reach',
            'time_range': time_range,
            'filtering': json.dumps([{
                'field': f'{level}.id',
                'operator': 'IN',
                'value': [entity1_id, entity2_id]
            }])
        }
        data_combined = await self.make_api_call(f"{account_id}/insights", params_combined)
        combined_reach = int(data_combined['data'][0].get('reach', 0)) if data_combined.get('data') else 0
        print(f"   ✓ Combined Reach: {combined_reach:,}")
        
        # Calculate overlap
        overlap_count = max(0, reach1 + reach2 - combined_reach)
        overlap_percentage = (overlap_count / min(reach1, reach2) * 100) if min(reach1, reach2) > 0 else 0
        
        print(f"   📊 Overlap: {overlap_count:,} ({overlap_percentage:.1f}%)")
        
        return {
            'entity1_id': entity1_id,
            'entity1_name': entity1_name,
            'entity2_id': entity2_id,
            'entity2_name': entity2_name,
            'reach1': reach1,
            'reach2': reach2,
            'combined_reach': combined_reach,
            'overlap_count': overlap_count,
            'overlap_percentage': overlap_percentage
        }
    
    async def test_overlap_analysis(
        self,
        account_id: str,
        start_date: str,
        end_date: str,
        level: str = 'campaign',
        max_pairs: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Test overlap analysis for multiple pairs.
        
        Args:
            account_id: Meta ad account ID
            start_date: Start date
            end_date: End date
            level: campaign or adset
            max_pairs: Maximum number of pairs to test (to limit API calls)
        """
        print(f"\n🔍 Testing Overlap Analysis")
        print(f"   Account: {account_id}")
        print(f"   Level: {level}")
        print(f"   Max pairs to test: {max_pairs}")
        
        # Get campaigns or adsets
        if level == 'campaign':
            entities = await self.get_campaigns(account_id, limit=10)
        else:
            # For adsets, we'd need similar function
            print("   ⚠️  Adset level not implemented in test")
            return []
        
        if len(entities) < 2:
            print("   ⚠️  Need at least 2 entities for overlap analysis")
            return []
        
        # Test first few pairs
        pairs = list(combinations(entities[:min(5, len(entities))], 2))[:max_pairs]
        print(f"   Testing {len(pairs)} pairs out of {len(list(combinations(entities, 2)))} total")
        
        overlap_results = []
        
        for i, (entity1, entity2) in enumerate(pairs, 1):
            print(f"\n   Pair {i}/{len(pairs)}:")
            try:
                result = await self.calculate_overlap_for_pair(
                    account_id,
                    level,
                    entity1['id'],
                    entity1['name'],
                    entity2['id'],
                    entity2['name'],
                    start_date,
                    end_date
                )
                overlap_results.append(result)
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"   ❌ Failed to calculate overlap: {e}")
        
        # Summary
        if overlap_results:
            print(f"\n📊 Overlap Analysis Summary:")
            print(f"   Pairs analyzed: {len(overlap_results)}")
            avg_overlap = sum(r['overlap_percentage'] for r in overlap_results) / len(overlap_results)
            print(f"   Average overlap: {avg_overlap:.1f}%")
            
            # Show top overlapping pair
            top_pair = max(overlap_results, key=lambda x: x['overlap_percentage'])
            print(f"   Highest overlap: {top_pair['entity1_name']} ↔ {top_pair['entity2_name']}")
            print(f"                    {top_pair['overlap_percentage']:.1f}%")
        
        return overlap_results


async def test_with_recommended_account(access_tokens: List[str]):
    """Test RNF extraction with a recommended account."""
    # Use Porter - BM - new as default test account (accessible)
    test_account_id = "act_547569015598645"
    test_account_name = "Porter - BM - new"
    
    # Date range: last 7 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    print("🧪 RNF Extraction Test")
    print("=" * 60)
    print(f"Test Account: {test_account_name}")
    print(f"Account ID: {test_account_id}")
    print(f"Tokens available: {len(access_tokens)}")
    print("=" * 60)
    
    async with RNFTester(access_tokens) as tester:
        try:
            # Test 1: Cumulative R&F - Account Level (Daily)
            print("\n" + "="*60)
            print("TEST 1: Cumulative R&F - Account Level (Daily)")
            print("="*60)
            
            results_daily = await tester.test_cumulative_reach_frequency(
                account_id=test_account_id,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                level='account',
                time_increment='1'
            )
            
            # Test 2: Cumulative R&F - Campaign Level
            print("\n" + "="*60)
            print("TEST 2: Cumulative R&F - Campaign Level")
            print("="*60)
            
            # First get campaigns
            campaigns = await tester.get_campaigns(test_account_id, limit=3)
            
            if campaigns:
                campaign_ids = [c['id'] for c in campaigns[:2]]  # Test with first 2 campaigns
                
                results_campaign = await tester.test_cumulative_reach_frequency(
                    account_id=test_account_id,
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d'),
                    level='campaign',
                    time_increment='1',
                    entity_ids=campaign_ids
                )
            
            # Test 3: Overlap Analysis
            print("\n" + "="*60)
            print("TEST 3: Audience Overlap Analysis")
            print("="*60)
            
            overlap_results = await tester.test_overlap_analysis(
                account_id=test_account_id,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                level='campaign',
                max_pairs=3  # Limit to 3 pairs = 9 API calls
            )
            
            # Final Summary
            print("\n" + "="*60)
            print("✅ TEST SUMMARY")
            print("="*60)
            print(f"Daily R&F records: {len(results_daily)}")
            print(f"Campaign R&F records: {len(results_campaign) if campaigns else 0}")
            print(f"Overlap pairs analyzed: {len(overlap_results)}")
            print(f"Total API calls made: ~{tester.current_token_index}")
            print(f"Tokens rotated: {tester.current_token_index // len(access_tokens)} times")
            
            # Data structure for schema design
            print("\n📋 Schema Design Notes:")
            print("   RNF Cumulative fields needed:")
            if results_daily:
                print(f"   {list(results_daily[0].keys())}")
            print("\n   RNF Overlap fields needed:")
            if overlap_results:
                print(f"   {list(overlap_results[0].keys())}")
            
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
    print("🚀 Meta RNF Data Extraction Test")
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

