#!/usr/bin/env python3
"""
Dashboard Generation Script
Automatically generates dashboard notebooks for all registered job types.
"""

import sys
import logging
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from notebooks.utils.dashboard_factory import dashboard_factory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Generate dashboard notebooks for all job types."""
    print("🚀 Starting dashboard generation...")
    
    try:
        # Discover and create dashboards
        results = dashboard_factory.discover_and_create_dashboards()
        
        print(f"\n📊 Dashboard Generation Results:")
        print("=" * 50)
        
        created_count = 0
        existed_count = 0
        error_count = 0
        
        for result in results:
            job_type = result['job_type_id']
            job_name = result['job_name']
            
            if result['error']:
                print(f"❌ {job_name} ({job_type}): ERROR - {result['error']}")
                error_count += 1
            elif result['created']:
                print(f"✅ {job_name} ({job_type}): CREATED - {result['notebook_filename']}")
                created_count += 1
            elif result['existed']:
                print(f"ℹ️  {job_name} ({job_type}): EXISTS - {result['notebook_filename']}")
                existed_count += 1
        
        print("=" * 50)
        print(f"📈 Summary:")
        print(f"  • Created: {created_count}")
        print(f"  • Already existed: {existed_count}")
        print(f"  • Errors: {error_count}")
        print(f"  • Total job types: {len(results)}")
        
        if error_count == 0:
            print("\n🎉 All dashboards generated successfully!")
        else:
            print(f"\n⚠️  {error_count} errors occurred during generation.")
            return 1
        
        # Show dashboard registry
        print(f"\n📋 Dashboard Registry:")
        print("=" * 50)
        
        registry = dashboard_factory.get_dashboard_registry()
        for dashboard in registry:
            status = "✅ Active" if dashboard['notebook_exists'] else "❌ Missing"
            data_status = "📊 Has Data" if dashboard['data_stats']['has_data'] else "📭 No Data"
            
            print(f"{dashboard['job_name']} ({dashboard['job_type_id']})")
            print(f"  Status: {status}")
            print(f"  Data: {data_status}")
            print(f"  Records: {dashboard['data_stats']['total_records']:,}")
            print(f"  Accounts: {dashboard['data_stats']['account_count']}")
            print(f"  File: {dashboard['notebook_filename']}")
            print()
        
        return 0
        
    except Exception as e:
        logger.error(f"Dashboard generation failed: {e}")
        print(f"❌ Dashboard generation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())