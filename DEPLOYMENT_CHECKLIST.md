# Deployment Checklist

Use this checklist to deploy the News Crawler system to production.

## Pre-Deployment Checklist

### 1. Environment Setup

- [ ] Python 3.11+ installed
- [ ] Docker and Docker Compose installed
- [ ] Sufficient disk space (10GB+ recommended)
- [ ] Sufficient RAM (4GB+ recommended)
- [ ] Network connectivity to news sources

### 2. Configuration Review

- [ ] Copy `.env.example` to `.env`
- [ ] Set production environment: `ENVIRONMENT=production`
- [ ] Configure Elasticsearch connection
  - [ ] `ES_HOST` (default: localhost)
  - [ ] `ES_PORT` (default: 9200)
  - [ ] `ES_INDEX` (default: news_articles)
  - [ ] `ES_USERNAME` and `ES_PASSWORD` (if authentication enabled)
- [ ] Configure API settings
  - [ ] `API_HOST` (0.0.0.0 for all interfaces)
  - [ ] `API_PORT` (default: 8000)
- [ ] Configure crawler settings
  - [ ] `CRAWLER_DOWNLOAD_DELAY` (increase for production: 1.0)
  - [ ] `CRAWLER_CONCURRENT_REQUESTS` (tune based on resources)
- [ ] Configure scheduler
  - [ ] `SCHEDULER_ENABLED` (true/false)
  - [ ] `SCHEDULER_INTERVAL_MINUTES` (default: 30)
- [ ] Configure logging
  - [ ] `LOG_LEVEL` (INFO for production)
  - [ ] `LOG_ROTATION` (100 MB)
  - [ ] `LOG_RETENTION` (30 days)
- [ ] Set `DEBUG=false` for production

### 3. Security Configuration

- [ ] Change default Elasticsearch password
- [ ] Enable Elasticsearch security (xpack.security.enabled=true)
- [ ] Configure firewall rules
  - [ ] Allow port 9200 (ES) only from application servers
  - [ ] Allow port 8000 (API) from authorized clients
  - [ ] Block direct access to Elasticsearch from internet
- [ ] Add API authentication (if required)
- [ ] Configure CORS appropriately (not allow_origins=["*"])
- [ ] Review robots.txt compliance
- [ ] Set up SSL/TLS for API (use reverse proxy like Nginx)

## Installation Steps

### 1. Initial Setup

```bash
# Clone repository
git clone <repository-url>
cd crawler

# Run automated setup
./scripts/setup.sh
```

Or manual setup:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Elasticsearch
docker-compose up -d elasticsearch

# Wait for ES to be ready
sleep 30

# Install IK plugin
docker exec news-crawler-elasticsearch \
  /usr/share/elasticsearch/bin/elasticsearch-plugin install \
  https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v8.12.0/elasticsearch-analysis-ik-8.12.0.zip

# Restart Elasticsearch
docker restart news-crawler-elasticsearch
sleep 15

# Initialize index
python scripts/init_elasticsearch.py
```

### 2. Verify Installation

```bash
# Run verification script
python scripts/verify.py

# Expected output:
# ✓ Configuration
# ✓ Elasticsearch
# ✓ Text Processing
# ⚠ API Server (if not started yet)
```

### 3. Test Crawling

```bash
# Run a test crawl
python scripts/run_crawler.py --spider sina --output test_results.json

# Check results
curl http://localhost:9200/news_articles/_count

# Should return document count > 0
```

### 4. Start Services

#### Option A: Manual Start (for testing)

```bash
# Terminal 1: API Server
source venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Scheduler (optional)
source venv/bin/activate
python scheduler/scheduler.py
```

#### Option B: Production Start (systemd)

Create systemd service files:

**`/etc/systemd/system/news-crawler-api.service`**
```ini
[Unit]
Description=News Crawler API
After=network.target elasticsearch.service

[Service]
Type=simple
User=crawler
WorkingDirectory=/opt/crawler
Environment="PATH=/opt/crawler/venv/bin"
ExecStart=/opt/crawler/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/news-crawler-scheduler.service`**
```ini
[Unit]
Description=News Crawler Scheduler
After=network.target elasticsearch.service

[Service]
Type=simple
User=crawler
WorkingDirectory=/opt/crawler
Environment="PATH=/opt/crawler/venv/bin"
ExecStart=/opt/crawler/venv/bin/python scheduler/scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable news-crawler-api
sudo systemctl enable news-crawler-scheduler
sudo systemctl start news-crawler-api
sudo systemctl start news-crawler-scheduler
```

#### Option C: Docker Compose (full stack)

Create production `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    container_name: news-crawler-elasticsearch
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
      - xpack.security.enabled=true
      - ELASTIC_PASSWORD=${ES_PASSWORD}
    ports:
      - "127.0.0.1:9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    restart: unless-stopped

  api:
    build: .
    container_name: news-crawler-api
    environment:
      - ES_HOST=elasticsearch
      - ES_PORT=9200
      - ES_PASSWORD=${ES_PASSWORD}
    ports:
      - "8000:8000"
    depends_on:
      - elasticsearch
    restart: unless-stopped

  scheduler:
    build: .
    container_name: news-crawler-scheduler
    command: python scheduler/scheduler.py
    environment:
      - ES_HOST=elasticsearch
      - ES_PORT=9200
      - ES_PASSWORD=${ES_PASSWORD}
    depends_on:
      - elasticsearch
    restart: unless-stopped

volumes:
  es_data:
```

Start:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Post-Deployment Verification

### 1. Health Checks

```bash
# Elasticsearch health
curl http://localhost:9200/_cluster/health

# API health
curl http://localhost:8000/api/v1/health

# Check index
curl http://localhost:9200/news_articles/_count
```

### 2. Functional Tests

```bash
# Test search
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "新闻", "page": 1, "page_size": 5}'

# Test statistics
curl http://localhost:8000/api/v1/stats/sources
curl http://localhost:8000/api/v1/stats/categories

# Test article retrieval (use actual article ID)
curl http://localhost:8000/api/v1/articles/{article_id}
```

### 3. Performance Tests

```bash
# Run load test (using Apache Bench)
ab -n 100 -c 10 http://localhost:8000/api/v1/health

# Check response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/v1/health
```

curl-format.txt:
```
time_namelookup:  %{time_namelookup}\n
time_connect:  %{time_connect}\n
time_appconnect:  %{time_appconnect}\n
time_pretransfer:  %{time_pretransfer}\n
time_redirect:  %{time_redirect}\n
time_starttransfer:  %{time_starttransfer}\n
time_total:  %{time_total}\n
```

### 4. Log Verification

```bash
# Check logs
tail -f logs/api.log
tail -f logs/crawler.log
tail -f logs/scheduler.log

# Check for errors
grep ERROR logs/*.log
```

## Monitoring Setup

### 1. Log Monitoring

- [ ] Set up log aggregation (ELK stack, Loki, etc.)
- [ ] Configure log alerts for errors
- [ ] Set up log rotation (already configured)

### 2. Metrics Monitoring

- [ ] Monitor Elasticsearch metrics
  - Cluster health
  - Index size
  - Query performance
  - JVM heap usage
- [ ] Monitor API metrics
  - Request rate
  - Response times
  - Error rate
- [ ] Monitor crawler metrics
  - Articles crawled per hour
  - Success/failure rate
  - Response times

### 3. Alerts

Set up alerts for:
- [ ] Elasticsearch cluster status != green
- [ ] API response time > 1s
- [ ] Crawler failure rate > 10%
- [ ] Disk usage > 80%
- [ ] Memory usage > 90%

## Maintenance Procedures

### Daily

- [ ] Check service status
- [ ] Review error logs
- [ ] Monitor disk space

### Weekly

- [ ] Review crawler statistics
- [ ] Check for duplicate articles
- [ ] Analyze search query patterns
- [ ] Review API usage

### Monthly

- [ ] Update dependencies
- [ ] Review and optimize ES index
- [ ] Backup Elasticsearch data
- [ ] Review and clean old logs
- [ ] Performance tuning

## Backup and Recovery

### Elasticsearch Backup

```bash
# Create snapshot repository
curl -X PUT "localhost:9200/_snapshot/backup_repo" -H 'Content-Type: application/json' -d'
{
  "type": "fs",
  "settings": {
    "location": "/backup/elasticsearch"
  }
}'

# Create snapshot
curl -X PUT "localhost:9200/_snapshot/backup_repo/snapshot_1?wait_for_completion=true"

# List snapshots
curl -X GET "localhost:9200/_snapshot/backup_repo/_all"

# Restore snapshot
curl -X POST "localhost:9200/_snapshot/backup_repo/snapshot_1/_restore"
```

### Configuration Backup

```bash
# Backup configuration files
tar -czf config-backup-$(date +%Y%m%d).tar.gz \
  .env \
  config/ \
  docker-compose.yml
```

## Troubleshooting

### Elasticsearch Issues

**Problem**: Elasticsearch won't start
```bash
# Check logs
docker logs news-crawler-elasticsearch

# Check disk space
df -h

# Increase heap size if needed (in docker-compose.yml)
ES_JAVA_OPTS=-Xms2g -Xmx2g
```

**Problem**: IK plugin not working
```bash
# Verify installation
docker exec news-crawler-elasticsearch \
  /usr/share/elasticsearch/bin/elasticsearch-plugin list

# Reinstall
docker exec news-crawler-elasticsearch \
  /usr/share/elasticsearch/bin/elasticsearch-plugin remove analysis-ik
# Then re-run setup
```

### Crawler Issues

**Problem**: Getting blocked by websites
- Increase `CRAWLER_DOWNLOAD_DELAY`
- Check robots.txt compliance
- Verify user agent is set correctly
- Review rate limiting settings

**Problem**: No articles being crawled
- Check website structure hasn't changed
- Review spider selectors
- Check logs for errors
- Test with small sample first

### API Issues

**Problem**: API returning 503
- Check Elasticsearch is running
- Verify ES connection in .env
- Check API logs

**Problem**: Slow search responses
- Check ES cluster health
- Review query complexity
- Consider adding caching
- Optimize index settings

## Rollback Procedure

If issues occur after deployment:

1. **Stop services**
   ```bash
   sudo systemctl stop news-crawler-api
   sudo systemctl stop news-crawler-scheduler
   ```

2. **Restore previous version**
   ```bash
   git checkout <previous-commit>
   pip install -r requirements.txt
   ```

3. **Restore Elasticsearch snapshot** (if needed)
   ```bash
   curl -X POST "localhost:9200/_snapshot/backup_repo/snapshot_previous/_restore"
   ```

4. **Restart services**
   ```bash
   sudo systemctl start news-crawler-api
   sudo systemctl start news-crawler-scheduler
   ```

## Performance Tuning

### Elasticsearch

- Increase heap size for large datasets
- Adjust refresh interval for better indexing performance
- Configure replica shards for high availability
- Use index lifecycle management (ILM)

### Crawler

- Tune concurrent requests based on server capacity
- Adjust download delay for optimal throughput
- Enable HTTP cache for development
- Use distributed crawling for scale

### API

- Add caching layer (Redis)
- Use connection pooling
- Enable compression
- Implement rate limiting

## Security Hardening

- [ ] Enable Elasticsearch authentication
- [ ] Use HTTPS for API (via reverse proxy)
- [ ] Implement API rate limiting
- [ ] Add API authentication (JWT)
- [ ] Regular security updates
- [ ] Monitor for suspicious activity
- [ ] Implement request validation
- [ ] Use secrets management (not .env in production)

## Compliance

- [ ] Review robots.txt compliance
- [ ] Implement rate limiting per site
- [ ] Add user agent identification
- [ ] Respect copyright and terms of service
- [ ] Implement data retention policies
- [ ] Add privacy policy (if exposing API publicly)

---

**Last Updated**: March 17, 2026
**Version**: 1.0.0
**Status**: Ready for production deployment
