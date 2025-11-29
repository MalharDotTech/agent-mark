"""
Database connection utilities for Marimo notebooks.
Provides shared connection management and query utilities.
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class NotebookDatabaseManager:
    """Database manager specifically designed for Marimo notebook usage."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager with path to SQLite database."""
        if db_path is None:
            # Default path relative to notebooks directory
            self.db_path = Path(__file__).parent.parent.parent / "data" / "meta_ads.db"
        else:
            self.db_path = Path(db_path)
    
    def get_connection(self) -> sqlite3.Connection:
        """Get SQLite database connection with optimized settings for notebooks."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        
        return conn
    
    def query_to_dataframe(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Execute query and return results as pandas DataFrame."""
        try:
            with self.get_connection() as conn:
                if params:
                    df = pd.read_sql_query(query, conn, params=params)
                else:
                    df = pd.read_sql_query(query, conn)
                return df
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            return pd.DataFrame()
    
    def get_accounts(self) -> pd.DataFrame:
        """Get all available accounts."""
        query = """
        SELECT 
            account_id,
            account_name,
            last_updated
        FROM accounts
        ORDER BY account_name
        """
        return self.query_to_dataframe(query)
    
    def get_job_types_for_account(self, account_id: str) -> pd.DataFrame:
        """Get available job types for a specific account."""
        # First get all registered job types
        job_types_query = """
        SELECT job_type_id, job_name, table_name
        FROM data_job_types
        WHERE is_active = 1
        """
        job_types_df = self.query_to_dataframe(job_types_query)
        
        if job_types_df.empty:
            return pd.DataFrame()
        
        # Check which job types have data for this account
        results = []
        for _, job_type_row in job_types_df.iterrows():
            job_type_id = job_type_row['job_type_id']
            job_name = job_type_row['job_name']
            table_name = job_type_row['table_name']
            
            # Check if table exists and has data for this account
            try:
                data_query = f"""
                SELECT 
                    COUNT(*) as record_count,
                    MAX(extracted_at) as last_updated
                FROM {table_name}
                WHERE account_id = :account_id
                """
                data_result = self.query_to_dataframe(data_query, {"account_id": account_id})
                
                if not data_result.empty and data_result.iloc[0]['record_count'] > 0:
                    results.append({
                        'job_type': job_type_id,
                        'job_name': job_name,
                        'record_count': data_result.iloc[0]['record_count'],
                        'last_updated': data_result.iloc[0]['last_updated']
                    })
            except Exception as e:
                logger.error(f"Error checking data for job type {job_type_id}: {e}")
                continue
        
        return pd.DataFrame(results)
    
    def get_all_job_types(self) -> pd.DataFrame:
        """Get all registered job types."""
        query = """
        SELECT 
            job_type_id,
            job_name,
            description,
            table_name,
            is_active
        FROM data_job_types
        ORDER BY job_name
        """
        return self.query_to_dataframe(query)
    
    def get_data_for_job_type(self, job_type_id: str, account_id: str, days: int = 30) -> pd.DataFrame:
        """Get data for any job type."""
        # First get the table name for this job type
        job_type_query = """
        SELECT table_name
        FROM data_job_types
        WHERE job_type_id = :job_type_id AND is_active = 1
        """
        job_type_result = self.query_to_dataframe(job_type_query, {"job_type_id": job_type_id})
        
        if job_type_result.empty:
            return pd.DataFrame()
        
        table_name = job_type_result.iloc[0]['table_name']
        
        # Get the table schema to find date columns
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(f"PRAGMA table_info({table_name})")
                columns = [row['name'] for row in cursor.fetchall()]
                
                # Find a date column
                date_column = None
                for col in ['date_start', 'date_stop', 'extracted_at', 'created_at']:
                    if col in columns:
                        date_column = col
                        break
                
                if date_column:
                    query = f"""
                    SELECT *
                    FROM {table_name}
                    WHERE account_id = :account_id
                    AND {date_column} >= date('now', '-' || :days || ' days')
                    ORDER BY {date_column} DESC
                    """
                else:
                    # No date column found, just get all data for the account
                    query = f"""
                    SELECT *
                    FROM {table_name}
                    WHERE account_id = :account_id
                    """
                
                return self.query_to_dataframe(query, {"account_id": account_id, "days": days})
        except Exception as e:
            logger.error(f"Error getting data for job type {job_type_id}: {e}")
            return pd.DataFrame()
    
    def get_ad_performance_data(self, account_id: str, days: int = 30) -> pd.DataFrame:
        """Get ad performance data for an account within specified days."""
        query = """
        SELECT 
            date_start,
            date_stop,
            campaign_name,
            adset_name,
            ad_name,
            impressions,
            clicks,
            spend,
            reach,
            frequency,
            cpm,
            cpc,
            ctr,
            extracted_at
        FROM ad_performance_data
        WHERE account_id = :account_id
        AND date_start >= date('now', '-' || :days || ' days')
        ORDER BY date_start DESC, campaign_name
        """
        return self.query_to_dataframe(query, {"account_id": account_id, "days": days})
    
    def test_connection(self) -> bool:
        """Test database connection and return True if successful."""
        try:
            with self.get_connection() as conn:
                conn.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False


# Global instance for easy import
db_manager = NotebookDatabaseManager()