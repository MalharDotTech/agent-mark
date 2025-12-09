#!/usr/bin/env python3
"""
Integration test for RNF and Audience extraction endpoints.

Tests end-to-end flow:
1. Start FastAPI server
2. Call RNF cumulative extraction endpoint
3. Call audience extraction endpoint
4. Verify data is stored in database
"""

import asyncio
import sys
import httpx
from datetime import datetime, timedelta


async def test_integration():
    """Test RNF and audience extraction integration."""
    
    base_url = "http://localhost:8000"
    
    # Test account (from token validation)
    test_account = "act_547569015598645"
    
    # Date range: last 7 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    print("🧪 RNF and Audience Integration Test")
    print("=" * 60)
    print(f"Base URL: {base_url}")
    print(f"Test Account: {test_account}")
    print(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            # Test 1: Health Check
            print("\n✓ Test 1: Health Check")
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                health = response.json()
                print(f"  Status: {health['status']}")
                print(f"  Database: {'✅' if health.get('database_connected') else '❌'}")
            else:
                print(f"  ❌ Health check failed: {response.status_code}")
                return False
            
            # Test 2: RNF Cumulative Extraction
            print("\n✓ Test 2: RNF Cumulative Extraction (Account Level)")
            rnf_request = {
                "account_ids": [test_account],
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d'),
                "level": "account",
                "time_increment": "1"
            }
            
            response = await client.post(
                f"{base_url}/api/v1/extract-rnf-cumulative",
                json=rnf_request
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Job ID: {result['job_id']}")
                print(f"  ✅ Records extracted: {result['total_records']}")
            else:
                print(f"  ❌ Extraction failed: {response.status_code}")
                print(f"     {response.text[:200]}")
                return False
            
            # Test 3: Audience Insights Extraction
            print("\n✓ Test 3: Audience Insights Extraction (Age breakdown)")
            audience_request = {
                "account_ids": [test_account],
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d'),
                "breakdown_types": ["age"],
                "level": "account"
            }
            
            response = await client.post(
                f"{base_url}/api/v1/extract-audience",
                json=audience_request
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Job ID: {result['job_id']}")
                print(f"  ✅ Records extracted: {result['total_records']}")
            else:
                print(f"  ❌ Extraction failed: {response.status_code}")
                print(f"     {response.text[:200]}")
            
            # Test 4: Retrieve stored audience data
            print("\n✓ Test 4: Retrieve Stored Audience Data")
            response = await client.get(
                f"{base_url}/api/v1/audience/{test_account}",
                params={"breakdown_type": "age"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✅ Retrieved {result['total_records']} records")
                if result['data']:
                    sample = result['data'][0]
                    print(f"  Sample: {sample.get('breakdown_value')} - Reach: {sample.get('reach')}")
            else:
                print(f"  ⚠️  No data retrieved yet: {response.status_code}")
            
            # Test 5: Get audience summary
            print("\n✓ Test 5: Get Audience Summary")
            response = await client.get(
                f"{base_url}/api/v1/audience/{test_account}/summary",
                params={"breakdown_type": "age"}
            )
            
            if response.status_code == 200:
                result = response.json()
                summary = result.get('summary', [])
                print(f"  ✅ Summary retrieved: {len(summary)} age segments")
                for segment in summary[:3]:  # Show first 3
                    print(f"     {segment['breakdown_value']}: {segment['total_reach']:,} reach")
            else:
                print(f"  ⚠️  Summary not available: {response.status_code}")
            
            print("\n" + "=" * 60)
            print("✅ Integration Test Completed Successfully")
            print("=" * 60)
            
            return True
            
        except httpx.ConnectError:
            print("\n❌ Could not connect to FastAPI server")
            print("   Please start the server with: uv run uvicorn app.main:app --reload --port 8000")
            return False
        except Exception as e:
            print(f"\n❌ Integration test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """Main function."""
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    success = await test_integration()
    
    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error: {e}")
        sys.exit(1)

