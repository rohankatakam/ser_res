# Similarity and Embedding Fallbacks

Locations where we use fallback logic instead of Pinecone query. Logged with `[sim_fallback]` for verification.

**Note:** Cold start (no user_vector) is an edge case, not a fallback; it uses quality + recency only.

## Ranking Core (`algorithm/stages/ranking/core.py`)

| Location | Condition | Fallback | Log tag |
|----------|-----------|----------|---------|
| ~60 | similarity_by_id provided but ep_id/content_id not in map | sim_score=0.5 | `SIMILARITY_MISSING_IN_QUERY_RESULTS` |
| ~67 | Fetch path: no Pinecone query results | sim_score=0.5 | `SIMILARITY_FETCH_PATH_NO_PINECONE` (when missing ep_emb or user_vec) |

## Session Route (`server/routes/sessions.py`)

| Location | Condition | Fallback | Log tag |
|----------|-----------|----------|---------|
| ~175 | user_vector is None | Fetch path instead of query | `SESSION_USER_VECTOR_NONE_FETCH_PATH` |
| ~179 | vector_store has no query_async | Fetch path instead of query | `SESSION_NO_QUERY_ASYNC` |

## User Vector (`algorithm/stages/ranking/user_vector.py`)

| Location | Condition | Fallback | Log tag |
|----------|-----------|----------|---------|
| 61-64 | no engagement_vector, no use_anchor | return None | `USER_VECTOR_NONE_NO_ANCHOR` |
| 72-74 | len(eng_arr) != len(anc_arr) | return engagement_vector (no blend) | `USER_VECTOR_DIM_MISMATCH` |

## Engagement Embeddings (`algorithm/stages/ranking/engagement_embeddings.py`)

| Location | Condition | Fallback | Log tag |
|----------|-----------|----------|---------|
| 41-43 | embedding not found for engagement | skip engagement (not in user vector) | `ENGAGEMENT_EMBEDDING_SKIPPED` |

---

**Verification:** Run backend with logging, trigger For You sessions (with/without engagements, cold start, etc.), then `grep "sim_fallback"` in logs. If no hits, all paths use Pinecone query.
