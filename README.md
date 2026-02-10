# Serafis Recommendation Engine

Recommendation engine and evaluation framework for podcast content.

## Prerequisites

- Docker Desktop
- API keys (OpenAI required, Gemini/Anthropic optional)

## Quick Start

```bash
# 1. Clone
git clone https://github.com/your-org/serafis.git
cd serafis/rec

# 2. Configure API keys
cp .env.example .env
# Edit .env and add your keys (see below)

# 3. Start
docker-compose up -d

# 4. Open http://localhost:3000
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

## Common Commands

```bash
docker-compose up -d          # Start
docker-compose down           # Stop
docker-compose logs -f        # View logs
docker-compose up --build -d  # Rebuild after code changes
```

> **Tip:** `./start.sh` is a helper script that validates your setup before starting.

---

## Environment Variables

Create `rec/.env`:

```env
# Required - embeddings
OPENAI_API_KEY=sk-...

# Optional - multi-LLM evaluation
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Project Structure

```
serafis/
├── rec/                    # Recommendation engine
│   ├── algorithms/         # Algorithm versions (v1.0-v1.5)
│   ├── server/             # FastAPI backend
│   ├── prototype/          # React frontend
│   ├── evaluation/         # Test suite and reports
│   ├── datasets/           # Episode data
│   ├── docs/               # Phase 7 documentation
│   └── docker-compose.yml
└── evaluation/             # External evaluation tools
```

---

## Running Evaluations

```bash
# Via UI
# Navigate to Developer > Tests in the frontend

# Via CLI
cd rec
python -m evaluation.runner --algorithm v1_5_diversified --dataset eval_909_feb2026
```

---

## Documentation

- [Algorithm Evolution](rec/docs/phase7_evolution/README.md) — v1.0 → v1.5 documentation
- [API Docs](http://localhost:8000/docs) — OpenAPI spec (when running)
