# Algorithm Refactor — Modular Layout

The `algorithm/` package is split into **models**, **utils**, and **stages** so each concern lives in one place and the pipeline is easy to follow.

---

## Layout

```
algorithm/
├── __init__.py              # Re-exports public API (create_recommendation_queue, get_embed_text, etc.)
├── manifest.json
├── config.json
├── config_schema.json
├── embedding_strategy.py    # Unchanged: get_embed_text, STRATEGY_VERSION, EMBEDDING_*
├── computed_params.py       # Unchanged: compute_parameters()
├── recommendation_engine.py # Thin facade: adds algo dir to path, re-exports from models/ and stages/
├── models/                  # Data structures and config
│   ├── __init__.py
│   ├── config.py            # RecommendationConfig, DEFAULT_CONFIG, from_dict()
│   ├── scoring.py           # ScoredEpisode
│   └── session.py           # RecommendationSession
├── utils/                   # Shared helpers (no I/O)
│   ├── __init__.py
│   ├── scores.py            # days_since(), quality_score(), recency_score()
│   ├── similarity.py        # cosine_similarity()
│   └── episode.py          # get_episode_primary_category()
└── stages/                  # Pipeline stages
    ├── __init__.py
    ├── candidate_pool.py    # Stage A: get_candidate_pool()
    ├── ranking/              # Stage B: core (rank_candidates), get_badges; submodules: user_vector, similarity, blended_scoring, cold_start, badges
    └── queue.py             # create_recommendation_queue() — runs Stage A then Stage B
```

---

## Responsibilities

| Area | Responsibility |
|------|----------------|
| **models/** | Config and data classes only. No business logic. |
| **utils/** | Pure functions: scores, similarity, episode metadata. Used by both stages. |
| **stages/candidate_pool** | Stage A: quality/freshness gates, sort by quality, cap pool size. |
| **stages/ranking** | Stage B: user vector, similarity (mean-pool or sum-of-sim), quality/recency blend, cold start, category diversity, badges. |
| **stages/queue** | Orchestration: call Stage A, then Stage B, return queue + cold_start + user_vector_episodes. |
| **recommendation_engine.py** | Ensures algorithm dir is on `sys.path`, then re-exports from models and stages so existing imports (server, evaluation) keep working. |

---

## Imports and loader

- **As a package** (e.g. `from algorithm import create_recommendation_queue`): the algorithm directory is the package root; `recommendation_engine.py` adds it to `sys.path` and imports `models.*`, `stages.*`.
- **Via AlgorithmLoader** (server): the loader loads `recommendation_engine.py` by path; that file adds its parent dir to `sys.path` and then imports `models` and `stages`, so submodules resolve correctly. No change to the loader is required.

---

## Public API (unchanged)

- `create_recommendation_queue(engagements, excluded_ids, episodes, embeddings, episode_by_content_id, config)`
- `RecommendationConfig`, `RecommendationConfig.from_dict()`, `DEFAULT_CONFIG`
- `ScoredEpisode`, `RecommendationSession`
- `get_candidate_pool()`, `rank_candidates()`, `get_badges()`
- `get_embed_text()`, `STRATEGY_VERSION`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS` (from `embedding_strategy.py`)

All of these are still available from `algorithm` and from the engine module returned by the loader.
