"""
Pydantic models for API responses.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ArticleResponse(BaseModel):
    """Article response model."""

    id: str = Field(..., description="Article ID")
    title: str = Field(..., description="Article title")
    content: str = Field(..., description="Article content")
    summary: str = Field(..., description="Article summary")
    source: str = Field(..., description="News source")
    category: str = Field(..., description="Article category")
    author: str = Field(..., description="Article author")
    tags: List[str] = Field(default_factory=list, description="Article tags")
    url: str = Field(..., description="Original article URL")
    images: List[str] = Field(default_factory=list, description="Article images")
    publish_time: str = Field(..., description="Publish time")
    crawl_time: str = Field(..., description="Crawl time")
    highlight: Optional[Dict[str, List[str]]] = Field(None, description="Search highlights")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "abc123",
                "title": "人工智能技术发展迅速",
                "content": "文章内容...",
                "summary": "摘要...",
                "source": "sina",
                "category": "科技",
                "author": "新浪科技",
                "tags": ["人工智能", "科技"],
                "url": "https://news.sina.com.cn/...",
                "images": ["https://example.com/image.jpg"],
                "publish_time": "2024-03-17 10:00:00",
                "crawl_time": "2024-03-17 11:00:00"
            }
        }


class SearchResponse(BaseModel):
    """Search response model."""

    total: int = Field(..., description="Total number of results")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Results per page")
    results: List[ArticleResponse] = Field(..., description="Search results")
    aggregations: Optional[Dict[str, Any]] = Field(None, description="Aggregations by source/category")
    took: int = Field(..., description="Search time in milliseconds")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 100,
                "page": 1,
                "page_size": 10,
                "results": [],
                "aggregations": {
                    "sources": {"sina": 50, "netease": 30, "tencent": 20},
                    "categories": {"科技": 60, "财经": 40}
                },
                "took": 25
            }
        }


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Service status")
    elasticsearch: Dict[str, Any] = Field(..., description="Elasticsearch health")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="Current timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "elasticsearch": {
                    "status": "green",
                    "cluster_name": "news-crawler",
                    "number_of_nodes": 1
                },
                "version": "1.0.0",
                "timestamp": "2024-03-17T10:00:00"
            }
        }


class StatsResponse(BaseModel):
    """Statistics response model."""

    total_articles: int = Field(..., description="Total number of articles")
    breakdown: Dict[str, int] = Field(..., description="Breakdown by dimension")

    class Config:
        json_schema_extra = {
            "example": {
                "total_articles": 1000,
                "breakdown": {
                    "sina": 500,
                    "netease": 300,
                    "tencent": 200
                }
            }
        }
