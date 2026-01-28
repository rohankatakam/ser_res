# Quality Framework — Trial Project Proposal

> **For our sync:** Wednesday, Jan 28 (2:00pm PT)  
> **Purpose:** Align on trial scope and quality dimensions

---

## Overview

This document is structured for a **30-minute decision meeting**. Each section has 1-2 key decisions. Total: **7 decision points**.

---

## Section 1: Trial Scope (5 min)

### 1.1: Trial Duration
> **How long is the trial period?**

| Option | Scope | Deliverables |
|--------|-------|--------------|
| **A. 2 weeks** | Quality Framework only | Spec, Evaluation Dataset, Baseline Report |
| **B. 4 weeks** | Framework + Quick Wins | Above + 2-3 targeted improvements |
| **C. 4 weeks** | Framework + Rating Engine | Above + Bullish/Bearish rating prototype (see Appendix) |

**Context:** Option C builds toward the Robinhood/Webull integration you mentioned. The rating engine depends on validated quality signals — see Appendix for details.

**Our Decision:** _______________________________________________________

---

### 1.2: Trial Focus
> **What is the primary deliverable?**

| Option | Focus | Risk |
|--------|-------|------|
| **A. Measurement** | Build evaluation infrastructure, establish baseline | Doesn't ship user-visible improvement |
| **B. Improvement** | Fix 2-3 quality gaps based on McKinsey feedback | May optimize wrong things without baseline |
| **C. A → B** | Baseline first, then targeted fixes | Takes longer, but data-driven |

**Our Decision:** _______________________________________________________

---

## Section 2: Priority Signals (5 min)

### 2.1: Customer-Driven Prioritization
> **What does McKinsey actually use and care about?**

| Question | Rohan's Input |
|----------|---------------|
| Which search mode has highest usage? (Org/Person/Theme/Ask AI) | _______ |
| Top 3 complaints or feature requests from McKinsey? | _______ |
| What differentiates Serafis from alternatives for them? | _______ |

---

### 2.2: Feature Priority
> **Based on customer signal, how should we prioritize?**

| Priority | Features | Rationale |
|----------|----------|-----------|
| **P0 (Must evaluate)** | Ask AI, Org Search | Core workflows |
| **P1 (Should evaluate)** | Person Search, Episode Analysis | Supporting features |
| **P2 (Minimal)** | Theme Search | Lower usage |
| **P3 (Skip)** | Discover, Bookmarks, AI Queries | Utility features |

**Proposed:** Focus 80% of evaluation effort on P0.

**Our Decision on Priorities:** _______________________________________________________

---

## Section 3: Core Quality Dimensions (10 min)

> *These are the quality signals that make Serafis "institutional-grade" per the investor memo.*

### 3.1: Credibility Weighting
> **Should speaker credibility influence search ranking?**

The investor memo's moat is "credibility-weighted narratives." Currently, episode-level Credibility scores (★★★★) exist but don't affect search ranking.

| Option | Description |
|--------|-------------|
| **A. Boost Ranking** | High-credibility episodes rank higher automatically |
| **B. Filter Option** | User can filter "★★★+ Credibility only" |
| **C. Display Only** | Show scores in results, user decides |
| **D. Phase 2** | Don't change ranking for trial |

**Proposed:** B (filter option) as quick win, roadmap to A.

**Our Decision:** _______________________________________________________

---

### 3.2: Non-Consensus / "Priced-In" Detection
> **How do we surface alpha-generating (non-consensus) vs. priced-in ideas?**

The investor memo states: *"evaluate to what extent a claim is non-consensus or priced-in."* Currently, "Critical Views" section exists in Episode Analysis but isn't searchable or tagged in Ask AI answers.

| Priority Question | Notes |
|-------------------|-------|
| Is non-consensus detection core to McKinsey value? | _______ |
| Should Ask AI tag claims as "Non-Consensus" / "Consensus"? | _______ |
| Is this P0 for trial or roadmap item? | _______ |

**Our Decision on Non-Consensus Priority:** _______________________________________________________

---

### 3.3: Recency Weighting
> **Should more recent content rank higher?**

For institutional products (Robinhood, TipRanks), recency is key. TipRanks uses 3-month windows. Podcast content differs, but stale narratives may be less valuable.

| Option | Description |
|--------|-------------|
| **A. No Default Weight** | Recency shown but doesn't affect ranking |
| **B. Decay Function** | Weight decays over time (e.g., 0.75× after 90 days) |
| **C. User Toggle** | "Most Recent" vs "Most Relevant" sort option |

**Proposed:** C (user toggle) — lowest implementation risk.

**Our Decision:** _______________________________________________________

---

### 3.4: Speed Requirements
> **What latency is acceptable for search and AI responses?**

| Feature | Target Latency | Priority |
|---------|----------------|----------|
| Org/Person Search | < 2 seconds | P0 |
| Ask AI (RAG) | < 5 seconds | P0 |
| Episode Detail Load | < 1 second | P1 |
| Rating Engine (future, see Appendix) | < 500ms (pre-computed) | P2 |

**Key Question:** Are there current speed issues? _______ 

**Our Decision on Speed Targets:** _______________________________________________________

---

## Section 4: Evaluation Approach (5 min)

### 4.1: Evaluation Dataset
> **How many test queries, and what mix?**

| Feature | # of Queries | Example |
|---------|--------------|---------|
| Org Search | 10 | "OpenAI" — expect operator interviews ranked high |
| Person Search | 5 | "Jensen Huang" — expect guest episodes first |
| Ask AI | 10 | "What are bearish views on OpenAI?" |
| Episode Analysis | 5 | Verify Credibility scores accuracy |

**Total:** 30 test cases (can expand to 50 if needed)

**Our Decision on Dataset Size:** _______________________________________________________

---

### 4.2: Evaluation Cadence
> **How often do we measure quality?**

| Phase | Cadence |
|-------|---------|
| Trial | One-time baseline, then end-of-trial comparison |
| Post-trial | Weekly regression checks |
| Future | Continuous monitoring (production) |

**Our Decision:** _______________________________________________________

---

## Section 5: Success Criteria (5 min)

### 5.1: Trial Deliverables
> **What must be completed for a successful trial?**

| Deliverable | Required? | Notes |
|-------------|-----------|-------|
| Finalized Quality Spec | ⬜ Yes / ⬜ No | This document, with decisions filled in |
| Evaluation Dataset (30 queries) | ⬜ Yes / ⬜ No | Benchmark queries with expected outcomes |
| Baseline Report | ⬜ Yes / ⬜ No | Current quality scores documented |
| Quick Wins (2-3 fixes) | ⬜ Yes / ⬜ No | Targeted improvements based on gaps |
| Rating Engine Prototype | ⬜ Yes / ⬜ No | Only if Option C selected (see Appendix) |

**Our Decision:** _______________________________________________________

---

### 5.2: Quality Targets
> **What quality bar defines success?**

| Metric | Baseline (TBD) | Target |
|--------|----------------|--------|
| Org Search Precision@5 | ___% | ≥ 80% |
| Ask AI Citation Accuracy | ___% | ≥ 90% |
| Speed (P95 latency) | ___ ms | ≤ target |

**Our Decision on Targets:** _______________________________________________________

---

## Summary: Decision Checklist

| # | Decision | Status |
|---|----------|--------|
| 1.1 | Trial Duration | ⬜ |
| 1.2 | Trial Focus | ⬜ |
| 2.2 | Feature Priority | ⬜ |
| 3.1 | Credibility Weighting | ⬜ |
| 3.2 | Non-Consensus Detection Priority | ⬜ |
| 3.3 | Recency Weighting | ⬜ |
| 3.4 | Speed Requirements | ⬜ |
| 4.1 | Evaluation Dataset Size | ⬜ |
| 4.2 | Evaluation Cadence | ⬜ |
| 5.1 | Trial Deliverables | ⬜ |
| 5.2 | Quality Targets | ⬜ |

**Total:** 11 decision points

---

## Notes from Discussion

_Space for live notes during the meeting_

---

## Appendix: Rating Engine (Option C Context)

The **Bullish/Bearish Rating Engine** is a potential Phase 2 feature that aggregates podcast sentiment into actionable ratings — similar to TipRanks or Robinhood's "Buy/Hold/Sell" analyst consensus section.

**How it connects to the Quality Framework:**

| Framework Signal | Rating Engine Use |
|------------------|-------------------|
| Credibility weighting | Weight ratings by speaker authority (CEO > analyst > commentator) |
| Recency scoring | Time-decay for prediction relevance (recent opinions weighted higher) |
| Non-consensus detection | Surface contrarian signals that may indicate alpha |

**Why it's Option C (not default):** The Rating Engine depends on validated quality signals. Building the Framework first de-risks this feature by ensuring the underlying data quality meets institutional standards.

*This is included to show roadmap connection, but is not required for the trial.*
