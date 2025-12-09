"""
RNF (Reach & Frequency) data extraction service.

Handles:
1. Cumulative reach & frequency extraction
2. Audience overlap analysis
3. Storage in database
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from itertools import combinations

from ..services.meta_client import MetaAPIClient
from ..core.database import DatabaseManager
from ..core.logging import get_logger

logger = get_logger(__name__)


class RNFExtractionService:
    """Service for extracting and storing RNF data."""
    
    def __init__(self, meta_client: MetaAPIClient, db_manager: DatabaseManager):
        """
        Initialize RNF extraction service.
        
        Args:
            meta_client: Meta API client instance
            db_manager: Database manager instance
        """
        self.meta_client = meta_client
        self.db_manager = db_manager
        
        logger.info("RNFExtractionService initialized")
    
    async def extract_cumulative_rnf(
        self,
        account_id: str,
        start_date: str,
        end_date: str,
        level: str = 'account',
        time_increment: str = '1',
        entity_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract cumulative reach & frequency data and store in database.
        
        Args:
            account_id: Meta ad account ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            level: Analysis level (account, campaign, adset, ad)
            time_increment: '1' for daily, '7' for weekly, 'monthly' for monthly
            entity_ids: Optional list of entity IDs to filter
            
        Returns:
            Dictionary with extraction statistics
        """
        logger.info(f"Starting cumulative R&F extraction for account {account_id}")
        logger.info(f"Date range: {start_date} to {end_date}, Level: {level}")
        
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
        
        records_processed = 0
        records_to_insert = []
        
        try:
            # Extract data from Meta API
            async for item in self.meta_client.get_cumulative_reach_frequency(
                account_id=account_id,
                level=level,
                time_range=time_range,
                time_increment=time_increment,
                entity_ids=entity_ids
            ):
                # Transform to database record
                db_record = self._transform_rnf_to_db_record(item, account_id, level)
                records_to_insert.append(db_record)
                records_processed += 1
                
                # Bulk insert every 100 records
                if len(records_to_insert) >= 100:
                    await self.db_manager.insert_bulk_rnf_cumulative_data_async(records_to_insert)
                    logger.debug(f"Inserted {len(records_to_insert)} records")
                    records_to_insert = []
            
            # Insert remaining records
            if records_to_insert:
                await self.db_manager.insert_bulk_rnf_cumulative_data_async(records_to_insert)
                logger.debug(f"Inserted final {len(records_to_insert)} records")
            
            logger.info(f"Cumulative R&F extraction completed: {records_processed} records stored")
            
            return {
                'success': True,
                'records_processed': records_processed,
                'account_id': account_id,
                'level': level,
                'date_range': {'start': start_date, 'end': end_date},
                'extraction_time': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Cumulative R&F extraction failed: {e}")
            raise
    
    async def extract_audience_overlap(
        self,
        account_id: str,
        start_date: str,
        end_date: str,
        level: str,
        entity_ids: List[str],
        refresh_existing: bool = False
    ) -> Dict[str, Any]:
        """
        Extract audience overlap data and store in database.
        
        This is expensive: N entities = N*(N-1)/2 pairs = 3 API calls per pair
        
        Args:
            account_id: Meta ad account ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            level: Analysis level (campaign or adset)
            entity_ids: List of entity IDs to analyze (minimum 2)
            refresh_existing: Whether to refresh existing overlap data
            
        Returns:
            Dictionary with extraction statistics
        """
        if len(entity_ids) < 2:
            raise ValueError("Need at least 2 entities for overlap analysis")
        
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
        
        logger.info(f"Starting overlap analysis for account {account_id}")
        logger.info(f"Level: {level}, Entities: {len(entity_ids)}")
        
        time_range = {
            'since': start_date,
            'until': end_date
        }
        
        # Generate all pairs
        pairs = list(combinations(entity_ids, 2))
        total_pairs = len(pairs)
        logger.info(f"Analyzing {total_pairs} pairs (requires {total_pairs * 3} API calls)")
        
        overlap_results = []
        processed_pairs = 0
        failed_pairs = 0
        
        # Get entity names (campaigns or adsets)
        entity_names = {}
        if level == 'campaign':
            campaigns = await self.meta_client.get_campaigns_for_account(account_id)
            entity_names = {c['id']: c['name'] for c in campaigns if c['id'] in entity_ids}
        elif level == 'adset':
            adsets = await self.meta_client.get_adsets_for_account(account_id)
            entity_names = {a['id']: a['name'] for a in adsets if a['id'] in entity_ids}
        
        try:
            # Process pairs with concurrency control
            semaphore = asyncio.Semaphore(3)  # Max 3 concurrent pair analyses
            
            async def process_pair(entity1_id: str, entity2_id: str):
                nonlocal processed_pairs, failed_pairs
                
                try:
                    async with semaphore:
                        logger.debug(f"Processing pair: {entity1_id} vs {entity2_id}")
                        
                        # Calculate overlap
                        overlap_data = await self.meta_client.calculate_audience_overlap_pair(
                            account_id=account_id,
                            level=level,
                            entity1_id=entity1_id,
                            entity2_id=entity2_id,
                            time_range=time_range
                        )
                        
                        # Add metadata
                        overlap_data['account_id'] = account_id
                        overlap_data['date_start'] = start_date
                        overlap_data['date_stop'] = end_date
                        overlap_data['analysis_level'] = level
                        overlap_data['entity1_name'] = entity_names.get(entity1_id, entity1_id)
                        overlap_data['entity2_name'] = entity_names.get(entity2_id, entity2_id)
                        
                        overlap_results.append(overlap_data)
                        processed_pairs += 1
                        
                        # Small delay to avoid rate limiting
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    logger.warning(f"Failed to calculate overlap for pair {entity1_id} vs {entity2_id}: {e}")
                    failed_pairs += 1
            
            # Process all pairs
            tasks = [process_pair(entity1_id, entity2_id) for entity1_id, entity2_id in pairs]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Store results in database
            if overlap_results:
                await self.db_manager.insert_bulk_rnf_overlap_data_async(overlap_results)
                logger.info(f"Stored {len(overlap_results)} overlap records")
            
            logger.info(f"Overlap analysis completed: {processed_pairs} pairs analyzed, {failed_pairs} failed")
            
            return {
                'success': True,
                'total_pairs': total_pairs,
                'processed_pairs': processed_pairs,
                'failed_pairs': failed_pairs,
                'account_id': account_id,
                'level': level,
                'date_range': {'start': start_date, 'end': end_date},
                'extraction_time': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Overlap analysis failed: {e}")
            raise
    
    def _transform_rnf_to_db_record(
        self,
        item: Dict[str, Any],
        account_id: str,
        level: str
    ) -> Dict[str, Any]:
        """
        Transform Meta API R&F record to database record format.
        
        Args:
            item: Raw R&F record from Meta API
            account_id: Account ID
            level: Analysis level
            
        Returns:
            Dictionary formatted for database insertion
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
        
        return {
            'account_id': account_id,
            'date_start': item.get('date_start'),
            'date_stop': item.get('date_stop'),
            'analysis_level': level,
            'entity_id': item.get('campaign_id') or item.get('adset_id') or item.get('ad_id'),
            'entity_name': item.get('campaign_name') or item.get('adset_name') or item.get('ad_name'),
            'reach': safe_int(item.get('reach')),
            'frequency': safe_numeric(item.get('frequency')),
            'impressions': safe_int(item.get('impressions')),
            'spend': safe_numeric(item.get('spend')),
            'clicks': safe_int(item.get('clicks')),
            'cpm': safe_numeric(item.get('cpm')),
            'cpp': safe_numeric(item.get('cpp')),
            'ctr': safe_numeric(item.get('ctr'))
        }
    
    async def get_stored_overlap(
        self,
        account_id: str,
        level: Optional[str] = None,
        date_start: Optional[str] = None,
        date_stop: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get stored overlap data from database.
        
        Args:
            account_id: Account ID
            level: Optional analysis level filter
            date_start: Optional start date filter
            date_stop: Optional end date filter
            
        Returns:
            List of overlap records
        """
        filters = {}
        if level:
            filters['analysis_level'] = level
        if date_start:
            filters['date_start'] = date_start
        if date_stop:
            filters['date_stop'] = date_stop
        
        return await self.db_manager.query_data_async(
            table_name='rnf_overlap_data',
            account_id=account_id,
            filters=filters if filters else None
        )

