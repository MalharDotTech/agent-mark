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


