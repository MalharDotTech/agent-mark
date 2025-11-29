"""SQLite database utilities for Meta Ads service."""

import sqlite3
import asyncio
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database connections and operations."""
    
    def __init__(self, db_path: str = None):
        """Initialize database manager with optional custom path."""
        self.db_path = db_path or settings.sqlite_db_path
        self._ensure_data_directory()
    
    def _ensure_data_directory(self):
        """Ensure the data directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a SQLite database connection."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
            return conn
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise ConnectionError(f"Database connection failed: {e}")
    
    async def get_connection_async(self) -> sqlite3.Connection:
        """Get a SQLite database connection asynchronously."""
        # Run the synchronous connection in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_connection)
    
    def create_tables(self):
        """Create all required database tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create accounts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id TEXT PRIMARY KEY,
                    account_name TEXT NOT NULL,
                    api_token_key TEXT NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create data_job_types table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS data_job_types (
                    job_type_id TEXT PRIMARY KEY,
                    job_name TEXT NOT NULL,
                    description TEXT,
                    table_name TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Create ad_performance_data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ad_performance_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id TEXT NOT NULL,
                    date_start DATE NOT NULL,
                    date_stop DATE NOT NULL,
                    campaign_id TEXT,
                    campaign_name TEXT,
                    adset_id TEXT,
                    adset_name TEXT,
                    ad_id TEXT,
                    ad_name TEXT,
                    impressions INTEGER,
                    clicks INTEGER,
                    spend DECIMAL(10,2),
                    reach INTEGER,
                    frequency DECIMAL(5,2),
                    cpm DECIMAL(10,2),
                    cpc DECIMAL(10,2),
                    ctr DECIMAL(5,2),
                    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
                )
            """)
            
            # Create indexes for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ad_performance_account_date 
                ON ad_performance_data(account_id, date_start, date_stop)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ad_performance_campaign 
                ON ad_performance_data(campaign_id)
            """)
            
            conn.commit()
            logger.info("Database tables created successfully")
    
    async def create_tables_async(self):
        """Create all required database tables asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.create_tables)
    
    def get_accounts(self) -> List[Dict[str, Any]]:
        """Retrieve all accounts from the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts ORDER BY account_name")
            return [dict(row) for row in cursor.fetchall()]
    
    async def get_accounts_async(self) -> List[Dict[str, Any]]:
        """Retrieve all accounts from the database asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_accounts)
    
    def get_data_job_types(self) -> List[Dict[str, Any]]:
        """Retrieve all active data job types."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM data_job_types 
                WHERE is_active = TRUE 
                ORDER BY job_name
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    async def get_data_job_types_async(self) -> List[Dict[str, Any]]:
        """Retrieve all active data job types asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_data_job_types)
    
    def query_data(
        self, 
        table_name: str, 
        account_id: str = None, 
        filters: Dict[str, Any] = None,
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """Query data from a specific table with optional filters."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build the query
            query = f"SELECT * FROM {table_name}"
            params = []
            conditions = []
            
            if account_id:
                conditions.append("account_id = ?")
                params.append(account_id)
            
            if filters:
                for key, value in filters.items():
                    conditions.append(f"{key} = ?")
                    params.append(value)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY extracted_at DESC"
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    async def query_data_async(
        self, 
        table_name: str, 
        account_id: str = None, 
        filters: Dict[str, Any] = None,
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """Query data from a specific table with optional filters asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.query_data, table_name, account_id, filters, limit
        )
    
    def insert_account(self, account_id: str, account_name: str, api_token_key: str):
        """Insert or update an account record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO accounts 
                (account_id, account_name, api_token_key, last_updated)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (account_id, account_name, api_token_key))
            conn.commit()
    
    async def insert_account_async(self, account_id: str, account_name: str, api_token_key: str):
        """Insert or update an account record asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.insert_account, account_id, account_name, api_token_key)
    
    def insert_ad_performance_data(self, data: Dict[str, Any]):
        """Insert ad performance data record."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ad_performance_data (
                    account_id, date_start, date_stop, campaign_id, campaign_name,
                    adset_id, adset_name, ad_id, ad_name, impressions, clicks,
                    spend, reach, frequency, cpm, cpc, ctr
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('account_id'),
                data.get('date_start'),
                data.get('date_stop'),
                data.get('campaign_id'),
                data.get('campaign_name'),
                data.get('adset_id'),
                data.get('adset_name'),
                data.get('ad_id'),
                data.get('ad_name'),
                data.get('impressions'),
                data.get('clicks'),
                data.get('spend'),
                data.get('reach'),
                data.get('frequency'),
                data.get('cpm'),
                data.get('cpc'),
                data.get('ctr')
            ))
            conn.commit()
    
    async def insert_ad_performance_data_async(self, data: Dict[str, Any]):
        """Insert ad performance data record asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.insert_ad_performance_data, data)
    
    def insert_bulk_ad_performance_data(self, data_list: List[Dict[str, Any]]):
        """Insert multiple ad performance data records efficiently."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            records = []
            for data in data_list:
                records.append((
                    data.get('account_id'),
                    data.get('date_start'),
                    data.get('date_stop'),
                    data.get('campaign_id'),
                    data.get('campaign_name'),
                    data.get('adset_id'),
                    data.get('adset_name'),
                    data.get('ad_id'),
                    data.get('ad_name'),
                    data.get('impressions'),
                    data.get('clicks'),
                    data.get('spend'),
                    data.get('reach'),
                    data.get('frequency'),
                    data.get('cpm'),
                    data.get('cpc'),
                    data.get('ctr')
                ))
            
            cursor.executemany("""
                INSERT INTO ad_performance_data (
                    account_id, date_start, date_stop, campaign_id, campaign_name,
                    adset_id, adset_name, ad_id, ad_name, impressions, clicks,
                    spend, reach, frequency, cpm, cpc, ctr
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, records)
            
            conn.commit()
            logger.info(f"Inserted {len(records)} ad performance records")
    
    async def insert_bulk_ad_performance_data_async(self, data_list: List[Dict[str, Any]]):
        """Insert multiple ad performance data records efficiently asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.insert_bulk_ad_performance_data, data_list)
    
    def initialize_default_job_types(self):
        """Initialize default data job types."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert default job type for ad performance
            cursor.execute("""
                INSERT OR IGNORE INTO data_job_types 
                (job_type_id, job_name, description, table_name, is_active)
                VALUES (?, ?, ?, ?, ?)
            """, (
                'ad_performance',
                'Ad Performance Insights',
                'Campaign, ad set, and ad level performance metrics including impressions, clicks, spend, and conversion data',
                'ad_performance_data',
                True
            ))
            
            conn.commit()
            logger.info("Default job types initialized")
    
    async def initialize_default_job_types_async(self):
        """Initialize default data job types asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.initialize_default_job_types)
    
    def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def health_check_async(self) -> bool:
        """Check if database connection is healthy asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.health_check)


# Global database manager instance
db_manager = DatabaseManager()