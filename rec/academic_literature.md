# Academic Research Backing Serafis Recommendation Engine

This document traces the research foundations for the Serafis recommendation engine (v1.0 → v1.4) and its evaluation framework. Unlike aspirational "future features," this reflects what is **actually implemented**.

---

## Core Algorithm (v1.0 → v1.4)

The Serafis algorithm originated from a simple brief (January 2026):

> **Original Specification:**
> - Calculate user-specific ranking scores for episode candidates
> - For top 10 episodes in user activity: compute vector similarity, aggregate scores
> - Weight: similarity to interests + quality score (credibility higher) + recency
> - Order activity by engagement depth (bookmarks weighted heavily)

### Implementation Evolution

| Version | Key Changes | Academic Backing |
|---------|-------------|------------------|
| **v1.0** | Baseline: similarity + quality + recency | Standard embedding-based RecSys |
| **v1.2** | Config loading fix, auto-exclusion | Industry best practices (Netflix, Spotify) |
| **v1.3** | 5x bookmark weight, 85% similarity, sum-of-similarities | Engagement signal amplification |
| **v1.4** | 7x bookmark weight | ✅ **Accepted** |

---

## Research Foundations

### 1. Hard Quality Floors for Professional Users

**Paper:** [Scholar Inbox: Personalized Paper Recommendations for Scientists (2025)](https://arxiv.org/abs/2504.08385)

**Influence:** This paper addresses the "High-Signal/Low-Volume" problem in professional research. For experts (scientists, investors), a **hard quality floor** is superior to probabilistic filtering. One low-quality recommendation destroys trust built by ten high-quality ones.

**Application in Serafis:**
```python
# Stage A: Quality Gates
credibility_floor = 2  # No episode with credibility < 2
combined_floor = 5     # All episodes must have C + I >= 5
```

This mirrors the Scholar Inbox approach: enforce minimum standards *before* personalization, ensuring alpha is credible, not clickbait.

**v1.0 → v1.4:** Quality gates are enforced consistently across all versions. Test 03 (Quality Gates) passes with 10.0/10 (0 violations).

---

### 2. Embedding-Based Semantic Similarity

**Foundation:** Standard recommender systems research (2015-2025)

**Core Technique:**
- Embed episode titles + descriptions using OpenAI `text-embedding-3-small` (1536-dim)
- Compute user interest vector from weighted engagements
- Rank candidates by cosine similarity to user vector

**Why This Approach:**
- **Cold start resilience:** New episodes are immediately recommendable via semantic match
- **No collaborative filtering dependency:** Works without user-user or item-item graphs
- **Transparent scoring:** Similarity scores are interpretable

**v1.3 Evolution:** Switched from mean-pooling to `use_sum_similarities: true`, preserving interest diversity across user's top-10 engagements.

---

### 3. Engagement Signal Amplification

**Commercial Precedent:** Spotify Discover Weekly, TikTok For You Page

**Approach:**
```python
engagement_weights = {
    "bookmark": 7.0,  # v1.4: Strong signal of value
    "listen": 1.5,    # Moderate signal
    "click": 1.0      # Weak signal (curiosity)
}
```

**Rationale:** Bookmarks signal "this is alpha I want to revisit." Clicks alone may indicate curiosity, not conviction.

**v1.0 → v1.4 Evolution:**
- v1.0: `bookmark_weight: 2.0` (too weak)
- v1.2: `bookmark_weight: 2.0` (same)
- v1.3: `bookmark_weight: 5.0` (aggressive tuning)
- v1.4: `bookmark_weight: 7.0` (✅ achieves Test 07 pass)

---

### 4. Recency Decay for Freshness

**Standard Technique:** Exponential decay with half-life

**Implementation:**
```python
recency_lambda = 0.03  # ~23 day half-life
recency_score = exp(-lambda * days_since_publish)
```

**Rationale:** Investors need current insights. A 3-month-old podcast about Fed policy may be outdated. Decay ensures freshness without completely excluding older evergreen content.

**v1.0 → v1.4:** Consistently uses `recency_lambda: 0.03`. v1.3/v1.4 reduce recency weight (`0.15 → 0.05`) to prioritize personalization over timeliness.

---

### 5. Cold Start Mode

**Research Context:** Cold start is a classic RecSys challenge for new users with no engagement history.

**Serafis Approach:**
```python
cold_start_config = {
    "weight_quality": 0.60,   # Showcase best content
    "weight_recency": 0.40    # Prioritize current topics
}
# No similarity component (no user vector yet)
```

**Rationale:** For first-time users, show the highest-quality, most-recent content to establish trust. Once they engage, switch to personalized mode.

**Test Results:** Test 01 (Cold Start Quality) passes deterministic criteria (credibility >= 4.0 avg, quality >= 0.7) with 10.0/10 in all versions.

---

## Evaluation Framework (Multi-LLM Judge System)

The evaluation infrastructure (Phase 6) is grounded in the latest research on LLM-as-a-Judge systems, specifically addressing reliability, bias correction, and aggregation strategies.

### 6. Bias-Corrected Aggregation for Multi-LLM Judges

**Paper:** [How to Correctly Report LLM-as-a-Judge Evaluations (2025)](https://arxiv.org/abs/2511.21140)

**Influence:** Demonstrates that uncalibrated LLM judges systematically bias results due to position bias, verbosity bias, and model-specific quirks. Simple averaging across models is suboptimal.

**Application in Serafis:** The **two-stage aggregation pipeline** (within-model mean → cross-model mean) with standard deviation reporting. Future enhancement: bias-corrected aggregation with calibration data.

---

### 7. Distribution-Calibrated Inference

**Paper:** [Distribution-Calibrated BTD (Bradley-Terry-Dawid) Inference (2025)](https://arxiv.org/abs/2512.03019)

**Influence:** Shows that repeated sampling from a judge with `temperature > 0` produces a judgment distribution that better captures uncertainty than single greedy decoding.

**Application in Serafis:**
```python
judge_config = {
    "temperature": 0.8,      # Stochastic sampling
    "default_n": 3,          # 3 samples per judge
    "judges": [
        "gpt-5-mini",         # OpenAI
        "gemini-2.5-flash",   # Google
        "claude-sonnet-4-5"   # Anthropic
    ]
}
```

Within-model aggregation uses the mean of the judgment distribution (not a single greedy sample).

---

### 8. Optimal Sampling Without Verifiers

**Paper:** [Large Language Monkeys: Scaling Inference Compute with Repeated Sampling (2024)](https://arxiv.org/abs/2407.21787)

**Influence:** Key finding: for qualitative evaluation tasks without automatic verifiers, performance plateaus at **N=5-10 samples**. Beyond this, diminishing returns.

**Application in Serafis:** Default `N=3` samples per judge (configurable up to 10 via UI). This balances reliability with API cost, using repeated sampling for variance reduction rather than coverage.

---

### 9. Temperature and Stochastic Sampling

**Paper:** [Improving LLM-as-a-Judge Inference: Distributional Decoding and Temperature Tuning (2025)](https://arxiv.org/abs/2503.03064)

**Critical Finding:**
- **Temperature = 0.0 (greedy):** Worst for judges, loses distributional signal
- **Temperature = 0.7-1.0:** Optimal for diverse, well-calibrated judgments
- **Avoid Chain-of-Thought:** CoT "collapses" the judgment distribution

**Application in Serafis:** All judges use **temperature=0.8** with **no CoT prompting**, enabling diverse sampling while maintaining scoring consistency.

---

### 10. Inter-Model Consensus as Reliability Signal

**Paper:** [Enhancing Answer Reliability Through Inter-Model Consensus (2024)](https://arxiv.org/abs/2411.16797)

**Influence:** Cross-model standard deviation predicts answer reliability. Low consensus (high std) should trigger human review.

**Application in Serafis:**

```python
# Consensus categorization
if cross_model_std < 0.5:
    consensus = "STRONG"
    confidence = "HIGH"
elif cross_model_std < 1.0:
    consensus = "GOOD"
    confidence = "HIGH"
elif cross_model_std < 1.5:
    consensus = "PARTIAL"
    confidence = "MEDIUM"
else:
    consensus = "LOW"
    confidence = "LOW"
    flag_for_review = True
```

UI displays per-model breakdowns (OpenAI, Gemini, Anthropic scores + reasoning) to surface disagreements.

---

### 11. Confidence-Weighted Voting (Future Enhancement)

**Paper:** [Confidence Improves Self-Consistency in LLM Reasoning (2025)](https://arxiv.org/abs/2502.06233)

**Influence:** Weighting judge outputs by self-assessed confidence improves aggregate reliability, especially for ambiguous cases.

**Status in Serafis:** Not yet implemented (planned for Phase 6.B). Current consensus metrics (STRONG/GOOD/PARTIAL/LOW) provide foundation for confidence-weighted aggregation.

---

## Summary Tables

### Core Algorithm Research Backing

| Feature | Research Foundation |
|---------|-------------------|
| **Quality Gates (C >= 2, C+I >= 5)** | [Scholar Inbox (2025)](https://arxiv.org/abs/2504.08385) |
| **Embedding-Based Similarity** | Standard RecSys (2015-2025) |
| **Bookmark Amplification (7x)** | Industry patterns (Spotify, TikTok) |
| **Recency Decay (23-day half-life)** | Standard temporal weighting |
| **Cold Start Mode** | RecSys best practices |

### Evaluation Framework Research Backing

| Evaluation Component | Research Foundation |
|---------------------|-------------------|
| **Two-Stage Aggregation** | [Bias-Corrected Reporting (2025)](https://arxiv.org/abs/2511.21140) |
| **N=3 Samples, temp=0.8** | [Distribution-Calibrated BTD (2025)](https://arxiv.org/abs/2512.03019) + [Improving Inference (2025)](https://arxiv.org/abs/2503.03064) |
| **Optimal N Range (5-10)** | [Large Language Monkeys (2024)](https://arxiv.org/abs/2407.21787) |
| **Consensus Metrics (STRONG/GOOD/PARTIAL/LOW)** | [Inter-Model Consensus (2024)](https://arxiv.org/abs/2411.16797) |
| **Future: Confidence Weighting** | [Confidence Improves Self-Consistency (2025)](https://arxiv.org/abs/2502.06233) |

---

## What's NOT in Serafis

To maintain clarity, here are features mentioned in other RecSys research but **not implemented** in Serafis v1.0-v1.4:

- ❌ **Generative Ranking:** We use traditional scoring, not sequential generation
- ❌ **POV Waterfall or Narrative Re-ranking:** No multi-stage diversity logic
- ❌ **Semantic IDs:** We use standard OpenAI embeddings, not hierarchical tokenization
- ❌ **LLM-powered POV Derivation:** Metadata is pre-computed, not generated per-query
- ❌ **Category Overlap Scoring:** Deferred to future versions (mentioned in original spec as "v2")
- ❌ **Collaborative Filtering:** Pure content-based approach, no user-user or item-item graphs

**Design Philosophy:** Serafis prioritizes simplicity, interpretability, and cold-start resilience over complex multi-stage pipelines. The algorithm is **configuration-driven** (all v1.0→v1.4 improvements are parameter tuning, zero code changes), making it easy to experiment and deploy.

---

## Market Position

| Dimension | TikTok For You | Bloomberg Terminal | **Serafis** |
|-----------|----------------|-------------------|------------|
| **Quality Control** | None (viral focus) | Manual curation | Hard quality floors (C >= 2) |
| **Personalization** | Deep (engagement graph) | None (keyword search) | Semantic similarity (embeddings) |
| **Cold Start** | Poor (needs engagement) | N/A (search-based) | Strong (quality + recency) |
| **Transparency** | Black box | Fully transparent | Interpretable scores |

**Serafis Positioning:** High-signal personalization for professional investors, combining Bloomberg's quality standards with TikTok's discovery experience—without the filter bubble or credibility risks.

---

## Key Insight: Simplicity as a Feature

The multi-LLM evaluation framework captures different "perspectives" on quality. OpenAI, Gemini, and Anthropic have different biases and evaluation styles. By aggregating across models with proper uncertainty quantification, we achieve more robust evaluation than any single judge, while surfacing genuinely ambiguous cases for human review.

**Example from Test Reports:**
```
llm_hypothesis_alignment:
  OpenAI:    5.0/10 (σ=0.00) - Very sure it's mediocre
  Gemini:    7.0/10 (σ=0.00) - Very sure it's good
  Anthropic: 3.3/10 (σ=0.47) - Very sure it's poor
  → Cross-model std=1.50 → LOW consensus → Flag for human review ⚠️
```

This transparency is only possible because the core algorithm is simple enough to reason about. More complex multi-stage pipelines would make LLM judge reasoning much harder to calibrate.

---

By combining academic rigor with pragmatic simplicity, Serafis achieves a "Bloomberg for the TikTok generation" architecture—high-signal discovery without sacrificing professional standards.
