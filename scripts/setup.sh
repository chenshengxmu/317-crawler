#!/bin/bash
# Setup script for News Crawler project

set -e

echo "========================================"
echo "News Crawler - Setup Script"
echo "========================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Dependencies installed"

# Check Docker
echo ""
echo "Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi
echo "✓ Docker is available"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi
echo "✓ Docker Compose is available"

# Start Elasticsearch
echo ""
echo "Starting Elasticsearch..."
docker-compose up -d elasticsearch

echo "Waiting for Elasticsearch to be ready (this may take a minute)..."
sleep 20

# Check if Elasticsearch is running
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:9200/_cluster/health > /dev/null 2>&1; then
        echo "✓ Elasticsearch is running"
        break
    fi
    attempt=$((attempt + 1))
    echo "  Waiting... ($attempt/$max_attempts)"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Elasticsearch failed to start"
    exit 1
fi

# Install IK Analysis plugin
echo ""
echo "Installing IK Analysis plugin for Chinese text..."
docker exec news-crawler-elasticsearch /usr/share/elasticsearch/bin/elasticsearch-plugin list | grep analysis-ik > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ IK Analysis plugin already installed"
else
    docker exec news-crawler-elasticsearch /usr/share/elasticsearch/bin/elasticsearch-plugin install https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v8.12.0/elasticsearch-analysis-ik-8.12.0.zip
    echo "Restarting Elasticsearch..."
    docker restart news-crawler-elasticsearch
    sleep 15
    echo "✓ IK Analysis plugin installed"
fi

# Initialize Elasticsearch index
echo ""
echo "Initializing Elasticsearch index..."
python scripts/init_elasticsearch.py
if [ $? -eq 0 ]; then
    echo "✓ Elasticsearch index initialized"
else
    echo "❌ Failed to initialize Elasticsearch index"
    exit 1
fi

# Create logs directory
mkdir -p logs
echo "✓ Logs directory created"

echo ""
echo "========================================"
echo "Setup completed successfully!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Run a test crawl: make crawl-sina"
echo "  3. Start API server: make api"
echo "  4. Access API docs: http://localhost:8000/docs"
echo ""
echo "For more commands, run: make help"
echo ""
