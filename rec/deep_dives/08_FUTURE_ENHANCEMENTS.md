# Deep Dive 08: Future Enhancements (V2)

> *Documented features deferred from V1 for future implementation.*

**Document:** 8 of 8  
**Type:** Future Roadmap  
**Status:** Design Complete — Not Implemented

---

## 1. Purpose

This document captures features that were considered during V1 design but deferred due to:
- Complexity not justified for initial launch
- Missing product infrastructure
- Insufficient data to validate value
- Risk of noise outweighing signal

Each feature includes the full specification so it can be implemented when conditions are met.

---

## 2. Enhancement Summary

| Enhancement | Priority | Complexity | Dependency |
|-------------|----------|------------|------------|
| S_entity (Entity Alignment Score) | **High** | Medium | Explicit entity tracking feature |
| Sentiment-Based POV | Medium | Medium | LLM sentiment model tuning |
| Velocity Bypass (Breaking News) | Medium | High | Velocity tracking infrastructure |
| Dual Freshness Decay | Low | Low | Content type classification |
| Search Query Signal | Medium | Medium | Query logging infrastructure |
| Vector Clustering (Anti-Grey-Sludge) | Low | High | Power user base |
| Score Explanation UI | Low | Low | Frontend development |
| Session State Decay | Low | Low | Power user feedback |

---

## 3. S_entity: Entity Alignment Score

### 3.1 Overview

**What:** A scoring component that boosts episodes mentioning entities the user explicitly tracks.

**Why Deferred:** Requires an explicit "Follow Company" or "Follow Person" feature in the app, which does not currently exist.

**Impact if Added:** Adds a 4th scoring component, enabling more personalized feeds for users who actively track specific companies.

### 3.2 Product Requirement

The mobile app must implement:
- "Follow" button on entity pages (companies, people)
- `U.tracked_entities` field in user data model
- UI to manage followed entities

### 3.3 Full Specification

**Formula:**
```
overlap = |U.tracked_entities ∩ E.entities|
matchable = max(1, min(|U.tracked_entities|, |E.entities|))
S_entity = overlap / matchable
```

**Input Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `U.tracked_entities` | Set[String] | Entities the user explicitly follows |
| `E.entities` | List[{name, relevance}] | Entities mentioned in episode |

**Output:**

| Property | Value |
|----------|-------|
| Range | [0, 1] |
| If no tracked entities | 0 |

**Weight Redistribution (when added):**

| Component | V1 Weight | V2 Weight |
|-----------|-----------|-----------|
| S_sim | 50% | 45% |
| S_alpha | 35% | 30% |
| S_fresh | 15% | 10% |
| S_entity | 0% | **15%** |

**Implementation:**
```python
def compute_s_entity(user_entities: set[str], episode_entities: list[dict]) -> float:
    if not user_entities:
        return 0.0
    
    episode_entity_names = {e['name'] for e in episode_entities}
    
    if not episode_entity_names:
        return 0.0
    
    overlap = len(user_entities & episode_entity_names)
    matchable = max(1, min(len(user_entities), len(episode_entity_names)))
    
    return overlap / matchable
```

### 3.4 Activation Criteria

- [ ] "Follow entity" feature shipped in app
- [ ] `U.tracked_entities` field populated for users
- [ ] At least 10% of active users have tracked ≥1 entity

---

## 4. Sentiment-Based POV

### 4.1 Overview

**What:** Extend POV from binary (Contrarian/Consensus) to 4 values (Contrarian/Bullish/Bearish/Neutral).

**Why Deferred:** 
- LLM sentiment analysis adds cost and latency
- Risk of misclassification (hedged language, sarcasm)
- Binary POV achieves core goal of surfacing contrarian views

**Impact if Added:** Enables more nuanced narrative flow (e.g., boost Bearish after Bullish sequence).

### 4.2 Full Specification

**POV Values:**

| POV | Definition |
|-----|------------|
| Contrarian | Challenges conventional wisdom |
| Bullish | Optimistic outlook on topics |
| Bearish | Pessimistic outlook on topics |
| Neutral | Balanced, informational |

**Derivation Logic:**
```
1. IF non_consensus_level ∈ {highly_non_consensus, non_consensus}
   → POV = Contrarian

2. ELSE: sentiment = LLM(E.critical_views.key_insights)
   → IF sentiment > 0.3  → POV = Bullish
   → IF sentiment < -0.3 → POV = Bearish
   → ELSE               → POV = Neutral
```

**Sentiment Thresholds:**

| Parameter | Default | Range |
|-----------|---------|-------|
| Bullish threshold | +0.3 | +0.2 to +0.4 |
| Bearish threshold | -0.3 | -0.4 to -0.2 |

**Updated Contrarian Boost Logic:**
```
IF LastPOV == Bullish AND E.POV == Contrarian → ×1.15
IF LastPOV == Bullish AND E.POV == Bearish   → ×1.10  (new)
IF LastPOV == Bearish AND E.POV == Bullish   → ×1.10  (new)
```

**LLM Prompt:**
```
Analyze the sentiment of the following investment insight text.
Return a single number between -1 (very bearish) and +1 (very bullish).
Consider overall tone about markets, companies, or investment opportunities.

Text: "{key_insights_text}"

Sentiment score:
```

### 4.3 Activation Criteria

- [ ] Sentiment model tuned on investment content
- [ ] <10% misclassification rate on test set
- [ ] Pre-computation pipeline for sentiment scores
- [ ] User feedback indicates desire for more narrative nuance

---

## 5. Velocity Bypass (Breaking News)

### 5.1 Overview

**What:** Route high-velocity content from unverified sources to a "Speculative" slot with an "Unverified" badge, bypassing the credibility gate.

**Why Deferred:**
- Requires velocity tracking infrastructure (view/share rate)
- Requires UI treatment for speculative content
- Risk of surfacing misinformation

**Impact if Added:** Catches breaking news from unknown sources (the "whistleblower" case).

### 5.2 Full Specification

**Velocity Metric:**
```
velocity = (views_last_24h + shares_last_24h × 2) / hours_since_publish
```

**Bypass Logic:**
```
IF E.velocity > 99th_percentile AND E.scores.credibility < 2:
    → Route to "Speculative Slot" (position 10 in feed)
    → Display with "Unverified Source" badge
    → Do NOT apply to main quality gates
```

**Parameters:**

| Parameter | Value | Tunable? |
|-----------|-------|----------|
| Velocity percentile threshold | 99th | Yes |
| Speculative slot position | 10 (last) | Yes |
| Max speculative per feed | 1 | Yes |

**UI Treatment:**
- Gray badge: "Unverified Source"
- Disclaimer: "This content is trending but from an unverified source"
- Option to hide speculative content in settings

### 5.3 Activation Criteria

- [ ] Velocity tracking implemented (views, shares, timestamps)
- [ ] 99th percentile velocity threshold calibrated
- [ ] "Unverified" badge UI designed and implemented
- [ ] Editorial review queue for high-velocity/low-credibility content

---

## 6. Dual Freshness Decay

### 6.1 Overview

**What:** Use different decay rates for news content vs. thematic/evergreen content.

**Why Deferred:**
- Requires content type classification
- Single λ=0.03 is a reasonable default

**Impact if Added:** Better freshness handling — news decays fast, educational content persists.

### 6.2 Full Specification

**Content Types:**

| Type | Description | Example |
|------|-------------|---------|
| News | Time-sensitive, market-moving | "Nvidia Q4 Earnings Analysis" |
| Thematic | Educational, evergreen | "How Transformer Architecture Works" |

**Dual Decay:**
```python
if episode.content_type == "news":
    lambda_fresh = 0.10  # ~7 day half-life
else:
    lambda_fresh = 0.03  # ~23 day half-life
```

**Decay Comparison:**

| Days Old | News (λ=0.10) | Thematic (λ=0.03) |
|----------|---------------|-------------------|
| 7 | 0.50 | 0.81 |
| 14 | 0.25 | 0.66 |
| 30 | 0.05 | 0.41 |

### 6.3 Activation Criteria

- [ ] Content type classification implemented in ingestion
- [ ] >90% accuracy on news vs. thematic classification
- [ ] User feedback indicates stale news or buried evergreen content

---

## 7. Search Query Signal

### 7.1 Overview

**What:** Incorporate user's recent search queries into personalization.

**Why Deferred:**
- Requires query logging infrastructure
- Spec already accounts for this as "Future (V2)"

**Impact if Added:** Captures active research intent, not just passive viewing history.

### 7.2 Full Specification

**New User Signal:**
```
U.search_queries = List[{query: String, timestamp: DateTime}]
```

**Intent Vector:**
```python
if len(user.search_queries) > 0:
    recent_queries = user.search_queries[-3:]  # Last 3 queries
    query_embeddings = [embed(q.query) for q in recent_queries]
    V_intent = mean(query_embeddings)
```

**Scoring Integration:**

Option A: Blend into V_activity
```python
V_activity = 0.7 × V_activity_views + 0.3 × V_intent
```

Option B: Separate component
```python
S_intent = CosineSim(V_intent, E.embedding)
# Add as 5th component with 10% weight
```

### 7.3 Activation Criteria

- [ ] Query logging implemented
- [ ] Query embeddings computed and stored
- [ ] A/B test shows improvement in engagement

---

## 8. Vector Clustering (Anti-Grey-Sludge)

### 8.1 Overview

**What:** For power users with 1000+ views, use K-means clustering to identify distinct interest clusters instead of a single mean embedding.

**Why Deferred:**
- Only needed for power users (rare at launch)
- High complexity
- V1's N_max=10 limit mitigates the issue

**Impact if Added:** Prevents user embedding from averaging to corpus centroid.

### 8.2 Full Specification

**Detection:**
```python
if len(user.viewed_episodes) > 1000:
    use_clustered_embedding = True
```

**Clustering:**
```python
from sklearn.cluster import KMeans

embeddings = [ep.embedding for ep in user.recent_episodes]
kmeans = KMeans(n_clusters=3)
clusters = kmeans.fit_predict(embeddings)

# Use cluster centroids as multiple V_activity vectors
V_activity_clusters = kmeans.cluster_centers_
```

**Scoring:**
```python
# Take max similarity across clusters
S_sim = max(CosineSim(cluster, E.embedding) for cluster in V_activity_clusters)
```

### 8.3 Activation Criteria

- [ ] Power users (1000+ views) exist in user base
- [ ] Users report "feed feels generic" after heavy usage
- [ ] A/B test shows improvement for power users

---

## 9. Score Explanation UI

### 9.1 Overview

**What:** "Why am I seeing this?" feature showing score component breakdown.

**Why Deferred:**
- Frontend development required
- Not essential for MVP

**Impact if Added:** Increases user trust and enables feedback.

### 9.2 Full Specification

**UI Elements:**

1. **Radar Chart:** Visual breakdown of S_sim, S_alpha, S_fresh
2. **Text Explanation:**
   - "This episode matches your interest in AI (82% similarity)"
   - "High-quality source: Credibility 4/4, Insight 3/4"
   - "Published 5 days ago (fresh)"
3. **Feedback Buttons:** "More like this" / "Less like this"

**Data Required (already logged):**
```json
{
  "s_sim": 0.82,
  "s_alpha": 0.875,
  "s_fresh": 0.86,
  "adjustments": {
    "contrarian_boost": true
  }
}
```

### 9.3 Activation Criteria

- [ ] Frontend capacity for feature
- [ ] User research indicates demand for transparency
- [ ] Logging infrastructure validated

---

## 10. Session State Decay

### 10.1 Overview

**What:** Gradually decay tracker counts within a session instead of hard persistence.

**Why Deferred:**
- Current hard persistence works for typical sessions
- Only needed if power users report issues

**Impact if Added:** Smoother experience for long sessions.

### 10.2 Full Specification

**Decay Logic:**
```python
# After each batch, decay counts by 50%
for key in series_tracker:
    series_tracker[key] = int(series_tracker[key] * 0.5)
```

**Effect:** 
- Batch 1: Series A count = 2
- Batch 2: Series A count = 1 (after decay)
- Series A can appear again in batch 2

### 10.3 Activation Criteria

- [ ] Power users request 5+ batches per session
- [ ] Users report "running out of content" in long sessions

---

## 11. Implementation Priority Matrix

| Enhancement | User Value | Complexity | Priority |
|-------------|-----------|------------|----------|
| S_entity | High | Medium | **P1** — Implement when entity tracking ships |
| Search Query Signal | High | Medium | **P1** — Implement when query logging ships |
| Velocity Bypass | Medium | High | **P2** — Consider for news-heavy use cases |
| Sentiment-Based POV | Medium | Medium | **P2** — Consider if users want more nuance |
| Dual Freshness Decay | Low | Low | **P3** — Low effort, low impact |
| Score Explanation UI | Low | Low | **P3** — Nice to have |
| Vector Clustering | Low | High | **P4** — Only for power users |
| Session State Decay | Low | Low | **P4** — Only if power users report issues |

---

## 12. Document References

| Related Document | Features Deferred |
|------------------|-------------------|
| 01: Data Model | U.tracked_entities, U.search_queries |
| 04: Scoring Components | S_entity |
| 06: POV Derivation | Sentiment-based POV |
| 07: Narrative Reranking | Session state decay |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Feb 2026 | Initial V2 roadmap document |
