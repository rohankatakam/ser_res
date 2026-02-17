# Serafis Recommendation Evaluation Framework

## Docker

```bash
# 1. Env (project root; .env is gitignored)
cp .env.example .env
# Edit .env: OPENAI_API_KEY (required), GEMINI_API_KEY / ANTHROPIC_API_KEY (optional)

# 2. Build and run
docker compose up --build

# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
```

```bash
docker compose up -d              # background
docker compose logs -f             # logs
docker compose down -v            # stop and remove volumes (clean slate)
docker compose up -d --build      # rebuild and run
```

### Using Firebase (optional)

To use Firestore for episodes/series and user persistence:

1. In `.env`, set `DATA_SOURCE=firebase` and point Docker at your service account key:
   - `FIREBASE_CREDENTIALS_FILE=./path/to/your-firebase-key.json`  
   (Use your downloaded key filename; no need to rename it.)
2. Copy the Firebase override so the key is mounted into the backend container:
   ```bash
   cp docker-compose.override.firebase.example.yml docker-compose.override.yml
   ```
3. Restart: `docker compose down -v && docker compose up -d --build`

See `server/docs/FIRESTORE.md` for uploading data to Firestore and creating the key.

## Directory skeleton

```
<project_root>/
├── .env.example                  # Env template (copy to .env; .env is gitignored)
├── docker-compose.yml            # qdrant + backend + frontend
├── algorithm/                    # Recommendation algorithm (single entry: __init__.py)
│   ├── algorithm_meta.json       # Version, name, embedding config, required_fields
│   ├── __init__.py               # Engine + re-exports (config, stages, embedding)
│   ├── embedding/
│   │   ├── __init__.py
│   │   └── embedding_strategy.py # get_embed_text, STRATEGY_VERSION, model constants
│   ├── models/                   # RecommendationConfig, ScoredEpisode, RecommendationSession
│   │   ├── config.py, scoring.py, session.py
│   │   └── __init__.py
│   ├── stages/                   # Pipeline: candidate_pool → semantic_scoring; orchestrator runs both
│   │   ├── candidate_pool.py, semantic_scoring.py, orchestrator.py
│   │   └── __init__.py
│   └── utils/                    # scores, similarity, episode helpers
│       ├── scores.py, similarity.py, episode.py
│       └── __init__.py
├── datasets/                     # Episode/series data (e.g. eval_909_feb2026/)
│   └── <dataset>/manifest.json, episodes.json, series.json
├── cache/                        # Embedding cache (gitignored)
├── server/                       # FastAPI backend
│   ├── server.py, app.py, config.py, state.py, utils.py
│   ├── routes/                   # root, config, embeddings, sessions, episodes, evaluation, stats
│   ├── services/                 # algorithm_loader, dataset_loader, embedding_*, qdrant_store, etc.
│   ├── models/                   # Pydantic request/response models
│   └── Dockerfile
├── frontend/                     # React UI (Vite)
│   └── src/                      # App.jsx, api.js, components/
├── evaluation/                   # Test runner, profiles, test_cases, reports, judges
│   ├── runner.py
│   ├── judges/                   # LLM judge client + config
│   └── profiles/, test_cases/, reports/, criteria/
└── docs/
```
