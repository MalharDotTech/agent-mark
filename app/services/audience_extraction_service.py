"""
Audience Insights data extraction service.

Handles:
1. Demographic breakdowns (age, gender)
2. Geographic breakdowns (country, region)
3. Device/platform breakdowns
4. Storage in database
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..services.meta_client import MetaAPIClient
from ..core.database import DatabaseManager
from ..core.logging import get_logger

logger = get_logger(__name__)


class AudienceExtractionService:
    """Service for extracting and storing audience insights data."""
    
    def __init__(self, meta_client: MetaAPIClient, db_manager: DatabaseManager):
        """
        Initialize audience extraction service.
        
        Args:
            meta_client: Meta API client instance
            db_manager: Database manager instance
        """
        self.meta_client = meta_client
        self.db_manager = db_manager
        
        logger.info("AudienceExtractionService initialized")
    
    async def extract_audience_insights(
        self,
        account_id: str,
        start_date: str,
        end_date: str,
        breakdown_types: List[str],
        level: str = 'campaign',
        entity_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract audience insights data and store in database.
        
        Args:
            account_id: Meta ad account ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            breakdown_types: List of breakdown types (e.g., ['age', 'gender'])
            level: Analysis level (campaign, adset, ad)
            entity_ids: Optional list of entity IDs to filter
            
        Returns:
            Dictionary with extraction statistics
        """
        logger.info(f"Starting audience insights extraction for account {account_id}")
        logger.info(f"Date range: {start_date} to {end_date}")
        logger.info(f"Breakdown types: {breakdown_types}")
        
        # Ensure account is registered in database
        try:
            # Get account info from Meta API
            account_info = await self.meta_client.get_ad_account(account_id)
            account_name = account_info.get('name', f'Account {account_id}')
            
            # Register account in database
            await self.db_manager.insert_account_async(
                account_id=account_id,
                account_name=account_name,
                api_token_key="meta_api_token"
            )
            logger.info(f"Account registered: {account_name} ({account_id})")
        except Exception as e:
            logger.warning(f"Could not register account {account_id}: {e}")
        
        time_range = {
            'since': start_date,
            'until': end_date
        }
        
        total_records_processed = 0
        breakdown_stats = {}
        
        try:
            # Process each breakdown type separately
            for breakdown_type in breakdown_types:
                logger.info(f"Processing breakdown: {breakdown_type}")
                
                records_processed = 0
                records_to_insert = []
                
                # Handle combined breakdowns (e.g., 'age,gender')
                breakdown_list = [b.strip() for b in breakdown_type.split(',')]
                
                # Extract data from Meta API
                async for item in self.meta_client.get_insights_with_demographics(
                    account_id=account_id,
                    breakdowns=breakdown_list,
                    time_range=time_range,
                    level=level,
                    entity_ids=entity_ids
                ):
                    # Transform to database record(s)
                    # For combined breakdowns, create separate records for each dimension
                    db_records = self._transform_audience_to_db_records(
                        item,
                        account_id,
                        breakdown_list
                    )
                    records_to_insert.extend(db_records)
                    records_processed += len(db_records)
                    
                    # Bulk insert every 100 records
                    if len(records_to_insert) >= 100:
                        await self.db_manager.insert_bulk_audience_insights_data_async(records_to_insert)
                        logger.debug(f"Inserted {len(records_to_insert)} records")
                        records_to_insert = []
                
                # Insert remaining records
                if records_to_insert:
                    await self.db_manager.insert_bulk_audience_insights_data_async(records_to_insert)
                    logger.debug(f"Inserted final {len(records_to_insert)} records")
                
                breakdown_stats[breakdown_type] = records_processed
                total_records_processed += records_processed
                
                logger.info(f"Breakdown '{breakdown_type}' completed: {records_processed} records")
            
            logger.info(f"Audience insights extraction completed: {total_records_processed} total records")
            
            return {
                'success': True,
                'total_records': total_records_processed,
                'breakdown_stats': breakdown_stats,
                'account_id': account_id,
                'level': level,
                'date_range': {'start': start_date, 'end': end_date},
                'extraction_time': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Audience insights extraction failed: {e}")
            raise
    
    def _transform_audience_to_db_records(
        self,
        item: Dict[str, Any],
        account_id: str,
        breakdown_types: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Transform Meta API audience record to database record format.
        
        For combined breakdowns (e.g., age + gender), creates separate records
        for each breakdown dimension.
        
        Args:
            item: Raw audience record from Meta API
            account_id: Account ID
            breakdown_types: List of breakdown types in this record
            
        Returns:
            List of dictionaries formatted for database insertion
        """
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
        
        records = []
        
        # Base record data
        base_data = {
            'account_id': account_id,
            'date_start': item.get('date_start'),
            'date_stop': item.get('date_stop'),
            'campaign_id': item.get('campaign_id'),
            'campaign_name': item.get('campaign_name'),
            'reach': safe_int(item.get('reach')),
            'impressions': safe_int(item.get('impressions')),
            'spend': safe_numeric(item.get('spend')),
            'clicks': safe_int(item.get('clicks'))
        }
        
        # Create a record for each breakdown dimension
        for breakdown_type in breakdown_types:
            breakdown_value = item.get(breakdown_type)
            
            if breakdown_value:
                record = base_data.copy()
                record['breakdown_type'] = breakdown_type
                record['breakdown_value'] = str(breakdown_value)
                records.append(record)
        
        # If no breakdown values found, create a single record with 'unknown'
        if not records:
            for breakdown_type in breakdown_types:
                record = base_data.copy()
                record['breakdown_type'] = breakdown_type
                record['breakdown_value'] = 'unknown'
                records.append(record)
        
        return records
    
    async def get_stored_audience_insights(
        self,
        account_id: str,
        breakdown_type: Optional[str] = None,
        breakdown_value: Optional[str] = None,
        date_start: Optional[str] = None,
        date_stop: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get stored audience insights data from database.
        
        Args:
            account_id: Account ID
            breakdown_type: Optional breakdown type filter
            breakdown_value: Optional breakdown value filter
            date_start: Optional start date filter
            date_stop: Optional end date filter
            
        Returns:
            List of audience insights records
        """
        filters = {}
        if breakdown_type:
            filters['breakdown_type'] = breakdown_type
        if breakdown_value:
            filters['breakdown_value'] = breakdown_value
        if date_start:
            filters['date_start'] = date_start
        if date_stop:
            filters['date_stop'] = date_stop
        
        return await self.db_manager.query_data_async(
            table_name='audience_insights_data',
            account_id=account_id,
            filters=filters if filters else None
        )
    
    async def get_breakdown_summary(
        self,
        account_id: str,
        breakdown_type: str,
        date_start: Optional[str] = None,
        date_stop: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get summary statistics for a breakdown type.
        
        Args:
            account_id: Account ID
            breakdown_type: Breakdown type (age, gender, country, etc.)
            date_start: Optional start date filter
            date_stop: Optional end date filter
            
        Returns:
            Dictionary with aggregated statistics per breakdown value
        """
        records = await self.get_stored_audience_insights(
            account_id=account_id,
            breakdown_type=breakdown_type,
            date_start=date_start,
            date_stop=date_stop
        )
        
        # Aggregate by breakdown value
        summary = {}
        for record in records:
            value = record.get('breakdown_value', 'unknown')
            
            if value not in summary:
                summary[value] = {
                    'breakdown_value': value,
                    'total_reach': 0,
                    'total_impressions': 0,
                    'total_spend': 0.0,
                    'total_clicks': 0,
                    'record_count': 0
                }
            
            summary[value]['total_reach'] += record.get('reach', 0) or 0
            summary[value]['total_impressions'] += record.get('impressions', 0) or 0
            summary[value]['total_spend'] += record.get('spend', 0.0) or 0.0
            summary[value]['total_clicks'] += record.get('clicks', 0) or 0
            summary[value]['record_count'] += 1
        
        return {
            'breakdown_type': breakdown_type,
            'account_id': account_id,
            'date_range': {'start': date_start, 'end': date_stop},
            'summary': list(summary.values())
        }

