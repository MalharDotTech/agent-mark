"""Meta Graph API client with httpx and connection pooling."""

import httpx
import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta, date
from calendar import monthrange
from typing import Dict, List, Any, Optional, AsyncIterator, Tuple, Callable
from urllib.parse import urljoin

from ..core.config import settings
from ..core.logging import get_logger
from ..core.token_manager import TokenManager
from ..core.rate_limiter import RateLimiter
from ..core.exceptions import MetaAPIException, RateLimitException, TokenException
from ..core.metrics import metrics_collector

logger = get_logger(__name__)


class MetaAPIClient:
    """
    Async HTTP client for Meta Graph API interactions.
    
    Provides HTTP client with connection pooling, token management, rate limiting,
    and core methods for Meta Graph API v23.0 endpoints with request/response logging.
    """
    
    BASE_URL = "https://graph.facebook.com"
    
    def __init__(self, token_manager: Optional[TokenManager] = None, rate_limiter: Optional[RateLimiter] = None):
        """
        Initialize MetaAPIClient with token management and rate limiting.
        
        Args:
            token_manager: TokenManager instance for handling multiple tokens
            rate_limiter: RateLimiter instance for handling API rate limits
        """
        # HTTP client configuration with connection pooling
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(30.0, connect=10.0),  # 30s total, 10s connect
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
        
        self.api_version = settings.meta_api_version
        
        # Initialize token manager if not provided
        if token_manager is None:
            tokens = settings.get_access_tokens()
            if not tokens:
                raise TokenException("No access tokens configured")
            self.token_manager = TokenManager(tokens)
        else:
            self.token_manager = token_manager
        
        # Initialize rate limiter if not provided
        if rate_limiter is None:
            self.rate_limiter = RateLimiter(self.token_manager)
        else:
            self.rate_limiter = rate_limiter
        
        logger.info(f"MetaAPIClient initialized with API version {self.api_version}, "
                   f"{len(self.token_manager.tokens)} tokens")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close the HTTP client and cleanup connections."""
        if self.client:
            await self.client.aclose()
            logger.debug("MetaAPIClient closed")
    
    def _build_url(self, endpoint: str) -> str:
        """
        Build full URL for Meta Graph API endpoint.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            Full URL with API version
        """
        if endpoint.startswith('/'):
            endpoint = endpoint[1:]
        return f"/{self.api_version}/{endpoint}"
    
    async def _make_request_with_token_and_rate_limiting(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request with automatic token management and rate limiting.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            
        Returns:
            JSON response data
            
        Raises:
            httpx.HTTPError: For HTTP errors
            ValueError: For invalid responses
        """
        async def make_single_request():
            # Get available token
            token_index, access_token = await self.token_manager.get_available_token_async()
            
            try:
                return await self._make_request_raw(method, endpoint, params, data, access_token)
            except Exception as e:
                # Check if this is a rate limit exception
                if isinstance(e, RateLimitException) and hasattr(e, 'response_data'):
                    error_data = e.response_data['error']
                    self.rate_limiter.handle_rate_limit_error(error_data, token_index)
                    raise  # Re-raise to trigger retry
                
                # Check if this is a Meta API error that should trigger rate limiting
                elif hasattr(e, 'response_data') and 'error' in e.response_data:
                    error_data = e.response_data['error']
                    
                    # Handle rate limit errors
                    if self.rate_limiter.should_retry_error(error_data):
                        self.rate_limiter.handle_rate_limit_error(error_data, token_index)
                        raise  # Re-raise to trigger retry
                
                # Handle transport errors by recreating client
                elif isinstance(e, (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)):
                    logger.warning(f"Transport error: {e}. Recreating client...")
                    await self.recreate_client()
                
                raise
        
        # Use rate limiter to execute with backoff
        return await self.rate_limiter.execute_with_backoff(make_single_request)
    
    async def _make_request_raw(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        access_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Make raw HTTP request to Meta Graph API with logging.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            access_token: Meta API access token
            
        Returns:
            JSON response data
            
        Raises:
            httpx.HTTPError: For HTTP errors
            ValueError: For invalid responses with error data attached
        """
        url = self._build_url(endpoint)
        
        # Add access token to params
        if params is None:
            params = {}
        if access_token:
            params['access_token'] = access_token
        
        # Log request (without token for security)
        safe_params = {k: v for k, v in params.items() if k != 'access_token'}
        request_start_time = time.time()
        
        logger.info(f"API Request: {method} {url}", extra={
            "method": method,
            "endpoint": url,
            "params": list(safe_params.keys()),
            "request_id": str(uuid.uuid4())[:8]
        })
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                params=params,
                json=data if data else None
            )
            
            # Calculate response time
            response_time = time.time() - request_start_time
            response_time_ms = round(response_time * 1000, 2)
            
            # Log response with timing
            logger.info(f"API Response: {response.status_code} for {method} {url}", extra={
                "method": method,
                "endpoint": url,
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "success": True
            })
            
            # Record metrics
            metrics_collector.record_api_call(
                endpoint=url,
                method=method,
                success=True,
                response_time_ms=response_time_ms
            )
            
            # Parse JSON response
            response_data = response.json()
            
            # Check for Meta API errors in response
            if 'error' in response_data:
                error = response_data['error']
                error_code = error.get('code')
                error_message = error.get('message', 'Unknown error')
                
                logger.error(f"Meta API error: {error}")
                
                # Check if this is a rate limit error
                if error_code in [4, 17, 32, 613]:
                    # Create rate limit exception with error data attached for rate limiting
                    exc = RateLimitException(
                        message=f"Meta API rate limit: {error_message}",
                        meta_error_code=error_code
                    )
                    exc.response_data = response_data
                    raise exc
                else:
                    # Create general Meta API exception with error data attached
                    exc = MetaAPIException(
                        message=f"Meta API error: {error_message}",
                        error_code=f"META_API_{error_code}" if error_code else "META_API_ERROR",
                        details=error
                    )
                    exc.response_data = response_data
                    raise exc
            
            # Raise for HTTP errors after checking for API errors
            response.raise_for_status()
            
            return response_data
            
        except httpx.HTTPError as e:
            response_time = time.time() - request_start_time
            response_time_ms = round(response_time * 1000, 2)
            
            logger.error(f"HTTP error for {method} {url}: {e}", extra={
                "method": method,
                "endpoint": url,
                "response_time_ms": response_time_ms,
                "success": False,
                "error_type": "HTTP_ERROR"
            })
            
            # Record metrics
            metrics_collector.record_api_call(
                endpoint=url,
                method=method,
                success=False,
                response_time_ms=response_time_ms,
                error_type="HTTP_ERROR"
            )
            
            raise MetaAPIException(
                message=f"HTTP error: {str(e)}",
                error_code="HTTP_ERROR",
                details={"status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None}
            )
        except (RateLimitException, MetaAPIException):
            # Log error with timing for our custom exceptions
            response_time = time.time() - request_start_time
            response_time_ms = round(response_time * 1000, 2)
            
            logger.error(f"Meta API error for {method} {url}", extra={
                "method": method,
                "endpoint": url,
                "response_time_ms": response_time_ms,
                "success": False,
                "error_type": "META_API_ERROR"
            })
            
            # Record metrics
            metrics_collector.record_api_call(
                endpoint=url,
                method=method,
                success=False,
                response_time_ms=response_time_ms,
                error_type="META_API_ERROR"
            )
            
            # Re-raise our custom exceptions as-is
            raise
        except Exception as e:
            response_time = time.time() - request_start_time
            response_time_ms = round(response_time * 1000, 2)
            
            logger.error(f"Unexpected error for {method} {url}: {e}", extra={
                "method": method,
                "endpoint": url,
                "response_time_ms": response_time_ms,
                "success": False,
                "error_type": "UNEXPECTED_ERROR"
            })
            
            # Record metrics
            metrics_collector.record_api_call(
                endpoint=url,
                method=method,
                success=False,
                response_time_ms=response_time_ms,
                error_type="UNEXPECTED_ERROR"
            )
            
            raise MetaAPIException(
                message=f"Unexpected error: {str(e)}",
                error_code="UNEXPECTED_ERROR"
            )
    
    async def get_ad_accounts(self) -> List[Dict[str, Any]]:
        """
        Get list of ad accounts accessible with managed tokens.
        
        Returns:
            List of ad account data
        """
        logger.info("Fetching ad accounts")
        
        params = {
            'fields': 'id,name,account_status,currency,timezone_name'
        }
        
        response = await self._make_request_with_token_and_rate_limiting(
            method='GET',
            endpoint='me/adaccounts',
            params=params
        )
        
        accounts = response.get('data', [])
        logger.info(f"Retrieved {len(accounts)} ad accounts")
        
        return accounts
    
    async def get_campaigns(
        self, 
        account_id: str, 
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get campaigns for a specific ad account.
        
        Args:
            account_id: Meta ad account ID
            fields: List of fields to retrieve
            
        Returns:
            List of campaign data
        """
        if not account_id.startswith('act_'):
            account_id = f'act_{account_id}'
        
        logger.info(f"Fetching campaigns for account {account_id}")
        
        # Default fields for campaigns
        if fields is None:
            fields = ['id', 'name', 'status', 'objective', 'created_time', 'updated_time']
        
        params = {
            'fields': ','.join(fields)
        }
        
        response = await self._make_request_with_token_and_rate_limiting(
            method='GET',
            endpoint=f'{account_id}/campaigns',
            params=params
        )
        
        campaigns = response.get('data', [])
        logger.info(f"Retrieved {len(campaigns)} campaigns for account {account_id}")
        
        return campaigns
    
    async def get_adsets(
        self, 
        account_id: str, 
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get ad sets for a specific ad account.
        
        Args:
            account_id: Meta ad account ID
            fields: List of fields to retrieve
            
        Returns:
            List of ad set data
        """
        if not account_id.startswith('act_'):
            account_id = f'act_{account_id}'
        
        logger.info(f"Fetching ad sets for account {account_id}")
        
        # Default fields for ad sets
        if fields is None:
            fields = ['id', 'name', 'status', 'campaign_id', 'created_time', 'updated_time']
        
        params = {
            'fields': ','.join(fields)
        }
        
        response = await self._make_request_with_token_and_rate_limiting(
            method='GET',
            endpoint=f'{account_id}/adsets',
            params=params
        )
        
        adsets = response.get('data', [])
        logger.info(f"Retrieved {len(adsets)} ad sets for account {account_id}")
        
        return adsets
    
    async def get_ads(
        self, 
        account_id: str, 
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get ads for a specific ad account.
        
        Args:
            account_id: Meta ad account ID
            fields: List of fields to retrieve
            
        Returns:
            List of ad data
        """
        if not account_id.startswith('act_'):
            account_id = f'act_{account_id}'
        
        logger.info(f"Fetching ads for account {account_id}")
        
        # Default fields for ads
        if fields is None:
            fields = ['id', 'name', 'status', 'adset_id', 'campaign_id', 'created_time', 'updated_time']
        
        params = {
            'fields': ','.join(fields)
        }
        
        response = await self._make_request_with_token_and_rate_limiting(
            method='GET',
            endpoint=f'{account_id}/ads',
            params=params
        )
        
        ads = response.get('data', [])
        logger.info(f"Retrieved {len(ads)} ads for account {account_id}")
        
        return ads
    
    async def get_insights(
        self,
        account_id: str,
        level: str = 'account',
        time_range: Optional[Dict[str, str]] = None,
        fields: Optional[List[str]] = None,
        breakdowns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get insights data for a specific ad account.
        
        Args:
            account_id: Meta ad account ID
            level: Insights level (account, campaign, adset, ad)
            time_range: Time range dict with 'since' and 'until' keys
            fields: List of metrics to retrieve
            breakdowns: List of breakdowns to apply
            
        Returns:
            Insights response data
        """
        if not account_id.startswith('act_'):
            account_id = f'act_{account_id}'
        
        logger.info(f"Fetching insights for account {account_id}, level: {level}")
        
        # Default fields for insights
        if fields is None:
            fields = [
                'impressions', 'clicks', 'spend', 'reach', 'frequency',
                'cpm', 'cpc', 'ctr', 'date_start', 'date_stop'
            ]
        
        params = {
            'level': level,
            'fields': ','.join(fields)
        }
        
        # Add time range if provided
        if time_range:
            params['time_range'] = time_range
        
        # Add breakdowns if provided
        if breakdowns:
            params['breakdowns'] = ','.join(breakdowns)
        
        response = await self._make_request_with_token_and_rate_limiting(
            method='GET',
            endpoint=f'{account_id}/insights',
            params=params
        )
        
        insights = response.get('data', [])
        logger.info(f"Retrieved {len(insights)} insights records for account {account_id}")
        
        return response
    
    async def recreate_client(self):
        """
        Recreate the HTTP client to handle transport errors.
        
        This method closes the current client and creates a new one,
        which can help recover from connection issues.
        """
        logger.warning("Recreating HTTP client due to transport error")
        
        # Close existing client
        if self.client:
            await self.client.aclose()
        
        # Create new client with same configuration
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            http2=True,
        )
        
        logger.info("HTTP client recreated successfully")
    
    # ========== PAGINATION METHODS ==========
    
    async def paginate_results(
        self, 
        url: str, 
        params: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Paginate through Meta API results using cursor-based pagination.
        
        Args:
            url: API endpoint URL
            params: Query parameters
            
        Yields:
            Individual data items from paginated results
        """
        after_cursor = None
        page_count = 0
        
        while True:
            # Add pagination cursor if we have one
            current_params = params.copy()
            if after_cursor:
                current_params['after'] = after_cursor
            
            # Make request with token management and rate limiting
            response = await self._make_request_with_token_and_rate_limiting(
                method='GET',
                endpoint=url.replace(f'/{self.api_version}/', ''),  # Remove version prefix
                params=current_params
            )
            
            # Extract data
            data = response.get('data', [])
            page_count += 1
            
            logger.debug(f"Page {page_count}: Retrieved {len(data)} items")
            
            # Yield each item
            for item in data:
                yield item
            
            # Check for next page
            paging = response.get('paging', {})
            cursors = paging.get('cursors', {})
            after_cursor = cursors.get('after')
            
            if not after_cursor:
                logger.debug(f"Pagination complete after {page_count} pages")
                break
    
    async def get_insights_paginated(
        self,
        account_id: str,
        level: str = 'account',
        time_range: Optional[Dict[str, str]] = None,
        fields: Optional[List[str]] = None,
        breakdowns: Optional[List[str]] = None,
        action_breakdowns: Optional[List[str]] = None,
        filtering: Optional[List[Dict[str, Any]]] = None,
        limit: int = 1000
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Get insights data with automatic pagination.
        
        Args:
            account_id: Meta ad account ID
            level: Insights level (account, campaign, adset, ad)
            time_range: Time range dict with 'since' and 'until' keys
            fields: List of metrics to retrieve
            breakdowns: List of breakdowns to apply
            action_breakdowns: List of action breakdowns
            filtering: List of filtering conditions
            limit: Number of results per page
            
        Yields:
            Individual insights records
        """
        if not account_id.startswith('act_'):
            account_id = f'act_{account_id}'
        
        logger.info(f"Fetching paginated insights for account {account_id}, level: {level}")
        
        # Default fields for insights
        if fields is None:
            fields = [
                'impressions', 'clicks', 'spend', 'reach', 'frequency',
                'cpm', 'cpc', 'ctr', 'date_start', 'date_stop',
                'campaign_name', 'campaign_id', 'adset_name', 'adset_id',
                'ad_name', 'ad_id', 'actions', 'inline_link_clicks'
            ]
        
        params = {
            'level': level,
            'fields': ','.join(fields),
            'limit': limit,
            'time_increment': 1,  # Daily data
            'locale': 'en_US'
        }
        
        # Add time range if provided
        if time_range:
            params['time_range'] = time_range
        
        # Add breakdowns if provided
        if breakdowns:
            params['breakdowns'] = ','.join(breakdowns)
        
        # Add action breakdowns if provided
        if action_breakdowns:
            params['action_breakdowns'] = ','.join(action_breakdowns)
        
        # Add filtering if provided
        if filtering:
            params['filtering'] = json.dumps(filtering, separators=(',', ':'))
        
        # Use pagination to get all results
        url = f'{account_id}/insights'
        total_records = 0
        
        async for item in self.paginate_results(url, params):
            total_records += 1
            yield item
        
        logger.info(f"Retrieved {total_records} insights records for account {account_id}")
    
    # ========== RNF (REACH & FREQUENCY) METHODS ==========
    
    async def get_cumulative_reach_frequency(
        self,
        account_id: str,
        level: str = 'account',
        time_range: Optional[Dict[str, str]] = None,
        time_increment: str = '1',
        entity_ids: Optional[List[str]] = None,
        fields: Optional[List[str]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Get cumulative reach and frequency data with pagination.
        
        Args:
            account_id: Meta ad account ID
            level: Analysis level (account, campaign, adset, ad)
            time_range: Time range dict with 'since' and 'until' keys
            time_increment: '1' for daily, '7' for weekly, 'monthly' for monthly
            entity_ids: Optional list of campaign/adset/ad IDs to filter
            fields: Optional list of fields to retrieve
            
        Yields:
            Individual reach & frequency records
        """
        if not account_id.startswith('act_'):
            account_id = f'act_{account_id}'
        
        logger.info(f"Fetching cumulative R&F for account {account_id}, level: {level}")
        
        # Default fields for R&F
        if fields is None:
            fields = [
                'reach', 'frequency', 'impressions', 'spend', 'clicks',
                'cpm', 'cpp', 'ctr', 'date_start', 'date_stop'
            ]
        
        params = {
            'level': level,
            'fields': ','.join(fields),
            'time_increment': time_increment,
            'limit': 1000
        }
        
        # Add time range if provided
        if time_range:
            params['time_range'] = time_range
        
        # Add filtering if specific entities selected
        if entity_ids and level != 'account':
            params['filtering'] = json.dumps([{
                'field': f'{level}.id',
                'operator': 'IN',
                'value': entity_ids
            }])
        
        # Use pagination to get all results
        url = f'{account_id}/insights'
        total_records = 0
        
        async for item in self.paginate_results(url, params):
            total_records += 1
            yield item
        
        logger.info(f"Retrieved {total_records} R&F records for account {account_id}")
    
    async def calculate_audience_overlap_pair(
        self,
        account_id: str,
        level: str,
        entity1_id: str,
        entity2_id: str,
        time_range: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Calculate audience overlap for a single pair using 3-API-call pattern.
        
        Pattern:
        1. Get reach for entity1
        2. Get reach for entity2
        3. Get combined reach for [entity1, entity2]
        4. Calculate overlap = reach1 + reach2 - combined_reach
        
        Args:
            account_id: Meta ad account ID
            level: Analysis level (campaign or adset)
            entity1_id: First entity ID
            entity2_id: Second entity ID
            time_range: Time range dict with 'since' and 'until' keys
            
        Returns:
            Dictionary with overlap data
        """
        if not account_id.startswith('act_'):
            account_id = f'act_{account_id}'
        
        logger.info(f"Calculating overlap for {entity1_id} vs {entity2_id}")
        
        # Call 1: Reach for entity1
        params1 = {
            'level': level,
            'fields': 'reach',
            'time_range': time_range,
            'filtering': json.dumps([{
                'field': f'{level}.id',
                'operator': 'IN',
                'value': [entity1_id]
            }])
        }
        
        response1 = await self._make_request_with_token_and_rate_limiting(
            method='GET',
            endpoint=f'{account_id}/insights',
            params=params1
        )
        
        reach1 = int(response1['data'][0].get('reach', 0)) if response1.get('data') else 0
        
        # Call 2: Reach for entity2
        params2 = {
            'level': level,
            'fields': 'reach',
            'time_range': time_range,
            'filtering': json.dumps([{
                'field': f'{level}.id',
                'operator': 'IN',
                'value': [entity2_id]
            }])
        }
        
        response2 = await self._make_request_with_token_and_rate_limiting(
            method='GET',
            endpoint=f'{account_id}/insights',
            params=params2
        )
        
        reach2 = int(response2['data'][0].get('reach', 0)) if response2.get('data') else 0
        
        # Call 3: Combined reach for both entities
        params_combined = {
            'level': 'account',  # Account level to get combined reach
            'fields': 'reach',
            'time_range': time_range,
            'filtering': json.dumps([{
                'field': f'{level}.id',
                'operator': 'IN',
                'value': [entity1_id, entity2_id]
            }])
        }
        
        response_combined = await self._make_request_with_token_and_rate_limiting(
            method='GET',
            endpoint=f'{account_id}/insights',
            params=params_combined
        )
        
        combined_reach = int(response_combined['data'][0].get('reach', 0)) if response_combined.get('data') else 0
        
        # Calculate overlap
        overlap_count = max(0, reach1 + reach2 - combined_reach)
        overlap_percentage = (overlap_count / min(reach1, reach2) * 100) if min(reach1, reach2) > 0 else 0
        
        logger.info(f"Overlap calculated: {overlap_count} ({overlap_percentage:.1f}%)")
        
        return {
            'entity1_id': entity1_id,
            'entity2_id': entity2_id,
            'reach1': reach1,
            'reach2': reach2,
            'combined_reach': combined_reach,
            'overlap_count': overlap_count,
            'overlap_percentage': overlap_percentage
        }
    
    # ========== AUDIENCE INSIGHTS METHODS ==========
    
    async def get_insights_with_demographics(
        self,
        account_id: str,
        breakdowns: List[str],
        time_range: Optional[Dict[str, str]] = None,
        level: str = 'campaign',
        entity_ids: Optional[List[str]] = None,
        fields: Optional[List[str]] = None,
        limit: int = 1000
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Get insights with demographic/geographic breakdowns.
        
        Args:
            account_id: Meta ad account ID
            breakdowns: List of breakdowns (e.g., ['age', 'gender'] or ['country'])
            time_range: Time range dict with 'since' and 'until' keys
            level: Analysis level (campaign, adset, ad)
            entity_ids: Optional list of campaign/adset/ad IDs to filter
            fields: Optional list of fields to retrieve
            limit: Number of results per page
            
        Yields:
            Individual insights records with breakdown data
        """
        if not account_id.startswith('act_'):
            account_id = f'act_{account_id}'
        
        logger.info(f"Fetching audience insights for account {account_id}, breakdowns: {breakdowns}")
        
        # Default fields for audience insights
        if fields is None:
            fields = [
                'reach', 'impressions', 'spend', 'clicks',
                'cpm', 'ctr', 'date_start', 'date_stop'
            ]
            
            # Add campaign info if not account level
            if level != 'account':
                fields.extend(['campaign_id', 'campaign_name'])
        
        params = {
            'level': level,
            'fields': ','.join(fields),
            'breakdowns': ','.join(breakdowns),
            'limit': limit
        }
        
        # Add time range if provided
        if time_range:
            params['time_range'] = time_range
        
        # Add filtering if specific entities selected
        if entity_ids and level != 'account':
            params['filtering'] = json.dumps([{
                'field': f'{level}.id',
                'operator': 'IN',
                'value': entity_ids
            }])
        
        # Use pagination to get all results
        url = f'{account_id}/insights'
        total_records = 0
        
        async for item in self.paginate_results(url, params):
            total_records += 1
            yield item
        
        logger.info(f"Retrieved {total_records} audience insights records for account {account_id}")
    
    async def get_campaigns_for_account(
        self,
        account_id: str,
        fields: Optional[List[str]] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get campaigns for an account (helper for RNF and audience analysis).
        
        Args:
            account_id: Meta ad account ID
            fields: Optional list of fields to retrieve
            limit: Maximum number of campaigns to retrieve
            
        Returns:
            List of campaign data
        """
        if not account_id.startswith('act_'):
            account_id = f'act_{account_id}'
        
        logger.info(f"Fetching campaigns for account {account_id}")
        
        # Default fields
        if fields is None:
            fields = ['id', 'name', 'status', 'objective']
        
        params = {
            'fields': ','.join(fields),
            'limit': limit
        }
        
        response = await self._make_request_with_token_and_rate_limiting(
            method='GET',
            endpoint=f'{account_id}/campaigns',
            params=params
        )
        
        campaigns = response.get('data', [])
        logger.info(f"Retrieved {len(campaigns)} campaigns for account {account_id}")
        
        return campaigns
    
    async def get_adsets_for_account(
        self,
        account_id: str,
        fields: Optional[List[str]] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get adsets for an account (helper for RNF analysis).
        
        Args:
            account_id: Meta ad account ID
            fields: Optional list of fields to retrieve
            limit: Maximum number of adsets to retrieve
            
        Returns:
            List of adset data
        """
        if not account_id.startswith('act_'):
            account_id = f'act_{account_id}'
        
        logger.info(f"Fetching adsets for account {account_id}")
        
        # Default fields
        if fields is None:
            fields = ['id', 'name', 'status', 'campaign_id']
        
        params = {
            'fields': ','.join(fields),
            'limit': limit
        }
        
        response = await self._make_request_with_token_and_rate_limiting(
            method='GET',
            endpoint=f'{account_id}/adsets',
            params=params
        )
        
        adsets = response.get('data', [])
        logger.info(f"Retrieved {len(adsets)} adsets for account {account_id}")
        
        return adsets
    
    # ========== DATE CHUNKING METHODS ==========
    
    @staticmethod
    def create_month_chunks(start_date: str, end_date: str) -> List[Tuple[str, str]]:
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
    
    @staticmethod
    def create_weekly_chunks(start_date: str, end_date: str, chunk_days: int = 7) -> List[Tuple[str, str]]:
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
    
    @staticmethod
    def create_date_chunks(start_date: str, end_date: str, chunk_days: int = 7) -> List[Tuple[str, str]]:
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
        monthly_chunks = MetaAPIClient.create_month_chunks(start_date, end_date)
        
        # Then subdivide each month into weekly chunks
        all_chunks = []
        for month_start, month_end in monthly_chunks:
            weekly_chunks = MetaAPIClient.create_weekly_chunks(month_start, month_end, chunk_days)
            all_chunks.extend(weekly_chunks)
        
        logger.info(f"Created {len(all_chunks)} total chunks ({len(monthly_chunks)} months × weekly sub-chunks)")
        return all_chunks
    
    # ========== CONCURRENT PROCESSING METHODS ==========
    
    async def process_chunks_concurrently(
        self,
        account_id: str,
        chunks: List[Tuple[str, str]],
        max_concurrent: int = 5,
        **insights_params
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Process multiple date chunks concurrently with simple threading control.
        
        Args:
            account_id: Meta ad account ID
            chunks: List of (start_date, end_date) tuples
            max_concurrent: Maximum number of concurrent requests
            **insights_params: Additional parameters for insights API
            
        Yields:
            Individual insights records from all chunks
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_chunk(chunk_start: str, chunk_end: str):
            async with semaphore:
                logger.debug(f"Processing chunk {chunk_start} to {chunk_end}")
                
                time_range = {
                    'since': chunk_start,
                    'until': chunk_end
                }
                
                chunk_results = []
                async for item in self.get_insights_paginated(
                    account_id=account_id,
                    time_range=time_range,
                    **insights_params
                ):
                    chunk_results.append(item)
                
                logger.debug(f"Chunk {chunk_start} to {chunk_end}: {len(chunk_results)} records")
                return chunk_results
        
        # Create tasks for all chunks
        tasks = [
            process_single_chunk(chunk_start, chunk_end)
            for chunk_start, chunk_end in chunks
        ]
        
        # Process chunks and yield results
        total_records = 0
        for task in asyncio.as_completed(tasks):
            chunk_results = await task
            for item in chunk_results:
                total_records += 1
                yield item
        
        logger.info(f"Processed {len(chunks)} chunks, total records: {total_records}")