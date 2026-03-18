# Docker Installation Guide

The Homebrew installation encountered a download error. Here are alternative options:

## Option 1: Direct Download (Recommended)

**For Apple Silicon Mac (M1/M2/M3):**
```bash
# Download directly
curl -L -o ~/Downloads/Docker.dmg "https://desktop.docker.com/mac/main/arm64/Docker.dmg"

# Install
open ~/Downloads/Docker.dmg
# Drag Docker to Applications folder
# Start Docker from Applications
```

**For Intel Mac:**
```bash
# Download directly
curl -L -o ~/Downloads/Docker.dmg "https://desktop.docker.com/mac/main/amd64/Docker.dmg"

# Install
open ~/Downloads/Docker.dmg
```

## Option 2: Download from Website

Visit: **https://www.docker.com/products/docker-desktop/**
- Click "Download for Mac"
- Choose your chip type (Apple Silicon or Intel)
- Install the downloaded .dmg file

## Option 3: Alternative - Colima (Lightweight Docker)

If you prefer a lightweight alternative:

```bash
# Install Colima (Docker runtime without Docker Desktop)
brew install colima docker docker-compose

# Start Colima
colima start

# Verify
docker --version
```

## After Installation

Once Docker is installed and running:

```bash
# Verify Docker is working
docker --version
docker ps

# Return to project and complete setup
cd /Users/chensheng/317/crawler
./scripts/setup.sh
```

## Troubleshooting

**If Docker Desktop won't start:**
1. Open Docker Desktop from Applications
2. Wait for the whale icon to appear in menu bar
3. Click the whale icon and ensure "Docker Desktop is running"

**If using Colima:**
```bash
# Check status
colima status

# Restart if needed
colima restart
```

## What Happens Next

After Docker is running, the setup script will:
1. ✅ Start Elasticsearch container
2. ✅ Install IK Analysis plugin (Chinese text support)
3. ✅ Initialize the database
4. ✅ Verify everything is working

**Total time**: ~10 minutes

---

**Current Status**: Python environment ready ✅, waiting for Docker ⏸️
