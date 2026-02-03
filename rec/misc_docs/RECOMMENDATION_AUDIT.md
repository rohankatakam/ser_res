# Serafis Recommendation Engine — Implementation Audit

> *Complete parameter mapping and behavioral documentation.*

**Date:** January 29, 2026  
**Status:** ⚠️ SUPERSEDED — See `FOR_YOU_SPEC.md` for current approach  
**Last Updated:** January 29, 2026 — Pivoted to single "For You" feed with embeddings

---

## ⚠️ PIVOT NOTICE

**This document describes the original 4-section approach.**

After call with Rohan S., the direction changed to:
- **Single "For You" feed** (TikTok-style) instead of 4 sections
- **Embeddings** as primary personalization signal (50%)
- **See:** `rec/FOR_YOU_SPEC.md` for current specification

The parameter mapping below remains valid — it documents what signals exist and their status.

---

## 0. Assumptions & Needs (Lock vs Verify)

| # | Assumption | Status | Need |
|---|------------|--------|------|
| 1 | "Visit/view" = meaningful intent (not just impression) | Assumed | Confirm event taxonomy |
| 2 | Timestamps (published_at) reliable in UTC | Assumed | Confirm timezone |
| 3 | Cold start: personalization after 2 views | Assumed | Confirm product stance |
| 4 | Bookmarks rare but high-signal (+2) | Assumed | Confirm distribution |
| 5 | Subscriptions are explicit series follows | Assumed | Confirm table structure |
| 6 | Credibility floor ≥2 safe globally | Assumed | Confirm business rules |
| 7 | Scores 0–4, comparable across categories | Assumed | Confirm calibration |
| 8 | critical_views trustworthy for Non-Consensus | Assumed | Confirm coverage |
| 9 | Exclusions persist across sessions | Assumed | Confirm storage |
| 10 | Recs cacheable ~5 min | Assumed | Confirm freshness |

---

## 1. Parameter Coverage Summary

### 1.1 Provided Parameters vs For You Status

| Parameter Category | Parameter | For You Status | Usage | Notes |
|-------------------|-----------|----------------|-------|-------|
| **User Activity** | entity_type (series/episode) | ⚠️ Episode only | Aggregated into user embedding | Series activity not tracked |
| **User Activity** | entity_id | ✅ Active | User embedding + exclusion | Core signal |
| **User Activity** | visit_timestamp | ✅ Active | Recency weighting in embedding | Also powers Jump In |
| **User Bookmarks** | entity_type | ⚠️ Episode only | Weighted 2x in user embedding | Series bookmarks not implemented |
| **User Bookmarks** | entity_id | ✅ Active | User embedding (2x weight) + exclusion | Strong signal |
| **User Bookmarks** | bookmark_timestamp | ✅ Active | Recency weighting in embedding | Also powers Jump In |
| **User Subscriptions** | series_id | ✅ Active | Boost signal (+0.5) | Part of 10% boost component |
| **User Subscriptions** | subscription_timestamp | ⏸️ Unused | Not implemented | Could weight newer subscriptions |
| **User Category Interests** | category_name | ✅ Cold Start | Text → embedding proxy | Only used when no activity |
| **Episode Metadata** | descriptions | ✅ Active | Episode embedding source | Combined with key_insight |
| **Episode Metadata** | categories | ✅ Cold Start | Category → text → embedding | Only used for cold start |
| **Episode Metadata** | insight score | ✅ Active | 55% of quality component | Part of 30% quality |
| **Episode Metadata** | credibility score | ✅ Active | 45% of quality + floor (≥2) | Part of 30% quality |
| **Episode Metadata** | information score | ⏸️ Unused (V2) | Available, not in formula | Could add at 10-15% |
| **Episode Metadata** | entertainment score | ⏸️ Unused | Not relevant for research | N/A |
| **Episode Metadata** | entities (companies) | ✅ Active | Episode embedding + entity boost | Part of embedding + 10% boost |
| **Episode Metadata** | people | ⏸️ Unused (V2) | Available, not in V1 | Could add person tracking |
| **Episode Metadata** | critical_views | ⏸️ Unused (V2) | Was Non-Consensus section | Could add contrarian boost |
| **Series Metadata** | popularity | ⏸️ Unused (V2) | Was Trending section | Could add as explicit boost |
| **Series Metadata** | description | ⏸️ Unused | Available but not surfaced | Could add to series embedding |

### 1.2 Interfaces Implementation Status

| Interface | Status | Implementation |
|-----------|--------|----------------|
| **Jump In / Recently Played** | ✅ Implemented | `JumpInSection.jsx` shows viewed/bookmarked with timestamps |
| **For You Feed** | 🚧 In Progress | Single unified feed with embeddings (see `FOR_YOU_SPEC.md`) |
| ~~Recommendations (4 sections)~~ | ⚠️ Deprecated | Replaced by For You feed |

---

## 2. Data Flow (NEW: For You with Embeddings)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER SIGNALS (INPUT)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐           │
│  │  User Activity   │  │  User Bookmarks  │  │ User Subscriptions│          │
│  │  ─────────────   │  │  ─────────────   │  │  ─────────────    │          │
│  │  • Episode ID ✅  │  │  • Episode ID ✅  │  │  • Series ID ✅    │          │
│  │  • Timestamp ✅   │  │  • Timestamp ✅   │  │                   │          │
│  │  → 1x weight     │  │  → 2x weight     │  │  → Boost signal   │          │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬──────────┘          │
│           │                     │                      │                     │
│           └──────────┬──────────┘                      │                     │
│                      ▼                                 │                     │
│  ┌─────────────────────────────────────┐               │                     │
│  │      USER EMBEDDING (50%)           │               │                     │
│  │  Aggregated from viewed/bookmarked  │               │                     │
│  │  episode embeddings                 │               │                     │
│  └─────────────────┬───────────────────┘               │                     │
│                    │                                   │                     │
│  ┌─────────────────┴───────────────────┐               │                     │
│  │  Category Interests (Cold Start)   │               │                     │
│  │  → Text → Embedding proxy          │               │                     │
│  └─────────────────────────────────────┘               │                     │
│                                                        │                     │
└────────────────────────────────────────────────────────┼─────────────────────┘
                                                         │
┌────────────────────────────────────────────────────────┼─────────────────────┐
│                    EPISODE SIGNALS (PRE-COMPUTED)      │                     │
├────────────────────────────────────────────────────────┼─────────────────────┤
│                                                        │                     │
│  ┌─────────────────────────────────────┐               │                     │
│  │      EPISODE EMBEDDING              │               │                     │
│  │  key_insight + description          │               │                     │
│  │  + entities (companies)             │               │                     │
│  └─────────────────┬───────────────────┘               │                     │
│                    │                                   │                     │
│  ┌─────────────────┴───────────────────┐               │                     │
│  │      QUALITY SCORES                 │               │                     │
│  │  insight (55%) + credibility (45%)  │               │                     │
│  └─────────────────┬───────────────────┘               │                     │
│                    │                                   │                     │
│  ┌─────────────────┴───────────────────┐               │                     │
│  │      PUBLISHED DATE                 │               │                     │
│  │  → Freshness decay (30 days)        │               │                     │
│  └─────────────────────────────────────┘               │                     │
│                                                        │                     │
└────────────────────────────────────────────────────────┼─────────────────────┘
                                                         │
                                                         ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                         FOR YOU SCORING                                        │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  GUARDRAILS (Apply First)                                                │  │
│  │  ─────────────────────────                                               │  │
│  │  1. Exclusion: viewed + bookmarked + not_interested → filter out         │  │
│  │  2. Credibility floor: credibility < 2 → filter out                      │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  UNIFIED SCORE                                                           │  │
│  │  ─────────────                                                           │  │
│  │  score = (similarity × 0.50) + (quality × 0.30)                          │  │
│  │        + (freshness × 0.10) + (boost × 0.10)                             │  │
│  │                                                                          │  │
│  │  Where:                                                                  │  │
│  │  • similarity = cosine(user_embedding, episode_embedding)                │  │
│  │  • quality = (insight × 0.55 + credibility × 0.45) / 4.0                 │  │
│  │  • freshness = max(0, 1 - days_old/30)                                   │  │
│  │  • boost = subscription_boost(0.5) + entity_boost(0.3), capped at 1.0    │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  DIVERSIFICATION                                                         │  │
│  │  ───────────────                                                         │  │
│  │  Max 2 episodes per series in results                                    │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
└───────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                              OUTPUT                                            │
├───────────────────────────────────────────────────────────────────────────────┤
│  ⏱️ Jump In    → History interface (unchanged)                                │
│  📱 For You    → Single unified feed, ranked by score                         │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Algorithm Details (NEW: For You)

### 3.1 Quality Score Formula (Updated)

```python
CREDIBILITY_FLOOR = 2  # Minimum credibility to be recommended

def calculate_quality_score(episode):
    """
    Simplified for For You: insight + credibility only.
    Information score available but unused in V1.
    """
    # Hard filter: exclude low-credibility content
    if episode.scores.credibility < CREDIBILITY_FLOOR:
        return 0.0
    
    quality = (
        episode.scores.insight * 0.55 +      # Novelty/depth of ideas
        episode.scores.credibility * 0.45     # Speaker authority
    ) / 4.0  # Normalize to [0.0, 1.0]
    return quality
```

| Score | Weight | Status | Rationale |
|-------|--------|--------|-----------|
| Insight | 55% | ✅ Active | Primary value for research users |
| Credibility | 45% | ✅ Active | Trust in speaker/source + floor filter (≥2) |
| Information | — | ⏸️ Unused (V2) | Available, could add at 10-15% |
| Entertainment | — | ⏸️ Unused | Not relevant for research value |

### 3.2 For You Unified Score

```python
def score_for_you(episode, user, user_embedding):
    """
    Single unified scoring function for For You feed.
    """
    # Guardrails
    if episode.id in user.excluded_ids:
        return 0.0
    if episode.scores.credibility < CREDIBILITY_FLOOR:
        return 0.0
    
    # 1. Embedding similarity (50%)
    similarity = cosine_similarity(user_embedding, episode.embedding)
    
    # 2. Quality (30%)
    quality = calculate_quality_score(episode)
    
    # 3. Freshness (10%)
    days_old = (now - episode.published_at).days
    freshness = max(0, 1 - days_old / 30)
    
    # 4. Boosts (10%)
    boost = 0.0
    if episode.series_id in user.subscriptions:
        boost += 0.5
    if episode.entities & user.tracked_entities:
        boost += 0.3
    boost = min(1.0, boost)
    
    return (similarity * 0.50) + (quality * 0.30) + (freshness * 0.10) + (boost * 0.10)
```

### 3.3 Deprecated Section Algorithms

> ⚠️ The following 4-section approach has been replaced by the unified For You feed.
> Kept here for reference only.

<details>
<summary>Click to expand deprecated section algorithms</summary>

#### 📊 Insights for You (DEPRECATED)
```python
# Filter: Episodes matching user's category interests
# Score: 60% quality + 40% recency
# Replaced by: For You with embedding similarity
```

#### 💎 Highest Signal This Week (DEPRECATED)
```python
# Filter: Published within 7 days
# Score: 100% quality
# Replaced by: For You quality component (30%)
```

#### 🔥 Non-Consensus Ideas (DEPRECATED)
```python
# Filter: critical_views + high credibility
# Replaced by: Could add as "contrarian boost" in V2
```

#### 📡 New from Your Shows (DEPRECATED)
```python
# Filter: Episodes from subscribed series
# Replaced by: Subscription boost (+0.5) in For You
```

#### 🌟 Trending in [Category] (DEPRECATED)
```python
# Filter: Popular in user's top category
# Replaced by: Series popularity could be added as boost in V2
```

</details>

### 3.3 Exclusion Logic

```python
# All sections exclude:
excluded_ids = (
    seen_episode_ids |        # User has viewed
    bookmarked_episode_ids |  # User has saved
    not_interested_ids        # User marked "not interested"
)
```

### 3.4 Diversification

```python
def diversify(episodes, limit, max_per_series=2):
    """Prevent any single series from dominating recommendations."""
    result = []
    series_count = {}
    for ep in episodes:
        if series_count.get(ep.series.id, 0) >= max_per_series:
            continue
        result.append(ep)
        series_count[ep.series.id] = series_count.get(ep.series.id, 0) + 1
        if len(result) >= limit:
            break
    return result
```

---

## 4. User Signal Processing

### 4.1 Frontend Signal Capture (App.jsx)

| Action | Signal Captured | Effect on Preferences | Effect on Exclusion |
|--------|-----------------|----------------------|---------------------|
| **View/Click** | Episode ID, categories, series | +1 per category, +1 series interest | Added to `viewedEpisodes` |
| **Bookmark** | Episode ID, categories | +2 per category (strong signal) | Added to `bookmarkedEpisodes` |
| **Not Interested** | Episode ID, categories | -1 per category (negative signal) | Added to `notInterestedEpisodes` |

### 4.2 Inferred Preferences (Derived)

```javascript
inferredPreferences = {
    topCategories: [["Technology & AI", 3], ["Crypto", 1]],  // Sorted by score
    excludedCategories: ["Sports"],                          // score < 0
    implicitSubscriptions: [{ id: "series_123", name: "20VC", count: 2 }],  // 2+ views
    totalViewed: 5,
    totalBookmarked: 2,
    totalExcluded: 7,  // viewedEpisodes ∪ bookmarkedEpisodes ∪ notInterestedEpisodes
}
```

### 4.3 Cold Start Behavior

When `totalViewed < 2`:
- "Insights for You" falls back to "Highest Signal" (global quality)
- UI displays hint to view more episodes
- No personalization active

---

## 5. Episode Card Display

### 5.1 Fields Displayed

| Field | Source | Display |
|-------|--------|---------|
| Title | `episode.title` | Bold, 2 lines max |
| Series | `episode.series.name` | Subtitle |
| Date | `episode.published_at` | "Jan 29" format |
| Insight | `episode.scores.insight` | 💎 number |
| Credibility | `episode.scores.credibility` | ⭐ number |
| Information | `episode.scores.information` | 📊 number |
| Key Insight | `episode.key_insight` | Preview quote |
| Category | `episode.categories.major[0]` | Tag badge |

### 5.2 Badge Logic

| Badge | Condition | Priority |
|-------|-----------|----------|
| `highly_contrarian` | `critical_views.has_critical_views == true` | 1 |
| `contrarian` | `critical_views.non_consensus_level` exists | 2 |
| `high_insight` | `scores.insight >= 3` | 3 |
| `high_credibility` | `scores.credibility >= 3` | 4 |

Max 2 badges displayed per card.

---

## 6. API Endpoints

### 6.1 Recommendation Endpoints

| Endpoint | Personalized | Signals Used |
|----------|--------------|--------------|
| `GET /api/recommendations/insights-for-you` | Yes | category_interests, activity |
| `GET /api/recommendations/highest-signal` | Minimal | activity (exclusion only) |
| `GET /api/recommendations/non-consensus` | Minimal | activity (exclusion only) |
| `GET /api/recommendations/new-from-shows` | Yes | subscriptions, activity |
| `GET /api/recommendations/trending/{category}` | Yes | category_interests, activity |
| `GET /api/recommendations/discover` | Yes | All signals |

### 6.2 Feedback Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/feedback/not-interested` | Mark episode to exclude + negative signal |

---

## 7. Known Gaps & Issues (Updated)

### 7.1 ~~Missing "Jump In" Interface~~ ✅ FIXED

**Status:** Implemented in `JumpInSection.jsx`

**Solution:** Added "Jump In" section at top of discover page showing:
- Recently viewed episodes with timestamps
- Recently bookmarked episodes with timestamps
- Sorted by most recent first
- Visual distinction (Viewed vs Saved badges)

### 7.2 ~~Timestamps Not Utilized~~ ✅ PARTIALLY FIXED

| Timestamp | Available | Used |
|-----------|-----------|------|
| visit_timestamp | ✅ Yes | Powers Jump In recency sorting |
| bookmark_timestamp | ✅ Yes | Powers Jump In recency sorting |
| subscription_timestamp | ❌ No | Could sort subscriptions by recency |

### 7.3 Series-Level Activity Not Tracked

Current implementation only tracks episode-level activity. Series follows/unfollows are not captured as explicit signals (only inferred from 2+ episode views).

**Future:** Add explicit Follow/Unfollow UI for series.

### 7.4 Entity Tracking Not Implemented

Episode data includes `entities` (companies) and `people` mentioned, but:
- No "Tracking: OpenAI" personalization
- No person/company-based recommendations
- Data exists but not surfaced in recommendations

**Future:** Add entity tracking UI and "Updates on Companies You Track" section.

### 7.5 Credibility Floor ✅ NEW

**Status:** Implemented

**Solution:** Episodes with `credibility < 2` are now filtered out from all recommendation sections. This ensures users only see content from sources with at least baseline credibility.

---

## 8. Mock User Profiles

| User ID | Category Interests | Subscribed Series | Purpose |
|---------|-------------------|-------------------|---------|
| `user_prosumer_ai` | Technology & AI, Startups | Dwarkesh, Training Data, ILTB | AI-focused prosumer |
| `user_prosumer_crypto` | Crypto & Web3, Technology | All-In, BG2, 20VC | Crypto-focused prosumer |
| `user_prosumer_markets` | Public Markets, Macro | Full Ratchet, No Priors, Lex | Markets-focused prosumer |
| `user_cold_start` | (none) | (none) | New user test case |

---

## 9. Testing Checklist

### 9.1 Exclusion Behavior
- [ ] Viewed episodes excluded from all sections
- [ ] Bookmarked episodes excluded from all sections
- [ ] "Not interested" episodes excluded from all sections
- [ ] Exclusion persists across page refreshes (within session)

### 9.2 Personalization
- [ ] "Insights for You" filters by category interests
- [ ] "Trending in X" shows user's top category
- [ ] "New from Shows" only shows subscribed series
- [ ] Category interest weights update on view/bookmark

### 9.3 Quality Ranking
- [ ] "Highest Signal" sorted by quality score
- [ ] Quality score = (insight×0.45 + credibility×0.40 + info×0.15) / 4
- [ ] Entertainment score NOT used in quality calculation

### 9.4 Cold Start
- [ ] New user sees "Highest Signal" only
- [ ] Cold start hint displayed
- [ ] Personalization unlocks after 2 views

---

## 10. Summary

**Pivoted to single "For You" feed with embeddings (January 29, 2026).**

### Current Status

| Component | Status |
|-----------|--------|
| **For You Spec** | ✅ Designed — see `FOR_YOU_SPEC.md` |
| **Jump In** | ✅ Implemented — history interface |
| **Embedding Infrastructure** | 🚧 To implement — OpenAI embeddings |
| **Multi-section Approach** | ⚠️ Deprecated — replaced by For You |

### For You Algorithm

```
score = (embedding_similarity × 0.50) + (quality × 0.30) + (freshness × 0.10) + (boosts × 0.10)
```

Where:
- **Embedding similarity** = cosine(user_embedding, episode_embedding)
- **Quality** = (insight × 0.55 + credibility × 0.45) / 4.0
- **Freshness** = decay over 30 days
- **Boosts** = subscription (+0.5) + entity match (+0.3)

### Parameters Status

| Status | Parameters |
|--------|------------|
| ✅ Active | Activity, Bookmarks, Subscriptions, Insight, Credibility, Descriptions, Entities, Published date |
| ✅ Cold Start | Category Interests (text → embedding proxy) |
| ⏸️ Unused (V2) | Information score, Entertainment, People, Popularity, Critical views |

### Guardrails (Unchanged)

- Credibility floor: ≥2 required
- Exclusion: Viewed + Bookmarked + Not Interested
- Diversification: Max 2 episodes per series
