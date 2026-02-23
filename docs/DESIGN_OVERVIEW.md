# rec_engine Design Overview

High-level architecture for the "For You" recommendation engine. Single source of truth for session flow, data flow, and key algorithms.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     POST /api/sessions/create                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐   │
│  │  Load data  │───▶│ Candidate   │───▶│   Ranking   │───▶│ Series          │   │
│  │  (parallel) │    │   Pool      │    │  (blended   │    │ Diversity       │   │
│  │             │    │  Stage A    │    │  scoring)   │    │ (in-processing) │   │
│  └─────────────┘    └─────────────┘    └─────────────┘    └────────┬────────┘   │
│        │                    │                  │                      │          │
│        ▼                    │                  │                      ▼          │
│  ┌─────────────┐            │                  │              ┌─────────────┐    │
│  │ user_vector │────────────┴──────────────────┘              │   Top 10    │    │
│  │ (cold start │                                               └─────────────┘    │
│  │  or mean)   │                                                                    │
│  └─────────────┘                                                                    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Flow:** Create session → load user, engagements, episodes (parallel) → compute user_vector → candidate pool (quality + freshness) → blended scoring → series diversity (max 2/series, no adjacent same) → return top 10.

---

## Data Flow

| Source | Data | When |
|--------|------|------|
| **Firestore** | Episodes, series, users | `DATA_SOURCE=firebase` |
| **Firestore** | Engagements | `users/{user_id}/engagements` |
| **Pinecone** | Episode embeddings | Fetched by episode id (no full load) |
| **In-memory** | Catalog, embeddings cache | Dataset or preloaded embeddings |

- Episode document id in Firestore = Pinecone vector id (must match for fetch by id).
- Namespace: `{algorithm_version}_s{strategy_version}__{dataset_version}`.

See [PINECONE_FIRESTORE_DATA_FLOW.md](PINECONE_FIRESTORE_DATA_FLOW.md) for details.

---

## Key Algorithms

| Component | Description | Key params |
|-----------|-------------|------------|
| **Cold start** | No engagements: score = quality + recency only. Category anchor blend α=0.15 when user has interests. | `category_anchor_weight=0.15` |
| **User vector** | Mean-pool of engagement embeddings (up to `user_vector_limit`). Optional weighted by engagement type (bookmark, listen, click). | `user_vector_limit=10` |
| **Candidate pool** | Quality gates (credibility ≥ floor, combined floor), freshness window (90 days), exclusions. | `candidate_pool_size=150` |
| **Blended scoring** | `final = weight_sim × sim + weight_quality × quality + weight_recency × recency`. Cold start: quality + recency only. | Weights from `RecommendationConfig` |
| **Series diversity** | In-processing selection: `effective_score = final × (α ** series_count)`. Max 2 per series, no adjacent same series. | `series_penalty_alpha=0.7`, `max_episodes_per_series=2` |

---

## References

- [PINECONE_FIRESTORE_DATA_FLOW.md](PINECONE_FIRESTORE_DATA_FLOW.md) — Embedding fetch, namespace, populate script
- [phase7_evolution/01_ARCHITECTURE_OVERVIEW.md](phase7_evolution/01_ARCHITECTURE_OVERVIEW.md) — Detailed Stage A/B, scoring formulas
- [SESSION_FLOW.md](SESSION_FLOW.md) — Step-by-step session create flow
- [ALGORITHM_SUMMARY.md](ALGORITHM_SUMMARY.md) — Algorithm details
