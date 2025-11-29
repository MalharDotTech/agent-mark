#!/usr/bin/env python3
"""
Database setup script for Meta Insights Harvester.

This script handles database creation, schema setup, and validation.
Can be run independently or as part of service startup.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.database import DatabaseService
from app.core.logging import setup_logging, get_logger
from app.core.config import settings

# Setup logging
setup_logging()
logger = get_logger(__name__)


async def setup_database():
    """
    Setup database with all required tables and indexes.
    
    Returns:
        True if setup successful, False otherwise
    """
    print("🗄️  Meta Insights Harvester - Database Setup")
    print("=" * 50)
    
    try:
        # Initialize database service
        db_service = DatabaseService()
        
        print(f"📊 Database URL: {settings.database_url}")
        print(f"🔧 Pool Size: {settings.database_pool_size}")
        print(f"⏱️  Timeout: {settings.database_timeout}s")
        print()
        
        # Initialize database (creates database, tables, indexes)
        print("🔄 Initializing database connection...")
        success = await db_service.initialize()
        
        if not success:
            print("❌ Database initialization failed")
            return False
        
        print("✅ Database initialization completed")
        print()
        
        # Perform health check
        print("🏥 Performing health check...")
        health = await db_service.health_check()
        
        if health['status'] == 'healthy':
            print("✅ Database health check passed")
            print(f"   📊 Pool stats: {health.get('pool_stats', {})}")
        else:
            print(f"❌ Database health check failed: {health.get('error', 'Unknown error')}")
            return False
        
        print()
        
        # Get job statistics
        print("📈 Getting job statistics...")
        stats = await db_service.get_job_statistics()
        print(f"   📋 Total jobs: {stats['total_jobs']}")
        print(f"   📊 By status: {stats['by_status']}")
        
        if stats['recent_job']:
            recent = stats['recent_job']
            print(f"   🕐 Recent job: {recent['id']} ({recent['status']}) at {recent['created_at']}")
        
        print()
        print("🎉 Database setup completed successfully!")
        print()
        print("📖 Next steps:")
        print("   • Start the FastAPI service: uv run uvicorn app.main:app --reload")
        print("   • Run integration tests: uv run python run_test.py")
        print("   • Check database with: psql -U malhar -d meta_ads_db")
        
        # Close database connection
        await db_service.close()
        return True
        
    except Exception as e:
        print(f"💥 Database setup failed: {e}")
        logger.error(f"Database setup error: {e}")
        return False


async def validate_database():
    """
    Validate existing database setup.
    
    Returns:
        True if validation successful, False otherwise
    """
    print("🔍 Meta Insights Harvester - Database Validation")
    print("=" * 50)
    
    try:
        db_service = DatabaseService()
        
        # Test connection
        print("🔄 Testing database connection...")
        await db_service._create_connection_pool()
        
        # Validate schema
        print("🔄 Validating database schema...")
        await db_service._validate_schema()
        
        # Health check
        print("🔄 Performing health check...")
        health = await db_service.health_check()
        
        if health['status'] != 'healthy':
            print(f"❌ Health check failed: {health.get('error')}")
            return False
        
        print("✅ Database validation completed successfully")
        
        # Show statistics
        stats = await db_service.get_job_statistics()
        print(f"📊 Database contains {stats['total_jobs']} jobs")
        
        await db_service.close()
        return True
        
    except Exception as e:
        print(f"❌ Database validation failed: {e}")
        return False


async def reset_database():
    """
    Reset database by dropping and recreating all tables.
    
    WARNING: This will delete all data!
    """
    print("⚠️  Meta Insights Harvester - Database Reset")
    print("=" * 50)
    print("WARNING: This will delete ALL data in the database!")
    
    # Confirm reset
    confirm = input("Type 'RESET' to confirm: ")
    if confirm != 'RESET':
        print("❌ Reset cancelled")
        return False
    
    try:
        db_service = DatabaseService()
        await db_service._create_connection_pool()
        
        # Drop all tables
        print("🔄 Dropping existing tables...")
        async with db_service.get_connection() as conn:
            await conn.execute("DROP TABLE IF EXISTS job_logs CASCADE")
            await conn.execute("DROP TABLE IF EXISTS meta_ads_insights CASCADE")
            await conn.execute("DROP TABLE IF EXISTS extraction_jobs CASCADE")
        
        print("✅ Tables dropped")
        
        # Recreate schema
        print("🔄 Recreating schema...")
        await db_service._create_schema()
        
        print("✅ Database reset completed")
        
        await db_service.close()
        return True
        
    except Exception as e:
        print(f"❌ Database reset failed: {e}")
        return False


def print_usage():
    """Print usage information."""
    print("🗄️  Meta Insights Harvester - Database Management")
    print("=" * 50)
    print()
    print("Usage: python scripts/setup_database.py [command]")
    print()
    print("Commands:")
    print("  setup     - Setup database with tables and indexes (default)")
    print("  validate  - Validate existing database setup")
    print("  reset     - Reset database (WARNING: deletes all data)")
    print("  help      - Show this help message")
    print()
    print("Examples:")
    print("  python scripts/setup_database.py")
    print("  python scripts/setup_database.py setup")
    print("  python scripts/setup_database.py validate")
    print()
    print("Environment:")
    print(f"  DATABASE_URL: {os.getenv('DATABASE_URL', 'Not set')}")
    print(f"  ENABLE_CSV_DEBUG: {os.getenv('ENABLE_CSV_DEBUG', 'false')}")


async def main():
    """Main function."""
    command = sys.argv[1] if len(sys.argv) > 1 else "setup"
    
    if command in ["help", "-h", "--help"]:
        print_usage()
        return 0
    
    success = False
    
    try:
        if command == "setup":
            success = await setup_database()
        elif command == "validate":
            success = await validate_database()
        elif command == "reset":
            success = await reset_database()
        else:
            print(f"❌ Unknown command: {command}")
            print_usage()
            return 1
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⏹️  Operation interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)