# Deep Dive 03: Quality Gates Subsystem

> *Hard filters that ensure only investor-grade content enters the recommendation pipeline.*

**Document:** 3 of 8  
**Subsystem:** Quality Gates  
**Pipeline Stage:** Stage 2 (Pre-Scoring Filters)  
**Status:** Final

---

## 1. Purpose

Quality Gates are **hard rejection filters** that run before scoring. They ensure that no episode enters the recommendation pool unless it meets minimum quality and relevance thresholds.

This subsystem implements the "Trust" pillar of Serafis's value proposition — investors must be able to trust that recommended content comes from credible sources.

---

## 2. Subsystem Context

```
┌─────────────────────────────────────────────────────────────────┐
│                   QUALITY GATES SUBSYSTEM                        │
│                      (This Document)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUTS                                                         │
│  ──────                                                         │
│  • E.scores.credibility (from Episode catalog)                  │
│  • E.scores.insight (from Episode catalog)                      │
│  • E.id (Episode identifier)                                    │
│  • U.excluded_ids (from User data)                              │
│                                                                  │
│                         │                                        │
│                         ▼                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Gate 1 → Gate 2 → Gate 3                               │    │
│  │  (Sequential evaluation; REJECT on any failure)         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                         │                                        │
│                         ▼                                        │
│                                                                  │
│  OUTPUT                                                         │
│  ──────                                                         │
│  • PASS: Episode proceeds to scoring                            │
│  • REJECT: Episode excluded from recommendation pool            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Stage 2: Scoring   │
                    │  (Only PASSED       │
                    │   episodes)         │
                    │  (Document 04)      │
                    └─────────────────────┘
```

---

## 3. Input Parameters

| Parameter | Source | Type | Description |
|-----------|--------|------|-------------|
| `E.scores.credibility` | Document 01 | Integer (1–4) | Speaker authority and track record |
| `E.scores.insight` | Document 01 | Integer (1–4) | Novelty and depth of ideas |
| `E.id` | Document 01 | String | Unique episode identifier |
| `U.excluded_ids` | Document 01 | Set[String] | Episodes user has seen, bookmarked, or dismissed |

---

## 4. Output Parameters

| Parameter | Type | Values | Description |
|-----------|------|--------|-------------|
| `gate_result` | Enum | PASS, REJECT | Whether episode proceeds to scoring |
| `rejection_reason` | String \| null | Gate identifier if rejected | For debugging/logging |

---

## 5. Gate Definitions

### 5.1 Gate 1: Credibility Floor

```
┌─────────────────────────────────────────────────────────────────┐
│  GATE 1: CREDIBILITY FLOOR                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Rule: IF E.scores.credibility < 2 → REJECT                     │
│                                                                  │
│  Rationale: Investors cannot rely on unverified sources.        │
│             A credibility score of 1 indicates unknown or       │
│             unverifiable speaker authority.                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

| Parameter | Value | Tunable? | Rationale |
|-----------|-------|----------|-----------|
| Credibility threshold | ≥ 2 | 🔒 Fixed | Non-negotiable investor safety requirement |

**What Credibility Scores Mean:**

| Score | Interpretation | Example |
|-------|----------------|---------|
| 4 | Exceptional authority | CEO of Fortune 500, renowned expert |
| 3 | Strong authority | Senior executive, established founder |
| 2 | Adequate authority | Industry professional, verified analyst |
| 1 | Unknown/unverified | Anonymous source, unverified claims |

**Rejection Examples:**
- Anonymous industry insider (C=1) → REJECT
- New analyst with unverified track record (C=1) → REJECT
- Junior employee discussing company strategy (C=1) → REJECT

---

### 5.2 Gate 2: Combined Signal Floor

```
┌─────────────────────────────────────────────────────────────────┐
│  GATE 2: COMBINED SIGNAL FLOOR                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Rule: IF (E.scores.credibility + E.scores.insight) < 5 → REJECT│
│                                                                  │
│  Rationale: Even credible speakers can produce low-value        │
│             content. This gate ensures minimum combined quality.│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

| Parameter | Value | Tunable? | Range | Rationale |
|-----------|-------|----------|-------|-----------|
| Combined threshold | ≥ 5 | ⚙️ Yes | 4–6 | Balances content volume with quality |

**Why C + I ≥ 5?**

This creates a quality surface where episodes must have meaningful value:

| Credibility | Insight | Sum | Gate 2 Result |
|-------------|---------|-----|---------------|
| 4 | 1 | 5 | ✅ PASS (expert, weak content) |
| 3 | 2 | 5 | ✅ PASS (good expert, adequate insight) |
| 2 | 3 | 5 | ✅ PASS (adequate expert, strong insight) |
| 2 | 2 | 4 | ❌ REJECT (mediocre on both) |
| 3 | 1 | 4 | ❌ REJECT (good expert, weak content) |

**Note:** An episode with (C=4, I=1) passes Gate 2 but represents a "credible but boring" episode. This is acceptable — the user may still value hearing from the expert even if this particular episode isn't insightful.

---

### 5.3 Gate 3: Exclusion Filter

```
┌─────────────────────────────────────────────────────────────────┐
│  GATE 3: EXCLUSION FILTER                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Rule: IF E.id ∈ U.excluded_ids → REJECT                        │
│                                                                  │
│  Rationale: Never recommend content the user has already        │
│             seen, saved, or explicitly dismissed.               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

| Parameter | Value | Tunable? | Rationale |
|-----------|-------|----------|-----------|
| Exclusion set | U.excluded_ids | 🔒 Fixed | Basic UX requirement — no repeats |

**U.excluded_ids Composition:**
```
U.excluded_ids = U.seen_episode_ids ∪ U.bookmarked_episode_ids ∪ U.not_interested_ids
```

---

## 6. Gate Evaluation Order

Gates are evaluated **sequentially**. Evaluation stops at the first failure.

```
┌─────────────────────────────────────────────────────────────────┐
│                    GATE EVALUATION FLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Episode E                                                      │
│      │                                                          │
│      ▼                                                          │
│  ┌─────────────┐                                                │
│  │   Gate 1    │ ──── C < 2? ──── YES ──▶ REJECT (gate_1)      │
│  │ Credibility │                                                │
│  └──────┬──────┘                                                │
│         │ NO                                                    │
│         ▼                                                       │
│  ┌─────────────┐                                                │
│  │   Gate 2    │ ── C+I < 5? ─── YES ──▶ REJECT (gate_2)       │
│  │  Combined   │                                                │
│  └──────┬──────┘                                                │
│         │ NO                                                    │
│         ▼                                                       │
│  ┌─────────────┐                                                │
│  │   Gate 3    │ ── in excluded? ─ YES ──▶ REJECT (gate_3)     │
│  │  Exclusion  │                                                │
│  └──────┬──────┘                                                │
│         │ NO                                                    │
│         ▼                                                       │
│      ✅ PASS                                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Why This Order?**

1. **Gate 1 first:** Cheapest check (single field comparison). Filters low-credibility content immediately.
2. **Gate 2 second:** Slightly more expensive (two fields). Filters mediocre content.
3. **Gate 3 last:** Potentially most expensive (set membership check). Only runs on quality content.

---

## 7. Algorithm Implementation

```python
from enum import Enum
from dataclasses import dataclass

class GateResult(Enum):
    PASS = "pass"
    REJECT = "reject"

@dataclass
class GateOutcome:
    result: GateResult
    rejection_reason: str | None = None

def evaluate_gates(episode: Episode, user: User) -> GateOutcome:
    """
    Evaluate all quality gates for an episode.
    
    Returns:
        GateOutcome with PASS or REJECT status
    """
    
    # Gate 1: Credibility Floor
    if episode.scores.credibility < CREDIBILITY_THRESHOLD:  # 2
        return GateOutcome(
            result=GateResult.REJECT,
            rejection_reason="gate_1_credibility"
        )
    
    # Gate 2: Combined Signal Floor
    combined = episode.scores.credibility + episode.scores.insight
    if combined < COMBINED_THRESHOLD:  # 5
        return GateOutcome(
            result=GateResult.REJECT,
            rejection_reason="gate_2_combined"
        )
    
    # Gate 3: Exclusion Filter
    if episode.id in user.excluded_ids:
        return GateOutcome(
            result=GateResult.REJECT,
            rejection_reason="gate_3_excluded"
        )
    
    # All gates passed
    return GateOutcome(result=GateResult.PASS)
```

---

## 8. Constants Summary

| Constant | Symbol | Value | Tunable? | Used In |
|----------|--------|-------|----------|---------|
| Credibility threshold | C_MIN | 2 | 🔒 Fixed | Gate 1 |
| Combined threshold | CI_MIN | 5 | ⚙️ Yes | Gate 2 |

---

## 9. Edge Cases

### 9.1 Boundary Conditions

| Scenario | C | I | C+I | Gate 1 | Gate 2 | Final |
|----------|---|---|-----|--------|--------|-------|
| Perfect episode | 4 | 4 | 8 | ✅ | ✅ | PASS |
| Expert, weak insight | 4 | 1 | 5 | ✅ | ✅ | PASS |
| New analyst, strong insight | 2 | 3 | 5 | ✅ | ✅ | PASS |
| Mediocre on both | 2 | 2 | 4 | ✅ | ❌ | REJECT |
| Good expert, weak insight | 3 | 1 | 4 | ✅ | ❌ | REJECT |
| Unknown source, brilliant | 1 | 4 | 5 | ❌ | — | REJECT |
| Unknown source, mediocre | 1 | 2 | 3 | ❌ | — | REJECT |

### 9.2 The "Whistleblower Risk"

**Scenario:** A breaking news episode from an unverified source (C=1) contains genuinely important, market-moving information (I=4).

**Current Behavior:** REJECT at Gate 1 (C < 2)

**Tradeoff Analysis:**

| Approach | Pros | Cons |
|----------|------|------|
| **Reject (current)** | Maintains trust; no false positives | May miss breaking news |
| **Allow (alternative)** | Catches breaking news | Risks recommending misinformation |

**V1 Decision:** Reject. Investor trust is paramount.

**V2 Consideration:** Velocity Bypass — high-velocity content from unverified sources routes to a "Speculative" slot with an "Unverified" badge (see Document 08).

### 9.3 Empty Feed Risk

**Scenario:** User has excluded all high-quality episodes; remaining episodes fail gates.

**Current Behavior:** Empty feed returned

**Mitigation:**
- Monitor rejection rates per user
- If >95% rejection rate, alert for investigation
- Consider expanding catalog or relaxing Combined threshold (CI_MIN = 4)

---

## 10. Worked Example

**Episode Under Evaluation:**
```json
{
  "id": "B7d9XwUOKOuoH7R8Tnzi",
  "title": "Gokul Rajaram - Lessons from Investing in 700 Companies",
  "scores": {
    "insight": 3,
    "credibility": 4,
    "information": 3,
    "entertainment": 2
  }
}
```

**User Context:**
```json
{
  "excluded_ids": ["abc123", "def456", "ghi789"]
}
```

**Gate Evaluation:**

| Gate | Check | Value | Threshold | Result |
|------|-------|-------|-----------|--------|
| Gate 1 | C ≥ 2? | 4 | 2 | ✅ PASS |
| Gate 2 | C + I ≥ 5? | 4 + 3 = 7 | 5 | ✅ PASS |
| Gate 3 | id ∈ excluded? | "B7d9..." ∉ excluded | — | ✅ PASS |

**Final Result:** PASS — Episode proceeds to scoring.

---

## 11. Tuning Guidance

### 11.1 Adjusting Combined Threshold

| Symptom | Current CI_MIN | Adjustment | New CI_MIN |
|---------|----------------|------------|------------|
| Feed feels low quality | 5 | Increase | 6 |
| Feed is too sparse/empty | 5 | Decrease | 4 |
| Good content being rejected | 5 | Investigate scores | — |

### 11.2 Monitoring Metrics

| Metric | Description | Target | Alert If |
|--------|-------------|--------|----------|
| Gate 1 rejection rate | % rejected by credibility | <5% | >10% (catalog quality issue) |
| Gate 2 rejection rate | % rejected by combined | <15% | >25% (threshold too strict) |
| Gate 3 rejection rate | % rejected by exclusion | Varies by user | >80% (power user, may need more content) |
| Total pass rate | % passing all gates | >70% | <50% |

---

## 12. Traceability

### 12.1 Design Decisions

| Decision | Rationale | Academic/Commercial Backing |
|----------|-----------|----------------------------|
| Hard credibility floor (C ≥ 2) | Investor-grade content requires verified sources | Scholar Inbox paper: "Hard Quality Floor" for professional research |
| Combined signal (C + I) | Neither credibility nor insight alone is sufficient | LinkedIn Author Authority uses similar composite quality signals |
| Sequential gate evaluation | Fail-fast design; cheap checks first | Standard filter pipeline pattern |
| Fixed credibility threshold | Trust is non-negotiable | Serafis value proposition |

### 12.2 Why Not Alternatives?

| Alternative | Why Not Used |
|-------------|--------------|
| Soft scoring (no hard gates) | Allows low-quality content with low scores; erodes trust |
| Credibility-only gate | Would allow boring content from credible speakers |
| Insight-only gate | Would allow unverified sources with interesting claims |
| User-adjustable thresholds | Complexity; users shouldn't have to think about this |

---

## 13. Dependencies

### 13.1 Upstream (Required)

| Dependency | Source | Description |
|------------|--------|-------------|
| Episode scores | Document 01 | `scores.credibility`, `scores.insight` |
| User exclusions | Document 01 | `U.excluded_ids` |

### 13.2 Downstream (Consumers)

| Consumer | Usage |
|----------|-------|
| Document 04: Scoring | Only PASSED episodes proceed |
| Document 07: Reranking | Only PASSED episodes in candidate pool |

---

## 14. Document References

| Related Document | Relationship |
|------------------|--------------|
| 01: Data Model | Provides E.scores.*, U.excluded_ids |
| 04: Scoring Components | Consumes only PASSED episodes |
| 08: Future Enhancements | Velocity Bypass for breaking news |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Feb 2026 | Initial deep dive document |
