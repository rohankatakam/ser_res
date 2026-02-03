# Serafis "For You" Feed — Testing & Tuning Guide

> *Companion document to FOR_YOU_SPEC_FINAL.md*

**Version:** 1.0  
**Date:** January 29, 2026  
**Purpose:** Edge cases, testing scenarios, tuning priorities, and implementation notes

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

| User Tracks | Episode Entities | Overlap | Matchable | S_entity |
|-------------|------------------|---------|-----------|----------|
| 1 (Nvidia) | 5 (incl. Nvidia) | 1 | min(1,5)=1 | 1.0 |
| 50 | 1 (Nvidia) | 1 | min(50,1)=1 | 1.0 |
| 50 | 5 (2 match) | 2 | min(50,5)=5 | 0.4 |
| 0 | 5 | 0 | 1 (max floor) | 0 |

**Test:** Verify the "Nvidia Trap" is avoided — user tracking 1 entity shouldn't see 100% Nvidia content.

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
| 5 Nvidia episodes from 5 series | All 5 could appear | **"One-Hit Wonder" risk** |
| 3 consecutive AI topics | 3rd gets 0.85 penalty | Topic saturation works |
| Bullish → Contrarian | 1.15x boost applied | Narrative flow works |
| Bullish → Bullish → Bullish | No boost, no penalty | May feel echo-chamber |

**Known Risk: Global Entity Domination**

Current design caps series (max 2) but not entities globally. If user tracks "Apple" and there are 5 great Apple episodes from 5 different series, feed could be 50% Apple content.

**Symptom:** Feed dominated by single hot stock/company.

**Mitigation (V2):**
- Add GlobalEntityTracker similar to TopicTracker
- Cap at 3 episodes mentioning same primary entity

---

### 1.6 POV Classification Edge Cases

| Key Insight | Expected POV | Risk |
|-------------|--------------|------|
| "NVDA will dominate AI for decades" | Bullish | Correct |
| "We see significant headwinds ahead" | Bearish | Correct |
| "Facing challenges but optimistic about Q4" | **Bullish by LLM** | Should be Bearish |
| "The market is overreacting to the downside" | **Contrarian** | Depends on non_consensus tag |

**Known Risk: LLM Sentiment Nuance**

LLMs struggle with:
- Hedged language ("cautiously optimistic")
- Irony/sarcasm
- Finance-specific phrases ("headwinds", "priced in")

**Symptom:** POV misclassification leads to poor narrative flow.

**Mitigation:**
- Ensure key_insight is a summarized analysis, not raw transcript
- Consider fine-tuning prompt for financial context
- Fall back to "Neutral" when confidence is low

---

## 2. Tuning Priorities

### 2.1 High Priority (Tune First)

| Parameter | Default | Range | Impact | How to Tune |
|-----------|---------|-------|--------|-------------|
| W_sim | 0.45 | 0.35–0.55 | Feed personalization strength | If feed feels generic, increase. If echo-chamber, decrease |
| W_alpha | 0.30 | 0.25–0.40 | Quality signal strength | If low-quality content appears, increase |
| Combined Floor | 5 | 4–6 | Content volume vs quality | If feed is empty, lower. If quality issues, raise |

### 2.2 Medium Priority

| Parameter | Default | Range | Impact | How to Tune |
|-----------|---------|-------|--------|-------------|
| λ_fresh | 0.03 | 0.02–0.05 | Content freshness | If feed feels stale, increase |
| Adjacency penalty | 0.80 | 0.70–0.90 | Entity diversity | If same entity repeats, lower |
| Topic penalty | 0.85 | 0.75–0.90 | Topic diversity | If topics repeat, lower |
| Contrarian boost | 1.15 | 1.10–1.25 | Narrative flow strength | If contrarian views buried, increase |

### 2.3 Low Priority (Fine-Tuning)

| Parameter | Default | Range | Impact |
|-----------|---------|-------|--------|
| Bookmark weight | 2.0 | 1.5–3.0 | Bookmark signal strength |
| λ_user | 0.05 | 0.03–0.10 | User interest recency |
| Freshness floor | 0.10 | 0.05–0.20 | Evergreen content visibility |
| W_entity | 0.15 | 0.10–0.20 | Entity tracking impact |
| W_fresh | 0.10 | 0.05–0.15 | Freshness impact |
| Series cap | 2 | 1–3 | Series diversity |

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

### 3.3 Entity Tracking Test

**Setup:** User tracks {Nvidia, OpenAI}. Episodes exist about both.

**Expected:**
- Episodes mentioning tracked entities get S_entity boost
- Mix of both entities in top 10
- Not 100% one entity

**Pass Criteria:** Both entities represented in top 10

---

### 3.4 Series Diversity Test

**Setup:** 10 high-quality episodes from same series.

**Expected:**
- Only 2 appear in top 10
- Remaining 8 slots go to other series

**Pass Criteria:** Max 2 from any single series

---

### 3.5 Narrative Flow Test

**Setup:** User sees Bullish episode first. Contrarian episode exists with similar base score.

**Expected:**
- Contrarian gets 1.15x boost
- Contrarian appears in slots 2-4

**Pass Criteria:** Bullish → Contrarian sequence appears

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
    S_entity: 0.50,
    S_fresh: 0.74
  },
  adjustments: {
    adjacency_penalty: false,
    topic_penalty: false,
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

### 5.1 From Feedback (Prioritized)

| Enhancement | Impact | Complexity | Priority |
|-------------|--------|------------|----------|
| Global Entity Tracker | Prevents single-entity dominance | Low | High |
| Dual λ (news vs thematic) | Better freshness handling | Medium | Medium |
| Search query signal (U_search) | Captures active intent | Medium | Medium |
| Vector clustering (K clusters) | Prevents grey sludge | High | Low |
| Score explanation UI | User trust & debugging | Low | Low |

### 5.2 Implementation Notes

**Global Entity Tracker:**
```
IF GlobalEntityTracker[E.PrimaryEntity] >= 3:
    TempScore *= 0.70
```
Add to Stage 3 reranking loop.

**Dual Freshness Decay:**
```
IF E.content_type == "News":
    λ = 0.10
ELSE:
    λ = 0.03
```
Requires content_type classification.

**Search Query Signal:**
```
IF |U.search_queries| > 0:
    V_intent = Mean(last 3 query embeddings)
    scores.append(CosineSim(V_intent, E.embedding))
```
Already spec'd as optional/future.

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
| **Reranking** | Contrarian boost applied | ☐ |
| **Session** | State persists across batches | ☐ |
| **Session** | State resets after 30min timeout | ☐ |
| **Performance** | Feed generation <1s P95 | ☐ |
| **Logging** | Score components logged | ☐ |

---

## 7. Quick Reference: Default Values

| Parameter | Value |
|-----------|-------|
| Credibility Floor | ≥ 2 |
| Combined Floor | ≥ 5 |
| W_sim | 0.45 |
| W_alpha | 0.30 |
| W_entity | 0.15 |
| W_fresh | 0.10 |
| W_insight (in alpha) | 0.5 |
| W_cred (in alpha) | 0.5 |
| λ_fresh | 0.03 |
| Freshness floor | 0.10 |
| Bookmark weight | 2.0 |
| λ_user | 0.05 |
| Max viewed episodes | 10 |
| Series cap | 2 |
| Topic cap | 2 |
| Adjacency penalty | 0.80 |
| Topic penalty | 0.85 |
| Contrarian boost | 1.15 |
| Bullish threshold | 0.3 |
| Bearish threshold | -0.3 |
| Session timeout | 30 min |
| Candidates for reranking | 50 |
| Final feed size | 10 |
