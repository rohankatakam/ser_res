# Session Flow: POST /api/sessions/create

Step-by-step flow for creating a "For You" recommendation session. See [PINECONE_FIRESTORE_DATA_FLOW.md](PINECONE_FIRESTORE_DATA_FLOW.md) for data source details and [PERFORMANCE_INVESTIGATION_FOR_YOU_LATENCY.md](PERFORMANCE_INVESTIGATION_FOR_YOU_LATENCY.md) for latency analysis.

---

## 1. Request

```
POST /api/sessions/create
{
  "engagements": [...],   // optional; Firestore engagements override when user_id set
  "excluded_ids": [...],  // episodes to exclude from results
  "user_id": "..."        // optional; used for Firestore engagements + user (category_vector)
}
```

---

## 2. Parallel Data Load

The backend fetches in parallel via `asyncio.gather`:

| Task | Source | Description |
|------|--------|-------------|
| `_get_engagements()` | Firestore `users/{uid}/engagements` | Engagements for ranking; limit 500, order by timestamp. If no `user_id`, uses `request.engagements`. |
| `_get_user()` | Firestore `users/{uid}` | User doc (e.g. `category_vector` for cold-start blend). Skipped if no user_id. |
| `_get_episodes()` | In-memory or Firestore | Episode catalog. Prefers in-memory dataset when loaded; otherwise `episode_provider.get_episodes_async(limit=None)`. |

`episode_by_content_id` is built from the episode list (avoids a second Firestore scan).

---

## 3. Exclusions and Embeddings

- **Excluded IDs:** `request.excluded_ids` ∪ engagement episode ids (don’t re-recommend).
- **Embeddings:** If `state.current_embeddings` is empty:
  - `engine.get_candidate_pool_ids()` → candidate episode ids
  - `needed_ids` = engagement episode ids ∪ candidate ids
  - `vector_store.get_embeddings_async(needed_ids)` → Pinecone fetch by id

---

## 4. Recommendation Queue

`engine.create_recommendation_queue()` runs:

1. **Stage A (candidate pool):** Filter episodes by quality gates, freshness, exclusions → ~150 candidates.
2. **Session metadata:** `cold_start = not engagements`; `user_vector_episodes` = min(engagements, user_vector_limit).
3. **Stage B (ranking):**
   - **User vector:** If engagements: mean-pool of engagement embeddings (optionally blended with `category_anchor_vector` at α=0.15). If cold start + category_anchor: use category_anchor.
   - **Blended scoring:** `final_score = weight_sim × similarity + weight_quality × quality + weight_recency × recency`. Cold start: quality + recency only.
   - **Series diversity:** In-processing selection; max 2 per series, no adjacent same series; effective_score = final × (α ** series_count).
4. **Output:** Sorted list of `ScoredEpisode` (top N).

---

## 5. Response

```json
{
  "session_id": "...",
  "episodes": [...],
  "total_in_queue": 10,
  "shown_count": 10,
  "remaining_count": 0,
  "cold_start": false,
  "algorithm": "v1.5",
  "debug": { ... }
}
```

Session is stored in `state.sessions[session_id]` for `load_more` and `engage` calls.

---

## 6. Follow-up Endpoints

- `POST /api/sessions/{id}/next` — Load more from the session queue.
- `POST /api/sessions/{id}/engage` — Record engagement; persists to Firestore when `user_id` is set.
