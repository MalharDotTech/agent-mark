"""
Request models for the Meta Ads API service.
"""
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class ExtractionRequest(BaseModel):
    """Model for data extraction requests."""
    
    account_ids: List[str] = Field(
        ..., 
        description="List of Meta ad account IDs to extract data from",
        min_items=1
    )
    start_date: str = Field(
        ..., 
        description="Start date in YYYY-MM-DD format",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    end_date: str = Field(
        ..., 
        description="End date in YYYY-MM-DD format", 
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    fields: Optional[List[str]] = Field(
        default=None,
        description="Optional list of fields to extract"
    )
    breakdowns: Optional[List[str]] = Field(
        default=None,
        description="Optional list of breakdowns to apply"
    )
    chunk_size_days: Optional[int] = Field(
        default=7,
        description="Number of days per chunk for processing",
        ge=1,
        le=30
    )
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Ensure end_date is after start_date."""
        if 'start_date' in values:
            start = date.fromisoformat(values['start_date'])
            end = date.fromisoformat(v)
            if end < start:
                raise ValueError('end_date must be after start_date')
        return v
    
    @validator('account_ids')
    def validate_account_ids(cls, v):
        """Ensure account IDs are valid."""
        for account_id in v:
            if not account_id.strip():
                raise ValueError('Account IDs cannot be empty')
        return v


class RNFCumulativeRequest(BaseModel):
    """Model for RNF cumulative reach & frequency extraction requests."""
    
    account_ids: List[str] = Field(
        ...,
        description="List of Meta ad account IDs",
        min_items=1
    )
    start_date: str = Field(
        ...,
        description="Start date in YYYY-MM-DD format",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    end_date: str = Field(
        ...,
        description="End date in YYYY-MM-DD format",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    level: str = Field(
        default='account',
        description="Analysis level: account, campaign, adset, or ad"
    )
    time_increment: str = Field(
        default='1',
        description="Time increment: '1' for daily, '7' for weekly, 'monthly' for monthly"
    )
    entity_ids: Optional[List[str]] = Field(
        default=None,
        description="Optional list of campaign/adset/ad IDs to filter"
    )
    chunk_size_days: int = Field(
        default=7,
        description="Number of days per chunk for processing",
        ge=1,
        le=30
    )
    
    @validator('level')
    def validate_level(cls, v):
        """Ensure level is valid."""
        allowed_levels = ['account', 'campaign', 'adset', 'ad']
        if v not in allowed_levels:
            raise ValueError(f'level must be one of: {", ".join(allowed_levels)}')
        return v
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Ensure end_date is after start_date."""
        if 'start_date' in values:
            start = date.fromisoformat(values['start_date'])
            end = date.fromisoformat(v)
            if end < start:
                raise ValueError('end_date must be after start_date')
        return v


class RNFOverlapRequest(BaseModel):
    """Model for RNF audience overlap analysis requests."""
    
    account_id: str = Field(
        ...,
        description="Meta ad account ID"
    )
    start_date: str = Field(
        ...,
        description="Start date in YYYY-MM-DD format",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    end_date: str = Field(
        ...,
        description="End date in YYYY-MM-DD format",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    level: str = Field(
        ...,
        description="Analysis level: campaign or adset"
    )
    entity_ids: List[str] = Field(
        ...,
        description="List of campaign/adset IDs to analyze (minimum 2)",
        min_items=2
    )
    refresh_existing: bool = Field(
        default=False,
        description="Whether to refresh existing overlap data"
    )
    
    @validator('level')
    def validate_level(cls, v):
        """Ensure level is valid for overlap analysis."""
        allowed_levels = ['campaign', 'adset']
        if v not in allowed_levels:
            raise ValueError(f'level must be one of: {", ".join(allowed_levels)}')
        return v
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Ensure end_date is after start_date."""
        if 'start_date' in values:
            start = date.fromisoformat(values['start_date'])
            end = date.fromisoformat(v)
            if end < start:
                raise ValueError('end_date must be after start_date')
        return v


class AudienceRequest(BaseModel):
    """Model for audience insights extraction requests."""
    
    account_ids: List[str] = Field(
        ...,
        description="List of Meta ad account IDs",
        min_items=1
    )
    start_date: str = Field(
        ...,
        description="Start date in YYYY-MM-DD format",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    end_date: str = Field(
        ...,
        description="End date in YYYY-MM-DD format",
        pattern=r'^\d{4}-\d{2}-\d{2}$'
    )
    breakdown_types: List[str] = Field(
        ...,
        description="List of breakdown types: age, gender, country, region, device_platform",
        min_items=1
    )
    level: str = Field(
        default='campaign',
        description="Analysis level: campaign, adset, or ad"
    )
    entity_ids: Optional[List[str]] = Field(
        default=None,
        description="Optional list of campaign/adset/ad IDs to filter"
    )
    
    @validator('breakdown_types')
    def validate_breakdown_types(cls, v):
        """Ensure breakdown types are valid."""
        allowed_breakdowns = [
            'age', 'gender', 'country', 'region',
            'device_platform', 'publisher_platform',
            'platform_position', 'impression_device'
        ]
        for breakdown in v:
            if breakdown not in allowed_breakdowns:
                raise ValueError(f'Invalid breakdown type: {breakdown}. Allowed: {", ".join(allowed_breakdowns)}')
        return v
    
    @validator('level')
    def validate_level(cls, v):
        """Ensure level is valid."""
        allowed_levels = ['account', 'campaign', 'adset', 'ad']
        if v not in allowed_levels:
            raise ValueError(f'level must be one of: {", ".join(allowed_levels)}')
        return v
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Ensure end_date is after start_date."""
        if 'start_date' in values:
            start = date.fromisoformat(values['start_date'])
            end = date.fromisoformat(v)
            if end < start:
                raise ValueError('end_date must be after start_date')
        return v


