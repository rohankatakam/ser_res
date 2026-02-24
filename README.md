# Serafis Recommendation Evaluation Framework

Serafis is **hosted in the cloud**. The frontend is deployed to **Vercel**; the backend is deployed to cloud infrastructure. Deployment details (backend target, CI/CD, env config) will be documented here once finalized.

To run the stack **locally** (e.g. development or evaluation), clone this repo, configure your own keys, and run with Docker or directly.

---

## Running locally

1. **Clone the repo**
   ```bash
   git clone https://github.com/rohankatakam/ser_res.git
   cd ser_res
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set your own API keys and paths (see below). **Do not commit `.env`**; it is gitignored.

3. **Run with Docker**
   ```bash
   docker compose up --build
   ```
   - **Frontend:** http://localhost:3000  
   - **Backend:** http://localhost:8000  

Data source is **Firestore**; config comes from `.env`. Compose mounts your Firebase key from `FIREBASE_CREDENTIALS_PATH`. See `server/docs/FIRESTORE.md` for creating a Firebase service account and uploading episode/series data.

### What to set in `.env`

- **Required:** `OPENAI_API_KEY`, `PINECONE_API_KEY`, `DATA_SOURCE=firebase`, `FIREBASE_CREDENTIALS_PATH=<path to service account JSON>`
- **Optional:** `PINECONE_INDEX_NAME` (default: `serafis-episodes`), `GEMINI_API_KEY` / `ANTHROPIC_API_KEY` for evaluation judges

See `.env.example` for all variables and comments.

### Useful Docker commands

```bash
docker compose up -d              # background
docker compose logs -f             # logs
docker compose down -v             # stop and remove volumes
docker compose up -d --build       # rebuild and run
```

---

## Cloud hosting (current)

- **Frontend:** Vercel  
- **Backend:** Cloud deployment in progress; details to be added here.

---

## Directory structure

```
<project_root>/
├── .env.example                  # Env template (copy to .env; .env is gitignored)
├── docker-compose.yml            # backend + frontend (no Qdrant; Pinecone + Firestore)
├── algorithm/                    # Recommendation algorithm (single entry: __init__.py)
│   ├── algorithm_meta.json       # Version, name, embedding config, required_fields
│   ├── __init__.py               # Engine + re-exports (config, stages, embedding)
│   ├── embedding/
│   │   ├── __init__.py
│   │   └── embedding_strategy.py # get_embed_text, STRATEGY_VERSION, model constants
│   ├── models/                   # RecommendationConfig, ScoredEpisode, RecommendationSession
│   │   ├── config.py, scoring.py, session.py
│   │   └── __init__.py
│   ├── stages/                   # Pipeline: candidate_pool → ranking (Stage B); orchestrator runs both
│   │   ├── candidate_pool.py, orchestrator.py
│   │   ├── ranking/              # Stage B: core, user_vector, blended_scoring, series_diversity
│   │   └── __init__.py
│   └── utils/                    # scores, similarity, episode helpers
│       ├── scores.py, similarity.py, episode.py
│       └── __init__.py
├── datasets/                     # Episode/series data (e.g. eval_909_feb2026/)
│   └── <dataset>/manifest.json, episodes.json, series.json
├── server/                       # FastAPI backend
│   ├── server.py, app.py, config.py, state.py, utils.py
│   ├── routes/                   # root, config, embeddings, sessions, episodes, evaluation, stats, users
│   ├── services/                 # algorithm_loader, dataset_loader, vector_store (Pinecone), firestore_engagement_store, etc.
│   ├── models/                   # Pydantic request/response models
│   ├── scripts/                  # e.g. populate_pinecone.py
│   └── Dockerfile
├── frontend/                     # React UI (Vite) — deploy root for Vercel
│   └── src/                      # App.jsx, api.js, components/
├── evaluation/                   # Test runner, profiles, test_cases, reports, judges
│   ├── runner.py
│   ├── judges/                   # LLM judge client + config
│   └── profiles/, test_cases/, reports/, criteria/
└── docs/                         # PINECONE_FIRESTORE_DATA_FLOW.md, etc.
```

Vectors live in **Pinecone**; episodes, series, and user engagements live in **Firestore**. See `docs/PINECONE_FIRESTORE_DATA_FLOW.md` for data flow and populating Pinecone.
