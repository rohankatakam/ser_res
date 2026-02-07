# Serafis Recommendation Evaluation Framework

A versioned evaluation framework for the Serafis "For You" podcast recommendation algorithm.

## Architecture Overview

```
rec/
├── algorithms/              # Algorithm versions
│   └── v1_2_blended/        # V1.2 Blended Scoring
│       ├── manifest.json    # Version metadata & requirements
│       ├── embedding_strategy.py  # How to embed episodes
│       ├── config.json      # Tunable parameters
│       └── recommendation_engine.py  # Core algorithm
│
├── datasets/                # Dataset versions
│   └── eval_909_feb2026/    # February 2026 evaluation dataset
│       ├── manifest.json    # Schema & statistics
│       ├── episodes.json    # Episode data (909 episodes)
│       └── series.json      # Series metadata
│
├── cache/                   # Embedding cache
│   └── embeddings/          # Cached embeddings per algo+dataset combo
│       └── v1_2_blended_s1.0__eval_909_feb2026.json
│
├── server/                  # FastAPI server
│   ├── server.py            # Main API server
│   ├── algorithm_loader.py  # Dynamic algorithm loading
│   ├── dataset_loader.py    # Dynamic dataset loading
│   ├── embedding_cache.py   # Embedding cache management
│   ├── embedding_generator.py  # OpenAI embedding generation
│   ├── validator.py         # Compatibility validation
│   └── config.py            # Configuration management
│
├── evaluation/              # Test framework
│   ├── profiles/            # User profiles for testing
│   ├── test_cases/          # Test case definitions
│   ├── reports/             # Saved test reports
│   ├── runner.py            # Test runner
│   └── llm_judge.py         # LLM-as-judge evaluation
│
├── prototype/               # React frontend
│   └── src/                 # Frontend source code
│
└── mock_api/                # Legacy API (for reference)
```

## Quick Start

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-your-key-here
```

### 2. Install Dependencies

```bash
# Server dependencies
cd server
pip install -r requirements.txt

# Frontend dependencies (optional)
cd ../prototype
npm install
```

### 3. Start the Server

```bash
# From rec/ directory
cd server
uvicorn server:app --reload --port 8000

# Or from rec/ directory
python -m uvicorn server.server:app --reload --port 8000
```

### 4. Load Configuration

The server starts without any algorithm/dataset loaded. Load one via API:

```bash
# Check available algorithms and datasets
curl http://localhost:8000/api/config/algorithms
curl http://localhost:8000/api/config/datasets

# Load a configuration
curl -X POST http://localhost:8000/api/config/load \
  -H "Content-Type: application/json" \
  -d '{"algorithm": "v1_2_blended", "dataset": "eval_909_feb2026"}'
```

### 5. Generate Embeddings (First Time)

If embeddings aren't cached, generate them:

```bash
curl -X POST http://localhost:8000/api/embeddings/generate \
  -H "Content-Type: application/json" \
  -H "X-OpenAI-Key: sk-your-key-here" \
  -d '{"algorithm": "v1_2_blended", "dataset": "eval_909_feb2026"}'
```

### 6. Start Frontend (Optional)

```bash
cd prototype
npm run dev
# Open http://localhost:5173
```

## API Endpoints

### Configuration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/config/algorithms` | GET | List available algorithm versions |
| `/api/config/datasets` | GET | List available datasets |
| `/api/config/validate` | POST | Check algorithm-dataset compatibility |
| `/api/config/load` | POST | Load an algorithm + dataset |
| `/api/config/current` | GET | Get currently loaded config |

### Embeddings

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/embeddings/status` | GET | Check embedding cache status |
| `/api/embeddings/generate` | POST | Generate embeddings (with progress) |

### Recommendations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sessions/create` | POST | Create recommendation session |
| `/api/sessions/{id}` | GET | Get session info |
| `/api/sessions/{id}/next` | POST | Load more recommendations |
| `/api/sessions/{id}/engage` | POST | Record engagement |

### Evaluation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/evaluation/profiles` | GET | List test profiles |
| `/api/evaluation/profiles/{id}` | GET | Get specific profile |
| `/api/evaluation/test-cases` | GET | List test cases |
| `/api/evaluation/test-cases/{id}` | GET | Get specific test case |
| `/api/evaluation/run` | POST | Run a single test |
| `/api/evaluation/run-all` | POST | Run all tests |
| `/api/evaluation/reports` | GET | List saved reports |
| `/api/evaluation/reports/{id}` | GET | Get specific report |

## Adding a New Algorithm Version

1. Create folder: `algorithms/v2_0_experimental/`

2. Add `manifest.json`:
```json
{
  "version": "2.0",
  "name": "Experimental Algorithm",
  "embedding_strategy_version": "1.0",
  "embedding_model": "text-embedding-3-small",
  "requires_schema": "1.0",
  "required_fields": ["id", "title", "scores", "key_insight", "published_at"]
}
```

3. Add `embedding_strategy.py`:
```python
STRATEGY_VERSION = "1.0"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

def get_embed_text(episode: dict) -> str:
    # Your embedding text generation logic
    return f"{episode['title']}. {episode.get('key_insight', '')}"
```

4. Add `recommendation_engine.py` with your algorithm logic

## Adding a New Dataset

1. Create folder: `datasets/eval_1200_march2026/`

2. Add `manifest.json`:
```json
{
  "version": "1.0",
  "name": "March 2026 Evaluation Dataset",
  "schema_version": "1.0",
  "episode_count": 1200,
  "source": {
    "episodes_file": "episodes.json",
    "series_file": "series.json"
  }
}
```

3. Add `episodes.json` with episode data (must match schema)

4. Optionally add `series.json` for series metadata

## Embedding Cache

Embeddings are cached by algorithm version + embedding strategy version + dataset version:

```
cache/embeddings/v1_2_blended_s1.0__eval_909_feb2026.json
```

This ensures:
- Changing the algorithm (but not embedding strategy) → reuses cache
- Changing the embedding strategy → regenerates embeddings
- Changing the dataset → regenerates embeddings

## Running Tests

```bash
# From evaluation/ directory
python runner.py --verbose

# Run specific test
python runner.py --test 01

# Run with LLM evaluation
python runner.py --with-llm

# Save report
python runner.py --save
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | For embeddings | OpenAI API key |
| `GEMINI_API_KEY` | For LLM tests | Gemini API key |
| `HOST` | No | Server host (default: 0.0.0.0) |
| `PORT` | No | Server port (default: 8000) |

## Legacy API

The original `mock_api/` folder contains the standalone V1.2 API for reference.
It can still be run independently:

```bash
cd mock_api
uvicorn server:app --reload --port 8000
```

---

## Docker Deployment

The framework can be deployed using Docker Compose for easy portability.

### Quick Start with Docker

```bash
# 1. Copy environment file and add your API keys
cp .env.example .env
# Edit .env and add OPENAI_API_KEY and GEMINI_API_KEY

# 2. Build and start services
docker-compose up --build

# 3. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
```

### Docker Services

| Service | Port | Description |
|---------|------|-------------|
| `frontend` | 3000 | React UI served by nginx |
| `backend` | 8000 | FastAPI server |

### Docker Commands

```bash
# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up --build

# Rebuild specific service
docker-compose build backend
docker-compose up -d backend
```

### Volume Mounts

The docker-compose configuration mounts local directories:

| Local Path | Container Path | Mode |
|------------|----------------|------|
| `./algorithms` | `/data/algorithms` | Read-only |
| `./datasets` | `/data/datasets` | Read-only |
| `./cache` | `/data/cache` | Read-write |
| `./evaluation` | `/data/evaluation` | Read-write |

This allows you to:
- Add new algorithms/datasets without rebuilding containers
- Persist embedding cache across restarts
- Save test reports locally

### Production Deployment

For production, consider:

1. **Environment Variables**: Set API keys via environment, not .env file
2. **SSL/TLS**: Add a reverse proxy (Traefik, Caddy) for HTTPS
3. **Persistence**: Use Docker volumes for cache and reports

```bash
# Production with external environment
OPENAI_API_KEY=sk-xxx GEMINI_API_KEY=AIza-xxx docker-compose up -d
```

## Development Roadmap

- [x] Phase 1: Folder restructure + cache infrastructure
- [x] Phase 2: Tests page UI in frontend (Developer > Tests tab)
- [x] Phase 3: Reports page UI (integrated in Tests tab)
- [x] Phase 4: Settings modal with algorithm/dataset selection
- [x] Phase 5: Docker deployment

## Frontend UI Features

The prototype frontend includes:

### Developer Tab
- **Insights Sub-tab**: Session state, engagement history, algorithm config, API stats
- **Tests Sub-tab**: Run individual or all tests, view results with criteria breakdown

### Settings Modal
- OpenAI API key configuration (for embeddings)
- Gemini API key configuration (for LLM-as-judge)
- Algorithm version selection
- Dataset version selection
- Compatibility validation
- Embedding cache status

### Test Runner
- List all test cases with descriptions
- Run individual tests or all tests at once
- Real-time pass/fail status
- Detailed criteria results breakdown
- View and compare historical reports
