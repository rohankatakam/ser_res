# Serafis Recommendation Engine V1 — Trial Brief

**Author:** Rohan Katakam  
**Date:** January 29, 2026  
**Status:** ⚠️ SUPERSEDED — See `FOR_YOU_SPEC.md` for current approach

> **PIVOT:** After call with Rohan S., direction changed from 4 sections to single "For You" feed with embeddings.

---

## Assumptions & Needs (Lock vs Verify)

| # | Assumption | Status | Need |
|---|------------|--------|------|
| 1 | "Visit/view" = meaningful intent (not just impression) | Assumed | Confirm event taxonomy + definitions |
| 2 | Timestamps (published_at) are reliable and in UTC | Assumed | Confirm timezone + backfill behavior |
| 3 | Cold start threshold: personalization after 2 views | Assumed | Confirm product stance |
| 4 | Bookmarks are rare but high-signal (+2 weight) | Assumed | Confirm real bookmark rate distribution |
| 5 | Subscriptions are explicit series follows | Assumed | Confirm table + unsubscribe handling |
| 6 | Credibility floor ≥2 is safe globally | Assumed | Confirm business rules + B2B overrides |
| 7 | Scores are 0–4 and comparable across categories | Assumed | Confirm calibration / score meaning |
| 8 | critical_views field is trustworthy for Non-Consensus | Assumed | Confirm coverage + accuracy rate |
| 9 | Exclusions persist across sessions/devices | Assumed | Confirm storage approach + user merge |
| 10 | Recs can be cached ~5 min without harming UX | Assumed | Confirm freshness expectations |

---

## The Problem (Updated)

Serafis needs a **single unified "For You" feed** (TikTok-style) that:

| Interface | Purpose | Algorithm Need |
|-----------|---------|----------------|
| **Jump In** | Resume listening (history) | Display, not recommendation |
| **For You** | Discovery (novel content) | **Single feed with embeddings** |

The approach combines:
1. **Quartr:** Research-first for investors, quality signals
2. **Snipd:** AI-powered semantic understanding via embeddings
3. **TikTok:** Single infinite scroll, no manual sections

---

## What I Built (Without Codebase Access)

### Mock Infrastructure
- **Dataset:** Extracted ~200 episodes + series metadata from Serafis website
- **API Server:** FastAPI with recommendation endpoints
- **Frontend:** React prototype with live algorithm testing

### NEW: For You Algorithm

```
score = (embedding_similarity × 0.50) + (quality × 0.30) + (freshness × 0.10) + (boosts × 0.10)
```

| Component | Weight | Source |
|-----------|--------|--------|
| **Embedding Similarity** | 50% | User embedding ↔ Episode embedding |
| **Quality** | 30% | (insight × 0.55 + credibility × 0.45) / 4.0 |
| **Freshness** | 10% | Decay over 30 days |
| **Boosts** | 10% | Subscription (+0.5), Entity match (+0.3) |

### Jump In Section (History)
- Displays recently viewed/bookmarked episodes
- Sorted by timestamp (most recent first)
- **Unchanged from original approach**

---

## Key Design Decisions

### 1. Embeddings as Primary Signal (50%)
Episode embeddings from: `key_insight + description + entities`  
User embedding from: Aggregated viewed/bookmarked episode embeddings

**Why:** Semantic understanding > category matching. Finds related content even across categories.

### 2. Quality Score Formula (30%)
```
quality = (insight × 0.55) + (credibility × 0.45)
```

**Why this weighting:**
- Insight (55%): Serafis's unique value is surfacing novel ideas
- Credibility (45%): Investors care deeply about source authority
- Information: ⏸️ Unused in V1 (could add back at 10-15%)
- Entertainment: ⏸️ Unused — not relevant for research users

### 3. Credibility Floor (≥2)
Episodes with `credibility < 2` are filtered out entirely.

**Why:** Guarantees minimum source quality. Users should never see unreliable sources.

### 4. Boosts (10%)
- Subscription boost: +0.5 if episode from subscribed series
- Entity boost: +0.3 if episode mentions tracked companies

**Why:** Rewards loyalty and research focus without dominating the score.

### 5. Exclusion & Diversification (Unchanged)
- Exclude: Viewed + Bookmarked + Not Interested
- Diversify: Max 2 episodes per series

---

## What Makes This Different from Spotify/Apple

| Feature | Spotify/Apple | Serafis V1 |
|---------|---------------|------------|
| Quality signal | Popularity only | Insight + Credibility scores |
| Discovery | Collaborative filtering | Category + quality hybrid |
| Contrarian content | None | Dedicated section |
| Research focus | Entertainment | Decision-support |

**Core insight:** Spotify optimizes for engagement. Serafis should optimize for intelligence quality.

---

## Questions for Monday (High-Leverage)

### Product/UX
- Should Recommendations include episodes from subscribed series, or strictly new series?
- Is the goal more episode discovery or series discovery?

### Data Reality
- Do we have listen duration/completion, or only visit events?
- How sparse is bookmark behavior vs plays?

### Business Logic
- Should credibility floor be configurable (e.g., B2B users get stricter filter)?
- Any editorial/curated collections to blend with algo recs?

---

## V2 Roadmap (Once I Have Access)

### Week 1: Integration
- Wire V1 algorithms to real data tables
- Instrument recommendation events (impressions, clicks, saves)
- Validate data assumptions (what is a "visit"? duration?)

### Week 2: Ranking Improvements
- Add recency decay (newer content boosted)
- Implement cold start strategy (new users → global quality)
- A/B test credibility floor threshold (2 vs 3)

### Week 3: Advanced Features
- Session-based recommendations (what you're researching right now)
- Entity tracking (companies/people you follow)
- Implicit feedback (listen completion → stronger signal than play)

---

## Integration Plan (Technical)

### Data Model Assumed
```
UserEvent: user_id, entity_type, entity_id, event_type, timestamp
UserPreferences: user_id, category_interests[], subscribed_series[]
Episode: id, series_id, scores{}, categories{}, critical_views{}
Series: id, name, popularity, description
```

### API Contract
```
GET /recommendations/discover?user_id=...     → Full discover page
GET /recommendations/insights-for-you?user_id=...
GET /recommendations/highest-signal?user_id=...
GET /jump-in?user_id=...                      → History interface
POST /feedback/not-interested                 → Exclusion signal
```

### Latency Target
- Recommendations: <200ms (can be cached per user, refresh every 5 min)
- Jump In: <50ms (direct query, no ranking)

---

## Monday Narrative (6-minute version)

> "After our call, I pivoted to a single 'For You' feed approach — like TikTok but for investment research.
>
> The key insight: embeddings let us understand *what you're researching*, not just what categories you selected. So if you've been viewing episodes about AI infrastructure, we'll surface content about GPU supply chains and data centers — even if they're in different categories.
>
> The score combines embedding similarity (50%), Serafis quality signals (30%), freshness (10%), and subscription/entity boosts (10%). Plus the credibility floor to filter unreliable sources.
>
> The architecture draws from Quartr's research-first approach and Snipd's AI-powered understanding, applied to Serafis's unique quality signals.
>
> I'm ready to implement the embedding infrastructure and wire it to real data."

---

## Files in This Prototype

| File | Purpose |
|------|---------|
| `rec/mock_api/server.py` | FastAPI server with 6 endpoints |
| `rec/mock_api/data/` | Extracted episodes, series, mock users |
| `rec/prototype/src/` | React frontend with live testing |
| `rec/RECOMMENDATION_AUDIT.md` | Full parameter mapping + algorithm docs |
| `rec/recommendation_engine_spec.md` | Original spec document |
| `rec/competitor_ui_research.md` | Spotify/Apple UI patterns |

---

## Success Metrics (For Trial Evaluation)

### Offline (Can compute now)
- Coverage: How many unique episodes recommended across users?
- Diversity: Category/series entropy in top 10
- Credibility floor accuracy: 100% compliance

### Online (Once instrumented)
- CTR on recommendations
- Bookmark rate from recommendations
- Listen completion rate
- Return rate (users coming back within 7 days)

---

## Bottom Line

I built this without access to prove I can create clarity and momentum from ambiguity. The algorithms are production-ready patterns; the integration is the work ahead. I'm ready to hit the ground running Monday.
