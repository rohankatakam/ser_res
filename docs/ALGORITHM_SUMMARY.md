# Algorithm Summary

Short reference for the recommendation algorithm's main components. Config is in `algorithm/models/config.py` and `algorithm/config.json`.

---

## Candidate Pool (Stage A)

Pre-filters the episode catalog before ranking.

| Filter | Default | Description |
|--------|---------|-------------|
| `credibility_floor` | 2 | Min credibility score; episodes below are excluded |
| `combined_floor` | 5 | Min (credibility + insight); ensures substantive content |
| `freshness_window_days` | 90 | Only episodes published within this window |
| `excluded_ids` | — | Episode ids to exclude (engaged + request exclusions) |
| `candidate_pool_size` | 150 | Max candidates returned; sorted by quality score |

**Output:** Up to 150 episodes passing quality gates, sorted by quality (credibility-weighted).

---

## User Vector

Represents user interests from engagement embeddings.

| Aspect | Implementation |
|--------|----------------|
| **Input** | Recent engagements (up to `user_vector_limit`, default 10), ordered by timestamp |
| **Computation** | Weighted mean-pool of engagement embeddings. Weights: `engagement_weight_bookmark` (2.0), `engagement_weight_click` (1.0). |
| **Four cases** | 1) No engagements, no categories → None. 2) Engagements, no categories → mean(engagements). 3) No engagements, categories → category_anchor. 4) Engagements + categories → blend. |
| **Category anchor** | Blend: `(1 - α) * engagement_vector + α * category_anchor`. Default `category_anchor_weight` (α) = 0.15. |

---

## Blended Scoring (Stage B)

Per-candidate score (same formula for all four user-state cases): `final = w_sim × similarity + w_quality × quality + w_recency × recency`.

| Default | Formula |
|---------|---------|
| All cases | `0.55 × sim + 0.30 × quality + 0.15 × recency` |

When no user vector (Case 1: no engagements, no categories): similarity = 0.5 (neutral).

- **Similarity:** From Pinecone query when user vector exists; else 0.5.
- **Quality:** Normalized from credibility and insight; capped at `max_quality_score`.
- **Recency:** `exp(-recency_lambda × days_old)`; default `recency_lambda` = 0.03.

---

## Series Diversity (In-Processing)

Applied after scoring, during selection. Ensures variety across series.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `series_penalty_alpha` (α) | 0.7 | Penalty per additional episode from same series |
| `max_episodes_per_series` | 2 | Hard cap; no more than 2 episodes per series |

Consecutive slots cannot be from the same series (always on).

**Effective score:** For each slot, `effective_score = final_score × (α ** series_count[series_id])`. Candidates from series already at the cap are skipped.
