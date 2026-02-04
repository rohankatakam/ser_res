# Serafis "For You" Feed — Testing & Tuning Guide

> *Companion document to FOR_YOU_SPEC_FINAL.md*

**Version:** 1.1  
**Date:** February 3, 2026  
**Purpose:** Edge cases, testing scenarios, tuning priorities, and implementation notes

> **Note:** Updated to align with deep dive documents. See `/rec/deep_dives/` for detailed specifications.

---

## 1. Edge Cases to Test

### 1.1 Quality Gate Edge Cases

| Scenario | C | I | C+I | Expected | Risk |
|----------|---|---|-----|----------|------|
| Verified expert, weak insight | 4 | 1 | 5 | ✅ Pass | Low value but safe |
| Unknown source, brilliant insight | 1 | 4 | 5 | ❌ Reject | **"Whistleblower Risk"** — may miss breaking news |
| New analyst, strong insight | 2 | 3 | 5 | ✅ Pass | Correct behavior |
| Mediocre on both | 2 | 2 | 4 | ❌ Reject | Correct behavior |
| Perfect episode | 4 | 4 | 8 | ✅ Pass | Correct behavior |

**Test:** Inject episodes at each boundary condition. Verify gate behavior matches table.

**Known Tradeoff:** Gate 2 may reject valuable content from unverified sources (whistleblowers, new analysts). This is an intentional safety decision for investor-grade content. If this causes feed quality issues, consider:
- Lowering combined floor to 4
- Adding "Breaking News" override flag
- **V2: Velocity Bypass** (see section 5.2)

---

### 1.2 User Embedding Edge Cases

| Scenario | Viewed | Bookmarked | Category Interests | Expected V_activity |
|----------|--------|------------|-------------------|---------------------|
| Brand new user | 0 | 0 | None | null → S_sim = 0.5 |
| Onboarded user | 0 | 0 | ["AI", "Crypto"] | Embed("AI Crypto") |
| Light user | 2 | 0 | ["AI"] | WeightedMean of 2 embeddings |
| Active user | 10+ | 3 | — | Full weighted mean |
| Power user | 100+ | 20+ | — | **Watch for "grey sludge"** |

**Test:** Create mock users at each tier. Verify cold start fallback works correctly.

**Known Risk: "Grey Sludge" / Vector Drift**

After 1000+ views, the user embedding may average out to the centroid of all finance topics, losing distinct interest spikes.

**Symptoms:**
- Recommendations become generic
- User reports "feed doesn't feel personalized anymore"

**Mitigation (V2):**
- Use top K distinct clusters instead of single mean
- More aggressive recency decay (λ_user = 0.10)
- Rolling window of last 50 interactions only

---

### 1.3 Entity Alignment Edge Cases

> **Note:** S_entity is deferred to V2 (requires explicit entity tracking feature). See `deep_dives/08_FUTURE_ENHANCEMENTS.md`.

For V1, entity diversity is handled by **GlobalEntityTracker** in reranking (see Section 1.5).

---

### 1.4 Freshness Edge Cases

| Days Old | S_fresh (λ=0.03) | Content Type | Concern |
|----------|------------------|--------------|---------|
| 0 | 1.00 | Breaking news | Correct |
| 7 | 0.81 | Recent earnings | Correct |
| 30 | 0.41 | Month-old interview | May be stale for news |
| 90 | 0.10 (floor) | Classic interview | Preserved by floor |
| 365 | 0.10 (floor) | Timeless content | Preserved by floor |

**Known Risk: News vs Thematic Decay**

λ=0.03 treats all content equally. In reality:
- Breaking news decays in hours/days
- Educational content stays relevant for months

**Symptom:** Feed feels stale for market-moving news.

**Mitigation (V2):**
- Dual decay rates: λ_news = 0.10, λ_thematic = 0.03
- Requires content type classification

---

### 1.5 Reranking Edge Cases

| Scenario | Expected Behavior | Test |
|----------|-------------------|------|
| 3 episodes from same series | Only 2 appear in top 10 | Hard cap works |
| 5 Nvidia episodes from 5 series | Max 3 appear, 4th+ gets 0.70× penalty | GlobalEntityTracker works |
| 3 consecutive AI topics | 3rd gets 0.85 penalty | Topic saturation works |
| Consensus → Contrarian | 1.15x boost applied | Narrative flow works |
| Consensus → Consensus → Consensus | No boost, no penalty | Expected behavior |

**GlobalEntityTracker (V1):**

Added to prevent single-entity dominance across different series.

| Entity Count | Behavior |
|--------------|----------|
| 1-2 | No penalty |
| 3+ | 0.70× penalty applied |

**Test:** If there are 5 great Nvidia episodes from 5 different series, verify that at most 3 appear in top 10 without heavy penalty.

---

### 1.6 POV Classification Edge Cases

POV is now **binary** (Contrarian/Consensus) based solely on `non_consensus_level`:

| non_consensus_level | Expected POV |
|---------------------|--------------|
| "highly_non_consensus" | Contrarian |
| "non_consensus" | Contrarian |
| null / absent | Consensus |

**No LLM sentiment analysis** — POV is deterministic based on pre-computed field.

**Test:** Verify episodes with `non_consensus_level` set are classified as Contrarian, all others as Consensus.

> **V2 Enhancement:** Sentiment-based POV (Bullish/Bearish/Neutral) deferred. See `deep_dives/08_FUTURE_ENHANCEMENTS.md`.

---

## 2. Tuning Priorities

### 2.1 High Priority (Tune First)

| Parameter | Default | Range | Impact | How to Tune |
|-----------|---------|-------|--------|-------------|
| W_sim | 0.50 | 0.40–0.60 | Feed personalization strength | If feed feels generic, increase. If echo-chamber, decrease |
| W_alpha | 0.35 | 0.25–0.45 | Quality signal strength | If low-quality content appears, increase |
| Combined Floor | 5 | 4–6 | Content volume vs quality | If feed is empty, lower. If quality issues, raise |

### 2.2 Medium Priority

| Parameter | Default | Range | Impact | How to Tune |
|-----------|---------|-------|--------|-------------|
| λ_fresh | 0.03 | 0.02–0.05 | Content freshness | If feed feels stale, increase |
| Adjacency penalty | 0.80 | 0.70–0.90 | Entity diversity | If same entity repeats consecutively, lower |
| Topic penalty | 0.85 | 0.75–0.90 | Topic diversity | If topics repeat, lower |
| Entity saturation threshold | 3 | 2–4 | Global entity diversity | If single entity dominates, lower to 2 |
| Entity saturation penalty | 0.70 | 0.60–0.80 | Strength of entity diversity | If users want more depth on topics, raise to 0.80 |
| Contrarian boost | 1.15 | 1.10–1.25 | Narrative flow strength | If contrarian views buried, increase |

### 2.3 Low Priority (Fine-Tuning)

| Parameter | Default | Range | Impact |
|-----------|---------|-------|--------|
| Bookmark weight | 2.0 | 1.5–3.0 | Bookmark signal strength |
| λ_user | 0.05 | 0.03–0.10 | User interest recency |
| Freshness floor | 0.10 | 0.05–0.20 | Evergreen content visibility |
| W_fresh | 0.15 | 0.10–0.20 | Freshness impact |
| Series cap | 2 | 1–3 | Series diversity |
| Session timeout | 30 min | 15–60 min | State persistence duration |

---

## 3. Testing Scenarios

### 3.1 Cold Start Test

**Setup:** New user with no activity, no interests.

**Expected:**
- S_sim = 0.5 for all episodes
- Feed ranked by S_alpha (quality) primarily
- High-quality, recent content surfaces

**Pass Criteria:** Top 10 episodes have average (C+I) ≥ 6

---

### 3.2 Personalization Test

**Setup:** User has viewed 10 AI episodes, 0 Crypto episodes.

**Expected:**
- AI episodes rank higher than Crypto
- S_sim reflects viewing history
- Feed is noticeably different from cold start

**Pass Criteria:** ≥7 of top 10 are AI-related

---

### 3.3 Entity Diversity Test (GlobalEntityTracker)

**Setup:** 5 high-quality Nvidia episodes from 5 different series.

**Expected:**
- First 2 Nvidia episodes appear without penalty
- 3rd Nvidia episode gets 0.70× penalty
- At most 3 Nvidia episodes in top 10

**Pass Criteria:** Max 3 episodes about same primary entity in feed

> **Note:** S_entity scoring is deferred to V2. Entity diversity is handled via GlobalEntityTracker in reranking.

---

### 3.4 Series Diversity Test

**Setup:** 10 high-quality episodes from same series.

**Expected:**
- Only 2 appear in top 10
- Remaining 8 slots go to other series

**Pass Criteria:** Max 2 from any single series

---

### 3.5 Narrative Flow Test

**Setup:** User sees Consensus episode first. Contrarian episode exists with similar base score.

**Expected:**
- Contrarian gets 1.15x boost
- Contrarian appears in slots 2-4

**Pass Criteria:** Consensus → Contrarian sequence appears

---

### 3.6 Session Persistence Test

**Setup:** User requests 10 episodes, then 10 more.

**Expected:**
- Batch 2 respects SeriesTracker from Batch 1
- No series appears >2 times across both batches (within session)
- TopicTracker and LastPOV persist

**Pass Criteria:** Diversity maintained across batches

---

### 3.7 Stress Test: Large Catalog

**Setup:** 10,000 episodes in catalog.

**Expected:**
- Stage 2 scoring completes in <500ms
- Stage 3 reranking (10 iterations on 50 candidates) completes in <100ms
- Total feed generation <1s

**Pass Criteria:** P95 latency <1s

---

### 3.8 Breaking News Test (V2)

**Setup:** High-velocity episode from unknown source (C=1, I=4, Velocity=99th percentile).

**Current Expected (V1):**
- Rejected by Gate 1 (C < 2)
- Does not appear in feed

**V2 Expected (with Velocity Bypass):**
- Routed to "Speculative Slot"
- Appears with "Unverified" badge
- Does not pollute main quality-filtered feed

**Pass Criteria (V2):** Breaking news visible within 1 hour of velocity spike

---

### 3.9 Echo Chamber Test

**Setup:** User views 10 consecutive Consensus AI episodes. No Contrarian content in catalog.

**Expected:**
- Contrarian boost has no effect (nothing to boost)
- Feed may feel one-sided

**Risk:** Without Contrarian content, feed becomes echo chamber.

**Mitigation:** Monitor POV distribution in catalog. Alert if <5% Contrarian.

**Pass Criteria:** If Contrarian content exists, it appears in top 5

---

## 4. Monitoring & Debugging

### 4.1 Score Logging

For every recommended episode, log:

```
{
  episode_id: "...",
  base_score: 0.78,
  temp_score: 0.89,  // After reranking adjustments
  components: {
    S_sim: 0.82,
    S_alpha: 0.75,
    S_fresh: 0.74
  },
  adjustments: {
    series_capped: false,
    adjacency_penalty: false,
    topic_penalty: false,
    entity_penalty: false,
    contrarian_boost: true
  },
  position: 3,
  batch: 1
}
```

**Use:** Enables "Why did I see this?" debugging and radar chart visualization.

---

### 4.2 Key Metrics to Track

| Metric | Description | Target | Alert If |
|--------|-------------|--------|----------|
| Feed CTR | Clicks / impressions | >5% | <3% |
| Quality of Clicks | Avg (C+I) of clicked episodes | >6 | <5 |
| Diversity Score | Unique series in top 10 | ≥6 | <4 |
| Cold Start Conversion | Users who view 3+ episodes | >50% | <30% |
| Session Depth | Episodes viewed per session | >3 | <2 |
| Contrarian Exposure | % of feeds with contrarian in top 5 | >20% | <10% |

---

### 4.3 Debug Scenarios

| Symptom | Likely Cause | Check |
|---------|--------------|-------|
| Feed feels generic | V_activity averaging out | Check user embedding diversity |
| Same entity repeating | No global entity cap | Count entity frequency in feed |
| Feed feels stale | λ too low or floor too high | Check S_fresh distribution |
| Quality feels low | Gates too permissive | Check avg C+I of recommended |
| Echo chamber | Contrarian boost not firing | Check POV distribution |
| Empty feed | Gates too strict | Check rejection rate at each gate |

---

## 5. V2 Considerations

> See `deep_dives/08_FUTURE_ENHANCEMENTS.md` for full specifications.

### 5.1 From Feedback (Prioritized)

| Enhancement | Impact | Complexity | Priority |
|-------------|--------|------------|----------|
| S_entity (Entity Alignment) | Enables explicit entity tracking | Medium | P1 |
| Search query signal (U_search) | Captures active intent | Medium | P1 |
| Velocity Bypass | Catches breaking news from unknown sources | High | P2 |
| Sentiment-based POV | Bullish/Bearish/Neutral classification | Medium | P2 |
| Dual λ (news vs thematic) | Better freshness handling | Low | P3 |
| Vector clustering (K clusters) | Prevents grey sludge | High | P4 |
| Score explanation UI | User trust & debugging | Low | P3 |

### 5.2 Implementation Notes

**Note:** GlobalEntityTracker is now **V1** (implemented in reranking).

**S_entity (V2):**
Requires explicit "Follow Company" feature in app. See `deep_dives/08_FUTURE_ENHANCEMENTS.md` for full spec.

**Velocity Bypass (V2):**
```
IF E.Velocity > 99th_percentile AND E.Credibility < 2:
    → Route to "Speculative Slot" or "Review Queue"
    → Display with "Unverified" badge
```
Requires velocity tracking infrastructure.

**Sentiment-based POV (V2):**
Extends binary POV to Contrarian/Bullish/Bearish/Neutral via LLM sentiment analysis.

---

## 6. Acceptance Criteria Checklist

Before launch, verify:

| Category | Test | Status |
|----------|------|--------|
| **Gates** | C=1 episodes rejected | ☐ |
| **Gates** | C+I<5 episodes rejected | ☐ |
| **Gates** | Excluded IDs not recommended | ☐ |
| **Scoring** | BaseScore ∈ [0,1] for all episodes | ☐ |
| **Scoring** | Cold start returns quality-ranked feed | ☐ |
| **Reranking** | Max 2 per series enforced | ☐ |
| **Reranking** | Adjacency penalty applied | ☐ |
| **Reranking** | Topic saturation penalty applied | ☐ |
| **Reranking** | Entity saturation penalty applied (≥3) | ☐ |
| **Reranking** | Contrarian boost applied (Consensus→Contrarian) | ☐ |
| **Session** | State persists across batches | ☐ |
| **Session** | State resets after 30min timeout | ☐ |
| **Performance** | Feed generation <1s P95 | ☐ |
| **Logging** | Score components logged | ☐ |
| **POV** | Binary classification working (Contrarian/Consensus) | ☐ |
| **Echo Chamber** | Contrarian appears in top 5 (if exists) | ☐ |

---

## 7. Quick Reference: Default Values

| Parameter | Value |
|-----------|-------|
| Credibility Floor | ≥ 2 |
| Combined Floor | ≥ 5 |
| W_sim | 0.50 |
| W_alpha | 0.35 |
| W_fresh | 0.15 |
| W_insight (in alpha) | 0.5 |
| W_cred (in alpha) | 0.5 |
| λ_fresh | 0.03 |
| Freshness floor | 0.10 |
| Bookmark weight | 2.0 |
| λ_user | 0.05 |
| Max viewed episodes | 10 |
| Series cap | 2 |
| Topic threshold | 2 |
| Entity threshold | 3 |
| Adjacency penalty | 0.80 |
| Topic penalty | 0.85 |
| Entity penalty | 0.70 |
| Contrarian boost | 1.15 |
| POV values | Contrarian, Consensus |
| Session timeout | 30 min |
| Candidates for reranking | 50 |
| Final feed size | 10 |
