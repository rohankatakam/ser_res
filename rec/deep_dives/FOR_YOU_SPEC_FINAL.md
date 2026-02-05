# Serafis "For You" Feed — Final Specification

> *Single-stream investment intelligence feed with mathematical defensibility.*

**Version:** 1.1 (Revised)  
**Date:** February 3, 2026  
**Status:** Design Complete — Ready for Implementation

> **Note:** See `/rec/deep_dives/` for detailed subsystem documentation.

---

## Executive Summary

A 3-stage recommendation pipeline that transforms raw user signals and episode metadata into a personalized, narrative-aware feed of 10 episodes.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   BASE INPUTS   │ ──▶ │   COMPUTED      │ ──▶ │   FINAL OUTPUT  │
│   (Raw Data)    │     │   SIGNALS       │     │   (10 Episodes) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
     Stage 0                Stage 1 + 2              Stage 3
   Data Layer            Retrieval + Score         Reranking
```

---

## Stage 0: Base Input Parameters

### User Signals

| Parameter | Type | Description | Required |
|-----------|------|-------------|----------|
| `U.viewed_episodes` | List[{episode_id, timestamp}] | Episodes user has viewed | Yes |
| `U.bookmarked_episodes` | List[{episode_id, timestamp}] | Episodes user has saved | Yes |
| `U.excluded_ids` | Set[episode_id] | Viewed + Bookmarked + Not Interested | Yes |
| `U.category_interests` | List[category_name] | Stated topic preferences | Cold start only |
| `U.tracked_entities` | List[entity_id] | Companies/people user follows | **Future (V2)** |
| `U.search_queries` | List[{query, timestamp}] | Recent AI search queries | **Future (V2)** |

### Episode Metadata

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `E.id` | String | — | Unique identifier |
| `E.embedding` | Vector[1536] | — | Pre-computed from key_insight + description |
| `E.Insight` | Float | 1–4 | Novelty and depth of ideas |
| `E.Credibility` | Float | 1–4 | Speaker authority and track record |
| `E.published_at` | DateTime | — | Publication timestamp |
| `E.series_id` | String | — | Parent podcast series |
| `E.Themes` | List[{name, relevance}] | relevance: 0–4 | Topic classifications |
| `E.Entities` | List[{id, name, relevance}] | relevance: 0–4 | Companies/people mentioned |
| `E.non_consensus_level` | Enum | highly_non_consensus, non_consensus, null | Contrarian flag (used for POV) |

### Derived Episode Fields

| Derived Field | Derivation | Rationale |
|---------------|------------|-----------|
| `E.PrimaryTopic` | `max(E.Themes, key=relevance).name` | Highest-signal theme for diversity tracking |
| `E.PrimaryEntity` | `max(E.Entities, key=relevance).id` | Highest-signal entity for adjacency penalty |
| `E.DaysOld` | `(now - E.published_at).days` | For freshness decay |
| `E.POV` | Binary classification (see below) | For narrative balancing (Contrarian/Consensus) |

---

## Stage 0.5: POV Derivation

POV uses **binary classification** (Contrarian vs Consensus) based on the most reliable signal:

```
┌─────────────────────────────────────────────────────────────────┐
│                     POV CLASSIFICATION                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  IF E.non_consensus_level ∈ {highly_non_consensus, non_consensus}
│     → POV = "Contrarian"                                        │
│                                                                  │
│  ELSE                                                           │
│     → POV = "Consensus"                                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

| POV Value | Definition |
|-----------|------------|
| Contrarian | Challenges conventional wisdom; non-consensus views |
| Consensus | Aligns with mainstream views; informational content |

> **V2 Enhancement:** Sentiment-based POV (Bullish/Bearish/Neutral) deferred — see deep_dives/08_FUTURE_ENHANCEMENTS.md

---

## Stage 1: Computed Signals — User Embedding

### User Research Vector (V_activity)

**Purpose:** Represents user's research interests based on consumption history.

```
V_activity = Σ(weight_i × embedding_i) / Σ(weight_i)

Where:
  weight_i = interaction_weight × recency_weight
  interaction_weight = 2.0 if bookmarked, 1.0 if viewed
  recency_weight = exp(-0.05 × days_since_interaction)
```

| Parameter | Default | Tunable? | Rationale |
|-----------|---------|----------|-----------|
| Bookmark weight | 2.0 | ⚙️ Yes | Bookmarks are explicit, stronger signal |
| View weight | 1.0 | 🔒 Fixed | Baseline interaction |
| Recency decay (λ_user) | 0.05 | ⚙️ Yes | ~14 days half-life for user interests |
| Max episodes considered | 10 | ⚙️ Yes | Recent activity most relevant |

### Cold Start Fallback

```
IF |U.viewed_episodes| + |U.bookmarked_episodes| == 0:
    IF |U.category_interests| > 0:
        V_activity = Embed(join(U.category_interests))
    ELSE:
        V_activity = null  // Use global quality ranking
```

---

## Stage 2: Computed Signals — Episode Scoring

### 2.1 Hard Quality Filters (Safety Gates)

```
┌─────────────────────────────────────────────────────────────────┐
│                    QUALITY GATES                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Gate 1: Credibility Floor                                      │
│  ─────────────────────────                                      │
│  IF E.Credibility < 2 → REJECT                                  │
│                                                                  │
│  Gate 2: Combined Signal Floor                                  │
│  ────────────────────────────                                   │
│  IF (E.Credibility + E.Insight) < 5 → REJECT                    │
│                                                                  │
│  Gate 3: Exclusion Filter                                       │
│  ────────────────────────                                       │
│  IF E.id ∈ U.excluded_ids → REJECT                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

| Gate | Threshold | Tunable? | Rationale |
|------|-----------|----------|-----------|
| Credibility Floor | ≥ 2 | 🔒 Fixed | No unverified sources for investors |
| Combined Floor | ≥ 5 | ⚙️ Yes | Ensures minimum total quality |

**Mathematical Guarantee:** An episode with (C=1, I=4) fails Gate 1. An episode with (C=2, I=2) fails Gate 2. Only (C≥2 AND C+I≥5) passes both.

### 2.2 Scoring Components (3 Components)

#### S_sim — Semantic Similarity (Weight: 50%)

```
IF V_activity is not null:
    S_sim = CosineSim(V_activity, E.embedding)
ELSE:
    S_sim = 0.5  // Neutral for cold start
```

| Property | Value |
|----------|-------|
| Range | [0, 1] (cosine similarity) |
| Cold start default | 0.5 |
| Tunable? | 🔒 Fixed (weight tunable) |

#### S_alpha — Signal Quality (Weight: 35%)

```
S_alpha = (W_insight × E.Insight + W_cred × E.Credibility) / 4.0
```

| Parameter | Default | Tunable? | Rationale |
|-----------|---------|----------|-----------|
| W_insight | 0.5 | ⚙️ Yes | Balanced V1, may favor insight later |
| W_cred | 0.5 | ⚙️ Yes | Balanced V1, may favor credibility later |
| Normalizer | 4.0 | 🔒 Fixed | Max score is 4, normalizes to [0,1] |

**Range:** [0.25, 1.0] after passing quality gates.

> **V2 Enhancement:** S_entity (Entity Alignment) deferred — requires explicit entity tracking feature. See deep_dives/08_FUTURE_ENHANCEMENTS.md

#### S_fresh — Freshness (Weight: 15%)

```
S_fresh = max(FLOOR, exp(-λ × E.DaysOld))
```

| Parameter | Default | Tunable? | Rationale |
|-----------|---------|----------|-----------|
| λ (decay rate) | 0.03 | ⚙️ Yes | ~23 days half-life, preserves timeless content |
| FLOOR | 0.10 | ⚙️ Yes | Evergreen content stays discoverable |

**Decay Curve:**

| Days Old | S_fresh (λ=0.03) |
|----------|------------------|
| 0 | 1.00 |
| 7 | 0.81 |
| 14 | 0.66 |
| 30 | 0.41 |
| 60 | 0.17 |
| 90+ | 0.10 (floor) |

### 2.3 Base Score Formula

```
BaseScore = (S_sim × W_sim) + (S_alpha × W_alpha) + (S_fresh × W_fresh)
```

| Weight | Symbol | Default | Tunable? | Rationale |
|--------|--------|---------|----------|-----------|
| Similarity | W_sim | 0.50 | ⚙️ Yes | Primary personalization signal |
| Signal Quality | W_alpha | 0.35 | ⚙️ Yes | Serafis differentiation |
| Freshness | W_fresh | 0.15 | ⚙️ Yes | Feed currency |

**Constraint:** W_sim + W_alpha + W_fresh = 1.0

**BaseScore Range:** [0, 1] — proven by all components being [0,1] and weights summing to 1.

---

## Stage 3: Narrative Reranking

### 3.1 Reranking Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `SeriesTracker` | Map[series_id → count] | Episodes per series in final feed |
| `TopicTracker` | Map[topic → count] | Episodes per topic in final feed |
| `GlobalEntityTracker` | Map[entity → count] | Episodes per primary entity in final feed |
| `LastEntity` | entity_id | Previous episode's primary entity |
| `LastPOV` | Enum | Previous episode's POV (Contrarian/Consensus) |

### 3.2 Adjustment Multipliers

```
┌─────────────────────────────────────────────────────────────────┐
│                  RERANKING ADJUSTMENTS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  HARD CAPS (Score = 0)                                          │
│  ─────────────────────                                          │
│  Series Limit:    IF SeriesTracker[E.series_id] ≥ 2             │
│                   → TempScore = 0                               │
│                                                                  │
│  PENALTIES (Score Reduction)                                    │
│  ──────────────────────────                                     │
│  Adjacency:       IF E.PrimaryEntity == LastEntity              │
│                   → TempScore × 0.80                            │
│                                                                  │
│  Topic Saturation: IF TopicTracker[E.PrimaryTopic] ≥ 2          │
│                   → TempScore × 0.85                            │
│                                                                  │
│  Entity Saturation: IF GlobalEntityTracker[E.PrimaryEntity] ≥ 3 │
│                   → TempScore × 0.70                            │
│                                                                  │
│  BOOSTS (Score Increase)                                        │
│  ────────────────────────                                       │
│  Contrarian Boost: IF LastPOV == "Consensus"                    │
│                    AND E.POV == "Contrarian"                    │
│                    → TempScore × 1.15                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

| Multiplier | Default | Tunable? | Rationale |
|------------|---------|----------|-----------|
| Series hard cap | 2 | ⚙️ Yes | Prevent single podcast dominance |
| Adjacency penalty | 0.80 | ⚙️ Yes | Encourage entity variety |
| Topic saturation penalty | 0.85 | ⚙️ Yes | Encourage topic variety |
| Entity saturation threshold | 3 | ⚙️ Yes | Prevent single-entity dominance |
| Entity saturation penalty | 0.70 | ⚙️ Yes | Strong discouragement for entity repetition |
| Contrarian boost | 1.15 | ⚙️ Yes | Surface opposing viewpoints |

### 3.3 Re-Selection Algorithm

**Strategy:** At each slot, recompute adjusted scores for all remaining candidates and select the highest.

```
┌─────────────────────────────────────────────────────────────────┐
│                 RE-SELECTION LOOP                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUT: CandidateList (Top 50 by BaseScore)                     │
│  OUTPUT: FinalFeed (10 episodes)                                │
│                                                                  │
│  Initialize:                                                    │
│    FinalFeed = []                                               │
│    SeriesTracker = {}                                           │
│    TopicTracker = {}                                            │
│    GlobalEntityTracker = {}                                     │
│    LastEntity = null                                            │
│    LastPOV = null                                               │
│                                                                  │
│  WHILE |FinalFeed| < 10 AND |CandidateList| > 0:                │
│                                                                  │
│    1. FOR EACH E in CandidateList:                              │
│         AdjustedScore = E.BaseScore                             │
│         Apply penalties/boosts based on current state           │
│         E.TempScore = AdjustedScore                             │
│                                                                  │
│    2. Sort CandidateList by TempScore DESC                      │
│                                                                  │
│    3. Winner = CandidateList[0]                                 │
│       Remove Winner from CandidateList                          │
│                                                                  │
│    4. IF Winner.TempScore == 0: BREAK                           │
│                                                                  │
│    5. Append Winner to FinalFeed                                │
│       Update SeriesTracker, TopicTracker, GlobalEntityTracker,  │
│       LastEntity, LastPOV                                       │
│                                                                  │
│  RETURN FinalFeed                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Complexity:** O(k × n) where k=10 (output size), n=50 (candidates). Acceptable for real-time.

---

## End-to-End Traceability

### Complete Score Flow

```
Raw Episode E
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ GATE 1: E.Credibility ≥ 2?                                      │
│         NO → REJECT                                             │
│         YES ↓                                                   │
├─────────────────────────────────────────────────────────────────┤
│ GATE 2: (E.Credibility + E.Insight) ≥ 5?                        │
│         NO → REJECT                                             │
│         YES ↓                                                   │
├─────────────────────────────────────────────────────────────────┤
│ GATE 3: E.id ∉ U.excluded_ids?                                  │
│         NO → REJECT                                             │
│         YES ↓                                                   │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ COMPUTE BASE SCORE                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  S_sim    = CosineSim(V_activity, E.embedding)      ∈ [0,1]     │
│  S_alpha  = (0.5×I + 0.5×C) / 4.0                   ∈ [0.25,1]  │
│  S_fresh  = max(0.1, exp(-0.03 × days))            ∈ [0.1,1]   │
│                                                                  │
│  BaseScore = 0.50×S_sim + 0.35×S_alpha + 0.15×S_fresh ∈ [0,1]  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ TOP 50 BY BASE SCORE                                            │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ RERANKING (10 iterations)                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Iteration i:                                                   │
│    TempScore = BaseScore                                        │
│    IF series_count ≥ 2:        TempScore = 0                    │
│    IF same entity as prev:     TempScore × 0.80                 │
│    IF topic_count ≥ 2:         TempScore × 0.85                 │
│    IF entity_count ≥ 3:        TempScore × 0.70                 │
│    IF consensus→contrarian:    TempScore × 1.15                 │
│                                                                  │
│    Select max(TempScore), update state                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ FINAL OUTPUT: 10 Episodes                                       │
│ Ordered by selection sequence (narrative flow)                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Parameter Summary

### Fixed Parameters (Robust, No Tuning)

| Parameter | Value | Justification |
|-----------|-------|---------------|
| Credibility Floor | ≥ 2 | Investor safety — non-negotiable |
| View weight | 1.0 | Baseline, other weights relative to this |
| Score normalizer | 4.0 | Max possible score |
| Weight sum | 1.0 | Mathematical constraint |

### Tunable Parameters (Require Testing)

| Parameter | Default | Range | Priority |
|-----------|---------|-------|----------|
| Combined Floor | 5 | 4–6 | Medium |
| Bookmark weight | 2.0 | 1.5–3.0 | Low |
| λ_user (user recency) | 0.05 | 0.03–0.10 | Medium |
| λ_fresh (content freshness) | 0.03 | 0.02–0.05 | Medium |
| Freshness floor | 0.10 | 0.05–0.20 | Low |
| W_sim | 0.50 | 0.40–0.60 | High |
| W_alpha | 0.35 | 0.25–0.45 | High |
| W_fresh | 0.15 | 0.10–0.20 | Low |
| W_insight (in alpha) | 0.5 | 0.4–0.6 | Medium |
| Series cap | 2 | 1–3 | Low |
| Adjacency penalty | 0.80 | 0.70–0.90 | Medium |
| Topic penalty | 0.85 | 0.75–0.90 | Medium |
| Entity saturation threshold | 3 | 2–4 | Medium |
| Entity saturation penalty | 0.70 | 0.60–0.80 | Medium |
| Contrarian boost | 1.15 | 1.10–1.25 | Medium |
| Session timeout | 30 min | 15–60 min | Low |

---

## Session & Batch Behavior

### Session Definition

A **session** is a continuous period of app usage. State resets when:
- User closes the app, OR
- 30 minutes of inactivity

### Batch Loading

| Event | Behavior |
|-------|----------|
| Initial load | Generate 10 episodes, initialize state |
| User requests more | Generate next 10 using **persisted** state |
| Session expires | Reset all state, start fresh |

**State Persistence:** SeriesTracker, TopicTracker, GlobalEntityTracker, LastEntity, LastPOV carry over between batches within a session. This ensures batch 2 doesn't repeat series/topics/entities from batch 1.

---

## Cold Start Behavior

| User State | V_activity | Scoring Behavior |
|------------|------------|------------------|
| No activity, no interests | null | S_sim = 0.5, rely on S_alpha |
| Has category interests | Embed(interests) | Normal flow |
| Has 1-2 views | WeightedMean of views | Normal flow |
| Has 3+ views | Full embedding | Normal flow |

---

## Mathematical Guarantees

| Property | Guarantee | Proof |
|----------|-----------|-------|
| BaseScore ∈ [0, 1] | All components ∈ [0,1], weights sum to 1 | Convex combination |
| No low-credibility content | Gate 1 rejects C < 2 | Hard filter |
| No viewed/bookmarked repeats | Gate 3 rejects excluded_ids | Hard filter |
| Max 2 per series | Reranking sets TempScore = 0 | Hard cap |
| Diversity in output | Penalties reduce same-entity/topic scores | Soft pressure |
| Entity diversity | GlobalEntityTracker caps at 3 | Soft penalty |
| Narrative balance | Contrarian boost after consensus | Explicit boost |

---

## Future Enhancements (V2)

> See `deep_dives/08_FUTURE_ENHANCEMENTS.md` for full specifications.

| Feature | Priority | Dependency |
|---------|----------|------------|
| S_entity (Entity Alignment) | P1 | Explicit entity tracking feature |
| Search query signal (U_search) | P1 | Query logging infrastructure |
| Sentiment-based POV | P2 | LLM sentiment model tuning |
| Velocity Bypass (Breaking News) | P2 | Velocity tracking infrastructure |
| Dual freshness decay | P3 | Content type classification |
| Vector clustering (Anti-grey-sludge) | P4 | Power user base |

---

## Appendix: Example Score Calculation

**User:**
- Viewed 5 AI episodes (V_activity computed)
- No exclusions

**Episode:**
- Insight: 4, Credibility: 3
- DaysOld: 10
- Entities: {Nvidia, Google, Microsoft}
- PrimaryTopic: "AI & Machine Learning"
- POV: Contrarian

**Gate Checks:**
- Gate 1: 3 ≥ 2 ✓
- Gate 2: 3 + 4 = 7 ≥ 5 ✓
- Gate 3: Not excluded ✓

**Score Components:**
- S_sim = 0.82 (high similarity to user's AI interests)
- S_alpha = (0.5 × 4 + 0.5 × 3) / 4.0 = 0.875
- S_fresh = max(0.10, exp(-0.03 × 10)) = 0.74

**BaseScore:**
```
= (0.82 × 0.50) + (0.875 × 0.35) + (0.74 × 0.15)
= 0.410 + 0.306 + 0.111
= 0.827
```

**Reranking:**
- If previous episode was also about Nvidia: 0.827 × 0.80 = 0.662
- If previous was Consensus and this is Contrarian: 0.827 × 1.15 = 0.951
- If this is the 4th Nvidia episode: 0.827 × 0.70 = 0.579

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 0.1 | Jan 29, 2026 | Initial 4-section approach |
| 0.5 | Jan 29, 2026 | Pivot to single For You feed |
| 0.8 | Jan 29, 2026 | Added embeddings, quality floor |
| 0.9 | Jan 29, 2026 | Academic review, 3-stage pipeline |
| 1.0 | Jan 29, 2026 | Final spec with all fixes |
| 1.1 | Feb 3, 2026 | Deep dive alignment: removed S_entity (V2), simplified POV to binary, added GlobalEntityTracker, updated weights (50/35/15) |
