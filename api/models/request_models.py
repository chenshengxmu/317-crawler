"""
Pydantic models for API request validation.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator


class DateRangeFilter(BaseModel):
    """Date range filter for search."""

    date_from: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")

    @validator('date_from', 'date_to')
    def validate_date_format(cls, v):
        """Validate date format."""
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('Date must be in YYYY-MM-DD format')
        return v


class SearchRequest(BaseModel):
    """Search request model."""

    query: str = Field(..., description="Search query (keywords)", min_length=1, max_length=200)
    sources: Optional[List[str]] = Field(None, description="Filter by sources (sina, netease, tencent)")
    categories: Optional[List[str]] = Field(None, description="Filter by categories")
    date_from: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    page: int = Field(1, description="Page number", ge=1)
    page_size: int = Field(10, description="Results per page", ge=1, le=100)
    sort_by: str = Field("relevance", description="Sort by: relevance, publish_time")

    @validator('date_from', 'date_to')
    def validate_date_format(cls, v):
        """Validate date format."""
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('Date must be in YYYY-MM-DD format')
        return v

    @validator('sort_by')
    def validate_sort_by(cls, v):
        """Validate sort_by field."""
        allowed = ['relevance', 'publish_time']
        if v not in allowed:
            raise ValueError(f'sort_by must be one of: {", ".join(allowed)}')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "query": "人工智能",
                "sources": ["sina"],
                "categories": ["科技"],
                "date_from": "2024-03-01",
                "date_to": "2024-03-17",
                "page": 1,
                "page_size": 10,
                "sort_by": "publish_time"
            }
        }
