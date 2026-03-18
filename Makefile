.PHONY: help install setup-es init-es test crawl api scheduler clean

help:
	@echo "News Crawler - Available Commands:"
	@echo "  make install      - Install Python dependencies"
	@echo "  make setup-es     - Start Elasticsearch and install IK plugin"
	@echo "  make init-es      - Initialize Elasticsearch index"
	@echo "  make test         - Run tests"
	@echo "  make crawl        - Run crawler manually"
	@echo "  make api          - Start API server"
	@echo "  make scheduler    - Start scheduler"
	@echo "  make clean        - Clean temporary files"

install:
	pip install -r requirements.txt

setup-es:
	@echo "Starting Elasticsearch..."
	docker-compose up -d elasticsearch
	@echo "Waiting for Elasticsearch to be ready..."
	@sleep 20
	@echo "Installing IK Analysis plugin..."
	docker exec news-crawler-elasticsearch /usr/share/elasticsearch/bin/elasticsearch-plugin install https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v8.12.0/elasticsearch-analysis-ik-8.12.0.zip || true
	@echo "Restarting Elasticsearch..."
	docker restart news-crawler-elasticsearch
	@sleep 10
	@echo "Elasticsearch setup complete!"

init-es:
	python scripts/init_elasticsearch.py

test:
	pytest tests/ -v --cov=. --cov-report=html

crawl:
	python scripts/run_crawler.py

crawl-sina:
	python scripts/run_crawler.py --spider sina

api:
	uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

scheduler:
	python scheduler/scheduler.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage
	@echo "Cleaned temporary files"
