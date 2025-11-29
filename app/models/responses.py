"""
Response models for the Meta Ads API service.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field



class AccountInfo(BaseModel):
    """Model for ad account information."""
    
    account_id: str = Field(
        ...,
        description="Meta ad account ID"
    )
    account_name: str = Field(
        ...,
        description="Meta ad account name"
    )


class HealthResponse(BaseModel):
    """Model for health check responses."""
    
    status: str = Field(
        ...,
        description="Service health status"
    )
    timestamp: datetime = Field(
        ...,
        description="Health check timestamp"
    )
    meta_api_accessible: bool = Field(
        ...,
        description="Whether Meta API is accessible"
    )
    database_connected: bool = Field(
        ...,
        description="Whether database is connected"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional health check details and metrics"
    )


class ErrorResponse(BaseModel):
    """Model for error responses."""
    
    error_code: str = Field(
        ...,
        description="Error code identifier"
    )
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )
    correlation_id: str = Field(
        ...,
        description="Request correlation ID for tracking"
    )
    timestamp: datetime = Field(
        ...,
        description="Error timestamp"
    )


class DataJobType(BaseModel):
    """Model for data job type information."""
    
    job_type_id: str = Field(
        ...,
        description="Unique identifier for the job type"
    )
    job_name: str = Field(
        ...,
        description="Human-readable name for the job type"
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of what this job type extracts"
    )
    table_name: str = Field(
        ...,
        description="Database table name where this job type's data is stored"
    )
    is_active: bool = Field(
        ...,
        description="Whether this job type is currently active"
    )


class AdPerformanceData(BaseModel):
    """Model for ad performance data records."""
    
    id: int = Field(
        ...,
        description="Unique record identifier"
    )
    account_id: str = Field(
        ...,
        description="Meta ad account ID"
    )
    date_start: str = Field(
        ...,
        description="Start date of the data period"
    )
    date_stop: str = Field(
        ...,
        description="End date of the data period"
    )
    campaign_id: Optional[str] = Field(
        default=None,
        description="Campaign ID"
    )
    campaign_name: Optional[str] = Field(
        default=None,
        description="Campaign name"
    )
    adset_id: Optional[str] = Field(
        default=None,
        description="Ad set ID"
    )
    adset_name: Optional[str] = Field(
        default=None,
        description="Ad set name"
    )
    ad_id: Optional[str] = Field(
        default=None,
        description="Ad ID"
    )
    ad_name: Optional[str] = Field(
        default=None,
        description="Ad name"
    )
    impressions: Optional[int] = Field(
        default=None,
        description="Number of impressions"
    )
    clicks: Optional[int] = Field(
        default=None,
        description="Number of clicks"
    )
    spend: Optional[float] = Field(
        default=None,
        description="Amount spent"
    )
    reach: Optional[int] = Field(
        default=None,
        description="Number of people reached"
    )
    frequency: Optional[float] = Field(
        default=None,
        description="Average frequency"
    )
    cpm: Optional[float] = Field(
        default=None,
        description="Cost per mille (thousand impressions)"
    )
    cpc: Optional[float] = Field(
        default=None,
        description="Cost per click"
    )
    ctr: Optional[float] = Field(
        default=None,
        description="Click-through rate"
    )
    extracted_at: datetime = Field(
        ...,
        description="Timestamp when the data was extracted"
    )


class DataResponse(BaseModel):
    """Model for data retrieval responses."""
    
    job_type: str = Field(
        ...,
        description="Type of data job"
    )
    account_id: str = Field(
        ...,
        description="Account ID the data belongs to"
    )
    total_records: int = Field(
        ...,
        description="Total number of records returned"
    )
    data: List[Dict[str, Any]] = Field(
        ...,
        description="The actual data records"
    )
    filters_applied: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Filters that were applied to the data"
    )
    retrieved_at: datetime = Field(
        ...,
        description="Timestamp when the data was retrieved"
    )