# Serafis Recommendation Evaluation Framework

## Docker

```bash
# 1. Env (project root; .env is gitignored)
cp .env.example .env
# Edit .env: OPENAI_API_KEY (required), GEMINI_API_KEY / ANTHROPIC_API_KEY (optional)

# 2. Build and run
docker-compose up --build

# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
```

```bash
docker-compose up -d              # background
docker-compose logs -f            # logs
docker-compose down               # stop
docker-compose up --build         # rebuild and run
```

## Directory skeleton

```
<project_root>/
├── .env.example                  # Env template (copy to .env; .env is gitignored)
├── docker-compose.yml            # qdrant + backend + frontend
├── algorithm/                    # Recommendation algorithm (v1.5)
│   ├── config.json, config_schema.json
│   ├── recommendation_engine.py, embedding_strategy.py, computed_params.py
│   └── manifest.json
├── datasets/                     # Episode/series data (e.g. eval_909_feb2026/)
│   └── <dataset>/manifest.json, episodes.json, series.json
├── cache/                        # Embedding cache (gitignored)
├── server/                       # FastAPI backend
│   ├── server.py, config.py
│   ├── algorithm_loader.py, dataset_loader.py
│   ├── embedding_cache.py, embedding_generator.py, qdrant_store.py
│   └── Dockerfile
├── frontend/                     # React UI
│   └── src/ (App.jsx, api.js, components/)
├── evaluation/                   # Test runner, profiles, test_cases, reports, judges
│   ├── runner.py
│   └── profiles/, test_cases/, reports/, judges/, criteria/
└── docs/
```
