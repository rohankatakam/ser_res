# Server Refactor Plan — Split into Submodules

The `server/` package is currently a flat set of 13 files with **server.py** at ~1950 lines holding the FastAPI app, AppState, all routes, Pydantic models, and helpers. This plan splits it into clear submodules so each area has a single responsibility and the layout stays maintainable as you add cloud (Pinecone, Firestore) and more endpoints.

---

## 1. Current State

| File | Lines | Role |
|------|-------|------|
| **server.py** | ~1947 | FastAPI app, AppState, all routes (config, algorithm, embeddings, sessions, episodes, evaluation, stats), Pydantic models, get_badges, to_episode_card, deep_merge, validate_config_against_schema |
| config.py | 105 | ServerConfig, get_config, load .env |
| algorithm_loader.py | 290 | Load algorithm from disk (manifest, config, embedding_strategy, engine, computed_params) |
| dataset_loader.py | 280 | Load datasets from disk (episodes, series) |
| validator.py | 258 | Algorithm–dataset compatibility |
| embedding_cache.py | 259 | JSON embedding cache |
| embedding_generator.py | 344 | OpenAI embedding generation |
| qdrant_store.py | 525 | Qdrant vector store |
| vector_store.py | 167 | VectorStore abstraction + QdrantJsonVectorStore |
| episode_provider.py | 161 | EpisodeProvider + DatasetEpisodeProvider + HttpEpisodeProvider |
| engagement_store.py | 57 | EngagementStore + RequestOnlyEngagementStore |
| mock_episodes_api.py | 139 | Standalone mock API (Firestore-like) |
| __init__.py | 30 | Re-exports |

**Problems:** One giant server.py, mixed concerns (HTTP, state, helpers, models), and no clear place for new route groups or new services (e.g. Pinecone, Firestore).

---

## 2. Target Layout

```
server/
├── __init__.py              # Re-export app, get_config, key types for "from server import app"
├── config.py                # Unchanged: ServerConfig, get_config
├── state.py                 # AppState, get_state (moved out of server.py)
├── app.py                   # create_app(): FastAPI instance, CORS, router includes, startup
├── models/                  # Pydantic request/response models
│   ├── __init__.py
│   ├── common.py            # SeriesInfo, EpisodeScores, EpisodeCard, Engagement
│   ├── sessions.py          # CreateSessionRequest, LoadMoreRequest, EngageRequest, SessionResponse, SessionDebugInfo
│   ├── config.py            # LoadConfigRequest, ConfigUpdateRequest, ComputeParamsRequest
│   ├── embeddings.py       # GenerateEmbeddingsRequest
│   └── evaluation.py       # RunTestRequest, RunAllTestsRequest
├── routes/                  # Route handlers by domain (thin: call state + services)
│   ├── __init__.py          # Register all routers on app
│   ├── root.py              # GET /, GET /api/health
│   ├── config.py            # /api/config/* (algorithms, datasets, load, validate, status, current)
│   ├── algorithm.py        # /api/algorithm/* (config, diff, update, compute)
│   ├── embeddings.py       # /api/embeddings/* (status, generate)
│   ├── sessions.py         # /api/sessions/* (create, next, engage) + get_badges, to_episode_card
│   ├── episodes.py         # /api/episodes, /api/episodes/{id}
│   ├── evaluation.py       # /api/evaluation/* (profiles, test-cases, reports, run, run-all, judge-config)
│   └── stats.py             # GET /api/stats
├── services/                # Backing logic (loaders, stores, abstractions)
│   ├── __init__.py          # Re-export for "from server.services import ..."
│   ├── algorithm_loader.py
│   ├── dataset_loader.py
│   ├── validator.py
│   ├── embedding_cache.py
│   ├── embedding_generator.py
│   ├── qdrant_store.py
│   ├── vector_store.py
│   ├── episode_provider.py
│   └── engagement_store.py
├── utils.py                 # deep_merge, validate_config_against_schema (used by routes)
└── mock_episodes_api.py     # Unchanged at top level (python -m server.mock_episodes_api)
```

**Entrypoint:** Keep `uvicorn server.app:app` (or `server.server:app` during migration). So `app` is created in `server/app.py` and assigned to `app` in `server/__init__.py` for backward compatibility.

**Docker:** The Dockerfile currently copies `*.py` into `/app` and runs `uvicorn server:app`. After refactor you have a package (server/ with subdirs). So the build context must be the **parent** of `server/` and copy the whole repo or at least `server/` as a directory. So Dockerfile should be updated to e.g. `COPY . .` from repo root or `COPY server server` and set `WORKDIR` so that `server` is a package. That’s a separate small change; see section 5.

---

## 3. Responsibilities by Layer

| Layer | Responsibility | Depends on |
|-------|----------------|------------|
| **app.py** | Create FastAPI app, mount routers, run startup (load config, algorithm, dataset, embeddings) | state, routes, config |
| **state.py** | AppState: config, loaders, vector_store, engagement_store, current_algorithm, current_dataset, current_embeddings, sessions | config, services (loaders, vector_store, engagement_store, episode_provider) |
| **models/** | Pydantic request/response schemas only | (none) |
| **routes/** | HTTP handlers: parse request, call state/services, return response | state, models, services (only what’s needed, e.g. get_badges in sessions) |
| **services/** | Algorithm/dataset loading, embeddings, vector store, episode provider, engagement store | config (paths), each other only where needed |
| **utils.py** | Pure helpers: deep_merge, validate_config_against_schema | (none) |

---

## 4. Migration Steps (Incremental)

Do these in order so you can run tests after each step.

### Step 1: Extract Pydantic models

- Create `server/models/__init__.py` and `server/models/common.py` (SeriesInfo, EpisodeScores, EpisodeCard, Engagement).
- Add `server/models/sessions.py`, `config.py`, `embeddings.py`, `evaluation.py` with the corresponding request/response models.
- In `server.py` replace model definitions with `from server.models import ...` (or `.models`).
- Run tests and smoke checks.

### Step 2: Extract state and utils

- Create `server/state.py`: move `AppState` and `get_state()` from server.py. Import loaders and abstractions from the existing modules (still at top level).
- Create `server/utils.py`: move `deep_merge`, `validate_config_against_schema`, and optionally `get_badges` and `to_episode_card` (or keep the last two in routes/sessions.py).
- In server.py, remove the moved code and use `from server.state import get_state`, `from server.utils import ...`.
- Run tests.

### Step 3: Move services into `server/services/`

- Create `server/services/` and move into it: algorithm_loader, dataset_loader, validator, embedding_cache, embedding_generator, qdrant_store, vector_store, episode_provider, engagement_store.
- In each moved file, fix relative imports (e.g. `from .embedding_cache` inside services).
- In state.py and server.py, change imports to `from server.services.algorithm_loader import ...` etc. (or `from .services ...`).
- Ensure Docker still builds: if Docker currently copies only `server/*.py` into `/app`, you must change the build so that `server/` is a package (e.g. build from repo root and `COPY server server`). See section 5.
- Run tests.

### Step 4: Extract routes by domain

- Create `server/routes/__init__.py` that defines a function `register_routes(app)` and attaches APIRouters.
- Create one file per domain (root, config, algorithm, embeddings, sessions, episodes, evaluation, stats). In each, create a router and move the corresponding `@app.get`/`@app.post` handlers to `@router.get`/`@router.post`. Handlers call `get_state()` and the same logic as today.
- In server.py (or the new app.py), create the FastAPI app and call `register_routes(app)`.
- Run tests.

### Step 5: Introduce app.py and slim server.py

- Create `server/app.py`: build FastAPI app, add CORS, call `register_routes(app)`, and register startup (e.g. `lifespan` or `on_event("startup")` that calls the same auto_load_config logic).
- Make `server/__init__.py` expose `app` from `server.app` so `uvicorn server:app` still works.
- Optionally keep `server.py` as a thin wrapper that imports and exposes `app` for backward compatibility, or remove it and use `server.app:app` everywhere.
- Run tests and Docker.

### Step 6: (Optional) Evaluation runner import path

- Evaluation routes import `run_test_async`, `run_all_tests_async`, etc. from `runner` (evaluation package). Keep that as-is; only the place from which they’re imported changes (e.g. `server/routes/evaluation.py`). No structural change needed unless you want to inject a runner interface later.

---

## 5. Docker and Import Compatibility

**Current Dockerfile:** Copies `server/*.py` into `/app` and runs `uvicorn server:app`. That flattens the package (all modules at top level under the name `server` when `server` is the single `server.py` file).

**After refactor:** `server` must be a **directory package** (server/app.py, server/routes/, server/services/, etc.). So:

- **Build context:** Use repo root: `docker build -f server/Dockerfile .` with context `.`, or keep Dockerfile at repo root and `COPY server server`.
- **Dockerfile:** Copy the whole `server` directory (and any parent needed for `server` to resolve), e.g.  
  `COPY server/ server/`  
  and set `WORKDIR` so that the parent of `server` is on `PYTHONPATH` (e.g. `WORKDIR /app` and copy so you have `/app/server/...`). Then `CMD ["python", "-m", "uvicorn", "server.app:app", ...]`.
- **Imports:** Use relative imports inside the package (e.g. `from .services.algorithm_loader import ...`) so that both `uvicorn server.app:app` from repo root and Docker work. Avoid relying on a flat copy of files.

If you prefer to keep the current Docker layout (flat copy), you could leave all current `.py` files at top level and only split **server.py** into multiple files under `server/` (e.g. server_routes_config.py, server_routes_sessions.py, ...) without a `services/` subdirectory; then the refactor is “split server.py only” and Docker needs no change. The plan above assumes you are willing to treat `server` as a proper package and adjust Docker once.

---

## 6. Summary

| Before | After |
|--------|--------|
| One 1950-line server.py | app.py + state.py + utils.py + models/ + routes/ + services/ |
| 12 modules at top level | config + state + app at top level; rest under routes/ and services/ |
| All routes in one file | One router module per domain (root, config, algorithm, embeddings, sessions, episodes, evaluation, stats) |
| Models and helpers in server.py | models/*.py, utils.py |

This keeps the same API and behavior, gives a clear place for new endpoints and new backends (Pinecone, Firestore), and makes the server easier to navigate and test. Implement in the order above and run tests after each step; adjust Docker in step 3 or 5 as needed.
