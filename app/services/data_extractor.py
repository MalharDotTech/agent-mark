"""
Data extractor for Meta Ads API with CSV output.

Implements data extraction that writes directly to CSV files using chunking
and processing logic with retry logic for failed chunks.
"""
import asyncio
import csv
import os
import uuid
from datetime import datetime, timedelta, date
from calendar import monthrange
from typing import Dict, Any, List, Tuple, Optional, Set, AsyncIterator
from pathlib import Path

from ..models.requests import ExtractionRequest
from ..models.csv_output import CSVTransformer, CSVConfig
from ..services.meta_client import MetaAPIClient
from ..core.logging import get_logger

logger = get_logger(__name__)


class DataExtractor:
    """
    Data extractor that writes directly to CSV files.
    
    Uses chunking and processing logic with simple retry logic for failed chunks.
    """
    
    def __init__(self, meta_client: MetaAPIClient, output_dir: str = "output"):
        """
        Initialize data extractor.
        
        Args:
            meta_client: Meta API client instance
            output_dir: Directory for CSV output files
        """
        self.meta_client = meta_client
        self.output_dir = Path(output_dir)
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
        # Deduplication tracking
        self._seen_keys: Set[Tuple] = set()
        self._dedup_lock = asyncio.Lock()
        
        logger.info(f"DataExtractor initialized with CSV output to: {self.output_dir}")
    
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
            
        Requirements: 4.1 - Implement date range chunking with configurable chunk sizes
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
    

    
    async def extract_to_csv(
        self, 
        extraction_request: ExtractionRequest,
        job_id: str,
        progress_callback: Optional[callable] = None
    ) -> str:
        """
        Extract data and write directly to CSV file.
        
        Args:
            extraction_request: Extraction parameters
            job_id: Job identifier for output filename
            progress_callback: Optional callback for progress updates
            
        Returns:
            Path to the generated CSV file
            
        Requirements: 4.2 - Create data extraction that writes directly to CSV files
        """
        # Generate output filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"meta_ads_data_{job_id}_{timestamp}.csv"
        output_path = self.output_dir / filename
        
        logger.info(f"Starting CSV extraction to {output_path}")
        
        # Reset deduplication for this extraction
        async with self._dedup_lock:
            self._seen_keys.clear()
        
        # Create date chunks
        chunks = self.create_date_chunks(
            extraction_request.start_date,
            extraction_request.end_date,
            extraction_request.chunk_size_days or 7
        )
        
        # Get account names for all accounts
        account_names = await self._get_account_names(extraction_request.account_ids)
        
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
        
        # Open CSV file for writing
        with open(output_path, 'w', newline='', encoding=CSVConfig.ENCODING, errors=CSVConfig.ERRORS) as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSVTransformer.CSV_HEADERS)
            writer.writeheader()
            
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
                            async for item in self._extract_chunk_data(
                                account_id, 
                                chunk_start, 
                                chunk_end,
                                extraction_request.fields,
                                extraction_request.breakdowns
                            ):
                                # Transform to CSV row
                                account_name = account_names.get(account_id, "")
                                csv_row = CSVTransformer.transform_to_csv_row(item, account_id, account_name)
                                
                                # Write to CSV
                                writer.writerow(csv_row)
                                chunk_records += 1
                                processed_records += 1
                        
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
        logger.info(f"CSV extraction completed: {processed_records} records written to {output_path}")
        
        if failed_chunks:
            logger.warning(f"Failed chunks: {len(failed_chunks)}")
            for account_id, chunk_start, chunk_end, error in failed_chunks:
                logger.warning(f"  {account_id} {chunk_start} to {chunk_end}: {error}")
        
        return str(output_path)
    
    async def _get_account_names(self, account_ids: List[str]) -> Dict[str, str]:
        """
        Get account names for all account IDs.
        
        Args:
            account_ids: List of account IDs
            
        Returns:
            Dictionary mapping account ID to account name
        """
        account_names = {}
        
        try:
            accounts = await self.meta_client.get_ad_accounts()
            
            for account in accounts:
                account_id = account.get('id', '').replace('act_', '')
                account_name = account.get('name', '')
                
                if account_id in account_ids:
                    account_names[account_id] = account_name
            
            logger.info(f"Retrieved names for {len(account_names)} accounts")
            
        except Exception as e:
            logger.warning(f"Failed to get account names: {e}")
        
        return account_names
    
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
                "impressions", "spend",
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
            dedup_key = CSVTransformer.make_dedup_key(item, account_id)
            
            # Check for duplicates
            async with self._dedup_lock:
                if dedup_key in self._seen_keys:
                    continue
                self._seen_keys.add(dedup_key)
            
            yield item
    
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
            
        Requirements: 4.4 - Add simple retry logic for failed chunks
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
                    records.append(item)
                
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
    
    def get_output_path(self, job_id: str) -> str:
        """
        Get the expected output path for a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Expected CSV file path
        """
        # This is a simplified version - in practice you'd need to track the actual filename
        return str(self.output_dir / f"meta_ads_data_{job_id}_*.csv")
    
    async def cleanup_old_files(self, max_age_days: int = 7) -> int:
        """
        Clean up old CSV files to prevent disk space issues.
        
        Args:
            max_age_days: Maximum age in days for CSV files
            
        Returns:
            Number of files cleaned up
        """
        cutoff_time = datetime.utcnow() - timedelta(days=max_age_days)
        cleaned_count = 0
        
        try:
            for file_path in self.output_dir.glob("meta_ads_data_*.csv"):
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_path.unlink()
                        cleaned_count += 1
                        logger.debug(f"Cleaned up old CSV file: {file_path}")
        
        except Exception as e:
            logger.warning(f"Error during CSV cleanup: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old CSV files")
        
        return cleaned_count