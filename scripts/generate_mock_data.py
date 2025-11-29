import asyncio
import random
from datetime import datetime, timedelta
import uuid
import sys
from pathlib import Path

# Add project root to path to allow imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.core.database import DatabaseManager

# Configuration
ACCOUNT_ID = "act_272178626"
ACCOUNT_NAME = "Mock Ad Account"
DAYS_OF_DATA = 30

# Mock Data Definitions
CAMPAIGNS = [
    {"name": "Summer Sale 2024", "objective": "OUTCOME_SALES"},
    {"name": "Brand Awareness Q4", "objective": "OUTCOME_AWARENESS"},
    {"name": "Retargeting - Cart Abandoners", "objective": "OUTCOME_SALES"},
    {"name": "New User Acquisition", "objective": "OUTCOME_LEADS"},
]

ADSETS = [
    "US - 18-65+ - Broad",
    "US - 25-45 - Tech Interest",
    "UK - 18-65+ - Lookalike 1%",
    "CA - 21-55 - Competitors",
]

ADS = [
    "Video - Product Demo",
    "Image - Lifestyle Shot",
    "Carousel - Top Sellers",
    "Video - Customer Testimonial",
]

async def generate_mock_data():
    print(f"🚀 Starting mock data generation for account {ACCOUNT_ID}...")
    
    db_manager = DatabaseManager()
    
    # 1. Ensure Account Exists
    print("Checking account...")
    await db_manager.insert_account_async(
        account_id=ACCOUNT_ID,
        account_name=ACCOUNT_NAME,
        api_token_key="mock_token"
    )
    print(f"✅ Account {ACCOUNT_NAME} ({ACCOUNT_ID}) ensured.")

    # 2. Generate Data
    print(f"Generating data for the last {DAYS_OF_DATA} days...")
    
    data_to_insert = []
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=DAYS_OF_DATA)
    
    # Create persistent IDs for consistency across days
    campaign_map = {}
    for camp in CAMPAIGNS:
        campaign_map[camp['name']] = {
            'id': str(random.randint(10000000, 99999999)),
            'adsets': {}
        }
        for adset_name in ADSETS:
            campaign_map[camp['name']]['adsets'][adset_name] = {
                'id': str(random.randint(10000000, 99999999)),
                'ads': {}
            }
            for ad_name in ADS:
                campaign_map[camp['name']]['adsets'][adset_name]['ads'][ad_name] = {
                    'id': str(random.randint(10000000, 99999999))
                }

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.isoformat()
        
        for camp_name, camp_data in campaign_map.items():
            # Randomly skip some campaigns on some days
            if random.random() < 0.1:
                continue
                
            for adset_name, adset_data in camp_data['adsets'].items():
                # Randomly skip some adsets
                if random.random() < 0.2:
                    continue
                    
                for ad_name, ad_data in adset_data['ads'].items():
                    # Randomly skip some ads
                    if random.random() < 0.3:
                        continue
                    
                    # Generate Metrics
                    impressions = random.randint(100, 5000)
                    cpm = random.uniform(5.0, 25.0)
                    spend = (impressions / 1000) * cpm
                    
                    ctr = random.uniform(0.5, 3.5) / 100
                    clicks = int(impressions * ctr)
                    
                    cpc = spend / clicks if clicks > 0 else 0
                    
                    reach = int(impressions * random.uniform(0.8, 0.95))
                    frequency = impressions / reach if reach > 0 else 0
                    
                    record = {
                        'account_id': ACCOUNT_ID,
                        'date_start': date_str,
                        'date_stop': date_str,
                        'campaign_id': camp_data['id'],
                        'campaign_name': camp_name,
                        'adset_id': adset_data['id'],
                        'adset_name': adset_name,
                        'ad_id': ad_data['id'],
                        'ad_name': ad_name,
                        'impressions': impressions,
                        'clicks': clicks,
                        'spend': round(spend, 2),
                        'reach': reach,
                        'frequency': round(frequency, 2),
                        'cpm': round(cpm, 2),
                        'cpc': round(cpc, 2),
                        'ctr': round(ctr * 100, 2) # Store as percentage
                    }
                    data_to_insert.append(record)
        
        current_date += timedelta(days=1)

    # 3. Insert Data
    print(f"Inserting {len(data_to_insert)} records...")
    await db_manager.insert_bulk_ad_performance_data_async(data_to_insert)
    
    print("✅ Mock data generation complete!")
    print(f"📊 Summary: {len(data_to_insert)} records created for {DAYS_OF_DATA} days.")

if __name__ == "__main__":
    asyncio.run(generate_mock_data())
