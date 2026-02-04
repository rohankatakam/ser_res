# Deep Dive 02: User Embedding Subsystem

> *Transforms user behavioral signals into a vector representation of research interests.*

**Document:** 2 of 8  
**Subsystem:** User Embedding (V_activity)  
**Pipeline Stage:** Stage 1 (Computed Signals)  
**Status:** Final

---

## 1. Purpose

This subsystem computes **V_activity** — a single embedding vector that represents the user's research interests based on their consumption history. This vector is the foundation for personalized recommendations via semantic similarity matching.

---

## 2. Subsystem Context

```
┌─────────────────────────────────────────────────────────────────┐
│                   USER EMBEDDING SUBSYSTEM                       │
│                      (This Document)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUTS (from Document 01)                                      │
│  ─────────────────────────                                      │
│  • U.viewed_episodes: List[{episode_id, timestamp, embedding}]  │
│  • U.bookmarked_episodes: List[{episode_id, timestamp, embedding}]
│  • U.category_interests: List[String]                           │
│                                                                  │
│                         │                                        │
│                         ▼                                        │
│              ┌─────────────────────┐                            │
│              │   COMPUTATION       │                            │
│              │   (Weighted Mean)   │                            │
│              └─────────────────────┘                            │
│                         │                                        │
│                         ▼                                        │
│                                                                  │
│  OUTPUT                                                         │
│  ──────                                                         │
│  • V_activity: Vector[1536] | null                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Stage 2: Scoring   │
                    │  (S_sim uses        │
                    │   V_activity)       │
                    │  (Document 04)      │
                    └─────────────────────┘
```

---

## 3. Input Parameters

| Parameter | Source | Type | Description |
|-----------|--------|------|-------------|
| `U.viewed_episodes` | Document 01 | List[{episode_id, timestamp, embedding}] | Episodes the user has viewed, with their embeddings |
| `U.bookmarked_episodes` | Document 01 | List[{episode_id, timestamp, embedding}] | Episodes the user has saved, with their embeddings |
| `U.category_interests` | Document 01 | List[String] | Stated topic preferences from onboarding |

---

## 4. Output Parameters

| Parameter | Type | Range | Description |
|-----------|------|-------|-------------|
| `V_activity` | Vector[1536] \| null | Unit vector or null | User's research interest embedding |

**Output States:**

| State | Condition | Downstream Behavior |
|-------|-----------|---------------------|
| `null` | No activity AND no interests | S_sim = 0.5 (neutral) |
| Valid vector | Any activity OR interests exist | S_sim = CosineSim(V_activity, E.embedding) |

---

## 5. Core Algorithm

### 5.1 Formula

```
V_activity = Σ(weight_i × embedding_i) / Σ(weight_i)

Where:
  weight_i = interaction_weight × recency_weight
  
  interaction_weight:
    • 2.0 if episode was bookmarked
    • 1.0 if episode was only viewed
    
  recency_weight = exp(-λ_user × days_since_interaction)
```

### 5.2 Parameters

| Parameter | Symbol | Default Value | Tunable? | Range | Rationale |
|-----------|--------|---------------|----------|-------|-----------|
| Bookmark weight | W_bookmark | 2.0 | ⚙️ Yes | 1.5–3.0 | Bookmarks are explicit intent signals, stronger than passive views |
| View weight | W_view | 1.0 | 🔒 Fixed | — | Baseline; other weights are relative to this |
| User recency decay | λ_user | 0.05 | ⚙️ Yes | 0.03–0.10 | Controls how quickly old interactions lose influence |
| Max episodes considered | N_max | 10 | ⚙️ Yes | 5–20 | Limits computation to most recent activity. *Tune during testing based on user engagement patterns.* |

### 5.3 Recency Decay Curve

The recency weight follows exponential decay with half-life ≈ 14 days (at λ_user = 0.05):

| Days Since Interaction | Recency Weight | Interpretation |
|------------------------|----------------|----------------|
| 0 | 1.00 | Full weight |
| 7 | 0.70 | 70% weight |
| 14 | 0.50 | Half weight (half-life) |
| 30 | 0.22 | ~22% weight |
| 60 | 0.05 | ~5% weight |

**Why Exponential Decay?**
- Reflects natural interest evolution — recent views better indicate current research focus
- Smooth degradation avoids cliff effects (unlike hard time windows)
- λ = 0.05 balances responsiveness with stability

---

## 6. Cold Start Handling

When users have no behavioral history, the system gracefully degrades:

```
┌─────────────────────────────────────────────────────────────────┐
│                   COLD START WATERFALL                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. IF |viewed_episodes| + |bookmarked_episodes| > 0:           │
│     → Compute V_activity using weighted mean (normal path)      │
│                                                                  │
│  2. ELSE IF |category_interests| > 0:                           │
│     → V_activity = Embed(join(category_interests))              │
│     → e.g., Embed("Technology & AI, Crypto & Web3")             │
│                                                                  │
│  3. ELSE:                                                        │
│     → V_activity = null                                         │
│     → S_sim will use default value of 0.5                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.1 Category Interest Embedding

When only category interests are available:

```python
def embed_category_interests(interests: list[str]) -> Vector:
    """
    Convert category interests to an embedding.
    
    Example: ["Technology & AI", "Crypto & Web3"]
           → "Technology & AI, Crypto & Web3"
           → Embed(text) → Vector[1536]
    """
    combined_text = ", ".join(interests)
    return embedding_model.encode(combined_text)
```

**Why join categories?**
- Simple, deterministic transformation
- Captures semantic relationship between interests
- No need for pre-computed category embeddings

---

## 7. Detailed Computation Steps

### 7.1 Step-by-Step Algorithm

```python
def compute_v_activity(user: User, now: datetime) -> Vector | None:
    """
    Compute user research vector from behavioral history.
    
    Returns:
        Vector[1536] if sufficient data exists
        None if no data available (cold start with no interests)
    """
    
    # Step 1: Collect all interactions (deduplicated, bookmark takes priority)
    interactions = {}  # keyed by episode_id
    
    # First pass: add all views
    for ep in user.viewed_episodes[-N_MAX:]:
        interactions[ep.id] = {
            'embedding': ep.embedding,
            'is_bookmark': False,
            'days_ago': (now - ep.timestamp).days
        }
    
    # Second pass: bookmarks override views (higher priority signal)
    for ep in user.bookmarked_episodes[-N_MAX:]:
        interactions[ep.id] = {
            'embedding': ep.embedding,
            'is_bookmark': True,
            'days_ago': (now - ep.timestamp).days
        }
    
    interactions = list(interactions.values())  # Convert back to list
    
    # Step 2: Check for cold start
    if len(interactions) == 0:
        if len(user.category_interests) > 0:
            # Cold start with interests
            return embed_category_interests(user.category_interests)
        else:
            # Pure cold start
            return None
    
    # Step 3: Compute weighted mean
    weighted_sum = np.zeros(1536)
    total_weight = 0.0
    
    for interaction in interactions:
        # Interaction weight
        w_interaction = W_BOOKMARK if interaction['is_bookmark'] else W_VIEW
        
        # Recency weight
        w_recency = math.exp(-LAMBDA_USER * interaction['days_ago'])
        
        # Combined weight
        weight = w_interaction * w_recency
        
        weighted_sum += weight * interaction['embedding']
        total_weight += weight
    
    # Step 4: Normalize
    v_activity = weighted_sum / total_weight
    
    return v_activity
```

### 7.2 Handling Duplicate Episodes

If an episode appears in both `viewed_episodes` and `bookmarked_episodes`:
- **Behavior:** Deduplicate — count only once using the **bookmark weight** (2.0)
- **Rationale:** Bookmarking is a stronger explicit signal than viewing. A casual view (skim and leave) shows some engagement, but a bookmark indicates clear intent. Deduplication with bookmark priority ensures we don't over-weight episodes that happen to appear in both lists while still honoring the stronger signal.

---

## 8. Intermediate Values

These values are computed during V_activity generation but not persisted:

| Intermediate | Type | Description |
|--------------|------|-------------|
| `interactions[]` | List | Combined list of views + bookmarks with metadata |
| `weight_i` | Float | Combined weight for each interaction |
| `weighted_sum` | Vector | Running sum of weighted embeddings |
| `total_weight` | Float | Sum of all weights (for normalization) |

---

## 9. Edge Cases

### 9.1 Single Episode User

| Scenario | Behavior | Result |
|----------|----------|--------|
| User has viewed exactly 1 episode | V_activity = that episode's embedding (weight = 1.0) | Works correctly |
| User has bookmarked 1 episode, viewed 0 | V_activity = that episode's embedding (weight = 2.0, but normalized) | Works correctly |

### 9.2 Very Old Activity

| Scenario | With λ_user = 0.05 | Mitigation |
|----------|-------------------|------------|
| User's only view was 90 days ago | recency_weight = 0.01 | Still contributes, just weakly |
| All views are 60+ days old | Combined weight < 0.1 | Consider treating as cold start (V2) |

### 9.3 Power User ("Grey Sludge" Risk)

| Scenario | Risk | Current Mitigation |
|----------|------|-------------------|
| User has 500+ views across all topics | V_activity averages toward corpus centroid | N_max = 10 limits to recent activity |
| User interests are truly diverse | V_activity is legitimately general | Not a bug; user is general |

**V2 Consideration:** If grey sludge becomes an issue, consider:
- Using K-means clustering to identify distinct interest clusters
- Maintaining multiple V_activity vectors per interest cluster
- More aggressive recency decay (λ_user = 0.10)

---

## 10. Worked Example

**User Profile:**
```json
{
  "viewed_episodes": [
    {"id": "ep1", "embedding": [0.1, 0.2, ...], "days_ago": 2},
    {"id": "ep2", "embedding": [0.3, 0.1, ...], "days_ago": 7}
  ],
  "bookmarked_episodes": [
    {"id": "ep3", "embedding": [0.2, 0.3, ...], "days_ago": 1}
  ]
}
```

**Weight Calculations:**

| Episode | Type | W_interaction | Days Ago | W_recency (λ=0.05) | Total Weight |
|---------|------|---------------|----------|-------------------|--------------|
| ep1 | View | 1.0 | 2 | exp(-0.05 × 2) = 0.90 | 0.90 |
| ep2 | View | 1.0 | 7 | exp(-0.05 × 7) = 0.70 | 0.70 |
| ep3 | Bookmark | 2.0 | 1 | exp(-0.05 × 1) = 0.95 | 1.90 |

**Total Weight:** 0.90 + 0.70 + 1.90 = **3.50**

**V_activity Calculation:**
```
V_activity = (0.90 × embed_ep1 + 0.70 × embed_ep2 + 1.90 × embed_ep3) / 3.50
```

**Interpretation:**
- ep3 (bookmarked, recent) contributes 54% of the signal
- ep1 (viewed, recent) contributes 26%
- ep2 (viewed, week old) contributes 20%

This correctly prioritizes explicit + recent signals.

---

## 11. Tuning Guidance

### 11.1 When to Adjust Parameters

| Symptom | Likely Cause | Adjustment |
|---------|--------------|------------|
| Feed changes too slowly after new views | λ_user too low | Increase λ_user (e.g., 0.07) |
| Feed is too reactive to single views | λ_user too high | Decrease λ_user (e.g., 0.03) |
| Bookmarks don't seem impactful | W_bookmark too low | Increase W_bookmark (e.g., 2.5) |
| Single bookmark dominates feed | W_bookmark too high | Decrease W_bookmark (e.g., 1.5) |
| Feed feels generic for active users | N_max too high | Decrease N_max (e.g., 5) |

### 11.2 Testing Checklist

| Test | Expected Outcome |
|------|------------------|
| Cold start user with no interests | V_activity = null, downstream S_sim = 0.5 |
| Cold start user with interests | V_activity = Embed(interests) |
| User with 1 view | V_activity = that episode's embedding |
| User with 10 views | V_activity = weighted mean of all 10 |
| User bookmarks an episode | That episode's influence increases 2x |
| User's old views (30+ days) | Contribute ~20% of fresh view weight |

---

## 12. Traceability

### 12.1 Design Decisions

| Decision | Rationale | Academic/Commercial Backing |
|----------|-----------|----------------------------|
| Weighted mean of embeddings | Simple, interpretable, computationally efficient | Standard practice in embedding-based recommendation |
| Exponential recency decay | Smooth degradation, tunable half-life | Spotify Discover Weekly uses similar temporal weighting |
| Bookmark weight = 2x view | Explicit signals stronger than implicit | Artifact app prioritizes dwell time (explicit engagement) over impressions |
| N_max = 10 limit | Prevents grey sludge; focuses on recent interests | Practical constraint; tunable |
| Category interest fallback | Enables meaningful cold start experience | Spotify's onboarding flow uses genre preferences similarly |

### 12.2 Why Not Alternatives?

| Alternative | Why Not Used |
|-------------|--------------|
| Collaborative filtering | Requires user base scale; cold start problem worse |
| Average of all embeddings (no weighting) | Ignores recency and engagement strength |
| Most recent episode only | Too volatile; single misclick changes everything |
| Clustering user interests | Complexity not justified for V1; consider for V2 |

---

## 13. Dependencies

### 13.1 Upstream (Required)

| Dependency | Source | Description |
|------------|--------|-------------|
| Episode embeddings | Document 01 | Pre-computed 1536-dim vectors |
| User interaction history | Document 01 | Timestamped view/bookmark records |
| Embedding model | Infrastructure | Must match episode embedding model |

### 13.2 Downstream (Consumers)

| Consumer | Usage |
|----------|-------|
| Document 04: S_sim | CosineSim(V_activity, E.embedding) |
| Document 05: Base Score | Via S_sim component |

---

## 14. Document References

| Related Document | Relationship |
|------------------|--------------|
| 01: Data Model | Provides U.viewed_episodes, U.bookmarked_episodes, U.category_interests |
| 04: Scoring Components | Consumes V_activity for S_sim calculation |
| 08: Future Enhancements | Grey sludge mitigation via clustering |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Feb 2026 | Initial deep dive document |
