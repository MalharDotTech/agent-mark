#!/usr/bin/env python3
"""Database initialization script for Meta Ads SQLite database."""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import DatabaseManager
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_database():
    """Initialize the SQLite database with all required tables and default data."""
    try:
        logger.info("Starting database initialization...")
        
        # Create database manager
        db_manager = DatabaseManager()
        
        # Create all tables
        logger.info("Creating database tables...")
        db_manager.create_tables()
        
        # Initialize default job types
        logger.info("Initializing default job types...")
        db_manager.initialize_default_job_types()
        
        # Verify database health
        if db_manager.health_check():
            logger.info("Database initialization completed successfully!")
            logger.info(f"Database location: {db_manager.db_path}")
        else:
            logger.error("Database health check failed after initialization")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


async def initialize_database_async():
    """Initialize the SQLite database asynchronously."""
    try:
        logger.info("Starting async database initialization...")
        
        # Create database manager
        db_manager = DatabaseManager()
        
        # Create all tables
        logger.info("Creating database tables...")
        await db_manager.create_tables_async()
        
        # Initialize default job types
        logger.info("Initializing default job types...")
        await db_manager.initialize_default_job_types_async()
        
        # Verify database health
        if await db_manager.health_check_async():
            logger.info("Database initialization completed successfully!")
            logger.info(f"Database location: {db_manager.db_path}")
        else:
            logger.error("Database health check failed after initialization")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


def reset_database():
    """Reset the database by removing the existing file and reinitializing."""
    try:
        db_path = Path(settings.sqlite_db_path)
        
        if db_path.exists():
            logger.info(f"Removing existing database: {db_path}")
            db_path.unlink()
        
        return initialize_database()
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        return False


def show_database_info():
    """Display information about the current database."""
    try:
        db_manager = DatabaseManager()
        
        if not Path(db_manager.db_path).exists():
            logger.info("Database does not exist yet. Run initialization first.")
            return
        
        logger.info(f"Database location: {db_manager.db_path}")
        
        # Check health
        if db_manager.health_check():
            logger.info("Database connection: OK")
        else:
            logger.error("Database connection: FAILED")
            return
        
        # Show table information
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            logger.info("Database tables:")
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                logger.info(f"  - {table_name}: {count} records")
        
    except Exception as e:
        logger.error(f"Failed to show database info: {e}")


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python init_database.py [init|reset|info|async-init]")
        print("  init      - Initialize database with tables and default data")
        print("  reset     - Remove existing database and reinitialize")
        print("  info      - Show database information")
        print("  async-init - Initialize database asynchronously")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "init":
        success = initialize_database()
        sys.exit(0 if success else 1)
    
    elif command == "reset":
        success = reset_database()
        sys.exit(0 if success else 1)
    
    elif command == "info":
        show_database_info()
        sys.exit(0)
    
    elif command == "async-init":
        success = asyncio.run(initialize_database_async())
        sys.exit(0 if success else 1)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()