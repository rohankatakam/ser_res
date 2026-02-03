# Recommendation Engine V1 — Decision Brief

**To:** Rohan Sharma  
**From:** Rohan Katakam  
**Date:** January 29, 2026  
**Re:** EOD Update — Recommendation Engine Trial Prep

---

## TL;DR

- Built a shippable V1 with 5 rec sections + Jump In history, using insight/credibility/info scores and available user signals.
- Added credibility floor ≥2 and clean exclusion/diversification to protect quality and UX.
- Next step is not "more algorithms"—it's locking event semantics + wiring to real tables + instrumentation.

---

## What I Built (Without Codebase Access)

| Component | Status |
|-----------|--------|
| Mock dataset (~200 episodes extracted from Serafis) | ✅ |
| FastAPI backend (6 endpoints) | ✅ |
| React prototype (live algorithm testing) | ✅ |
| 5 recommendation sections + Jump In history | ✅ |
| Full documentation | ✅ |

---

## V1 Sections & Algorithms

| Section | Candidate Source | Scoring | Filters |
|---------|------------------|---------|---------|
| **📊 Insights for You** | Category interests | 60% quality + 40% recency | Cred ≥2, exclude seen |
| **💎 Highest Signal** | Global (past 7 days) | 100% quality | Cred ≥2, exclude seen |
| **🔥 Non-Consensus** | critical_views data | Insight + credibility | Cred ≥3, exclude seen |
| **📡 New from Shows** | Subscribed series | Recency (newest first) | Cred ≥2, exclude seen |
| **🌟 Trending** | Top category | 50% popularity + 30% quality + 20% recency | Cred ≥2, exclude seen |

**Jump In (History):** Viewed + bookmarked episodes sorted by timestamp. Not a recommendation—just history.

---

## Quality Score Formula

```
quality = (insight × 0.45) + (credibility × 0.40) + (information × 0.15)
```

- **Insight (45%):** Serafis's unique value — surfacing novel ideas
- **Credibility (40%):** Investor trust in source authority
- **Information (15%):** Data density (secondary)
- **Entertainment (0%):** Excluded — research tool, not podcast app

**Credibility floor:** Episodes with credibility < 2 filtered out entirely.

---

## Global Rules

| Rule | Implementation |
|------|----------------|
| **Exclusions** | Seen + bookmarked + not-interested |
| **Diversification** | Max 2 episodes per series per section |
| **Cold start** | Global Highest Signal until 2+ views |

---

## Assumptions to Confirm

| # | Assumption | Need |
|---|------------|------|
| 1 | "Visit" = meaningful intent (not just impression) | Confirm event taxonomy |
| 2 | Insight/credibility scores accessible in mobile backend | Confirm API availability |
| 3 | Subscriptions exist as queryable table | Confirm data model |
| 4 | "Not interested" signal exists or can be added | Confirm storage approach |
| 5 | Credibility floor ≥2 is safe globally | Confirm business rules |

---

## Quick Confirmations Needed

1. **Event semantics:** Is "visit" an episode open, play event, or page view? Do we have listen duration/completion?
2. **Subscribed series in recs:** Should Recommendations include subscribed series episodes, or only "New from Your Shows"?
3. **Not interested:** Do we already have this signal, or should we add it?

---

## Instrumentation Plan (For Iteration)

**Minimum events to log:**
- `rec_impression(section, episode_id, position, request_id)`
- `rec_click(section, episode_id, position, request_id)`
- `bookmark_create(episode_id)`
- `not_interested(episode_id)`
- `play_start`, `play_complete`, `dwell_seconds` (if available)

**Success metrics:**
- CTR per section
- Bookmark rate from recs
- Listen completion rate
- 7-day return rate

---

## Monday Plan

| Block | Duration | Focus |
|-------|----------|-------|
| Pair programming | 45 min | Code together, show problem-solving approach |
| Project walkthrough | 45 min | Previous projects, tie to Serafis |
| Trial kickoff | 45 min | Finalize scope, success metrics, milestones |

**Week 1 goal (if trial starts):** Wire V1 to real data tables, instrument events, validate assumptions.

---

## Attachments (Available on Request)

- `RECOMMENDATION_AUDIT.md` — Full parameter mapping + algorithm documentation
- `MONDAY_CHEATSHEET.md` — Talk track + questions for kickoff
- Prototype code — React frontend + FastAPI backend

---

**Bottom line:** I built this without access to prove I can create clarity and momentum from ambiguity. The algorithms are production-structured; the integration is the work ahead. Ready to hit the ground running Monday.

— Rohan K.
