"""
Data extraction service that stores insights data in SQLite database.

Replaces CSV output with SQLite database storage while maintaining the same
extraction logic and chunking approach.
"""
import asyncio
import uuid
from datetime import datetime, timedelta, date
from calendar import monthrange
from typing import Dict, Any, List, Tuple, Optional, Set, AsyncIterator
from pathlib import Path

from ..models.requests import ExtractionRequest
from ..services.meta_client import MetaAPIClient
from ..core.database import DatabaseManager
from ..core.logging import get_logger

logger = get_logger(__name__)


class DataExtractionService:
    """
    Data extraction service that stores data in SQLite database.
    
    Uses chunking and processing logic with retry logic for failed chunks,
    storing results in SQLite instead of CSV files.
    """
    
    def __init__(self, meta_client: MetaAPIClient, db_manager: DatabaseManager):
        """
        Initialize data extraction service.
        
        Args:
            meta_client: Meta API client instance
            db_manager: Database manager instance
        """
        self.meta_client = meta_client
        self.db_manager = db_manager
        
        # Deduplication tracking
        self._seen_keys: Set[Tuple] = set()
        self._dedup_lock = asyncio.Lock()
        
        logger.info("DataExtractionService initialized with SQLite storage")
    
    def create_date_chunks(self, start_date: str, end_date: str, chunk_days: int = 7) -> List[Tuple[str, str]]:
        """
        Create date chunks using the same logic as the working script.
        
        First creates monthly chunks, then subdivides each month into weekly chunks.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            chunk_days: Number of days per sub-chunk (default 7 for weekly)
            
        Returns:
            List of (start_date, end_date) tuples for each chunk
        """
        # First create monthly chunks
        monthly_chunks = self._create_month_chunks(start_date, end_date)
        
        # Then subdivide each month into weekly chunks
        all_chunks = []
        for month_start, month_end in monthly_chunks:
            weekly_chunks = self._create_weekly_chunks(month_start, month_end, chunk_days)
            all_chunks.extend(weekly_chunks)
        
        logger.info(f"Created {len(all_chunks)} total chunks ({len(monthly_chunks)} months × weekly sub-chunks)")
        return all_chunks
    
    def _create_month_chunks(self, start_date: str, end_date: str) -> List[Tuple[str, str]]:
        """
        Create monthly date chunks from start to end date.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of (start_date, end_date) tuples for each month
        """
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        if end < start:
            raise ValueError("End date must be after start date")
        
        chunks = []
        current = date(start.year, start.month, 1)
        start_day = start
        
        while current <= end:
            # Get last day of current month
            last_day = monthrange(current.year, current.month)[1]
            month_end = date(current.year, current.month, last_day)
            
            # Calculate chunk boundaries
            chunk_start = max(start_day, date(current.year, current.month, 1))
            chunk_end = min(end, month_end)
            
            chunks.append((chunk_start.isoformat(), chunk_end.isoformat()))
            
            # Move to next month
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)
        
        logger.debug(f"Created {len(chunks)} monthly chunks from {start_date} to {end_date}")
        return chunks
    
    def _create_weekly_chunks(self, start_date: str, end_date: str, chunk_days: int = 7) -> List[Tuple[str, str]]:
        """
        Create weekly (or custom day) chunks from start to end date.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            chunk_days: Number of days per chunk (default 7 for weekly)
            
        Returns:
            List of (start_date, end_date) tuples for each chunk
        """
        if chunk_days <= 0:
            return [(start_date, end_date)]
        
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        chunks = []
        current = start
        
        while current <= end:
            chunk_end = min(end, current + timedelta(days=chunk_days - 1))
            chunks.append((current.isoformat(), chunk_end.isoformat()))
            current = chunk_end + timedelta(days=1)
        
        logger.debug(f"Created {len(chunks)} {chunk_days}-day chunks from {start_date} to {end_date}")
        return chunks
    
    async def extract_and_store(
        self, 
        extraction_request: ExtractionRequest,
        job_id: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Extract data and store directly in SQLite database.
        
        Args:
            extraction_request: Extraction parameters
            job_id: Job identifier for tracking
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with extraction results and statistics
        """
        logger.info(f"Starting SQLite extraction for job {job_id}")
        
        # Reset deduplication for this extraction
        async with self._dedup_lock:
            self._seen_keys.clear()
        
        # Create date chunks
        chunks = self.create_date_chunks(
            extraction_request.start_date,
            extraction_request.end_date,
            extraction_request.chunk_size_days or 7
        )
        
        # Get account names for all accounts and store them
        await self._ensure_accounts_stored(extraction_request.account_ids)
        
        # Create extraction plan (account + chunk combinations)
        extraction_plan = []
        for account_id in extraction_request.account_ids:
            for chunk_start, chunk_end in chunks:
                extraction_plan.append((account_id, chunk_start, chunk_end))
        
        logger.info(f"Created extraction plan with {len(extraction_plan)} tasks "
                   f"({len(extraction_request.account_ids)} accounts × {len(chunks)} chunks)")
        
        # Initialize progress tracking
        total_chunks = len(extraction_plan)
        completed_chunks = 0
        processed_records = 0
        failed_chunks = []
        
        # Process chunks with concurrency control
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent chunks
        
        async def process_chunk_with_retry(account_id: str, chunk_start: str, chunk_end: str):
            nonlocal completed_chunks, processed_records
            
            chunk_records = 0
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    async with semaphore:
                        logger.debug(f"Processing chunk {account_id} {chunk_start} to {chunk_end} (attempt {attempt + 1})")
                        
                        # Extract data for this chunk
                        chunk_data = []
                        async for item in self._extract_chunk_data(
                            account_id, 
                            chunk_start, 
                            chunk_end,
                            extraction_request.fields,
                            extraction_request.breakdowns
                        ):
                            # Transform to database record
                            db_record = self._transform_to_db_record(item, account_id)
                            chunk_data.append(db_record)
                            chunk_records += 1
                        
                        # Store chunk data in database
                        if chunk_data:
                            await self.db_manager.insert_bulk_ad_performance_data_async(chunk_data)
                            processed_records += chunk_records
                    
                    # Chunk completed successfully
                    completed_chunks += 1
                    logger.debug(f"Completed chunk {account_id} {chunk_start} to {chunk_end}: {chunk_records} records")
                    
                    # Update progress
                    if progress_callback:
                        await progress_callback(total_chunks, completed_chunks, processed_records)
                    
                    return  # Success, exit retry loop
                    
                except Exception as e:
                    logger.warning(f"Chunk failed {account_id} {chunk_start} to {chunk_end} (attempt {attempt + 1}): {e}")
                    
                    if attempt == max_retries - 1:
                        # Final attempt failed
                        failed_chunks.append((account_id, chunk_start, chunk_end, str(e)))
                        completed_chunks += 1  # Count as completed (failed)
                        
                        if progress_callback:
                            await progress_callback(total_chunks, completed_chunks, processed_records)
                    else:
                        # Wait before retry
                        await asyncio.sleep(2 ** attempt)
        
        # Process all chunks concurrently
        tasks = [
            process_chunk_with_retry(account_id, chunk_start, chunk_end)
            for account_id, chunk_start, chunk_end in extraction_plan
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log results
        logger.info(f"SQLite extraction completed: {processed_records} records stored for job {job_id}")
        
        if failed_chunks:
            logger.warning(f"Failed chunks: {len(failed_chunks)}")
            for account_id, chunk_start, chunk_end, error in failed_chunks:
                logger.warning(f"  {account_id} {chunk_start} to {chunk_end}: {error}")
        
        return {
            "job_id": job_id,
            "total_records": processed_records,
            "total_chunks": total_chunks,
            "completed_chunks": completed_chunks,
            "failed_chunks": len(failed_chunks),
            "accounts_processed": len(extraction_request.account_ids),
            "date_range": {
                "start": extraction_request.start_date,
                "end": extraction_request.end_date
            },
            "extraction_time": datetime.utcnow().isoformat()
        }
    
    async def _ensure_accounts_stored(self, account_ids: List[str]):
        """
        Ensure all account information is stored in the accounts table.
        
        Args:
            account_ids: List of account IDs to ensure are stored
        """
        try:
            # Get account information from Meta API
            accounts = await self.meta_client.get_ad_accounts()
            
            # Store each account that we're processing
            for account in accounts:
                account_id = account.get('id', '').replace('act_', '')
                account_name = account.get('name', '')
                
                if account_id in account_ids:
                    # Use a generic token key since we don't track which specific token was used
                    await self.db_manager.insert_account_async(
                        account_id=account_id,
                        account_name=account_name,
                        api_token_key="meta_api_token"  # Generic key for now
                    )
            
            logger.info(f"Ensured account information is stored for {len(account_ids)} accounts")
            
        except Exception as e:
            logger.warning(f"Failed to store account information: {e}")
    
    async def _extract_chunk_data(
        self,
        account_id: str,
        start_date: str,
        end_date: str,
        fields: Optional[List[str]] = None,
        breakdowns: Optional[List[str]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Extract data for a single chunk with deduplication.
        
        Args:
            account_id: Meta ad account ID
            start_date: Chunk start date
            end_date: Chunk end date
            fields: Optional list of fields to extract
            breakdowns: Optional list of breakdowns
            
        Yields:
            Individual insights records (deduplicated)
        """
        # Default fields matching the working script
        if fields is None:
            fields = [
                "campaign_name", "campaign_id",
                "adset_name", "adset_id", 
                "ad_name", "ad_id",
                "impressions", "spend", "clicks", "reach", "frequency",
                "cpm", "cpc", "ctr",
                "inline_link_clicks", "actions",
                "date_start", "date_stop"
            ]
        
        # Default breakdowns matching the working script
        if breakdowns is None:
            breakdowns = ["publisher_platform", "platform_position"]
        
        # Time range for this chunk
        time_range = {
            'since': start_date,
            'until': end_date
        }
        
        # Extract insights data with pagination
        async for item in self.meta_client.get_insights_paginated(
            account_id=account_id,
            level='ad',  # Ad level as per working script
            time_range=time_range,
            fields=fields,
            breakdowns=breakdowns,
            action_breakdowns=['action_type'],  # For actions data
            filtering=[{
                "field": "action_type", 
                "operator": "IN", 
                "value": ["landing_page_view", "link_click"]
            }],
            limit=1000
        ):
            # Create deduplication key
            dedup_key = self._make_dedup_key(item, account_id)
            
            # Check for duplicates
            async with self._dedup_lock:
                if dedup_key in self._seen_keys:
                    continue
                self._seen_keys.add(dedup_key)
            
            yield item
    
    def _make_dedup_key(self, item: Dict[str, Any], account_id: str) -> Tuple:
        """
        Create a deduplication key for an insights record.
        
        Args:
            item: Insights record
            account_id: Account ID
            
        Returns:
            Tuple that uniquely identifies the record
        """
        return (
            account_id,
            item.get('date_start', ''),
            item.get('date_stop', ''),
            item.get('campaign_id', ''),
            item.get('adset_id', ''),
            item.get('ad_id', ''),
            # Include breakdowns in dedup key
            item.get('publisher_platform', ''),
            item.get('platform_position', '')
        )
    
    def _transform_to_db_record(self, item: Dict[str, Any], account_id: str) -> Dict[str, Any]:
        """
        Transform Meta API insights record to database record format.
        
        Args:
            item: Raw insights record from Meta API
            account_id: Account ID
            
        Returns:
            Dictionary formatted for database insertion
        """
        # Helper function to safely convert to numeric values
        def safe_numeric(value, default=None):
            if value is None or value == '':
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        
        def safe_int(value, default=None):
            if value is None or value == '':
                return default
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return default
        
        return {
            'account_id': account_id,
            'date_start': item.get('date_start'),
            'date_stop': item.get('date_stop'),
            'campaign_id': item.get('campaign_id'),
            'campaign_name': item.get('campaign_name'),
            'adset_id': item.get('adset_id'),
            'adset_name': item.get('adset_name'),
            'ad_id': item.get('ad_id'),
            'ad_name': item.get('ad_name'),
            'impressions': safe_int(item.get('impressions')),
            'clicks': safe_int(item.get('clicks')),
            'spend': safe_numeric(item.get('spend')),
            'reach': safe_int(item.get('reach')),
            'frequency': safe_numeric(item.get('frequency')),
            'cpm': safe_numeric(item.get('cpm')),
            'cpc': safe_numeric(item.get('cpc')),
            'ctr': safe_numeric(item.get('ctr'))
        }
    
    async def get_stored_data(
        self, 
        account_id: str, 
        job_type: str = 'ad_performance', 
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve stored data from the database.
        
        Args:
            account_id: Account ID to filter by
            job_type: Data job type (currently only 'ad_performance')
            filters: Additional filters to apply
            
        Returns:
            List of stored records
        """
        # Map job type to table name
        table_mapping = {
            'ad_performance': 'ad_performance_data'
        }
        
        table_name = table_mapping.get(job_type)
        if not table_name:
            raise ValueError(f"Unknown job type: {job_type}")
        
        return await self.db_manager.query_data_async(
            table_name=table_name,
            account_id=account_id,
            filters=filters
        )
    
    async def process_chunk(
        self, 
        account_id: str, 
        chunk_start: str, 
        chunk_end: str,
        extraction_request: ExtractionRequest
    ) -> List[Dict[str, Any]]:
        """
        Process a single chunk and return the data.
        
        Args:
            account_id: Meta ad account ID
            chunk_start: Chunk start date
            chunk_end: Chunk end date
            extraction_request: Extraction parameters
            
        Returns:
            List of processed records for this chunk
        """
        records = []
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"Processing chunk {account_id} {chunk_start} to {chunk_end} (attempt {attempt + 1})")
                
                async for item in self._extract_chunk_data(
                    account_id,
                    chunk_start,
                    chunk_end,
                    extraction_request.fields,
                    extraction_request.breakdowns
                ):
                    db_record = self._transform_to_db_record(item, account_id)
                    records.append(db_record)
                
                logger.debug(f"Chunk {account_id} {chunk_start} to {chunk_end}: {len(records)} records")
                return records
                
            except Exception as e:
                logger.warning(f"Chunk failed {account_id} {chunk_start} to {chunk_end} (attempt {attempt + 1}): {e}")
                
                if attempt == max_retries - 1:
                    logger.error(f"Chunk permanently failed after {max_retries} attempts: "
                               f"{account_id} {chunk_start} to {chunk_end}")
                    raise
                
                # Wait before retry with exponential backoff
                await asyncio.sleep(2 ** attempt)
        
        return records