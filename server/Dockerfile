# Serafis Evaluation Server
# Python FastAPI backend for recommendation testing

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY *.py ./
COPY .env.example .env.example

# Create directories for mounted volumes
RUN mkdir -p /data/algorithms /data/datasets /data/cache /data/evaluation

# Environment defaults (can be overridden)
ENV HOST=0.0.0.0
ENV PORT=8000
ENV ALGORITHMS_DIR=/data/algorithms
ENV DATASETS_DIR=/data/datasets
ENV CACHE_DIR=/data/cache
ENV EVALUATION_DIR=/data/evaluation

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

EXPOSE 8000

# Run server
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
