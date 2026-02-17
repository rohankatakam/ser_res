# Algorithm Cloud Architecture

This document describes the **ideal cloud architecture** for the `algorithm/` implementation when Firestore (episodes + engagements) and Pinecone (embeddings) are the existing infrastructure. It covers: refactoring the algorithm for cloud, **realtime vs batch** embedding generation, **in-memory vs fetch-by-id** vector usage, and how the recommendation API should orchestrate data and call the algorithm.

---

## 1. Current State

| Component | Today | Cloud (target) |
|-----------|--------|-----------------|
| **Episodes** | File-based dataset (`datasets/*/episodes.json`) or HTTP mock | **Firestore** (existing) |
| **Engagements** | Request body only (in-memory) | **Firestore** (per user) |
| **Embeddings** | Qdrant + JSON cache; **batch**-generated for entire episode set; **loaded in full** into API memory | **Pinecone**; batch or **realtime** per episode; **fetch by id** at request time |
| **Algorithm** | `algorithm/` loaded from disk; receives `(episodes, embeddings dict, engagements, config)` | Same logic; **data sources** swapped (Firestore provider, Pinecone store) |

The algorithm itself is already **data-source agnostic**: it only needs:
- `episodes: List[Dict]` (candidate pool + metadata)
- `embeddings: Dict[str, List[float]]` (episode_id → vector)
- `episode_by_content_id: Dict[str, Dict]`
- `engagements: List[Dict]`, `excluded_ids: Set[str]`, `config`

So the refactor is **not** “rewrite the algorithm for cloud”; it is **orchestration and data access**: where episodes/embeddings/engagements come from and how embeddings are generated and stored.

---

## 2. Target Cloud Architecture (High Level)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CLIENTS (mobile, web, test harness)                                         │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ HTTPS
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  RECOMMENDATION API (Cloud Run / ECS / same server)                          │
│  • Loads algorithm/ (embedding_strategy, recommendation_engine, config)       │
│  • EpisodeProvider → Firestore (or dataset for eval)                         │
│  • VectorStore → Pinecone fetch-by-id (or Qdrant/JSON for eval)              │
│  • EngagementStore → Firestore (or request-only for eval)                    │
│  • Session create: get episodes → get embeddings by id → run algorithm       │
└───────┬─────────────────────┬─────────────────────┬────────────────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────────┐   ┌─────────────────────────────┐
│  PINECONE    │   │  FIRESTORE          │   │  REALTIME EMBEDDING (optional)│
│  • Vectors   │   │  • Episodes (catalog)│   │  • On new/updated episode:   │
│    by        │   │  • Users/engagements │   │    embed → upsert Pinecone   │
│    episode_id│   │  • Same schema as    │   │  • Cloud Function / Run job │
│  • Fetch by  │   │    current episodes  │   └─────────────────────────────┘
│    id or     │   └─────────────────────┘
│    query     │
└───────────────┘
```

- **Episodes**: Firestore is source of truth; API uses `FirestoreEpisodeProvider` (or `HttpEpisodeProvider` for mock).
- **Engagements**: Firestore per user; API uses `FirestoreEngagementStore`.
- **Embeddings**: Pinecone holds one vector per episode (same as today). API **does not** load all vectors into memory; it fetches only the vectors it needs for the current request (see §4).
- **Algorithm**: Unchanged `algorithm/` code; API passes it the same shapes (episodes list, embeddings dict, engagements, config).

---

## 3. Embedding Generation: Batch vs Realtime

Today, embeddings are generated in **batch** for the **entire** episode set (e.g. on config load or via `/api/embeddings/generate`), then stored in Qdrant/JSON and loaded in full into `state.current_embeddings`.

In cloud:

### 3.1 Batch (still useful)

- **Backfill / evaluation**: For a fixed catalog (e.g. Firestore export or file-based dataset), run a job that:
  - Gets all episodes (Firestore or file).
  - For each episode: `get_embed_text(episode)` (from `algorithm/embedding_strategy.py`) → OpenAI embed → upsert to Pinecone with id = `episode_id`.
- Use case: initial index, evaluation over static datasets, periodic full refresh.

### 3.2 Realtime (per-episode, not per-request)

- **When**: A new episode is created or updated in Firestore (or when you explicitly “index” an episode).
- **How**:
  - **Option A – Firestore trigger**: Cloud Function (or similar) on Firestore write → load episode doc → `get_embed_text(episode)` → call OpenAI → upsert vector to Pinecone (by episode_id).
  - **Option B – API + job**: Backend exposes “index episode” (or a job consumes a queue); same flow: episode doc → embed → Pinecone upsert.
- **Important**: “Realtime” here means **on episode lifecycle**, not on every recommendation request. The API does **not** call OpenAI on each session create; it only **reads** vectors from Pinecone.

So:

- **Episode embeddings**: Pre-indexed in Pinecone (batch or realtime on episode create/update). No in-request embedding for episodes.
- **User vector**: Computed **at request time** from the user’s engagement episode ids: fetch those embeddings **from Pinecone by id** (see §4), then mean-pool (or sum-of-similarities) in the existing algorithm. No extra OpenAI call if engagement episodes are already in Pinecone.

---

## 4. In-Memory vs Fetch-by-Id (Critical for Scale)

Today the server often **loads all episode embeddings** into memory (`state.current_embeddings`) and passes that full dict into the algorithm. That does not scale when the catalog is large and vectors live in Pinecone.

### 4.1 Desired behavior in production

- **Do not** load the full Pinecone index into API memory.
- For each **session create**:
  1. Get **candidate episodes** (e.g. 150) from Firestore via EpisodeProvider (filter by quality/freshness or pass a larger set and let the algorithm’s Stage A trim).
  2. Get **user engagements** (e.g. last 10) from Firestore.
  3. Collect episode ids: `candidate_ids + engagement_episode_ids` (deduplicated).
  4. **Fetch only those embeddings from Pinecone** by id (e.g. `get_embeddings(episode_ids)`).
  5. Pass the resulting `embeddings: Dict[str, List[float]]` (and episodes, engagements, config) into the existing algorithm. Algorithm code is unchanged.

So: **in-memory** only for the **small set** of vectors needed for that request (~hundreds), not the entire catalog.

### 4.2 VectorStore contract extension

The current `VectorStore` protocol has:

- `has_cache(algorithm_version, strategy_version, dataset_version)`
- `load_embeddings(...)` → full dict (all vectors for that namespace)
- `save_embeddings(...)`

For cloud, add (or prefer) **fetch by id**:

- `get_embeddings(episode_ids: List[str], algorithm_version, strategy_version, dataset_version) -> Dict[str, List[float]]`

Implementations:

- **PineconeVectorStore**: `fetch(ids=episode_ids)` in Pinecone, return dict. Optionally use namespace = `f"{algorithm_version}_s{strategy_version}"` or similar.
- **QdrantJsonVectorStore**: Can implement `get_embeddings(ids)` by filtering the full load to `ids`, or by querying Qdrant by id if supported; for eval, loading full set is still acceptable for small datasets.

Session-create flow then becomes:

```text
episodes = episode_provider.get_episodes(limit=…)
candidate_pool_ids = [e["id"] for e in candidates]  # after Stage A or from provider
engagement_episode_ids = [e["episode_id"] for e in engagements]
all_ids = list(set(candidate_pool_ids) | set(engagement_episode_ids))
embeddings = vector_store.get_embeddings(all_ids, algorithm_version, strategy_version, dataset_version)
queue, cold_start, n = create_recommendation_queue(engagements, excluded_ids, episodes, embeddings, episode_by_content_id, config)
```

No “load all embeddings” into the API.

---

## 5. Algorithm Refactor (What to Change in `/algorithm`)

The `algorithm/` directory should remain a **pure logic** layer:

- **No** direct Firestore or Pinecone calls.
- **No** I/O; only functions that take in-memory data (episodes, embeddings dict, engagements, config) and return queues/scores.

Suggested refactor (minimal):

1. **Keep structure**: `embedding_strategy.py`, `recommendation_engine.py`, `config.json`, `manifest.json`, `computed_params.py`, `config_schema.json` as they are. The server already loads them via `AlgorithmLoader` from a directory (e.g. mounted `algorithm/` or a built package).

2. **Expose a clear entrypoint**: e.g. `create_recommendation_queue(engagements, excluded_ids, episodes, embeddings, episode_by_content_id, config)` and `RecommendationConfig.from_dict(...)`. The server already uses these; just document them as the **only** contract the cloud API needs.

3. **Optional – package as library**: If you want to run the same logic in a Cloud Function or another service, turn `algorithm/` into a proper Python package (e.g. `algorithm/` with `__init__.py` exporting `create_recommendation_queue`, `RecommendationConfig`, `get_embed_text`) and install it where needed. The server would then `from algorithm import create_recommendation_queue` (or keep loading from disk for flexibility). For a single API deployment, loading from disk is fine.

4. **Versioning**: Keep `manifest.json` and `embedding_strategy.py` versioning (e.g. `STRATEGY_VERSION`) so Pinecone namespacing and cache invalidation stay consistent.

No change to the **ranking logic** (Stage A/B, cold start, weights) is required for cloud; only the **data plumbing** (where episodes/embeddings/engagements come from) changes in the server.

### 5.1 Algorithm refactor checklist

| Task | Purpose |
|------|--------|
| Keep `algorithm/` I/O-free | No Firestore/Pinecone imports; only in-memory inputs. |
| Document public contract | `create_recommendation_queue`, `RecommendationConfig.from_dict`, `get_embed_text` (from embedding_strategy). |
| Optional: add `algorithm/__init__.py` | Re-export engine + config + `get_embed_text` for use as a library (e.g. Cloud Function that does realtime embed). |
| Keep versioning | `manifest.json` version, `STRATEGY_VERSION` in embedding_strategy; Pinecone namespace/keying aligns with these. |

---

## 6. Ideal Data Flows (Summary)

### 6.1 New episode (realtime embedding)

1. Episode created/updated in Firestore.
2. Trigger (Cloud Function or job) runs: read episode doc → `get_embed_text(episode)` (from algorithm’s embedding_strategy) → OpenAI embed → upsert to Pinecone with id = `episode["id"]` (and correct namespace/index).

### 6.2 Session create (recommendation request)

1. Authenticate user (e.g. Firebase Auth) → `user_id`.
2. **Engagements**: `engagement_store.get_engagements_for_session(user_id, request_engagements)` → from Firestore (or merge with request body).
3. **Episodes**: `episode_provider.get_episodes(...)` → from Firestore (paginated/filtered as needed).
4. **Candidate pool**: Optionally apply Stage A in the API or pass a subset; collect candidate episode ids.
5. **Embeddings**: `vector_store.get_embeddings(episode_ids, algo_version, strategy_version, dataset_version)` → from Pinecone by id (~candidate set + engagement episode ids).
6. **Episode map**: Build `episode_by_content_id` from episode list (or from provider helper).
7. **Algorithm**: `create_recommendation_queue(engagements, excluded_ids, episodes, embeddings, episode_by_content_id, config)` → queue, cold_start, n.
8. Return first page of recommendations; persist session in memory (or Firestore if you want “continue on another device”).

### 6.3 Engage

1. Update in-memory session (shown/engaged).
2. `engagement_store.record_engagement(user_id, episode_id, type)` → write to Firestore.

---

## 7. Configuration (Env / Config)

Suggested env-driven behavior (align with existing CLOUD_ARCHITECTURE_MIGRATION):

| Env / config | Options | Effect |
|--------------|--------|--------|
| `EPISODE_SOURCE` | `dataset` \| `firestore` \| `http` | EpisodeProvider implementation. |
| `VECTOR_STORE` | `qdrant_json` \| `pinecone` | VectorStore implementation; Pinecone ⇒ fetch-by-id, no full load. |
| `ENGAGEMENT_STORE` | `request` \| `firestore` | EngagementStore implementation. |
| `PINECONE_*` | index name, API key, namespace pattern | Used when `VECTOR_STORE=pinecone`. |

Algorithm directory path (e.g. `ALGORITHMS_DIR` or mounted volume) stays as today; algorithm code itself is unchanged.

---

## 8. Summary Table

| Question | Answer |
|----------|--------|
| **Where do episodes come from?** | Firestore (production); dataset/HTTP for eval. |
| **Where do embeddings live?** | Pinecone (production); Qdrant/JSON for eval. |
| **Batch vs realtime embeddings?** | Episode embeddings: batch backfill **or** realtime on episode create/update (Firestore trigger or job). User vector: computed at request time from engagement ids, no extra batch. |
| **Load all embeddings into API memory?** | No. Fetch only the episode ids needed for the request (candidates + engagement episodes) from Pinecone. |
| **What changes in `algorithm/`?** | No cloud I/O; optional packaging as library; keep contract (create_recommendation_queue, get_embed_text, config). |
| **What changes in the server?** | Wire FirestoreEpisodeProvider, PineconeVectorStore (with `get_embeddings(ids)`), FirestoreEngagementStore; session create uses fetch-by-id and then calls the same algorithm. |

This gives you an **ideal cloud architecture** for the current algorithm: Firestore for episodes and engagements, Pinecone for embeddings, realtime indexing of new episodes, and in-request only the embeddings needed for that request, with the existing `algorithm/` implementation unchanged.
