# Deep Dive 01: Data Model & Input Layer

> *Foundation layer defining all raw inputs to the "For You" recommendation pipeline.*

**Document:** 1 of 8  
**Subsystem:** Data Model & Input Layer  
**Pipeline Stage:** Stage 0 (Base Inputs)  
**Status:** Final

---

## 1. Purpose

This document defines the **complete data schema** for the "For You" recommendation system. It serves as the canonical reference for:

- All user signal parameters (U.*)
- All episode metadata parameters (E.*)
- Derived fields computed from raw data
- Data relationships and dependencies

Every downstream subsystem (User Embedding, Scoring, Reranking) consumes data defined here.

---

## 2. System Context

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA MODEL LAYER                             │
│                     (This Document)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐         ┌─────────────────────┐               │
│   │  User Data  │         │   Episode Catalog   │               │
│   │    (U.*)    │         │       (E.*)         │               │
│   └──────┬──────┘         └──────────┬──────────┘               │
│          │                           │                          │
│          └───────────┬───────────────┘                          │
│                      │                                          │
│                      ▼                                          │
│          ┌───────────────────────┐                              │
│          │    Derived Fields     │                              │
│          │  (Computed at runtime)│                              │
│          └───────────────────────┘                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Stage 1: User      │
                    │  Embedding          │
                    │  (Document 02)      │
                    └─────────────────────┘
```

---

## 3. User Data Model (U.*)

User data captures behavioral signals and explicit preferences that drive personalization.

### 3.1 Core User Fields

| Field Name | Type | Required | Description |
|------------|------|----------|-------------|
| `id` | String | Yes | Unique user identifier |
| `name` | String | No | Display name (not used in recommendation) |
| `category_interests` | List[String] | No | User-selected topic preferences during onboarding (e.g., "Technology & AI", "Crypto & Web3") |
| `subscribed_series` | List[String] | No | Series IDs the user has explicitly followed |
| `seen_episode_ids` | List[String] | Yes | Episode IDs the user has viewed (implicit signal) |
| `bookmarked_episode_ids` | List[String] | Yes | Episode IDs the user has explicitly saved (explicit signal) |
| `not_interested_ids` | List[String] | Yes | Episode IDs the user has dismissed |

### 3.2 Computed User Fields

These fields are derived at recommendation time from core user data.

| Derived Field | Derivation | Used In |
|---------------|------------|---------|
| `U.viewed_episodes` | Join `seen_episode_ids` with episode metadata + timestamps | Stage 1: User Embedding |
| `U.bookmarked_episodes` | Join `bookmarked_episode_ids` with episode metadata + timestamps | Stage 1: User Embedding |
| `U.excluded_ids` | Union of `seen_episode_ids` ∪ `bookmarked_episode_ids` ∪ `not_interested_ids` | Stage 2: Gate 3 |

**Future Enhancement: Entity Tracking**

> Explicit entity tracking (`U.tracked_entities`) is not currently a product feature. When/if the app adds a "Follow Company" or "Follow Person" feature, this would enable an additional scoring component (S_entity) that boosts episodes mentioning tracked entities. See Document 08 for the full S_entity specification.

### 3.3 User Data Example

```json
{
  "id": "user_prosumer_ai",
  "name": "AI Prosumer",
  "category_interests": [
    "Technology & AI",
    "Startups, Growth & Founder Journeys"
  ],
  "subscribed_series": [
    "dwarkesh-podcast-6fptkm",
    "training-data-by-m3369e",
    "invest-like-the--j397bp"
  ],
  "seen_episode_ids": [],
  "bookmarked_episode_ids": [],
  "not_interested_ids": []
}
```

### 3.4 User State Categories

| User State | Condition | Recommendation Behavior |
|------------|-----------|------------------------|
| **Cold Start (No Activity)** | `seen_episode_ids` = [] AND `bookmarked_episode_ids` = [] AND `category_interests` = [] | Rely on S_alpha (quality) only; S_sim = 0.5 |
| **Cold Start (Onboarded)** | `seen_episode_ids` = [] AND `bookmarked_episode_ids` = [] AND `category_interests` ≠ [] | Embed category interests for V_activity |
| **Light User** | 1-2 views | Weighted mean of available embeddings |
| **Active User** | 3+ views | Full weighted embedding computation |
| **Power User** | 100+ views | Monitor for "grey sludge" (V2 consideration) |

---

## 4. Episode Data Model (E.*)

Episode data is pre-computed and stored in the catalog. The recommendation system reads this data; it does not modify it.

### 4.1 Core Episode Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `id` | String | Unique episode identifier (Firebase-style, e.g., "B7d9XwUOKOuoH7R8Tnzi") |
| `content_id` | String | Slug-style identifier for URL routing |
| `title` | String | Episode title |
| `published_at` | ISO DateTime | Publication timestamp (e.g., "2026-01-29T09:00:00+00:00") |
| `content_type` | String | Always "podcast_episodes" for current corpus |

### 4.2 Series Information

| Field Name | Type | Description |
|------------|------|-------------|
| `series.id` | String | Unique series identifier |
| `series.name` | String | Display name of the podcast series |

### 4.3 Quality Scores

These are pre-computed by Serafis's intelligence pipeline (LLM-based analysis).

| Field Name | Type | Range | Description |
|------------|------|-------|-------------|
| `scores.insight` | Integer | 1–4 | Novelty and depth of ideas presented |
| `scores.credibility` | Integer | 1–4 | Speaker authority and track record |
| `scores.information` | Integer | 1–4 | Specificity and data density |
| `scores.entertainment` | Integer | 1–4 | Engagement and storytelling quality |

**Score Interpretation:**

| Score | Meaning |
|-------|---------|
| 4 | Exceptional — top tier |
| 3 | Strong — above average |
| 2 | Adequate — meets baseline |
| 1 | Weak — below standard |

### 4.4 Category Classification

| Field Name | Type | Description |
|------------|------|-------------|
| `categories.major` | List[String] | High-level thematic buckets (e.g., "Technology & AI", "Venture & Private Markets") |
| `categories.subcategories` | List[String] | Granular topic tags |

### 4.5 Entity Mentions

| Field Name | Type | Description |
|------------|------|-------------|
| `entities` | List[Entity] | Organizations mentioned in the episode |
| `entities[].name` | String | Entity name (e.g., "OpenAI", "Google") |
| `entities[].relevance` | Integer (0–4) | How central this entity is to the episode |
| `entities[].context` | String | Summary of how the entity is discussed |

### 4.6 People Mentions

| Field Name | Type | Description |
|------------|------|-------------|
| `people` | List[Person] | Individuals mentioned or featured |
| `people[].name` | String | Person's name |
| `people[].relevance` | Integer (0–4) | How central this person is to the episode |
| `people[].context` | String | Summary of person's role in discussion |
| `people[].title` | String | Role/position (e.g., "CEO of OpenAI") |

### 4.7 Critical Views (POV Source)

This nested object contains the LLM-generated analysis used for POV derivation.

| Field Name | Type | Description |
|------------|------|-------------|
| `critical_views` | Object \| null | Container for contrarian analysis (null if not computed) |
| `critical_views.non_consensus_level` | Enum | "highly_non_consensus", "non_consensus", or absent |
| `critical_views.has_critical_views` | Boolean | Whether contrarian views were detected |
| `critical_views.new_ideas_summary` | String | Full contrarian analysis with "Overall Assessment" |
| `critical_views.key_insights` | String | Top 3 structured takeaways (used for sentiment) |

**Example `new_ideas_summary` (truncated):**
```
"Contrarian Insights Analysis\n\nThis episode contains 2-3 genuinely 
contrarian insights...\n\nOverall Assessment: Highly Non-Consensus\n\n
This episode presents genuinely contrarian thinking..."
```

### 4.8 Search & Scoring Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `search_relevance_score` | Float (0–1) | Pre-computed relevance for search ranking |
| `aggregate_score` | Float \| null | Pre-computed composite score (if available) |
| `top_in_categories` | List[String] | Categories where this episode ranks highly |
| `key_insight` | String | **Legacy field** — often contains entity context; use `critical_views.key_insights` instead |

### 4.9 Episode Embedding

| Field Name | Type | Description |
|------------|------|-------------|
| `embedding` | Vector[1536] | Pre-computed from episode content (key_insights + description) |

---

## 5. Derived Episode Fields

These fields are computed at recommendation time from raw episode data.

| Derived Field | Computation | Used In |
|---------------|-------------|---------|
| `E.DaysOld` | `(now - E.published_at).days` | Stage 2: S_fresh |
| `E.PrimaryTopic` | `max(E.categories.major, key=frequency)` or first element | Stage 3: TopicTracker |
| `E.PrimaryEntity` | `max(E.entities, key=relevance).name` | Stage 3: Adjacency penalty, GlobalEntityTracker |
| `E.POV` | Binary classification: Contrarian if `non_consensus_level` exists, else Consensus (see Document 06) | Stage 3: Contrarian boost |

### 5.1 DaysOld Calculation

```python
from datetime import datetime, timezone

def compute_days_old(published_at: str) -> int:
    pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    return (now - pub_date).days
```

### 5.2 PrimaryTopic Extraction

```python
def get_primary_topic(episode: dict) -> str | None:
    major_categories = episode.get('categories', {}).get('major', [])
    if major_categories:
        return major_categories[0]  # First category is typically highest relevance
    return None
```

### 5.3 PrimaryEntity Extraction

```python
def get_primary_entity(episode: dict) -> str | None:
    entities = episode.get('entities', [])
    if not entities:
        return None
    # Sort by relevance descending, return highest
    sorted_entities = sorted(entities, key=lambda e: e.get('relevance', 0), reverse=True)
    return sorted_entities[0].get('name')
```

---

## 6. Series Data Model

Series data provides metadata about podcast sources.

| Field Name | Type | Description |
|------------|------|-------------|
| `id` | String | Unique series identifier |
| `name` | String | Display name |
| `popularity` | Integer (0–100) | Popularity score |
| `serafis_score` | Integer (0–100) | Serafis quality rating |
| `tier_label` | String | Percentile tier (e.g., "Top 5%", "Top 0.1%") |
| `is_curated` | Boolean | Whether editorially selected |
| `publisher_type` | String | Source type (e.g., "Content Creator", "Investor - VC") |
| `episode_count` | Integer | Number of episodes in series |

**Note:** Series data is used for:
- Series cap enforcement (max 2 per series in feed)
- Future: Series quality weighting

---

## 7. Data Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                     DATA RELATIONSHIPS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User ──────────────────────────────────────────┐               │
│    │                                            │               │
│    ├── seen_episode_ids ──────────┐             │               │
│    ├── bookmarked_episode_ids ────┼──▶ Episode  │               │
│    ├── not_interested_ids ────────┘     │       │               │
│    │                                    │       │               │
│    └── subscribed_series ──────────────▶│Series │               │
│                                         │   │   │               │
│                                         │   │   │               │
│  Episode ◀──────────────────────────────┘   │   │               │
│    │                                        │   │               │
│    ├── series.id ───────────────────────────┘   │               │
│    ├── entities[] ──────────────────────────────┘               │
│    └── people[]                                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Data Quality Requirements

For the recommendation system to function correctly, the following data quality requirements must be met:

| Requirement | Field(s) | Validation |
|-------------|----------|------------|
| Non-null scores | `scores.insight`, `scores.credibility` | Must be 1–4; used in quality gates |
| Valid timestamps | `published_at` | Must be valid ISO 8601; used in freshness |
| Embedding availability | `embedding` | Must exist in vector DB; used in S_sim |
| Critical views for POV | `critical_views.non_consensus_level` | Should exist for contrarian classification |
| At least one category | `categories.major` | Should have ≥1 for topic tracking |

---

## 9. Field Usage Summary

| Field | Gate 1 | Gate 2 | S_sim | S_alpha | S_fresh | POV | Reranking |
|-------|--------|--------|-------|---------|---------|-----|-----------|
| `scores.credibility` | ✓ | ✓ | | ✓ | | | |
| `scores.insight` | | ✓ | | ✓ | | | |
| `embedding` | | | ✓ | | | | |
| `entities` | | | | | | | ✓ |
| `published_at` | | | | | ✓ | | |
| `series.id` | | | | | | | ✓ |
| `categories.major` | | | | | | | ✓ |
| `critical_views.non_consensus_level` | | | | | | ✓ | |
| `critical_views.new_ideas_summary` | | | | | | ✓ | |
| `critical_views.key_insights` | | | | | | ✓ | |

---

## 10. Traceability

### Why These Fields?

| Design Decision | Rationale | Academic/Commercial Backing |
|-----------------|-----------|----------------------------|
| Separate `insight` and `credibility` scores | Enables dual quality gates (C≥2 AND C+I≥5) | Scholar Inbox paper: "Hard Quality Floor" |
| Pre-computed embeddings | Enables real-time similarity without LLM calls | Spotify Semantic IDs paper |
| `critical_views` structure | Enables binary POV derivation (Contrarian/Consensus) without additional LLM inference | Podcast Recommendations paper |
| Entity relevance scores (0–4) | Enables PrimaryEntity extraction for diversity | MMR algorithm principles |
| Series as nested object | Simplifies join logic; series data rarely changes | Practical implementation choice |

### What's Not Included (and Why)

| Omitted Field | Reason |
|---------------|--------|
| Full transcript | Too large for recommendation context; use `key_insights` instead |
| `scores.entertainment` | Not used in current scoring formula; may add in V2 |
| `scores.information` | Not used in current scoring formula; may add in V2 |
| User demographics | Privacy-preserving design; personalize on behavior only |

---

## 11. Document References

| Downstream Document | Consumes |
|---------------------|----------|
| 02: User Embedding | `U.viewed_episodes`, `U.bookmarked_episodes`, `U.category_interests` |
| 03: Quality Gates | `E.scores.credibility`, `E.scores.insight`, `U.excluded_ids` |
| 04: Scoring Components | `E.embedding`, `E.scores.*`, `E.entities`, `E.published_at` |
| 06: POV Derivation | `E.critical_views.non_consensus_level` |
| 07: Narrative Reranking | `E.series.id`, `E.PrimaryTopic`, `E.PrimaryEntity`, `E.POV` |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Feb 2026 | Initial deep dive document |
