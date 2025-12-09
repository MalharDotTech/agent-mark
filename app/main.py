"""Main FastAPI application for Meta Ads API Service."""

import uuid
import time
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import settings
from .core.logging import setup_logging, get_logger
from .core.exceptions import (
    MetaAPIException, RateLimitException, TokenException, 
    DataExtractionException, ValidationException, ConfigurationException
)
from .core.metrics import metrics_collector

from .models.requests import (
    ExtractionRequest, RNFCumulativeRequest, RNFOverlapRequest, AudienceRequest
)
from .models.responses import (
    AccountInfo, HealthResponse, ErrorResponse, DataJobType, DataResponse
)

from .services.meta_client import MetaAPIClient
from .services.data_extraction_service import DataExtractionService
from .core.token_manager import TokenManager
from .core.rate_limiter import RateLimiter
from .core.database import db_manager
from .marimo_server import create_marimo_server

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Meta Ads API Service",
    description="FastAPI service for extracting Meta advertising data with intelligent rate limiting",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# These will be initialized in startup event
token_manager = None
rate_limiter = None
meta_client = None
data_extraction_service = None
rnf_extraction_service = None
audience_extraction_service = None

# Track startup time for metrics
startup_time = time.time()


# Exception handlers for custom exceptions

@app.exception_handler(RateLimitException)
async def rate_limit_exception_handler(request: Request, exc: RateLimitException):
    """Handle rate limit exceptions."""
    correlation_id = str(uuid.uuid4())
    
    logger.warning(
        f"Rate limit exceeded: {exc.message}",
        extra={
            "correlation_id": correlation_id,
            "path": request.url.path,
            "method": request.method,
            "meta_error_code": exc.meta_error_code,
            "cooldown_seconds": exc.cooldown_seconds
        }
    )
    
    return JSONResponse(
        status_code=429,
        content=ErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details={
                "meta_error_code": exc.meta_error_code,
                "cooldown_seconds": exc.cooldown_seconds,
                "retry_after": exc.cooldown_seconds
            },
            correlation_id=correlation_id,
            timestamp=exc.timestamp
        ).dict()
    )


@app.exception_handler(TokenException)
async def token_exception_handler(request: Request, exc: TokenException):
    """Handle token-related exceptions."""
    correlation_id = str(uuid.uuid4())
    
    logger.error(
        f"Token error: {exc.message}",
        extra={
            "correlation_id": correlation_id,
            "path": request.url.path,
            "method": request.method,
            "token_index": exc.token_index
        }
    )
    
    return JSONResponse(
        status_code=401,
        content=ErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details={"token_index": exc.token_index},
            correlation_id=correlation_id,
            timestamp=exc.timestamp
        ).dict()
    )


@app.exception_handler(DataExtractionException)
async def data_extraction_exception_handler(request: Request, exc: DataExtractionException):
    """Handle data extraction exceptions."""
    correlation_id = str(uuid.uuid4())
    
    logger.error(
        f"Data extraction error: {exc.message}",
        extra={
            "correlation_id": correlation_id,
            "path": request.url.path,
            "method": request.method,
            "account_id": exc.account_id
        }
    )
    
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details={
                "account_id": exc.account_id
            },
            correlation_id=correlation_id,
            timestamp=exc.timestamp
        ).dict()
    )


@app.exception_handler(ValidationException)
async def validation_exception_handler(request: Request, exc: ValidationException):
    """Handle validation exceptions."""
    correlation_id = str(uuid.uuid4())
    
    logger.warning(
        f"Validation error: {exc.message}",
        extra={
            "correlation_id": correlation_id,
            "path": request.url.path,
            "method": request.method,
            "field": exc.field
        }
    )
    
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details={"field": exc.field},
            correlation_id=correlation_id,
            timestamp=exc.timestamp
        ).dict()
    )


@app.exception_handler(ConfigurationException)
async def configuration_exception_handler(request: Request, exc: ConfigurationException):
    """Handle configuration exceptions."""
    correlation_id = str(uuid.uuid4())
    
    logger.error(
        f"Configuration error: {exc.message}",
        extra={
            "correlation_id": correlation_id,
            "path": request.url.path,
            "method": request.method,
            "config_key": exc.config_key
        }
    )
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details={"config_key": exc.config_key},
            correlation_id=correlation_id,
            timestamp=exc.timestamp
        ).dict()
    )


@app.exception_handler(MetaAPIException)
async def meta_api_exception_handler(request: Request, exc: MetaAPIException):
    """Handle general Meta API exceptions."""
    correlation_id = str(uuid.uuid4())
    
    logger.error(
        f"Meta API error: {exc.message}",
        extra={
            "correlation_id": correlation_id,
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.error_code,
            "details": exc.details
        }
    )
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            correlation_id=correlation_id,
            timestamp=exc.timestamp
        ).dict()
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    correlation_id = str(uuid.uuid4())
    
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "correlation_id": correlation_id,
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__
        }
    )
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="An internal server error occurred",
            correlation_id=correlation_id,
            timestamp=datetime.utcnow()
        ).dict()
    )


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    global token_manager, rate_limiter, meta_client, data_extraction_service
    global rnf_extraction_service, audience_extraction_service
    
    logger.info("Starting Meta Ads API Service")
    logger.info(f"Meta API Version: {settings.meta_api_version}")
    logger.info(f"Log Level: {settings.log_level}")
    logger.info(f"Max Concurrent Requests: {settings.max_concurrent_requests}")
    
    # Initialize database
    await db_manager.create_tables_async()
    await db_manager.initialize_default_job_types_async()
    
    # Initialize core services (Meta API client and supporting services)
    token_manager = TokenManager(settings.get_access_tokens())
    rate_limiter = RateLimiter(token_manager)
    meta_client = MetaAPIClient(token_manager, rate_limiter)
    
    # Initialize data extraction services
    data_extraction_service = DataExtractionService(meta_client, db_manager)
    
    # Initialize RNF and Audience extraction services
    from .services.rnf_extraction_service import RNFExtractionService
    from .services.audience_extraction_service import AudienceExtractionService
    
    rnf_extraction_service = RNFExtractionService(meta_client, db_manager)
    audience_extraction_service = AudienceExtractionService(meta_client, db_manager)
    
    # Log number of tokens (without exposing them)
    token_count = len(settings.get_access_tokens()) if settings.meta_access_tokens else 0
    logger.info(f"Configured with {token_count} access tokens")
    logger.info(f"SQLite database path: {settings.sqlite_db_path}")
    
    logger.info("Core services initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("Shutting down Meta Ads API Service")
    
    # Close Meta API client
    if meta_client:
        await meta_client.close()
    
    logger.info("Core services shut down successfully")


# API Endpoints

@app.get("/api/v1/accounts", response_model=List[AccountInfo])
async def get_accounts():
    """
    Get list of available Meta ad accounts from SQLite database.
    
    Returns all ad accounts stored in the database, with fallback to Meta API.
    
    Requirements: 1.3 - Support for listing available ad accounts
    """
    try:
        # First try to get accounts from database
        db_accounts = await db_manager.get_accounts_async()
        
        if db_accounts:
            # Transform database records to response model
            accounts = []
            for account in db_accounts:
                account_info = AccountInfo(
                    account_id=account["account_id"],
                    account_name=account["account_name"]
                )
                accounts.append(account_info)
            
            logger.info(f"Retrieved {len(accounts)} ad accounts from database")
            return accounts
        
        # Fallback: Get ad accounts from Meta API and store them
        accounts_data = await meta_client.get_ad_accounts()
        
        # Store accounts in database and transform to response model
        accounts = []
        for account in accounts_data:
            account_id = account.get("id", "").replace("act_", "")
            account_name = account.get("name", "")
            
            # Store in database
            await db_manager.insert_account_async(
                account_id=account_id,
                account_name=account_name,
                api_token_key="meta_api_token"
            )
            
            account_info = AccountInfo(
                account_id=account_id,
                account_name=account_name
            )
            accounts.append(account_info)
        
        logger.info(f"Retrieved and stored {len(accounts)} ad accounts from Meta API")
        return accounts
        
    except Exception as e:
        logger.error(f"Failed to get ad accounts: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve ad accounts: {str(e)}"
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for monitoring system status.
    
    Checks connectivity to Meta API and other system components.
    
    Requirements: 7.3 - Health check endpoints for monitoring system status
    """
    health_start_time = time.time()
    
    try:
        # Check Meta API accessibility with detailed testing
        meta_api_accessible = True
        meta_api_response_time = None
        
        try:
            # Try to get a simple response from Meta API
            api_start_time = time.time()
            accounts = await meta_client.get_ad_accounts()
            meta_api_response_time = round((time.time() - api_start_time) * 1000, 2)
            
            logger.info(f"Health check: Meta API accessible, {len(accounts)} accounts, "
                       f"response time: {meta_api_response_time}ms")
        except Exception as e:
            logger.warning(f"Meta API health check failed: {str(e)}")
            meta_api_accessible = False
        
        # Check token manager status
        token_stats = token_manager.get_token_stats()
        tokens_available = token_stats.get("available_tokens", 0) > 0
        
        # Check SQLite database connectivity
        database_connected = await db_manager.health_check_async()
        
        # Determine overall status based on Meta API, token availability, and database
        if meta_api_accessible and tokens_available and database_connected:
            status = "healthy"
        elif (meta_api_accessible and tokens_available) or (meta_api_accessible and database_connected) or (tokens_available and database_connected):
            status = "degraded"
        else:
            status = "unhealthy"
        
        health_response_time = round((time.time() - health_start_time) * 1000, 2)
        
        logger.info(f"Health check completed: {status} (took {health_response_time}ms)")
        
        return HealthResponse(
            status=status,
            timestamp=datetime.utcnow(),
            meta_api_accessible=meta_api_accessible,
            database_connected=database_connected,
            details={
                "meta_api_response_time_ms": meta_api_response_time,
                "health_check_time_ms": health_response_time,
                "token_stats": token_stats,
                "sqlite_db_path": settings.sqlite_db_path
            }
        )
        
    except Exception as e:
        health_response_time = round((time.time() - health_start_time) * 1000, 2)
        logger.error(f"Health check failed: {str(e)} (took {health_response_time}ms)")
        
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            meta_api_accessible=False,
            database_connected=False,
            details={
                "error": str(e),
                "health_check_time_ms": health_response_time,
                "sqlite_db_path": settings.sqlite_db_path
            }
        )


@app.get("/api/v1/metrics")
async def get_metrics():
    """
    Get basic system metrics for monitoring.
    
    Returns token statistics and system health metrics.
    
    Requirements: 7.4 - Track and expose metrics for API call success rates and latencies
    """
    try:
        # Get token manager statistics
        token_stats = token_manager.get_token_stats()
        
        # Get API call metrics
        api_metrics = metrics_collector.get_metrics_summary()
        
        # Get basic system metrics
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": {
                "name": "Meta Ads API Service",
                "version": "1.0.0",
                "uptime_seconds": time.time() - startup_time if 'startup_time' in globals() else 0
            },
            "tokens": token_stats,
            "meta_api": {
                "version": settings.meta_api_version,
                "max_concurrent_requests": settings.max_concurrent_requests
            },
            "database": {
                "type": "SQLite",
                "path": settings.sqlite_db_path,
                "connected": await db_manager.health_check_async()
            },
            "api_calls": api_metrics
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve metrics: {str(e)}"
        )


@app.get("/api/v1/job-types", response_model=List[DataJobType])
async def get_job_types():
    """
    Get list of available data job types.
    
    Returns all active data job types that can be used for data extraction.
    
    Requirements: 3.4, 4.1 - Support for listing available job types
    """
    try:
        job_types_data = await db_manager.get_data_job_types_async()
        
        # Transform to response model
        job_types = []
        for job_type in job_types_data:
            job_type_info = DataJobType(
                job_type_id=job_type["job_type_id"],
                job_name=job_type["job_name"],
                description=job_type.get("description"),
                table_name=job_type["table_name"],
                is_active=bool(job_type["is_active"])
            )
            job_types.append(job_type_info)
        
        logger.info(f"Retrieved {len(job_types)} job types")
        return job_types
        
    except Exception as e:
        logger.error(f"Failed to get job types: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve job types: {str(e)}"
        )


@app.get("/api/v1/data/{job_type}/{account_id}", response_model=DataResponse)
async def get_data(
    job_type: str,
    account_id: str,
    limit: Optional[int] = 1000,
    date_start: Optional[str] = None,
    date_end: Optional[str] = None
):
    """
    Get stored data for a specific job type and account.
    
    Args:
        job_type: Type of data to retrieve (e.g., 'ad_performance')
        account_id: Meta ad account ID
        limit: Maximum number of records to return (default 1000)
        date_start: Optional start date filter (YYYY-MM-DD)
        date_end: Optional end date filter (YYYY-MM-DD)
    
    Returns:
        Stored data records for the specified job type and account
    
    Requirements: 3.4, 4.1 - Support for retrieving stored data
    """
    try:
        # Build filters
        filters = {}
        if date_start:
            filters['date_start'] = date_start
        if date_end:
            filters['date_stop'] = date_end
        
        # Get data from extraction service
        data_records = await data_extraction_service.get_stored_data(
            account_id=account_id,
            job_type=job_type,
            filters=filters if filters else None
        )
        
        # Apply limit if specified
        if limit and len(data_records) > limit:
            data_records = data_records[:limit]
        
        logger.info(f"Retrieved {len(data_records)} records for {job_type}/{account_id}")
        
        return DataResponse(
            job_type=job_type,
            account_id=account_id,
            total_records=len(data_records),
            data=data_records,
            filters_applied=filters if filters else None,
            retrieved_at=datetime.utcnow()
        )
        
    except ValueError as e:
        logger.warning(f"Invalid job type {job_type}: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid job type: {job_type}"
        )
    except Exception as e:
        logger.error(f"Failed to get data for {job_type}/{account_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve data: {str(e)}"
        )


@app.post("/api/v1/extract")
async def extract_data(extraction_request: ExtractionRequest):
    """
    Extract data from Meta API and store in SQLite database.
    
    Args:
        extraction_request: Extraction parameters including account IDs and date range
    
    Returns:
        Extraction results with statistics and job information
    
    Requirements: 3.1, 3.2 - Extract data and store in SQLite database
    """
    try:
        # Generate job ID for tracking
        job_id = str(uuid.uuid4())
        
        logger.info(f"Starting data extraction job {job_id} for accounts: {extraction_request.account_ids}")
        logger.info(f"Date range: {extraction_request.start_date} to {extraction_request.end_date}")
        
        # Call the data extraction service
        result = await data_extraction_service.extract_and_store(
            extraction_request=extraction_request,
            job_id=job_id
        )
        
        logger.info(f"Extraction job {job_id} completed: {result['total_records']} records stored")
        
        return result
        
    except ValueError as e:
        logger.warning(f"Invalid extraction request: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Data extraction failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Data extraction failed: {str(e)}"
        )


@app.get("/api/v1/debug/recent-calls")
async def get_recent_api_calls(limit: int = 50):
    """
    Get recent API calls for debugging purposes.
    
    Args:
        limit: Maximum number of recent calls to return (default 50)
    
    Returns:
        List of recent API call records with timestamps and performance data
    """
    try:
        recent_calls = metrics_collector.get_recent_calls(limit)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "limit": limit,
            "total_calls": len(recent_calls),
            "calls": recent_calls
        }
        
    except Exception as e:
        logger.error(f"Failed to get recent API calls: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve recent API calls: {str(e)}"
        )


# RNF Endpoints

@app.post("/api/v1/extract-rnf-cumulative")
async def extract_rnf_cumulative(request: RNFCumulativeRequest):
    """
    Extract cumulative reach & frequency data.
    
    Args:
        request: RNF cumulative extraction parameters
    
    Returns:
        Extraction results with statistics
    
    Requirements: RNF cumulative extraction
    """
    try:
        job_id = str(uuid.uuid4())
        
        logger.info(f"Starting RNF cumulative extraction job {job_id}")
        logger.info(f"Accounts: {request.account_ids}, Level: {request.level}")
        
        results = []
        
        for account_id in request.account_ids:
            result = await rnf_extraction_service.extract_cumulative_rnf(
                account_id=account_id,
                start_date=request.start_date,
                end_date=request.end_date,
                level=request.level,
                time_increment=request.time_increment,
                entity_ids=request.entity_ids
            )
            results.append(result)
        
        total_records = sum(r['records_processed'] for r in results)
        
        logger.info(f"RNF cumulative extraction job {job_id} completed: {total_records} records")
        
        return {
            "job_id": job_id,
            "total_records": total_records,
            "accounts_processed": len(request.account_ids),
            "results": results,
            "extraction_time": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"RNF cumulative extraction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"RNF cumulative extraction failed: {str(e)}"
        )


@app.post("/api/v1/extract-rnf-overlap")
async def extract_rnf_overlap(request: RNFOverlapRequest):
    """
    Compute audience overlap (expensive - N² API calls).
    
    Args:
        request: RNF overlap extraction parameters
    
    Returns:
        Overlap analysis results
    
    Requirements: RNF overlap analysis
    """
    try:
        job_id = str(uuid.uuid4())
        
        logger.info(f"Starting RNF overlap analysis job {job_id}")
        logger.info(f"Account: {request.account_id}, Level: {request.level}")
        logger.info(f"Entities: {len(request.entity_ids)} (will compute {len(request.entity_ids) * (len(request.entity_ids) - 1) // 2} pairs)")
        
        result = await rnf_extraction_service.extract_audience_overlap(
            account_id=request.account_id,
            start_date=request.start_date,
            end_date=request.end_date,
            level=request.level,
            entity_ids=request.entity_ids,
            refresh_existing=request.refresh_existing
        )
        
        logger.info(f"RNF overlap analysis job {job_id} completed")
        
        return {
            "job_id": job_id,
            **result
        }
        
    except ValueError as e:
        logger.warning(f"Invalid RNF overlap request: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"RNF overlap analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"RNF overlap analysis failed: {str(e)}"
        )


@app.get("/api/v1/rnf-overlap/{account_id}")
async def get_stored_overlap(
    account_id: str,
    level: Optional[str] = None,
    date_start: Optional[str] = None,
    date_stop: Optional[str] = None
):
    """
    Get stored overlap results.
    
    Args:
        account_id: Meta ad account ID
        level: Optional analysis level filter
        date_start: Optional start date filter
        date_stop: Optional end date filter
    
    Returns:
        Stored overlap data
    
    Requirements: RNF overlap data retrieval
    """
    try:
        overlap_data = await rnf_extraction_service.get_stored_overlap(
            account_id=account_id,
            level=level,
            date_start=date_start,
            date_stop=date_stop
        )
        
        logger.info(f"Retrieved {len(overlap_data)} overlap records for account {account_id}")
        
        return {
            "account_id": account_id,
            "total_records": len(overlap_data),
            "data": overlap_data,
            "filters_applied": {
                "level": level,
                "date_start": date_start,
                "date_stop": date_stop
            },
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get overlap data for {account_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve overlap data: {str(e)}"
        )


# Audience Insights Endpoints

@app.post("/api/v1/extract-audience")
async def extract_audience_insights(request: AudienceRequest):
    """
    Extract audience insights with breakdowns.
    
    Args:
        request: Audience insights extraction parameters
    
    Returns:
        Extraction results with statistics
    
    Requirements: Audience insights extraction
    """
    try:
        job_id = str(uuid.uuid4())
        
        logger.info(f"Starting audience insights extraction job {job_id}")
        logger.info(f"Accounts: {request.account_ids}, Breakdowns: {request.breakdown_types}")
        
        results = []
        
        for account_id in request.account_ids:
            result = await audience_extraction_service.extract_audience_insights(
                account_id=account_id,
                start_date=request.start_date,
                end_date=request.end_date,
                breakdown_types=request.breakdown_types,
                level=request.level,
                entity_ids=request.entity_ids
            )
            results.append(result)
        
        total_records = sum(r['total_records'] for r in results)
        
        logger.info(f"Audience insights extraction job {job_id} completed: {total_records} records")
        
        return {
            "job_id": job_id,
            "total_records": total_records,
            "accounts_processed": len(request.account_ids),
            "results": results,
            "extraction_time": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Audience insights extraction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Audience insights extraction failed: {str(e)}"
        )


@app.get("/api/v1/audience/{account_id}")
async def get_audience_data(
    account_id: str,
    breakdown_type: Optional[str] = None,
    breakdown_value: Optional[str] = None,
    date_start: Optional[str] = None,
    date_stop: Optional[str] = None
):
    """
    Get stored audience insights.
    
    Args:
        account_id: Meta ad account ID
        breakdown_type: Optional breakdown type filter
        breakdown_value: Optional breakdown value filter
        date_start: Optional start date filter
        date_stop: Optional end date filter
    
    Returns:
        Stored audience insights data
    
    Requirements: Audience insights data retrieval
    """
    try:
        audience_data = await audience_extraction_service.get_stored_audience_insights(
            account_id=account_id,
            breakdown_type=breakdown_type,
            breakdown_value=breakdown_value,
            date_start=date_start,
            date_stop=date_stop
        )
        
        logger.info(f"Retrieved {len(audience_data)} audience insights records for account {account_id}")
        
        return {
            "account_id": account_id,
            "total_records": len(audience_data),
            "data": audience_data,
            "filters_applied": {
                "breakdown_type": breakdown_type,
                "breakdown_value": breakdown_value,
                "date_start": date_start,
                "date_stop": date_stop
            },
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get audience data for {account_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve audience data: {str(e)}"
        )


@app.get("/api/v1/audience/{account_id}/summary")
async def get_audience_summary(
    account_id: str,
    breakdown_type: str,
    date_start: Optional[str] = None,
    date_stop: Optional[str] = None
):
    """
    Get audience insights summary with aggregated statistics.
    
    Args:
        account_id: Meta ad account ID
        breakdown_type: Breakdown type (age, gender, country, etc.)
        date_start: Optional start date filter
        date_stop: Optional end date filter
    
    Returns:
        Aggregated audience insights summary
    
    Requirements: Audience insights summary
    """
    try:
        summary = await audience_extraction_service.get_breakdown_summary(
            account_id=account_id,
            breakdown_type=breakdown_type,
            date_start=date_start,
            date_stop=date_stop
        )
        
        logger.info(f"Retrieved audience summary for account {account_id}, breakdown: {breakdown_type}")
        
        return {
            **summary,
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get audience summary for {account_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve audience summary: {str(e)}"
        )


# Mount marimo dashboards at root (must be done after all FastAPI routes)
# FastAPI will check its routes first, then fall through to marimo for unmatched paths
try:
    marimo_asgi = create_marimo_server()
    app.mount("/", marimo_asgi)
    logger.info("Marimo dashboards mounted at root path")
except Exception as e:
    logger.error(f"Failed to mount marimo dashboards: {e}")
    logger.warning("Continuing without marimo dashboard integration")