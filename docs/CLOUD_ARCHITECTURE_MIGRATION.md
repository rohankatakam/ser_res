# Cloud Architecture & Migration Plan

This document describes the **target cloud architecture** (Pinecone + Firebase/Firestore) and a **phased migration path** from the current single-node, file-based setup to a live recommendation engine that serves mobile and web clients, with the existing frontend treated as a **test harness** for the engine and evaluation.

---

## 1. Target Architecture

### 1.1 Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CLIENTS                                                                     │
│  • Mobile app (production)  • Web app (production)  • Test harness (frontend) │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                 │ HTTPS / API
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  RECOMMENDATION API (your backend)                                           │
│  • Session create / next / engage                                            │
│  • User-scoped: bookmarks, views, engagement history from Firestore          │
│  • Algorithm: same ranking logic (algorithm/)                                 │
└───────┬───────────────────────┬───────────────────────┬────────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐     ┌─────────────────┐     ┌─────────────────────────────┐
│  PINECONE     │     │  FIREBASE       │     │  FIREBASE (optional)          │
│  Vector store │     │  FIRESTORE      │     │  Auth / other                │
│  • Episode    │     │  • Episodes      │     │  • Auth for user_id          │
│    embeddings │     │    (queryable:  │     │  • Cloud Functions if needed │
│  • Similarity │     │    by date,      │     └─────────────────────────────┘
│    search     │     │    limit, etc.) │
│               │     │  • User data:    │
│               │     │    bookmarks,    │
│               │     │    views,       │
│               │     │    engagement   │
└───────────────┘     └─────────────────┘
```

### 1.2 Data Flow (Production)

1. **Episodes**  
   Backend gets episode catalog from **Firestore** (e.g. “get N episodes”, “by date range”, “full set for indexing”). Schema aligns with current `datasets/eval_909_feb2026` (id, title, scores, key_insight, published_at, series, categories, etc.) so the same algorithm code works.

2. **Embeddings / vectors**  
   Stored and queried in **Pinecone** (one index per algorithm+strategy, or namespaced by index + metadata). On “create session”, backend either uses pre-indexed episode vectors or fetches them; user vector is computed from recent engagements and used for similarity (e.g. query or fetch-by-ids).

3. **User state (bookmarks, views)**  
   Stored in **Firestore** (e.g. `users/{userId}/engagements`, `users/{userId}/bookmarks`). When creating a recommendation session, backend loads that user’s engagements from Firestore and passes them into the same ranking pipeline (candidate pool + blended scoring). New bookmarks/views from “engage” are written back to Firestore.

4. **Sessions**  
   Can stay short-lived in API memory (current behavior) with engagement persisted in Firestore, or optionally persisted in Firestore for “continue where I left off” across devices. Recommendation **queue** can still be computed once per “create session” and paginated with “next” as today.

5. **Algorithm**  
   Unchanged: `algorithm/` (embedding_strategy, recommendation_engine, config) remains the source of ranking logic. Only the **data sources** (episodes, vectors, engagements) become pluggable.

### 1.3 Role of the Current Frontend

- The app in **`frontend/`** is the **evaluation and test harness**: run algorithm + evaluation (tests, reports), try different configs, debug sessions.
- **Production** mobile and web apps are separate; they call the same Recommendation API (sessions, engage) with a **user identity** (e.g. Firebase Auth `id_token` or `user_id`).
- The harness can keep using anonymous or test users and local/demo config; production uses Firestore + Pinecone and real user ids.

---

## 2. Abstractions to Introduce

To move to cloud without a big-bang rewrite, introduce clear boundaries between “algorithm + orchestration” and “where data lives”.

### 2.1 Episode provider (replace “dataset from disk”)

**Interface (conceptually):**

- `get_episodes(limit=None, offset=0, since=None, until=None, episode_ids=None) -> List[dict]`
- `get_episode(episode_id: str) -> Optional[dict]`
- `get_series() -> List[dict]` (or derived from episodes)
- Optional: `get_episode_count()`, `get_manifest()` for compatibility with current “dataset” concept.

**Implementations:**

- **Current:** `DatasetEpisodeProvider(LoadedDataset)` — wraps existing `LoadedDataset` from `dataset_loader` (reads from `datasets/eval_909_feb2026`).
- **Cloud:** `FirestoreEpisodeProvider` — talks to Firestore (your “get episodes” function / collection). Queries by date, limit, etc., and returns the same episode shape as today so the rest of the stack is unchanged.

Evaluation and harness continue to use the file-based provider; production uses Firestore.

### 2.2 Vector store (replace “Qdrant + JSON cache”)

**Interface (conceptually):**

- `has_embeddings(algorithm_version, strategy_version, dataset_or_namespace) -> bool`
- `load_embeddings(...) -> Dict[str, List[float]]` (optional: for “load all” like today)
- `get_embeddings(episode_ids: List[str], ...) -> Dict[str, List[float]]`
- `save_embeddings(..., embeddings, metadata)`
- Optional: `query_similar(vector, top_k, filter) -> List[(id, score)]` if you want to push “similarity search” into the store instead of in-memory.

**Implementations:**

- **Current:** Keep existing `EmbeddingCache` + `QdrantEmbeddingStore` behind this interface (or a thin facade) for local and evaluation.
- **Cloud:** `PineconeVectorStore` — one index (or index + namespace) per algorithm+strategy; upsert episode vectors; at request time either fetch vectors by episode ids or run similarity search in Pinecone. Same embedding model and dimensions as today (e.g. text-embedding-3-small, 1536).

Algorithm and session logic only depend on the interface, not on Pinecone vs Qdrant vs JSON.

### 2.3 User engagement store (new)

**Interface (conceptually):**

- `get_engagements(user_id: str, limit=N) -> List[{episode_id, type, timestamp}]`
- `record_engagement(user_id: str, episode_id: str, type: str)` (bookmark, view, etc.)
- Optional: `get_excluded_ids(user_id)`, or derive from engagements.

**Implementations:**

- **Current / harness:** In-memory or “per request” (request body carries engagements; no persistence). Optional simple implementation that reads/writes a JSON file or a stub DB for local testing.
- **Cloud:** `FirestoreEngagementStore` — Firestore collections for user engagements and bookmarks; backend reads when creating a session and writes on “engage”. Same schema as your current engagement payload (episode_id, type, timestamp).

Sessions can stay in-memory; only the **source** of engagements (and optional persistence of new ones) moves to Firestore in production.

### 2.4 Optional: config / feature flags

- Algorithm config (weights, gates, etc.) can stay in repo (current `algorithm/config.json`) or be moved to Firestore/Secret Manager for production. Not required for the first version; keep file-based config and pass it through as today.

---

## 3. Phased Migration

### Phase 1: Abstractions in place (no cloud yet) — **DONE**

**Goal:** Backend talks to **interfaces** for episodes, vectors, and engagements so you can swap implementations later.

**Implemented:** `server/episode_provider.py` (EpisodeProvider + DatasetEpisodeProvider), `server/vector_store.py` (VectorStore + QdrantJsonVectorStore), `server/engagement_store.py` (EngagementStore + RequestOnlyEngagementStore). AppState uses them; session create/engage go through these abstractions. Local testing unchanged (dataset + Qdrant/JSON + request-only engagements).

**To swap for cloud later:** Implement `FirestoreEpisodeProvider`, `PineconeVectorStore`, `FirestoreEngagementStore` and set them on AppState (e.g. from config: `EPISODE_SOURCE=firestore`, `VECTOR_STORE=pinecone`, `ENGAGEMENT_STORE=firestore`). No change to API or algorithm code.

1. **Episode provider**
   - Define `EpisodeProvider` protocol (or abstract class) with the methods above.
   - Implement `DatasetEpisodeProvider` that wraps `LoadedDataset` and exposes `get_episodes`, `get_episode`, `get_series`.
   - In `AppState` / session creation, use “current episode provider” instead of `current_dataset.episodes` directly where possible (e.g. pass “list of episodes” from provider into the engine). Keep `current_dataset` for now if it simplifies manifest/versioning; the important part is that “episode list” comes from the provider.

2. **Vector store**
   - Define `VectorStore` protocol: `has_embeddings`, `load_embeddings` (or `get_embeddings` by ids), `save_embeddings`.
   - Implement a facade that delegates to existing Qdrant + JSON cache (current `has_embeddings` / `load_cached_embeddings` / `save_embeddings` logic). Session and embedding-generation code call the facade only.

3. **Engagement source**
   - Today engagements come only from the request body. Introduce an “engagement source” abstraction: e.g. `get_engagements_for_session(user_id, request_engagements) -> list`. Default implementation: return `request_engagements` (current behavior). Later, Firestore implementation will merge request with DB.

4. **Tests**
   - Existing evaluation and harness flows should behave the same (same dataset, same cache, same in-request engagements).

**Outcome:** No new infrastructure; code is ready to plug in Firestore and Pinecone.

---

### Phase 2: Pinecone as vector store

**Goal:** Production (or a “cloud” mode) uses Pinecone for vectors; evaluation/harness can still use JSON or Qdrant.

1. **Pinecone client and index**
   - Create index(es) with dimension 1536 (or your embedding_dimensions), metric cosine.
   - Use one index per “algorithm+strategy” or namespaces (e.g. `namespace = f"{algorithm_version}_s{strategy_version}"`) so you can support multiple algorithms.

2. **PineconeVectorStore implementation**
   - `save_embeddings`: upsert vectors with id = episode_id (or content_id), plus metadata (algorithm_version, strategy_version, etc.).
   - `has_embeddings`: check index/namespace and optionally count.
   - `load_embeddings`: query all vectors in that namespace (Pinecone “fetch” or list) and return dict id → vector; or implement `get_embeddings(episode_ids)` with fetch by id.
   - Optional: `query_similar(user_vector, top_k)` for “similarity search in Pinecone” and then fetch episode docs from Firestore by id.

3. **Backend configuration**
   - Env or config: `VECTOR_STORE=qdrant|json|pinecone`; if `pinecone`, use `PineconeVectorStore` with API key and index name. Keep existing Qdrant/JSON for non-production.

4. **Embedding pipeline**
   - For production: episodes from Firestore (Phase 3); generate embeddings (OpenAI) and upsert to Pinecone. You can run a batch job (Cloud Function, Cloud Run, or worker) that pulls episodes from Firestore and backfills Pinecone, then keep it updated on new episodes.

**Outcome:** Vectors can live in Pinecone; recommendation logic still uses “get embeddings for these episodes” and “get user vector from engagements” as today.

---

### Phase 3: Firestore for episodes

**Goal:** Episode catalog comes from Firestore instead of `datasets/` files.

1. **Firestore schema**
   - Align with current episode shape: id, title, scores, key_insight, published_at, series, categories, content_id, etc. (e.g. collection `episodes` or `catalog/episodes`). Optionally a `series` subcollection or top-level collection.

2. **FirestoreEpisodeProvider**
   - Implement `get_episodes(limit, offset, since, until, episode_ids)` using Firestore queries (limit, orderBy published_at, where filters).
   - Implement `get_episode(id)`, `get_series()` (or from episode docs). Return same dict shape as current so algorithm and ranking need no changes.

3. **Backend configuration**
   - E.g. `EPISODE_SOURCE=dataset|firestore`. In production, use `FirestoreEpisodeProvider` with Firebase credentials; for evaluation and harness, keep `DatasetEpisodeProvider` reading from `datasets/eval_909_feb2026`.

4. **Evaluation**
   - Evaluation runner and test harness keep using the file-based dataset so tests are deterministic and don’t depend on Firestore. Optionally add a small “live” test that uses Firestore if you want.

**Outcome:** Production API can run entirely on Firestore for episodes; evaluation still uses local datasets.

---

### Phase 4: Firestore for user engagements (bookmarks, views)

**Goal:** User bookmarks and views are stored in Firestore; session creation reads them; “engage” writes them.

1. **Firestore schema**
   - E.g. `users/{userId}/engagements` (or `engagements` with `user_id`): documents with episode_id, type (bookmark, view, etc.), timestamp. Indexes for “by user, by time” for “last N engagements”.

2. **FirestoreEngagementStore**
   - `get_engagements(user_id, limit=10)` → query Firestore, return list of {episode_id, type, timestamp}.
   - `record_engagement(user_id, episode_id, type)` → write new document (and optionally update “excluded” or “bookmarks” aggregates if you use them).

3. **API and identity**
   - Production endpoints require a **user identity**. Options:
     - **Firebase Auth:** Client sends `Authorization: Bearer <id_token>`; backend verifies token and uses `uid` as `user_id`.
     - Or API key + `X-User-Id` for internal/mobile backends (less secure; use only if auth is handled elsewhere).
   - Session create: backend loads `user_id` from auth (or header); fetches engagements from Firestore via `FirestoreEngagementStore`; merges with any request-body engagements if you still allow overrides; runs same `create_recommendation_queue` with that engagement list.
   - Engage: after updating in-memory session, call `engagement_store.record_engagement(user_id, episode_id, type)`.

4. **Harness / evaluation**
   - No user_id or anonymous: keep “engagements only from request body” (current behavior). So evaluation and harness don’t need Firestore for engagements.

**Outcome:** Production has persistent, user-scoped bookmarks and views; recommendation engine is “live” and works the same on mobile and web.

---

### Phase 5: Harden production API and keep harness separate

**Goal:** Clear split between “evaluation harness” and “production recommendation API,” and secure production.

1. **Deploy**
   - **Production:** Deploy the same server (or a “production” profile) with `EPISODE_SOURCE=firestore`, `VECTOR_STORE=pinecone`, engagement store = Firestore; Firebase Auth for user_id. Expose only session/engage and any minimal config endpoints needed by clients.
   - **Harness / eval:** Deploy (or run locally) with `EPISODE_SOURCE=dataset`, `VECTOR_STORE=json` or `qdrant`, engagements from request; keep full config, embeddings, evaluation endpoints for running tests and the React harness.

2. **API surface**
   - Production: `POST /api/sessions/create`, `POST /api/sessions/{id}/next`, `POST /api/sessions/{id}/engage`, plus health and maybe config (e.g. algorithm version). Auth required.
   - Harness: all current endpoints (config load, algorithms, datasets, embeddings generate, evaluation run, etc.) for local or internal use only.

3. **Frontend**
   - `frontend/` stays the test harness: points at harness/eval backend; no production auth. Mobile and web apps are separate codebases that point at the production API with auth.

**Outcome:** One codebase, two deployment modes (production vs evaluation), and a clear path for mobile and web to consume the same recommendation engine.

---

## 4. Summary: What Changes vs What Stays

| Area | Current | Target (production) |
|------|---------|----------------------|
| Episodes | `datasets/*/episodes.json` + DatasetLoader | Firestore (queryable) |
| Vectors | Qdrant or JSON cache | Pinecone |
| User engagements | Request body only, in-memory session | Firestore (bookmarks, views); session can stay in-memory |
| Algorithm | `algorithm/` (files) | Same; only data sources are swapped |
| Evaluation | `evaluation/` + harness frontend | Unchanged; uses dataset + JSON/Qdrant |
| Clients | Harness (React) | Harness + mobile + web (same API, auth for prod) |

---

## 5. Suggested Next Steps

1. **Implement Phase 1** (abstractions: EpisodeProvider, VectorStore facade, engagement source) in the current repo so all behavior is unchanged but interfaces are in place.
2. **Add Pinecone** (Phase 2): new `PineconeVectorStore`, env-driven choice of vector store, and a small script or job to backfill Pinecone from current dataset/embeddings if useful.
3. **Add Firestore** (Phase 3 + 4): FirestoreEpisodeProvider and FirestoreEngagementStore; wire engagement store into session create and engage; add auth (e.g. Firebase Auth) for production user_id.
4. **Document** Firestore collection shapes and Pinecone index/namespace convention in this repo so backend and any Cloud Functions stay in sync.
5. Keep **evaluation and harness** on file-based dataset and optional JSON/Qdrant so they remain independent of cloud and deterministic.

This path gives you a **live recommendation engine** in the cloud (Pinecone + Firestore) with **bookmarks and views** persisted per user, while **reusing the same algorithm and evaluation stack** and treating the current frontend as the test harness for that engine.

---

## 6. Swapping implementations (after Phase 1)

| Abstraction        | Current (local)              | Cloud (when ready)        |
|--------------------|------------------------------|---------------------------|
| **EpisodeProvider**| `DatasetEpisodeProvider`     | `FirestoreEpisodeProvider`|
| **VectorStore**    | `QdrantJsonVectorStore`     | `PineconeVectorStore`     |
| **EngagementStore**| `RequestOnlyEngagementStore` | `FirestoreEngagementStore`|

In `AppState.__init__` (or a small factory), choose implementations from env, e.g.:

- `EPISODE_SOURCE=dataset` (default) or `firestore`
- `VECTOR_STORE=qdrant_json` (default) or `pinecone`
- `ENGAGEMENT_STORE=request` (default) or `firestore`

Then test locally with defaults; deploy with cloud env vars to use Pinecone and Firestore without changing API or algorithm code.

---

## 7. Mock Episodes API (Firestore-like testing)

A **mock episodes API** serves the same dataset as files (`datasets/eval_909_feb2026`) over HTTP so you can test the Firestore-like path without Firestore.

**Run the mock API:**
```bash
# From repo root (default: datasets/eval_909_feb2026)
python -m server.mock_episodes_api
# Or: uvicorn server.mock_episodes_api:app --reload --port 8001
```
Optional: `DATASET_PATH=/path/to/folder` (folder with `episodes.json` and optional `series.json`). Default port 8001.

**Endpoints (aligned with EpisodeProvider):**
- `GET /episodes?limit=&offset=&since=&until=&episode_ids=` — list episodes (paginated/filtered)
- `GET /episodes/{id}` — one episode by id or content_id
- `GET /series` — list series
- `GET /episode-by-content-id-map` — content_id → episode map for engagement resolution
- `GET /health` — status

**Use from the main server:** `HttpEpisodeProvider(base_url="http://localhost:8001")` implements `EpisodeProvider` by calling these endpoints. Wire it when you want to test the HTTP/Firestore path (e.g. set `current_episode_provider = HttpEpisodeProvider(os.environ["EPISODES_API_URL"])` when `EPISODE_SOURCE=http`).
