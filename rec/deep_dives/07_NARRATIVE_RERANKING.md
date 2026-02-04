# Deep Dive 07: Narrative Reranking Subsystem

> *Transforms a scored candidate list into a diverse, narrative-aware final feed.*

**Document:** 7 of 8  
**Subsystem:** Narrative Reranking  
**Pipeline Stage:** Stage 3 (Final Output)  
**Status:** Final

---

## 1. Purpose

The Narrative Reranking subsystem takes the **top 50 candidates** (sorted by BaseScore) and selects the **final 10 episodes** for the feed. It applies diversity constraints and narrative flow adjustments to ensure:

1. **Series Diversity:** No single podcast dominates the feed
2. **Topic Diversity:** Multiple themes are represented
3. **Entity Diversity:** No single company/person dominates
4. **Narrative Flow:** Contrarian views surface after consensus content

---

## 2. Subsystem Context

```
┌─────────────────────────────────────────────────────────────────┐
│              NARRATIVE RERANKING SUBSYSTEM                       │
│                    (This Document)                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUT                                                          │
│  ─────                                                          │
│  • CandidateList: Top 50 episodes by BaseScore                  │
│  • Each candidate has: BaseScore, POV, PrimaryTopic,            │
│    PrimaryEntity, series.id                                     │
│                                                                  │
│                         │                                        │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              RE-SELECTION LOOP                          │    │
│  │              (10 iterations)                            │    │
│  │                                                         │    │
│  │  For each slot:                                         │    │
│  │  1. Apply penalties/boosts to all remaining candidates  │    │
│  │  2. Select highest TempScore                            │    │
│  │  3. Update state trackers                               │    │
│  │  4. Remove winner from candidates                       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                         │                                        │
│                         ▼                                        │
│                                                                  │
│  OUTPUT                                                         │
│  ──────                                                         │
│  • FinalFeed: 10 episodes in narrative order                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Input Parameters

| Parameter | Source | Type | Description |
|-----------|--------|------|-------------|
| `CandidateList` | Document 05 | List[Episode] | Top 50 by BaseScore |
| `E.BaseScore` | Document 05 | Float [0,1] | Pre-computed score |
| `E.POV` | Document 06 | Enum | Contrarian or Consensus |
| `E.PrimaryTopic` | Document 01 | String | Highest-relevance category |
| `E.PrimaryEntity` | Document 01 | String | Highest-relevance entity |
| `E.series.id` | Document 01 | String | Parent podcast series |

---

## 4. Output Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `FinalFeed` | List[Episode] | 10 episodes ordered by selection sequence |
| `FinalFeed[].TempScore` | Float | Adjusted score at selection time |
| `FinalFeed[].position` | Integer | 1-10 position in feed |

---

## 5. State Trackers

The reranking loop maintains state that evolves with each selection:

| Tracker | Type | Initial Value | Description |
|---------|------|---------------|-------------|
| `SeriesTracker` | Map[series_id → count] | {} | Episodes per series in final feed |
| `TopicTracker` | Map[topic → count] | {} | Episodes per topic in final feed |
| `GlobalEntityTracker` | Map[entity → count] | {} | Episodes per primary entity in final feed |
| `LastEntity` | String \| null | null | Previous episode's primary entity |
| `LastPOV` | Enum \| null | null | Previous episode's POV |

---

## 6. Adjustment Rules

### 6.1 Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                  RERANKING ADJUSTMENTS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  HARD CAPS (Score = 0)                                          │
│  ─────────────────────                                          │
│  • Series Limit: SeriesTracker[series_id] ≥ 2 → TempScore = 0   │
│                                                                  │
│  PENALTIES (Score Reduction)                                    │
│  ──────────────────────────                                     │
│  • Adjacency: PrimaryEntity == LastEntity → ×0.80               │
│  • Topic Saturation: TopicTracker[topic] ≥ 2 → ×0.85            │
│  • Entity Saturation: GlobalEntityTracker[entity] ≥ 3 → ×0.70   │
│                                                                  │
│  BOOSTS (Score Increase)                                        │
│  ────────────────────────                                       │
│  • Contrarian: LastPOV == Consensus AND POV == Contrarian       │
│                → ×1.15                                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Adjustment Details

#### 6.2.1 Series Hard Cap

| Parameter | Value | Tunable? | Rationale |
|-----------|-------|----------|-----------|
| Series cap | 2 | ⚙️ Yes (range: 1–3) | Prevents single podcast dominance |

**Logic:**
```python
if series_tracker.get(episode.series.id, 0) >= 2:
    temp_score = 0  # Hard exclusion
```

**Why Hard Cap?** A single popular podcast (e.g., "All-In") could otherwise fill the entire feed if it has many high-scoring episodes.

---

#### 6.2.2 Adjacency Penalty

| Parameter | Value | Tunable? | Rationale |
|-----------|-------|----------|-----------|
| Adjacency penalty | 0.80 | ⚙️ Yes (range: 0.70–0.90) | Discourages same-entity sequences |

**Logic:**
```python
if episode.primary_entity == last_entity and last_entity is not None:
    temp_score *= 0.80
```

**Example:** If position 3 was about Nvidia, position 4 candidates about Nvidia get 20% penalty.

---

#### 6.2.3 Topic Saturation Penalty

| Parameter | Value | Tunable? | Rationale |
|-----------|-------|----------|-----------|
| Topic saturation threshold | 2 | ⚙️ Yes (range: 2–3) | Encourages topic variety |
| Topic saturation penalty | 0.85 | ⚙️ Yes (range: 0.75–0.90) | Soft discouragement |

**Logic:**
```python
if topic_tracker.get(episode.primary_topic, 0) >= 2:
    temp_score *= 0.85
```

**Example:** If 2 "AI & Machine Learning" episodes are already in the feed, the 3rd gets 15% penalty.

---

#### 6.2.4 Global Entity Saturation Penalty (V1 Addition)

| Parameter | Value | Tunable? | Rationale |
|-----------|-------|----------|-----------|
| Entity saturation threshold | 3 | ⚙️ Yes (range: 2–4) | Prevents single-entity dominance |
| Entity saturation penalty | 0.70 | ⚙️ Yes (range: 0.60–0.80) | Strong discouragement |

**Logic:**
```python
if global_entity_tracker.get(episode.primary_entity, 0) >= 3:
    temp_score *= 0.70
```

**Why Added to V1?** Data analysis showed high entity concentration (OpenAI: 13%, Nvidia: 11% of catalog). Without this, a user interested in AI could get 5+ Nvidia episodes from different series.

---

#### 6.2.5 Contrarian Boost

| Parameter | Value | Tunable? | Rationale |
|-----------|-------|----------|-----------|
| Contrarian boost | 1.15 | ⚙️ Yes (range: 1.10–1.25) | Surfaces opposing viewpoints |

**Logic:**
```python
if last_pov == POV.CONSENSUS and episode.pov == POV.CONTRARIAN:
    temp_score *= 1.15
```

**Academic Backing:** Twitter/X Bridging algorithm; Google DeepMind "User Feedback Alignment" paper.

---

## 7. Re-Selection Algorithm

### 7.1 Pseudocode

```python
def rerank_candidates(
    candidates: list[Episode],
    n_output: int = 10
) -> list[Episode]:
    """
    Select final feed from candidates using diversity-aware reranking.
    
    Args:
        candidates: Top 50 episodes by BaseScore
        n_output: Number of episodes in final feed (default 10)
    
    Returns:
        Ordered list of n_output episodes
    """
    
    # Initialize state
    final_feed = []
    series_tracker = {}
    topic_tracker = {}
    global_entity_tracker = {}
    last_entity = None
    last_pov = None
    
    # Make a working copy
    remaining = candidates.copy()
    
    # Select n_output episodes
    while len(final_feed) < n_output and remaining:
        
        # Step 1: Compute TempScore for all remaining candidates
        scored = []
        for episode in remaining:
            temp_score = compute_temp_score(
                episode=episode,
                series_tracker=series_tracker,
                topic_tracker=topic_tracker,
                global_entity_tracker=global_entity_tracker,
                last_entity=last_entity,
                last_pov=last_pov
            )
            scored.append((episode, temp_score))
        
        # Step 2: Sort by TempScore descending
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Step 3: Select winner
        winner, winner_score = scored[0]
        
        # Step 4: Check if winner is viable
        if winner_score == 0:
            break  # No more viable candidates
        
        # Step 5: Add to final feed
        final_feed.append({
            'episode': winner,
            'temp_score': winner_score,
            'position': len(final_feed) + 1
        })
        
        # Step 6: Update trackers
        series_id = winner.series.id
        series_tracker[series_id] = series_tracker.get(series_id, 0) + 1
        
        topic = winner.primary_topic
        if topic:
            topic_tracker[topic] = topic_tracker.get(topic, 0) + 1
        
        entity = winner.primary_entity
        if entity:
            global_entity_tracker[entity] = global_entity_tracker.get(entity, 0) + 1
        
        last_entity = winner.primary_entity
        last_pov = winner.pov
        
        # Step 7: Remove winner from remaining
        remaining.remove(winner)
    
    return final_feed
```

### 7.2 TempScore Computation

```python
def compute_temp_score(
    episode: Episode,
    series_tracker: dict,
    topic_tracker: dict,
    global_entity_tracker: dict,
    last_entity: str | None,
    last_pov: POV | None,
    # Tunable parameters
    series_cap: int = 2,
    topic_threshold: int = 2,
    topic_penalty: float = 0.85,
    entity_threshold: int = 3,
    entity_penalty: float = 0.70,
    adjacency_penalty: float = 0.80,
    contrarian_boost: float = 1.15
) -> float:
    """
    Compute adjusted score for an episode given current state.
    """
    
    temp_score = episode.base_score
    
    # Hard cap: Series limit
    if series_tracker.get(episode.series.id, 0) >= series_cap:
        return 0
    
    # Penalty: Adjacency
    if episode.primary_entity == last_entity and last_entity is not None:
        temp_score *= adjacency_penalty
    
    # Penalty: Topic saturation
    if topic_tracker.get(episode.primary_topic, 0) >= topic_threshold:
        temp_score *= topic_penalty
    
    # Penalty: Global entity saturation
    if global_entity_tracker.get(episode.primary_entity, 0) >= entity_threshold:
        temp_score *= entity_penalty
    
    # Boost: Contrarian after consensus
    if last_pov == POV.CONSENSUS and episode.pov == POV.CONTRARIAN:
        temp_score *= contrarian_boost
    
    return temp_score
```

---

## 8. Complexity Analysis

| Operation | Complexity | Notes |
|-----------|------------|-------|
| Outer loop | O(k) | k = 10 (output size) |
| Inner loop (scoring) | O(n) | n = 50 (candidates) |
| Sorting | O(n log n) | Per iteration |
| **Total** | O(k × n log n) | ~50 × 10 × log(50) ≈ 2,800 operations |

**Performance:** Negligible. Sub-millisecond on any modern hardware.

---

## 9. Parameters Summary

### 9.1 All Tunable Parameters

| Parameter | Default | Range | Priority | Effect |
|-----------|---------|-------|----------|--------|
| Series cap | 2 | 1–3 | Low | Max episodes per series |
| Topic threshold | 2 | 2–3 | Medium | When topic penalty applies |
| Topic penalty | 0.85 | 0.75–0.90 | Medium | Strength of topic diversity |
| Entity threshold | 3 | 2–4 | Medium | When entity penalty applies |
| Entity penalty | 0.70 | 0.60–0.80 | Medium | Strength of entity diversity |
| Adjacency penalty | 0.80 | 0.70–0.90 | Medium | Consecutive entity penalty |
| Contrarian boost | 1.15 | 1.10–1.25 | Medium | Strength of POV diversity |
| n_output | 10 | 10 | Fixed | Feed size |
| n_candidates | 50 | 30–100 | Low | Candidate pool size |

---

## 10. Session & Batch Behavior

### 10.1 Session Definition

A **session** is a continuous period of app usage. State resets when:
- User closes the app, OR
- 30 minutes of inactivity

| Parameter | Value | Tunable? |
|-----------|-------|----------|
| Session timeout | 30 min | ⚙️ Yes |

### 10.2 Batch Loading

| Event | Behavior |
|-------|----------|
| Initial load | Generate 10 episodes, initialize state |
| "Load more" | Generate next 10 using **persisted** state |
| Session expires | Reset all state, start fresh |

**State Persistence:** SeriesTracker, TopicTracker, GlobalEntityTracker, LastEntity, LastPOV carry over between batches within a session. This ensures batch 2 doesn't repeat series/topics from batch 1.

### 10.3 Cross-Batch Example

**Batch 1 State After Selection:**
```
SeriesTracker: {"all-in": 2, "20vc": 1}
TopicTracker: {"AI": 2, "Crypto": 1}
GlobalEntityTracker: {"Nvidia": 2, "OpenAI": 1}
LastEntity: "OpenAI"
LastPOV: Consensus
```

**Batch 2 Behavior:**
- "All-In" episodes get TempScore = 0 (series cap reached)
- 3rd "AI" episode gets 0.85× penalty
- 3rd "Nvidia" episode gets 0.70× penalty
- Contrarian episodes get 1.15× boost (LastPOV = Consensus)

---

## 11. Worked Example

### 11.1 Setup

**Candidates (Top 5 shown, sorted by BaseScore):**

| Rank | Episode | BaseScore | Series | Topic | Entity | POV |
|------|---------|-----------|--------|-------|--------|-----|
| 1 | "Nvidia Dominance" | 0.92 | All-In | AI | Nvidia | Consensus |
| 2 | "AI Bubble Warning" | 0.88 | 20VC | AI | OpenAI | Contrarian |
| 3 | "Nvidia Chips" | 0.85 | Training Data | AI | Nvidia | Consensus |
| 4 | "Crypto Rally" | 0.82 | All-In | Crypto | Bitcoin | Consensus |
| 5 | "Apple Vision" | 0.80 | Invest Best | Tech | Apple | Consensus |

### 11.2 Selection Process

**Slot 1:**
- All TempScores = BaseScore (no state yet)
- Winner: "Nvidia Dominance" (0.92)
- State: SeriesTracker={"All-In": 1}, TopicTracker={"AI": 1}, EntityTracker={"Nvidia": 1}, LastEntity="Nvidia", LastPOV=Consensus

**Slot 2:**
- "AI Bubble Warning": 0.88 × 1.15 (contrarian boost) = **1.012**
- "Nvidia Chips": 0.85 × 0.80 (adjacency) = 0.68
- "Crypto Rally": 0.82 (no adjustment)
- "Apple Vision": 0.80 (no adjustment)
- Winner: "AI Bubble Warning" (1.012)
- State: SeriesTracker={"All-In": 1, "20VC": 1}, TopicTracker={"AI": 2}, EntityTracker={"Nvidia": 1, "OpenAI": 1}, LastEntity="OpenAI", LastPOV=Contrarian

**Slot 3:**
- "Nvidia Chips": 0.85 × 0.85 (topic saturation, AI=2) = 0.72
- "Crypto Rally": 0.82 (no adjustment)
- "Apple Vision": 0.80 (no adjustment)
- Winner: "Crypto Rally" (0.82)
- State updated...

**Result:** The contrarian episode jumped from rank 2 to slot 2 due to the 1.15× boost after a consensus episode.

---

## 12. Edge Cases

### 12.1 Insufficient Candidates

| Scenario | Behavior |
|----------|----------|
| < 10 viable candidates | Return fewer than 10 episodes |
| All TempScores = 0 | Stop selection early |

### 12.2 Homogeneous Catalog

| Scenario | Risk | Mitigation |
|----------|------|------------|
| All episodes from 2 series | Feed limited to 4 episodes (2×2) | Expand catalog |
| All episodes on one topic | Topic penalty reduces variety | Catalog curation |
| No contrarian content | Contrarian boost never fires | Monitor POV distribution |

### 12.3 Power User (Long Session)

| Scenario | Behavior |
|----------|----------|
| User requests 50+ episodes | State accumulates; later batches heavily penalized |
| Mitigation | Consider state decay or reset after N batches (V2) |

---

## 13. Logging & Debugging

For every selected episode, log:

```json
{
  "episode_id": "B7d9XwUOKOuoH7R8Tnzi",
  "position": 2,
  "base_score": 0.88,
  "temp_score": 1.012,
  "adjustments": {
    "series_capped": false,
    "adjacency_penalty": false,
    "topic_penalty": false,
    "entity_penalty": false,
    "contrarian_boost": true
  },
  "state_at_selection": {
    "series_tracker": {"All-In": 1},
    "topic_tracker": {"AI": 1},
    "entity_tracker": {"Nvidia": 1},
    "last_entity": "Nvidia",
    "last_pov": "Consensus"
  },
  "batch": 1
}
```

---

## 14. Testing Checklist

| Test | Expected Outcome |
|------|------------------|
| 3 episodes from same series in candidates | Only 2 appear in final feed |
| 4 episodes about Nvidia from 4 series | Max 3 appear (entity saturation at 3) |
| Consensus → Contrarian sequence | Contrarian gets 1.15× boost |
| Same entity in consecutive slots | Second gets 0.80× penalty |
| 3 AI topics already selected | 4th AI episode gets 0.85× penalty |
| User requests batch 2 | State persists from batch 1 |
| Session expires (30 min) | State resets |

---

## 15. Traceability

### 15.1 Design Decisions

| Decision | Rationale | Backing |
|----------|-----------|---------|
| Greedy re-selection | Simple, interpretable, efficient | Standard diversification pattern |
| Series hard cap | Prevents single source dominance | UX best practice |
| Soft penalties (not hard caps) | Allows high-quality content to still surface | Balances diversity with relevance |
| Contrarian boost | Breaks filter bubbles | Twitter Bridging, Google DeepMind |
| Global Entity Tracker | Prevents entity dominance across series | Data analysis showed 13% OpenAI concentration |

### 15.2 Academic Backing

| Component | Paper/Precedent |
|-----------|-----------------|
| Re-selection loop | Generative Ranking (2025) |
| Diversity penalties | MMR (Maximal Marginal Relevance) |
| Contrarian boost | User Feedback Alignment (2025) |

---

## 16. Dependencies

### 16.1 Upstream (Required)

| Dependency | Source | Description |
|------------|--------|-------------|
| CandidateList | Document 05 | Top 50 by BaseScore |
| E.POV | Document 06 | Contrarian/Consensus classification |
| E.PrimaryTopic | Document 01 | Derived from categories |
| E.PrimaryEntity | Document 01 | Derived from entities |

### 16.2 Downstream (Consumers)

| Consumer | Usage |
|----------|-------|
| Mobile App | Displays FinalFeed to user |
| Analytics | Tracks feed composition metrics |

---

## 17. Document References

| Related Document | Relationship |
|------------------|--------------|
| 01: Data Model | Provides PrimaryTopic, PrimaryEntity, series.id |
| 05: Base Score | Provides BaseScore for each candidate |
| 06: POV Derivation | Provides POV for contrarian boost |
| 08: Future Enhancements | State decay, batch reset options |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Feb 2026 | Initial deep dive document |
