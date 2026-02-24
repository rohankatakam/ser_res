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
| **Computation** | Mean-pool of engagement episode embeddings. Optional: weighted by `engagement_weights` (bookmark=2.0, listen=1.5, click=1.0). |
| **Cold start** | If no engagements: returns `None`; ranking uses cold-start weights. If `category_anchor_vector` provided: returns that as user vector (or blend with engagement vector). |
| **Category anchor** | Blend: `(1 - α) * engagement_vector + α * category_anchor`. Default `category_anchor_weight` (α) = 0.15. |

---

## Blended Scoring (Stage B)

Per-candidate score: `final = w_sim × similarity + w_quality × quality + w_recency × recency`.

| Mode | Formula |
|------|---------|
| **Personalized** | `0.55 × sim + 0.30 × quality + 0.15 × recency` |
| **Cold start** | `0.60 × quality + 0.40 × recency` (no similarity) |

- **Similarity:** Cosine similarity of candidate embedding vs user vector (mean-pool of engagement embeddings).
- **Quality:** Normalized from credibility and insight; capped at `max_quality_score`.
- **Recency:** `exp(-recency_lambda × days_old)`; default `recency_lambda` = 0.03.

---

## Series Diversity (In-Processing)

Applied after scoring, during selection. Ensures variety across series.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `series_penalty_alpha` (α) | 0.7 | Penalty per additional episode from same series |
| `max_episodes_per_series` | 2 | Hard cap; no more than 2 episodes per series |
| `no_adjacent_same_series` | true | Consecutive slots cannot be from the same series |

**Effective score:** For each slot, `effective_score = final_score × (α ** series_count[series_id])`. Candidates from series already at the cap are skipped.
