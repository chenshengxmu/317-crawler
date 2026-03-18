# Quick Start Guide

Get the News Crawler system up and running in minutes.

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git

## Installation

### 1. Automated Setup (Recommended)

Run the automated setup script:

```bash
cd /Users/chensheng/317/crawler
./scripts/setup.sh
```

This script will:
- Create a virtual environment
- Install all dependencies
- Start Elasticsearch
- Install IK Analysis plugin for Chinese text
- Initialize the Elasticsearch index
- Verify the installation

### 2. Manual Setup

If you prefer manual setup:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Elasticsearch
make setup-es

# Initialize index
make init-es
```

## Verification

Verify that everything is working:

```bash
source venv/bin/activate
python scripts/verify.py
```

You should see all checks passing:
- ✓ Configuration
- ✓ Elasticsearch
- ✓ Text Processing
- ⚠ API Server (will pass after starting API)

## Running the System

### 1. Test Crawler

Run a test crawl from Sina News:

```bash
# Activate virtual environment
source venv/bin/activate

# Run Sina spider
make crawl-sina

# Or with custom output
python scripts/run_crawler.py --spider sina --output test_results.json
```

This will:
- Crawl articles from Sina News
- Process and clean the content
- Check for duplicates
- Store articles in Elasticsearch

### 2. Start API Server

Start the REST API server:

```bash
# In a new terminal
source venv/bin/activate
make api

# Or directly with uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Access the API:
- API Documentation: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc
- Health check: http://localhost:8000/api/v1/health

### 3. Test Search API

Search for articles:

```bash
# Search for "人工智能" (artificial intelligence)
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "人工智能",
    "page": 1,
    "page_size": 10,
    "sort_by": "publish_time"
  }'

# Search with filters
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "科技",
    "sources": ["sina"],
    "date_from": "2024-03-01",
    "page": 1,
    "page_size": 5
  }'

# Get statistics
curl http://localhost:8000/api/v1/stats/sources
curl http://localhost:8000/api/v1/stats/categories
```

### 4. Start Scheduler (Optional)

For automated crawling:

```bash
# In a new terminal
source venv/bin/activate
make scheduler

# Or directly
python scheduler/scheduler.py
```

The scheduler will run crawlers every 30 minutes (configurable in `.env`).

## Quick Reference

### Common Commands

```bash
# Setup
make install          # Install dependencies
make setup-es         # Setup Elasticsearch
make init-es          # Initialize index

# Crawling
make crawl            # Run all spiders
make crawl-sina       # Run Sina spider only

# Services
make api              # Start API server
make scheduler        # Start scheduler

# Testing
make test             # Run tests
python scripts/verify.py  # Verify system

# Maintenance
make clean            # Clean temporary files
```

### Directory Structure

```
crawler/
├── config/           # Configuration management
├── crawler/          # Scrapy spiders and crawling logic
│   ├── spiders/     # Site-specific spiders
│   ├── items.py     # Data models
│   ├── pipelines.py # Data processing
│   └── settings.py  # Scrapy settings
├── storage/          # Elasticsearch integration
├── api/              # FastAPI application
│   ├── routers/     # API endpoints
│   └── models/      # Request/response models
├── processing/       # Text processing utilities
├── scheduler/        # Scheduled crawling
├── scripts/          # Utility scripts
└── tests/           # Test suites
```

## Example Workflow

1. **Initial Setup**
   ```bash
   ./scripts/setup.sh
   ```

2. **Crawl Some Articles**
   ```bash
   source venv/bin/activate
   python scripts/run_crawler.py --spider sina
   ```

3. **Verify Data in Elasticsearch**
   ```bash
   curl http://localhost:9200/news_articles/_count
   ```

4. **Start API and Search**
   ```bash
   # Terminal 1
   make api

   # Terminal 2
   curl -X POST http://localhost:8000/api/v1/search \
     -H "Content-Type: application/json" \
     -d '{"query": "新闻", "page": 1, "page_size": 5}'
   ```

5. **View in Kibana (Optional)**
   ```bash
   docker-compose up -d kibana
   # Open http://localhost:5601
   ```

## Troubleshooting

### Elasticsearch not starting
```bash
# Check Docker logs
docker logs news-crawler-elasticsearch

# Restart Elasticsearch
docker restart news-crawler-elasticsearch
```

### IK plugin not working
```bash
# Verify plugin installation
docker exec news-crawler-elasticsearch /usr/share/elasticsearch/bin/elasticsearch-plugin list

# Reinstall if needed
docker exec news-crawler-elasticsearch /usr/share/elasticsearch/bin/elasticsearch-plugin remove analysis-ik
make setup-es
```

### Crawler not finding articles
- Check if the website structure has changed
- Verify robots.txt compliance
- Check logs in `logs/crawler.log`

### API returning errors
- Check Elasticsearch is running: `curl http://localhost:9200`
- Verify index exists: `curl http://localhost:9200/news_articles`
- Check API logs in `logs/api.log`

## Next Steps

- Add more spiders (NetEase, Tencent)
- Customize text processing
- Set up scheduled crawling
- Configure production deployment
- Add monitoring and alerts

For detailed documentation, see [README.md](README.md)
