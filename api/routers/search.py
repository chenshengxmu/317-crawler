"""
Search and article retrieval endpoints.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Path
from loguru import logger

from api.models import SearchRequest, SearchResponse, ArticleResponse, StatsResponse
from storage import es_client
from config import settings

router = APIRouter(prefix="/api/v1", tags=["search"])


def build_search_query(request: SearchRequest) -> Dict[str, Any]:
    """
    Build Elasticsearch query from search request.

    Args:
        request: Search request model

    Returns:
        Elasticsearch query DSL
    """
    # Base query - multi-match on title and content
    must_clauses = [
        {
            "multi_match": {
                "query": request.query,
                "fields": ["title^3", "content", "summary^2"],  # Boost title and summary
                "type": "best_fields",
                "operator": "or",
                "fuzziness": "AUTO"
            }
        }
    ]

    # Filter clauses
    filter_clauses = []

    # Filter by sources
    if request.sources:
        filter_clauses.append({
            "terms": {"source": request.sources}
        })

    # Filter by categories
    if request.categories:
        filter_clauses.append({
            "terms": {"category": request.categories}
        })

    # Filter by date range
    if request.date_from or request.date_to:
        date_range = {}
        if request.date_from:
            date_range["gte"] = request.date_from
        if request.date_to:
            date_range["lte"] = request.date_to + " 23:59:59"

        filter_clauses.append({
            "range": {"publish_time": date_range}
        })

    # Build bool query
    query = {
        "bool": {
            "must": must_clauses,
        }
    }

    if filter_clauses:
        query["bool"]["filter"] = filter_clauses

    return query


@router.post("/search", response_model=SearchResponse)
async def search_articles(request: SearchRequest):
    """
    Search articles with filters and pagination.

    Args:
        request: Search request with query and filters

    Returns:
        Search results with pagination and aggregations
    """
    try:
        # Build query
        query = build_search_query(request)

        # Calculate pagination
        from_ = (request.page - 1) * request.page_size

        # Build sort
        sort = []
        if request.sort_by == "publish_time":
            sort = [{"publish_time": {"order": "desc"}}]
        else:  # relevance (default)
            sort = [{"_score": {"order": "desc"}}]

        # Execute search with highlighting
        body = {
            "query": query,
            "from": from_,
            "size": request.page_size,
            "sort": sort,
            "highlight": {
                "fields": {
                    "title": {"pre_tags": ["<em>"], "post_tags": ["</em>"]},
                    "content": {
                        "pre_tags": ["<em>"],
                        "post_tags": ["</em>"],
                        "fragment_size": 150,
                        "number_of_fragments": 3
                    }
                }
            },
            "aggs": {
                "sources": {
                    "terms": {"field": "source", "size": 10}
                },
                "categories": {
                    "terms": {"field": "category", "size": 20}
                }
            }
        }

        result = es_client.get_client().search(index=settings.es_index, **body)

        # Parse results
        articles = []
        for hit in result['hits']['hits']:
            source = hit['_source']
            article = ArticleResponse(
                id=hit['_id'],
                title=source.get('title', ''),
                content=source.get('content', ''),
                summary=source.get('summary', ''),
                source=source.get('source', ''),
                category=source.get('category', ''),
                author=source.get('author', ''),
                tags=source.get('tags', []),
                url=source.get('url', ''),
                images=source.get('images', []),
                publish_time=source.get('publish_time', ''),
                crawl_time=source.get('crawl_time', ''),
                highlight=hit.get('highlight')
            )
            articles.append(article)

        # Parse aggregations
        aggregations = {}
        if 'aggregations' in result:
            aggregations['sources'] = {
                bucket['key']: bucket['doc_count']
                for bucket in result['aggregations']['sources']['buckets']
            }
            aggregations['categories'] = {
                bucket['key']: bucket['doc_count']
                for bucket in result['aggregations']['categories']['buckets']
            }

        return SearchResponse(
            total=result['hits']['total']['value'],
            page=request.page,
            page_size=request.page_size,
            results=articles,
            aggregations=aggregations,
            took=result['took']
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/articles/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: str = Path(..., description="Article ID")):
    """
    Get a single article by ID.

    Args:
        article_id: Article ID (url_hash)

    Returns:
        Article details
    """
    try:
        doc = es_client.get_document(settings.es_index, article_id)

        if not doc:
            raise HTTPException(status_code=404, detail="Article not found")

        return ArticleResponse(
            id=article_id,
            title=doc.get('title', ''),
            content=doc.get('content', ''),
            summary=doc.get('summary', ''),
            source=doc.get('source', ''),
            category=doc.get('category', ''),
            author=doc.get('author', ''),
            tags=doc.get('tags', []),
            url=doc.get('url', ''),
            images=doc.get('images', []),
            publish_time=doc.get('publish_time', ''),
            crawl_time=doc.get('crawl_time', '')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get article {article_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get article: {str(e)}")


@router.get("/stats/sources", response_model=StatsResponse)
async def get_source_stats():
    """
    Get article count by source.

    Returns:
        Statistics by news source
    """
    try:
        body = {
            "size": 0,
            "aggs": {
                "sources": {
                    "terms": {"field": "source", "size": 50}
                }
            }
        }

        result = es_client.get_client().search(index=settings.es_index, **body)

        breakdown = {
            bucket['key']: bucket['doc_count']
            for bucket in result['aggregations']['sources']['buckets']
        }

        return StatsResponse(
            total_articles=result['hits']['total']['value'],
            breakdown=breakdown
        )

    except Exception as e:
        logger.error(f"Failed to get source stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/stats/categories", response_model=StatsResponse)
async def get_category_stats():
    """
    Get article count by category.

    Returns:
        Statistics by category
    """
    try:
        body = {
            "size": 0,
            "aggs": {
                "categories": {
                    "terms": {"field": "category", "size": 50}
                }
            }
        }

        result = es_client.get_client().search(index=settings.es_index, **body)

        breakdown = {
            bucket['key']: bucket['doc_count']
            for bucket in result['aggregations']['categories']['buckets']
        }

        return StatsResponse(
            total_articles=result['hits']['total']['value'],
            breakdown=breakdown
        )

    except Exception as e:
        logger.error(f"Failed to get category stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/stats/trending")
async def get_trending_keywords(days: int = 7, top_k: int = 20):
    """
    Get trending keywords from recent articles.

    Args:
        days: Number of days to look back
        top_k: Number of top keywords to return

    Returns:
        List of trending keywords with counts
    """
    try:
        # Query articles from last N days
        body = {
            "size": 0,
            "query": {
                "range": {
                    "publish_time": {
                        "gte": f"now-{days}d/d"
                    }
                }
            },
            "aggs": {
                "trending_terms": {
                    "significant_text": {
                        "field": "content",
                        "size": top_k,
                        "filter_duplicate_text": True
                    }
                }
            }
        }

        result = es_client.get_client().search(index=settings.es_index, **body)

        trending = [
            {
                "keyword": bucket['key'],
                "score": bucket['score'],
                "doc_count": bucket['doc_count']
            }
            for bucket in result['aggregations']['trending_terms']['buckets']
        ]

        return {
            "days": days,
            "total_articles": result['hits']['total']['value'],
            "trending_keywords": trending
        }

    except Exception as e:
        logger.error(f"Failed to get trending keywords: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get trending keywords: {str(e)}")
