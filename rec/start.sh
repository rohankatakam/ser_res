#!/bin/bash
#
# Serafis Recommendation Engine - Quick Start Script
#
# Usage: ./start.sh
#
# This script starts the Serafis evaluation framework with:
# - Qdrant vector database (embeddings, similarity search)
# - Backend API server (FastAPI)
# - Frontend UI (React + nginx)
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================${NC}"
echo -e "${BLUE}  Serafis Recommendation Engine  ${NC}"
echo -e "${BLUE}=================================${NC}"
echo ""

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Docker is running
echo -e "${YELLOW}Checking Docker...${NC}"
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running.${NC}"
    echo "Please start Docker Desktop and try again."
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"

# Check .env file exists
echo -e "${YELLOW}Checking configuration...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found.${NC}"
    echo ""
    echo "Please create a .env file with your API keys:"
    echo "  cp .env.example .env"
    echo "  # Then edit .env and add your keys"
    exit 1
fi

# Check for required API keys
if ! grep -q "OPENAI_API_KEY=sk-" .env 2>/dev/null; then
    echo -e "${YELLOW}Warning: OPENAI_API_KEY not set in .env${NC}"
    echo "  Embedding generation will not work without this key."
    echo "  Add your key to .env: OPENAI_API_KEY=sk-your-key-here"
    echo ""
fi

if ! grep -q "GEMINI_API_KEY=AI" .env 2>/dev/null; then
    echo -e "${YELLOW}Warning: GEMINI_API_KEY not set in .env${NC}"
    echo "  LLM evaluation will not work without this key."
    echo "  Add your key to .env: GEMINI_API_KEY=your-key-here"
    echo ""
fi

echo -e "${GREEN}✓ Configuration found${NC}"

# Start services
echo ""
echo -e "${YELLOW}Starting services...${NC}"
echo "(This may take a minute on first run)"
echo ""

docker-compose up --build -d

# Wait for services to be healthy
echo ""
echo -e "${YELLOW}Waiting for services to be ready...${NC}"

# Wait for backend health check
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        break
    fi
    sleep 1
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
done
echo ""

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}Error: Backend failed to start.${NC}"
    echo "Check logs with: docker-compose logs backend"
    exit 1
fi

# Wait a bit more for frontend
sleep 2

# Print success message
echo ""
echo -e "${GREEN}=================================${NC}"
echo -e "${GREEN}  Services are ready!${NC}"
echo -e "${GREEN}=================================${NC}"
echo ""
echo -e "  ${BLUE}Frontend:${NC}  http://localhost:3000"
echo -e "  ${BLUE}Backend:${NC}   http://localhost:8000"
echo -e "  ${BLUE}API Docs:${NC}  http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}Quick Start:${NC}"
echo "  1. Open http://localhost:3000 in your browser"
echo "  2. Click Settings (gear icon) to configure API keys"
echo "  3. Navigate to Developer > Tests to run evaluations"
echo ""
echo -e "${YELLOW}Commands:${NC}"
echo "  Stop:    docker-compose down"
echo "  Logs:    docker-compose logs -f"
echo "  Restart: docker-compose restart"
echo ""
