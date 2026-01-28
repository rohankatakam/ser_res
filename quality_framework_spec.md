# Quality Framework — Trial Project Proposal

> **For our sync:** Wednesday, Jan 28 (2:00pm PT)  
> **Purpose:** Align on trial scope and quality dimensions  
> **Format:** Proposal with recommendations — happy to adjust based on your input

---

## 1. Trial Scope

### 1.1 Trial Duration

| Option | Scope | Deliverables |
|--------|-------|--------------|
| **A. 1 week** | Quality Framework only | Spec, Evaluation Dataset, Baseline Report |
| **B. 2 weeks** | Framework + Quick Wins | Above + 2-3 targeted improvements |

**My recommendation:** Option B (2 weeks). Week 1 establishes the baseline; Week 2 ships improvements based on what we find. A baseline without action feels incomplete.

---

### 1.2 Trial Focus

| Option | Focus | Trade-off |
|--------|-------|-----------|
| **A. Measurement** | Build evaluation infrastructure, establish baseline | Rigorous, but no user-visible improvement |
| **B. Improvement** | Fix 2-3 quality gaps based on McKinsey feedback | Ships faster, but may optimize wrong things |
| **C. A → B** | Baseline first, then targeted fixes | Takes longer, but data-driven |

**My recommendation:** Option C. Measure first (Week 1), then fix based on data (Week 2). This ensures we're improving what actually matters.

---

## 2. Feature Priority

### 2.1 Questions for You

To prioritize effectively, it would help to understand:
- Which search mode has highest McKinsey usage? (Org Search, Person Search, Theme Search, or Ask AI?)
- What are the top 2-3 complaints or requests from McKinsey?
- What differentiates Serafis from alternatives for them?

### 2.2 Proposed Priority

Based on my product exploration, I'd propose:

| Priority | Features | Rationale |
|----------|----------|-----------|
| **P0 (Must evaluate)** | Ask AI, Org Search | These appear to be core workflows |
| **P1 (Should evaluate)** | Person Search, Episode Analysis | Supporting features with good depth |
| **P2 (Minimal)** | Theme Search | Appears lower usage |
| **P3 (Skip for trial)** | Discover, Bookmarks, AI Queries | Utility features |

**Proposed approach:** Focus 80% of evaluation effort on P0. Happy to adjust based on actual usage data.

---

## 3. Core Quality Dimensions

These are the quality signals that move Serafis toward "institutional-grade" per the investor memo.

### 3.1 Credibility Weighting

**Context:** The investor memo's moat is "credibility-weighted narratives." Currently, episode-level Credibility scores (★★★★) exist but don't appear to affect search ranking.

| Option | Description |
|--------|-------------|
| **A. Boost Ranking** | High-credibility episodes rank higher automatically |
| **B. Filter Option** | User can filter "★★★+ Credibility only" |
| **C. Display Only** | Show scores in results, user decides |
| **D. Phase 2** | Don't change ranking for trial |

**My recommendation:** Start with B (filter option) as a quick win during the trial. It's low-risk and immediately useful. Roadmap to A if users respond well.

---

### 3.2 Non-Consensus Detection

**Context:** The investor memo states: *"evaluate to what extent a claim is non-consensus or priced-in."* Currently, a "Critical Views" section exists in Episode Analysis but isn't surfaced in search or Ask AI answers.

**Questions to discuss:**
- Is non-consensus detection core to McKinsey's use case, or more relevant for hedge fund users?
- Should Ask AI tag claims as "Non-Consensus" vs "Consensus"?

**My recommendation:** Evaluate during trial, but likely P1 (not P0). It's valuable but complex — we should nail credibility weighting first.

---

### 3.3 Recency Weighting

**Context:** For institutional products, recency matters. TipRanks uses 3-month windows. Podcast content may differ, but stale narratives are likely less valuable.

| Option | Description |
|--------|-------------|
| **A. No Default Weight** | Recency shown but doesn't affect ranking |
| **B. Decay Function** | Weight decays over time (e.g., 0.75× after 90 days) |
| **C. User Toggle** | "Most Recent" vs "Most Relevant" sort option |

**My recommendation:** C (user toggle). Lowest implementation risk, gives users control. We can analyze toggle usage to inform whether decay should become default.

---

### 3.4 Speed

**Context:** Speed is table stakes for a research tool.

| Feature | Proposed Target |
|---------|-----------------|
| Org/Person Search | < 2 seconds |
| Ask AI (RAG) | < 5 seconds |
| Episode Detail Load | < 1 second |

**Question:** Are there current speed issues I should be aware of? During my testing, things felt responsive, but I'd want to confirm with real usage data.

---

## 4. Evaluation Approach

### 4.1 Evaluation Dataset

I'd propose starting with 30 test queries across four feature types:

| Feature | # of Queries | Example |
|---------|--------------|---------|
| Org Search | 10 | "OpenAI" — expect operator interviews to rank high |
| Person Search | 5 | "Jensen Huang" — expect guest episodes first |
| Ask AI | 10 | "What are bearish views on OpenAI?" |
| Episode Analysis | 5 | Verify Credibility/Insight scores feel accurate |

### 4.2 Methodology by Feature Type

**Org Search / Person Search (Retrieval)**

These are straightforward to evaluate:
1. For each query, use Apple Podcasts + Spotify + Serafis itself to identify 5-10 episodes that *should* rank high
2. Create ground truth: `Query → Expected Top 5 Episodes`
3. Run query in Serafis, compare actual results to expected
4. **Metric:** Precision@5 — How many of Serafis's top 5 match our expected list?

**Ask AI (Generation)**

This is harder — there's no single "correct" answer. I'd propose evaluating two dimensions:

| Dimension | Question | Method |
|-----------|----------|--------|
| **Citation Relevance** | Are the cited episodes actually about the topic? | LLM-as-a-Judge + spot-check |
| **Answer Groundedness** | Is the answer supported by those citations? | LLM-as-a-Judge + spot-check |

For LLM-as-a-Judge, we prompt a model to evaluate each citation:
> "Given query X and citation Y, is this citation relevant? (Yes/Partially/No)"

Then spot-check a sample manually to ensure the LLM isn't too lenient or strict.

**Episode Analysis (Scoring)**

This is subjective — we're checking if Credibility/Insight scores "feel right."

1. Pick 5 episodes with varying scores (mix of ★★, ★★★, ★★★★)
2. Review speaker info, episode summary, and a sample of the transcript
3. Ask: "Does this Credibility score feel accurate?"
4. Document disagreements and patterns

This isn't about precision metrics — it's about calibrating whether the scoring logic makes sense.

---

## 5. Success Criteria

### 5.1 Trial Deliverables

| Deliverable | Included? | Notes |
|-------------|-----------|-------|
| Finalized Quality Spec | ✅ | This document, with our aligned decisions |
| Evaluation Dataset (30 queries) | ✅ | Queries + ground truth + methodology |
| Baseline Report | ✅ | Current scores documented, gaps identified |
| 2-3 Quick Wins | ✅ | Targeted improvements (if Option B selected) |

**Measurement approach:** Rather than setting hard targets upfront (which would be guessing), I'll establish a baseline first, identify where results feel wrong and why, then demonstrate measurable improvement after fixes.

---

## 6. Discussion Topics for Our Call

1. **McKinsey signal** — What do they actually use and care about?
2. **Trial duration** — 1 week vs 2 weeks?
3. **Priority alignment** — Does my P0/P1/P2 match your intuition?
4. **Credibility weighting** — Is the filter option a good starting point?
5. **Anything I'm missing** — Gaps in my understanding of the product or customer?

---

## Future Consideration: Rating Engine

One feature we discussed was a **Bullish/Bearish Rating Engine** — similar to Robinhood's "Buy/Hold/Sell" analyst section but powered by podcast data.

This is compelling, but I believe it depends on getting the Quality Framework right first:

| Framework Signal | Rating Engine Dependency |
|------------------|--------------------------|
| Credibility weighting | Weight ratings by speaker authority |
| Recency scoring | Recent opinions weighted higher |
| Non-consensus detection | Surface contrarian signals |

**My take:** The Rating Engine is a great Phase 2 goal. Building the Quality Framework now de-risks it by ensuring the underlying data quality meets institutional standards.

---

Looking forward to discussing tomorrow.
