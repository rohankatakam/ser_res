# Serafis Cleanup Plan

This document outlines a safe order to clean up the **api**, **frontend**, **server**, and **evaluation** modules, with testing after each change. It is based on the investor memo (narrative intelligence for investors from alternative content) and the current docker-compose architecture.

---

## Architecture Summary (from docker-compose)

| Component | Role | Location |
|-----------|------|----------|
| **qdrant** | Vector DB (embeddings, similarity) | Image only |
| **backend** | FastAPI server — config, embeddings, sessions, evaluation | `./server` |
| **frontend** | React UI (Browse, For You, Developer/Tests) | `./frontend` |
| **evaluation** | Test runner, profiles, test cases, reports, LLM judges | `./evaluation` (mounted into backend) |
| **algorithm** | Recommendation algorithm (v1.5) | `./algorithm` (mounted read-only) |
| **datasets** | Episode/series data | `./datasets` (mounted read-only) |
| **cache** | Embedding cache | `./cache` (read-write) |

**Important:** The legacy `api/` folder (V1.1/V1.2 mock API) has been **removed**. The frontend and evaluation both use **server** only (sessions API at `/api/sessions/*`). Confirmed before removal: frontend uses `createSession`/`loadMore`/`engageEpisode` only; evaluation uses `API_URL` → server; docker-compose does not reference api/.

---

## Where to Start: The Root

Start at the **repository root**, then move into each module in order.

### Phase 0: Root-level cleanup (start here)

**Goal:** Single source of truth for env, remove obsolete docs, fix README.

1. **Environment**
   - README says `cp .env.example .env` at root, but there is **no** root `.env.example`.
   - Either add a root `.env.example` that documents `OPENAI_API_KEY`, `GEMINI_API_KEY`, and (optional) `API_URL`, or update README to point to `server/.env.example` and `evaluation/.env.example` for the respective components.
   - **Recommendation:** Add a minimal root `.env.example` that matches what `docker-compose` and the docs expect (so `docker-compose up` users have one place to copy from).

2. **Obsolete / duplicate docs**
   - `academic_literature.md` at root — confirm if still needed; if not, remove or move under `docs/`.
   - FOR_YOU_* specs — api/README references `FOR_YOU_V1_1_SPEC.md`, `TESTING_STRATEGY.md`, `FOR_YOU_SPEC_FINAL.html`, `FOR_YOU_TESTING_GUIDE.md`. These files were **not** found at root. Either add them under `docs/` for reference or remove the references from `api/README.md` (especially if you remove or archive `api/`).

3. **README.md**
   - Update the "Folder Structure" diagram to remove or clearly mark `api/` as legacy.
   - Fix "Quick Start" to use the correct `.env.example` location(s).

**Test after Phase 0:**  
- `docker-compose up --build` (or at least `docker-compose config`) and a quick smoke test (e.g. `curl http://localhost:8000/api/health`) once backend is up.

---

## Phase 1: API (legacy) module

**Goal:** Decide whether to remove the legacy API or keep it as a minimal reference; remove or archive cleanly.

**Current state:**  
- `api/` contains: standalone FastAPI server (V1.1), mock data (`data/`), tests, and scripts that use a different contract (`/api/recommendations/for-you` etc.).  
- Nothing in docker-compose or the main app uses `api/`.  
- Evaluation and frontend use **server** (session-based API).

**Options:**

- **Option A — Remove `api/` entirely**  
  - Delete the `api/` directory.  
  - Remove references to "Legacy API" and `api/` from root README and any docs that point to it.  
  - Update evaluation and docs that still mention `mock_api` (see Phase 4).

- **Option B — Archive for reference**  
  - Move `api/` to e.g. `docs/legacy_api/` or `archive/api/`, or add a clear "LEGACY - not used by current stack" README inside `api/`.  
  - Strip down to only what you need for reference (e.g. keep `server.py`, `README.md`, drop heavy `data/` and test fixtures if not needed).  
  - Update root README and any links.

**Test after Phase 1:**  
- Ensure `docker-compose up` still builds and runs.  
- Frontend and evaluation should be unchanged (they don’t depend on `api/`).

---

## Phase 2: Server (backend) module

**Goal:** Remove dead code and unused dependencies; add any missing endpoints the frontend expects.

1. **Missing endpoint**
   - Frontend (`DiscoverPage.jsx`, `BrowsePage.jsx`) and `api.js` call **`GET /api/series`**.  
   - The backend does **not** expose `/api/series`; it only has `/api/episodes` and episode detail.  
   - **Action:** Add `GET /api/series` that returns `{"series": state.current_dataset.series}` (or equivalent from `dataset_loader`) when a dataset is loaded; return 400 or empty when none. Then remove any workarounds in the frontend if present.

2. **Dead code**
   - Search for unused routes, unused helpers, and duplicate logic.  
   - Ensure all routes referenced by the frontend and evaluation exist and are used.

3. **Dependencies**
   - Review `server/requirements.txt` and remove any packages that are no longer imported.

4. **Config / env**
   - Align `server/.env.example` with what the app and docker-compose actually use (e.g. `OPENAI_API_KEY`, `QDRANT_URL`, `EVALUATION_DIR`, etc.).

**Test after Phase 2:**  
- Start backend (e.g. `cd server && uvicorn server:app --reload --port 8000` or `docker-compose up backend`).  
- Run:  
  - `curl http://localhost:8000/api/health`  
  - `curl http://localhost:8000/api/config/algorithms`  
  - `curl http://localhost:8000/api/config/datasets`  
  - After loading config: `curl http://localhost:8000/api/episodes?limit=2` and `curl http://localhost:8000/api/series` (once implemented).  
- Run evaluation (Phase 4 test) to confirm sessions and evaluation endpoints still work.

---

## Phase 3: Frontend module

**Goal:** Remove unused pages/components and dead API calls; rely only on server.

1. **API usage**
   - Frontend uses **session API** (`createSession`, `loadMore`, `engageEpisode`) and various config/embedding/evaluation endpoints.  
   - `fetchForYou` in `api.js` calls `/api/recommendations/for-you`, which **only** exists on the legacy API.  
   - **Action:** If no code path uses `fetchForYou`, remove it (or keep as deprecated stub that points to createSession + first page for compatibility).  
   - Ensure all fetch URLs use the same `API_BASE` and that production build proxies `/api` to the backend (as in README).

2. **DiscoverPage.jsx / BrowsePage.jsx**
   - They use `API_BASE = 'http://localhost:8000'` directly instead of the shared `api.js` base. Prefer centralizing base URL and any `/api/series` and `/api/episodes` calls in `api.js` and use that in both pages so behavior is consistent and easy to change.

3. **Unused UI**
   - Identify pages or tabs that are not linked or used (e.g. a "Discover" tab that duplicates "For You", or placeholder pages). Remove or merge as appropriate.  
   - Remove unused components and dead routes in `App.jsx`.

4. **Dependencies**
   - Run `npm run build` and fix any warnings; remove unused npm packages.

**Test after Phase 3:**  
- `npm run dev` (or serve built frontend).  
- Manually: Browse, For You (create session, load more, engage), Developer tab (config, tests).  
- After backend has `/api/series`: confirm Discover/Browse pages that use series load without errors.

---

## Phase 4: Evaluation module

**Goal:** Remove obsolete scripts and references to legacy API/mock data; keep runner, judges, criteria, and reports structure.

1. **References to legacy API / mock data**
   - Several scripts assume a `mock_api` directory at repo root (which does not exist; the legacy app lives under `api/`):
     - `evaluation/analyze_dataset.py` — `DATA_DIR = ... parent.parent / "mock_api" / "data"`  
     - `evaluation/cleanup_episodes.py` — references `../mock_api/data/episodes.json`  
     - `evaluation/transform_search_results.py` — references `../mock_api/data/episodes.json`  
   - **Action:** Either update these to point to `../api/data` if you still need them for one-off data prep, or point to `../datasets/<your_dataset>/episodes.json` and series as appropriate. If the scripts are obsolete, remove or move to `scripts/` or `docs/` and document that they are legacy.

2. **Deprecated / legacy code**
   - `runner.py` imports `deprecated.llm_judge` for legacy single-LLM evaluation.  
   - Keep if you use `--legacy`; otherwise you can remove the import and the `--legacy` path after confirming no one relies on it.

3. **Reports and archives**
   - `evaluation/reports/` and `evaluation/reports/archive/` contain many JSON reports.  
   - Decide how many you need to keep (e.g. latest per algorithm/dataset, or a small archive). Move or delete the rest to reduce clutter. Optionally add a `.gitignore` rule for `reports/archive/*` if you want to stop tracking old reports.

4. **Criteria and test cases**
   - Keep criteria and test cases that are actually used by the runner. Remove or archive any that are never referenced.

5. **Env**
   - `evaluation/.env.example` and `evaluation/.env` — ensure they document `API_URL` (and LLM keys) and that runner/metrics use the same backend (server) URL.

**Test after Phase 4:**  
- From `evaluation/`:  
  - With backend running: `python runner.py --verbose` (and optionally `--save`).  
  - Run a single test: `python runner.py --test 01`.  
- Confirm no imports or paths assume `mock_api` or the legacy API unless you kept them on purpose.

---

## Suggested order and testing checklist

| Step | Phase | Main actions | Test |
|------|--------|---------------|------|
| 1 | 0 – Root | Add/fix root `.env.example`, trim root docs, update README | `docker-compose config`; optional `docker-compose up` + `curl .../api/health` |
| 2 | 1 – API | Remove or archive `api/`, update README and doc links | Same as step 1; no regression in frontend/evaluation |
| 3 | 2 – Server | Add `/api/series`, remove dead code, trim requirements, align .env.example | Backend health + config + episodes + series; run evaluation runner |
| 4 | 3 – Frontend | Remove legacy `fetchForYou` (or stub), centralize API base, remove unused UI/deps | `npm run build`; manual Browse / For You / Developer |
| 5 | 4 – Evaluation | Fix or remove mock_api references, prune reports/criteria, optional legacy LLM removal | `python runner.py --verbose` and `--test 01` |

After each step, run the test in the table. If anything breaks, fix before moving to the next phase. This keeps the cleanup incremental and safe.

---

## Quick reference: what depends on what

- **Frontend** → **server** (sessions, config, embeddings, evaluation, episodes; and series once added).  
- **Evaluation** → **server** (sessions, evaluation endpoints).  
- **Docker Compose** → server, frontend, qdrant; mounts algorithm, datasets, cache, evaluation.  
- **api/** → used by nothing in the current stack; safe to remove or archive after updating docs.

If you want, the next step can be implementing Phase 0 (root .env.example + README updates) and Phase 2’s `GET /api/series` so the frontend works against the current backend without legacy code.
