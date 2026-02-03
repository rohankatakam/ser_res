# Recommendation Algorithm V1 — Decision Brief

**To:** Rohan Sharma  
**From:** Rohan Katakam  
**Date:** January 29, 2026  
**Re:** EOD Update — Recommendation Engine

---

## Goal

Power the **Recommendations** interface with novel, high-signal episodes the user hasn't interacted with.

*(Jump In is history/playback — acknowledged as separate, not the focus here.)*

---

## Inputs (From Your Spec) → How Each Is Used

**User Signals:**
| Signal | Fields | Section(s) Using It | How |
|--------|--------|---------------------|-----|
| Activity | entity_type, entity_id, timestamp | ALL sections | Exclusion (seen = filter out) |
| Bookmarks | entity_type, entity_id, timestamp | ALL sections | Exclusion (saved = filter out) |
| Subscriptions | series_id, timestamp | **New from Your Shows** | Candidate source |
| Category Interests | category names | **Insights for You**, **Trending** | Candidate filtering + section selection |

**Content Metadata:**
| Field | Section(s) Using It | How |
|-------|---------------------|-----|
| Popularity (series) | **Trending** | 50% of ranking score |
| Categories (episodes) | **Insights for You**, **Trending** | Match to user interests |
| Insight score | ALL sections | 45% of quality score |
| Credibility score | ALL sections | 40% of quality score + floor filter (≥2) |
| Descriptions | V2 | Future: embeddings for similarity |

**Confirmed gaps (V2 opportunities):**
- Bookmarks as positive signal (not just exclusion) → boost similar content
- Timestamps for recency weighting → decay older activity
- Series-level activity → currently episode-focused

---

## V1 Recommendation Sections

| Section | Inputs Used | Candidate Source | Ranking Formula |
|---------|-------------|------------------|-----------------|
| **Insights for You** | category_interests, insight, credibility, categories | Episodes in user's preferred categories | `(quality × 0.6) + (recency × 0.4)` |
| **Highest Signal** | insight, credibility | All episodes (past 7 days) | `quality × 1.0` |
| **New from Your Shows** | subscriptions, published_at | Episodes from subscribed series | `recency` (newest first) |
| **Trending** | category_interests, popularity, insight, credibility | Episodes in user's top category | `(popularity × 0.5) + (quality × 0.3) + (recency × 0.2)` |

**Quality Score (used in all sections):**
```
quality = (insight × 0.45) + (credibility × 0.40)
```
*Note: If information score exists, can add at 15% weight. Need to confirm availability.*

**All sections apply:**
- Exclusion filter: activity (seen) + bookmarks (saved)
- Credibility floor: ≥2 required
- Diversification: max 2 episodes per series

---

## Global Rules

| Rule | Implementation |
|------|----------------|
| **Exclusions** | Activity (viewed) + Bookmarks + Not-interested |
| **Credibility floor** | Episodes with credibility < 2 filtered out |
| **Diversification** | Max 2 episodes per series per section |
| **Cold start** | No category interests → show Highest Signal only |

---

## Assumptions to Confirm

| # | Assumption | Quick Question |
|---|------------|----------------|
| 1 | "Visit" in activity = meaningful play intent | Is this episode open, play start, or page view? |
| 2 | Insight/credibility scores accessible in API | Available in the endpoint I'll integrate with? |
| 3 | Information score exists | You mentioned insight/credibility — is there also an information score? |
| 4 | Subscriptions queryable | Can I get user's subscribed series easily? |
| 5 | "Not interested" signal | Does this exist, or should we add it? |

---

## What I Built (Prototype)

- Mock dataset extracted from Serafis (~200 episodes)
- FastAPI backend with recommendation endpoints
- React frontend to test algorithms live

**Purpose:** Validate approach without codebase access. Ready to wire to real data Monday.

---

## Next Steps (If Confirmed)

1. **Week 1:** Integrate with real data tables, instrument rec events
2. **Week 2:** Iterate ranking weights based on CTR/bookmark rate
3. **Week 3:** Add session-based context, improve cold start

---

## Questions for You

1. Should "New from Your Shows" be the only place subscribed series appear, or also in other sections?
2. Is information score available, or just insight/credibility?
3. Any categories to prioritize or exclude for V1?

---

**Bottom line:** Focused on the recommendation algorithm using the exact inputs you provided. Ready to discuss tradeoffs and integrate Monday.
