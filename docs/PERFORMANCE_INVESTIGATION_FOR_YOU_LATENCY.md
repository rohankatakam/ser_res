# Performance Investigation: For You Generation Latency (5–10s)

**Goal:** Understand why For You feed generation takes 5–10 seconds on cold start or when engagements change, and identify optimizations before full cloud deployment.

---

## 1. Deployment Readiness Check

**Plan step order:** Steps 1–4 (Create User, Edit interests, Series diversity, Category anchor) are ✓. Step 5 (Deployment) is next.

**Gap:** No blocking issues for deployment. You can proceed with Cloud Run + Vercel. Performance work can run in parallel or before go-live if latency is a constraint.

---

## 2. Current Architecture (Mixed Local/Cloud)

| Component | Typical Setup | Latency |
|-----------|---------------|---------|
| **Server** | Local (or Cloud Run) | — |
| **Episodes** | Firestore (cloud) when `DATA_SOURCE=firebase` | Network RTT per query |
| **Engagements** | Firestore (cloud) when `DATA_SOURCE=firebase` | Network RTT per query |
| **Users** | Firestore (cloud) when firebase configured | Network RTT per query |
| **Embeddings** | Pinecone (cloud) | Network RTT per fetch |
| **Algorithm** | In-process Python | CPU only |

**Main issue:** Each cloud call adds network round-trip time (often 50–200ms per call). Requests are mostly **serial**, so latency accumulates.

---

## 3. create_session Latency Breakdown

The For You feed is built by `POST /api/sessions/create`. Flow (current implementation):

```
Frontend → createSession(engagements, excludedIds, userId)
         → Backend create_session()
         → asyncio.gather(
               engagement_store.get_engagements_for_ranking_async(),
               user_store.get_by_id_async() [if user_id],
               episodes from state.current_dataset.episodes OR episode_provider.get_episodes_async()
             )
         → episode_by_content_id built from episode list (no extra Firestore scan)
         → engine.get_candidate_pool_ids()
         → vector_store.get_embeddings_async(needed_ids)
         → engine.create_recommendation_queue()
         → Response
```

### 3.1 Data Fetches (Primary Latency Sources)

| Step | Implementation | Est. latency (typical) |
|------|----------------|------------------------|
| `get_engagements_for_ranking` | Firestore: `users/{uid}/engagements` stream, limit 500, order by timestamp | 200–800ms |
| `get_by_id` | Firestore: 1 user doc | 50–150ms |
| `get_episodes(limit=None)` | Firestore: `episodes` query, limit 2000, order by `published_at` | 500–2000ms |
| **`get_episode_by_content_id_map()`** | **Firestore: full `episodes` collection stream (no limit)** | **500–3000ms** |
| `get_candidate_pool_ids` | In-memory (no network) | &lt;10ms |
| `get_embeddings(needed_ids)` | Pinecone fetch, ~160 IDs (candidate 150 + engagement ~10) | 100–500ms |
| `create_recommendation_queue` | In-memory scoring/ranking | 20–100ms |

### 3.2 Critical Bug: Double Firestore Scan

`FirestoreEpisodeProvider.get_episode_by_content_id_map()` streams the **entire** episodes collection with no limit:

```python
# episode_provider.py:311-320
def get_episode_by_content_id_map(self) -> Dict[str, Dict]:
    if self._content_id_map_cache is not None:
        return self._content_id_map_cache
    docs = self._episodes_coll.stream()  # ← NO limit; full scan
    self._content_id_map_cache = {}
    for doc in docs:
        ...
```

- First session create: full collection scan (can be 1–3s for ~1000 docs).
- `get_episodes(limit=None)` already fetches up to 2000 docs.
- Together: two large reads per session on first call; only `get_episode_by_content_id_map` is cached for later requests.

**Fix:** Build `episode_by_content_id` from the `get_episodes()` result instead of a separate full scan. The ranking logic only needs content_id mapping for the episodes being considered.

---

## 4. Sessions vs Evaluation Paths

| Path | Episode source | Embedding fetch | Batch size |
|------|----------------|-----------------|------------|
| **Sessions** | `current_episode_provider.get_episodes()` | `get_embeddings(engagement_ids ∪ candidate_ids)` | Single call (~160 IDs) |
| **Evaluation** | Same | All episode IDs, batched 100 per request | 9+ batches for ~900 episodes |

Evaluation batching was added to avoid 414 Request-URI Too Large. The sessions route does not batch but typically uses ~160 IDs, so a single Pinecone fetch is sufficient. If catalog size grows or `candidate_pool_size` increases, batching may be needed.

---

## 5. Serial vs Parallel Execution

Current flow is mostly serial:

1. Engagements
2. User (if present)
3. Episodes
4. Episode-by-content-id map
5. Candidate pool IDs (depends on episodes)
6. Embeddings (depends on candidate + engagement IDs)
7. Algorithm

**Parallelizable:**
- `get_engagements_for_ranking`, `get_by_id`, `get_episodes` can run in parallel.
- `get_episode_by_content_id_map` can be replaced by deriving from `get_episodes()` result.
- After episodes and engagements are ready, `get_candidate_pool_ids` → `get_embeddings` → `create_recommendation_queue` must stay sequential.

---

## 6. Comparison with TikTok / X (For You Feeds)

| Aspect | Serafis | TikTok / X style |
|--------|---------|------------------|
| Ranking | In-process, on each request | Often precomputed / cached per user |
| Vector search | Fetch by ID, then similarity in Python | Approx NN search inside vector DB (Pinecone query) |
| Cold start | Fetch user vector, score 150 candidates | Pre-warmed or lightweight fallback |
| Engagement update | Re-rank on next session create | Asynchronous refresh + cached feed |
| Latency target | 5–10s today | Sub-second perceived (streaming, skeletons) |

**Gap:** Our design is “fresh compute every time.” TikTok/X rely on caching, precomputation, and streaming UI. Reaching sub-second latency would require architectural changes (precomputed queues, Pinecone similarity search, skeleton loading, etc.).

---

## 7. Recommended Optimizations (Priority Order)

### High impact — ✅ IMPLEMENTED

1. **Remove double Firestore scan** ✅  
   Build `episode_by_content_id` from `get_episodes()` result in the session path. Avoid `get_episode_by_content_id_map()` full collection stream. Implemented in `sessions.py` and `evaluation.py`.

2. **Parallelize initial fetches** ✅  
   Run `get_engagements_for_ranking`, `get_by_id`, and `get_episodes` concurrently using **asyncio.gather** with native async clients (Firestore AsyncClient, Pinecone IndexAsyncio). Implemented in `sessions.py`.

3. **In-memory episode catalog (avoids ~909 Firestore reads per session)** ✅  
   When a file-based dataset is loaded at startup (`state.current_dataset.episodes`), use it for session create instead of re-fetching the full catalog from Firestore. Saves hundreds of reads per request; critical when `episode_provider` is Firestore. Implemented in `sessions.py` (`_get_episodes`).

4. **Colocate server with data**  
   Run Cloud Run in the same region as Firestore and Pinecone (e.g. us-central1) to cut RTT per call. Deployment config.

### Medium impact

5. **Episode preload (redundant when using in-memory dataset)**  
   When using Firestore for episodes without a file dataset, preload on config load. Our current flow uses in-memory dataset when available, so this is already covered.

6. **Pinecone gRPC client**  
   Use Pinecone’s gRPC client instead of REST where supported to reduce per-call overhead.

7. **Tighten Firestore reads**  
   - `get_episodes`: add `since`/`until` or lower limit when possible.  
   - Ensure composite indexes exist for `published_at`, `timestamp` to keep queries fast.

### Lower impact / Future

8. **Reduce candidate pool size**  
   Test smaller `candidate_pool_size` (e.g. 100) to reduce embedding fetch size and scoring cost.

9. **Pinecone similarity search**  
   Consider using Pinecone `query()` for approximate NN instead of fetch-then-rank. Would require algorithm changes and tuning.

---

## 8. Async Strategy: asyncio vs ThreadPoolExecutor

**Decision: Prefer `asyncio.gather` with native async clients over `concurrent.futures.ThreadPoolExecutor`.**

| Approach | Pros | Cons |
|----------|------|------|
| **asyncio + native async** | Lightweight; scales to thousands of concurrent I/O-bound requests; no thread-pool limits; single-threaded (easier debugging); explicit `await` points | Requires async Firestore/Pinecone clients and async route handlers |
| **ThreadPoolExecutor** | Works with existing sync code; no API changes | Thread pool limits create bottlenecks under load; threads consume CPU/memory while idle; manual pool sizing |

Firestore and Pinecone both provide native async Python APIs. Using them with `asyncio.gather` yields the best latency and scalability before Cloud Run / Vercel deployment.

---

## 9. Async Implementation Guide (Firestore & Pinecone)

### Firestore Async

The `google.cloud.firestore` library provides `AsyncClient` for async operations. Use it alongside (or instead of) `firebase-admin` for Firestore reads.

**Setup (use same project/credentials as firebase):**

```python
from google.cloud.firestore import AsyncClient
from google.oauth2 import service_account

# Option A: Application Default Credentials
db = AsyncClient(project="your-project-id")

# Option B: Service account (production)
with open("path/to/serviceAccountKey.json") as f:
    creds = service_account.Credentials.from_service_account_info(json.load(f))
db = AsyncClient(project="your-project-id", credentials=creds)
```

**Query with async stream (no limit; full scan – avoid; use get_episodes result instead):**

```python
docs = db.collection("episodes").order_by("published_at", direction="DESCENDING").limit(2000).stream()
async for doc in docs:
    d = doc.to_dict()
    d["id"] = doc.id
    # process...
```

**Single document fetch:**

```python
doc_ref = db.collection("users").document(user_id)
doc = await doc_ref.get()
if doc.exists:
    user = doc.to_dict()
```

**Subcollection stream (engagements):**

```python
ref = db.collection("users").document(user_id).collection("engagements")
query = ref.order_by("timestamp", direction="DESCENDING").limit(500)
async for doc in query.stream():
    # process...
```

Note: `firebase_admin.initialize_app()` is not required when using `AsyncClient` directly. Both can coexist; use `AsyncClient` for async reads.

### Pinecone Async

Pinecone’s Python SDK supports asyncio. Use `IndexAsyncio` for data-plane operations (fetch by ids).

**Install:** Requires `pinecone` with asyncio extra (adds `aiohttp`). Use SDK 5.x+ (6.x recommended for full async support).
```bash
pip install "pinecone[asyncio]"
```

**Setup (preferred: reuse sync Pinecone client, get AsyncioIndex for data ops):**

```python
from pinecone import Pinecone

# At app startup (e.g. lifespan): create sync client
pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
# Use AsyncioIndex for async fetch; host from describe_index or env
```

**Async fetch by ids (for session create):**

```python
async def get_embeddings_async(ids: list[str], namespace: str) -> dict:
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    async with pc.AsyncioIndex(host=index_host) as idx:
        fetched = await idx.fetch(ids=ids, namespace=namespace)
        return {vid: list(vec.values) for vid, vec in fetched.vectors.items()}
```

For connection pooling, build `AsyncioIndex` once at startup (e.g. in FastAPI lifespan) and reuse it; see [Pinecone asyncio docs](https://sdk.pinecone.io/python/asyncio.html).

### Parallel fetches with asyncio.gather

```python
@router.post("/create", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest):
    # ...
    tasks = [
        get_engagements_async(user_id, request_engagements),
        get_user_async(user_id) if user_id else asyncio.sleep(0),  # sleep(0) yields, returns None
        get_episodes_async(limit=2000),
    ]
    engagements, user, episodes = await asyncio.gather(*tasks)
    episode_by_content_id = {ep["content_id"]: ep for ep in episodes if ep.get("content_id")}  # no extra Firestore scan
    # ... continue with candidate pool, embeddings, algorithm
```

---

## 10. Speed Tests for Evaluation (Future)

Add latency tests to the evaluation harness:

- **Target:** `create_session` (or equivalent engine call) completes within a threshold (e.g. &lt;3s or &lt;5s).
- **Implementation:**
  - Wrap `create_session` / `create_recommendation_queue` with timing.
  - Add a test case (e.g. `09_session_latency.json`) that asserts `p95 < X seconds`.
  - Run under both local and cloud setups to compare.

---

## 11. In-Memory vs Caching (Terminology)

| Term | Meaning | In Serafis |
|------|---------|------------|
| **In-memory** | Data held in the server process’s RAM (not disk, not remote DB) | `state.current_dataset.episodes` loaded from file at startup; `state.current_embeddings` when cached |
| **Caching** | Storing data for reuse; can be in-memory, on disk, or in a cache service | In-memory caching: dataset, embeddings; Firestore/Pinecone are authoritative remote stores |
| **Server-side** | Logic and storage on the backend | All of this is server-side; the React/React Native frontend only calls the API |

**Summary:** In-memory is a kind of server-side cache. When we “use in-memory dataset for episodes,” we avoid re-reading from Firestore and instead use the catalog already loaded into the server’s RAM. This reduces Firestore reads and latency.

---

## 12. Cloud Run Deployment — Maximized Efficiency

**Target:** Backend on Cloud Run, frontend on React (web) or React Native (iOS/Android).

### What We Already Do Well

| Optimization | Status | Effect |
|--------------|--------|--------|
| No double Firestore scan | ✅ | Saves ~1–3s per session |
| Parallel fetches (asyncio) | ✅ | Engagements + user + episodes in parallel instead of serial |
| In-memory episode catalog | ✅ | ~909 Firestore reads avoided per session when dataset is loaded from file |
| Firestore AsyncClient only | ✅ | Non-blocking I/O, scales with concurrent requests |
| Pinecone async fetch | ✅ | Single batch fetch for embeddings |

### Cloud Run Specifics

1. **Stateless containers**  
   Each Cloud Run instance keeps its own in-memory state. On cold start we load the dataset from the container image or Cloud Storage. Once loaded, requests in that instance reuse it until the instance scales down.

2. **Colocation**  
   Deploy Cloud Run in the same region as Firestore and Pinecone (e.g. `us-central1`) to reduce network RTT.

3. **Minimal cold-start payload**  
   Dataset and embeddings are loaded at startup. Keep the dataset file small (or load from Cloud Storage with caching) so cold starts stay fast.

4. **Frontend parity**  
   React and React Native both hit the same REST API. Backend behavior is identical; efficiency comes from the optimizations above.

5. **Optional: min instances**  
   Set Cloud Run `min-instances > 0` to keep at least one instance warm and avoid cold starts for the first request.

### Remaining Per-Session Firestore Reads

- **Engagements:** One stream (limit 500) per session
- **User:** One document per session
- **Episodes:** None when using in-memory dataset (current setup)

This keeps Firestore usage low and predictable.

---

## 13. Summary

| Finding | Severity | Status |
|---------|----------|--------|
| Double Firestore full scan for `get_episode_by_content_id_map` | **High** | ✅ Fixed |
| Serial data fetches | **High** | ✅ Fixed (parallel with asyncio.gather) |
| Re-fetching full episode catalog from Firestore on every session | **High** | ✅ Fixed (in-memory dataset when available) |
| Network RTT per cloud call (Firestore, Pinecone) | **Medium** | Mitigate with colocation |
| No batching in sessions embedding fetch (ok at ~160 IDs) | **Low** | OK at current scale |
| Architectural gap vs TikTok/X (no precomputation/caching) | **Strategic** | Future work |

**Implemented:** All high-impact optimizations are in place: no double scan, parallel async fetches, in-memory episode catalog when dataset is loaded, Firestore AsyncClient only, Pinecone async fetch.

**Deployment:** Ready for Cloud Run. Colocate with Firestore/Pinecone region; consider `min-instances > 0` to reduce cold starts.
