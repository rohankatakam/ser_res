# Deep Dive 06: POV Derivation Subsystem

> *Classifies episode narrative stance for diversity and contrarian boosting.*

**Document:** 6 of 8  
**Subsystem:** POV (Point of View) Derivation  
**Pipeline Stage:** Stage 0.5 (Pre-computed, used in Stage 3)  
**Status:** Final

---

## 1. Purpose

The POV Derivation subsystem classifies each episode's **narrative stance** into one of two categories: **Contrarian** or **Consensus**. This classification enables:

1. **Contrarian Boost:** After a "Consensus" episode, boost "Contrarian" episodes to break filter bubbles
2. **Narrative Diversity:** Ensure the feed presents alternative perspectives
3. **User Awareness:** Surface content that challenges conventional wisdom

---

## 2. Subsystem Context

```
┌─────────────────────────────────────────────────────────────────┐
│                POV DERIVATION SUBSYSTEM                          │
│                    (This Document)                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUT (from Document 01)                                       │
│  ────────────────────────                                       │
│  • E.critical_views.non_consensus_level                         │
│                                                                  │
│                         │                                        │
│                         ▼                                        │
│              ┌─────────────────────┐                            │
│              │   BINARY CHECK      │                            │
│              │   (Single condition)│                            │
│              └─────────────────────┘                            │
│                         │                                        │
│                         ▼                                        │
│                                                                  │
│  OUTPUT                                                         │
│  ──────                                                         │
│  • E.POV ∈ {Contrarian, Consensus}                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Document 07:       │
                    │  Narrative          │
                    │  Reranking          │
                    │  (Contrarian Boost) │
                    └─────────────────────┘
```

---

## 3. Input Parameters

| Parameter | Source | Type | Description |
|-----------|--------|------|-------------|
| `E.critical_views.non_consensus_level` | Document 01 | Enum \| null | Explicit contrarian flag: "highly_non_consensus", "non_consensus", or absent |

---

## 4. Output Parameters

| Parameter | Type | Values | Description |
|-----------|------|--------|-------------|
| `E.POV` | Enum | Contrarian, Consensus | Episode's narrative stance |

### 4.1 POV Value Definitions

| POV | Definition | Example Content |
|-----|------------|-----------------|
| **Contrarian** | Challenges conventional wisdom; presents non-consensus views | "AI is overhyped — here's why the bubble will burst" |
| **Consensus** | Aligns with mainstream views; informational or commonly-held opinions | "Nvidia continues to dominate the AI chip market" |

---

## 5. POV Classification Logic

The POV is determined through a **single binary check** using the most reliable signal:

```
┌─────────────────────────────────────────────────────────────────┐
│                     POV CLASSIFICATION                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  IF E.critical_views.non_consensus_level ∈                      │
│     {"highly_non_consensus", "non_consensus"}                   │
│  → POV = Contrarian                                             │
│                                                                  │
│  ELSE                                                           │
│  → POV = Consensus                                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.1 Why Binary Classification?

| Consideration | Decision |
|---------------|----------|
| **Simplicity** | Single field check; no LLM calls at recommendation time |
| **Reliability** | Uses structured data computed during content ingestion |
| **No Noise** | Avoids sentiment analysis misclassification |
| **Sufficient for V1** | Core goal (surface contrarian views) is achieved |

---

## 6. Implementation

```python
from enum import Enum

class POV(Enum):
    CONTRARIAN = "Contrarian"
    CONSENSUS = "Consensus"

def derive_pov(critical_views: dict | None) -> POV:
    """
    Derive episode POV using binary classification.
    
    Args:
        critical_views: The episode's critical_views object
    
    Returns:
        POV enum value (Contrarian or Consensus)
    """
    
    # Handle missing critical_views
    if not critical_views:
        return POV.CONSENSUS
    
    # Check non_consensus_level
    non_consensus = critical_views.get('non_consensus_level')
    
    if non_consensus in ['highly_non_consensus', 'non_consensus']:
        return POV.CONTRARIAN
    
    return POV.CONSENSUS
```

---

## 7. POV Distribution Expectations

Based on typical investment podcast content:

| POV | Expected Distribution | Notes |
|-----|----------------------|-------|
| Consensus | 85–95% | Most content aligns with mainstream views |
| Contrarian | 5–15% | Genuinely non-consensus views are rare |

**Monitoring Alert:** If Contrarian < 5%, the Contrarian Boost will rarely fire. Consider:
- Reviewing the content ingestion pipeline's contrarian detection
- Expanding the corpus to include more contrarian voices

---

## 8. Edge Cases

### 8.1 Missing Data

| Scenario | Behavior |
|----------|----------|
| `critical_views` is null | Return Consensus |
| `non_consensus_level` is null or absent | Return Consensus |
| `non_consensus_level` is empty string | Return Consensus |

### 8.2 Contrarian Detection Quality

The quality of POV classification depends entirely on the upstream content ingestion pipeline that computes `non_consensus_level`. This subsystem trusts that signal.

| Upstream Signal | POV Result |
|-----------------|------------|
| "highly_non_consensus" | Contrarian |
| "non_consensus" | Contrarian |
| null / absent | Consensus |
| Any other value | Consensus |

---

## 9. Worked Examples

### 9.1 Example: Contrarian Episode

**Input:**
```json
{
  "critical_views": {
    "non_consensus_level": "highly_non_consensus",
    "has_critical_views": true,
    "new_ideas_summary": "This episode contains genuinely contrarian insights..."
  }
}
```

**Logic:** `non_consensus_level` = "highly_non_consensus" → **Contrarian**

**Output:** `POV = Contrarian`

---

### 9.2 Example: Consensus Episode (Explicit)

**Input:**
```json
{
  "critical_views": {
    "non_consensus_level": null,
    "has_critical_views": false,
    "new_ideas_summary": "This episode aligns with commonly held views..."
  }
}
```

**Logic:** `non_consensus_level` = null → **Consensus**

**Output:** `POV = Consensus`

---

### 9.3 Example: Consensus Episode (Missing Data)

**Input:**
```json
{
  "critical_views": null
}
```

**Logic:** `critical_views` is null → **Consensus** (default)

**Output:** `POV = Consensus`

---

## 10. When POV is Computed

| Option | Timing | Recommendation |
|--------|--------|----------------|
| **Pre-computed** | During content ingestion | ✅ Recommended — fast at recommendation time |
| **On-demand** | At recommendation time | Also fine — computation is trivial |

Since POV derivation is a simple field check (no LLM call), it can be computed either during ingestion or at recommendation time with negligible performance difference.

---

## 11. Traceability

### 11.1 Design Decisions

| Decision | Rationale | Backing |
|----------|-----------|---------|
| Binary classification | Simpler, no LLM noise, uses reliable structured data | Engineering pragmatism |
| Trust `non_consensus_level` | Computed during ingestion by sophisticated LLM analysis | Data quality hierarchy |
| Default to Consensus | Most content is mainstream; safe default | Statistical expectation |

### 11.2 Academic Backing

| Component | Paper/Precedent |
|-----------|-----------------|
| Contrarian boost concept | User Feedback Alignment (Google DeepMind, 2025) |
| Bridging algorithms | Twitter/X Community Notes |

### 11.3 What's Deferred to V2

| Feature | Why Deferred | See Document |
|---------|--------------|--------------|
| Bullish/Bearish/Neutral sentiment | Adds complexity, noise risk, marginal value for V1 | Document 08 |
| Sentiment-specific boosts | Requires sentiment classification | Document 08 |

---

## 12. Dependencies

### 12.1 Upstream (Required)

| Dependency | Source | Description |
|------------|--------|-------------|
| `E.critical_views.non_consensus_level` | Document 01 | Contrarian flag from content ingestion |

### 12.2 Downstream (Consumers)

| Consumer | Usage |
|----------|-------|
| Document 07: Reranking | Contrarian Boost (Consensus → Contrarian = 1.15×) |

---

## 13. Document References

| Related Document | Relationship |
|------------------|--------------|
| 01: Data Model | Provides critical_views.non_consensus_level |
| 07: Narrative Reranking | Consumes E.POV for contrarian boost |
| 08: Future Enhancements | Sentiment-based POV (Bullish/Bearish/Neutral) |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Feb 2026 | Initial deep dive — simplified to binary POV |
