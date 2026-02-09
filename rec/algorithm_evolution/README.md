# Algorithm Evolution & Traceability

This folder documents the evolution of the Serafis "For You" recommendation algorithm from original specification through each version iteration. It serves as the primary reference for Phase 5 (Compare with Original Spec) while supporting ongoing Phase 4 (Tuning) work.

## Document Structure

```
algorithm_evolution/
├── README.md                    # This file - overview and navigation
├── CHANGELOG.md                 # Version-by-version changes summary
├── ORIGINAL_SPEC.md             # Original brief → v1.0 translation
├── PERFORMANCE_COMPARISON.md    # Test results across all versions
└── versions/
    ├── v1_0_default.md          # v1.0 implementation details
    ├── v1_2_blended.md          # v1.2 implementation details
    └── v1_3_tuned.md            # v1.3 implementation details
    └── (v1_4_*.md)              # Future versions added here
```

## Quick Reference

| Version | Name | Key Changes | Tests Passed | Overall Score |
|---------|------|-------------|--------------|---------------|
| **v1.0** | Default Baseline | Initial implementation of original spec | 4/8 | 7.65 |
| **v1.2** | Blended Scoring | Fixed config loading, auto-exclusion | 6/8 | 8.29 |
| **v1.3** | Tuned Personalization | 5x bookmark, 85% similarity, sum-of-similarities | 6/8 | 8.80 |

## Original Specification Trace

The algorithm originated from a brief text plan (January 2026):

> **Original Brief (Rohan Sharma):**
> - Determine user-specific ranking score for episode candidates
> - For top 10 episodes in user's activity: calculate vector similarity, sum scores
> - Parameters: similarity to interests, quality score (credibility weighted higher), recency
> - Order activity by recency (simple), later by depth of engagement (bookmarks, listens)

### How Original Spec Maps to Implementation

| Original Concept | v1.0 Implementation | Current Status |
|------------------|---------------------|----------------|
| "Sum scores across top 10" | Mean-pooling user vector | v1.3 adds `use_sum_similarities` option |
| "Credibility weighted higher" | `credibility_multiplier: 1.5` | Implemented in all versions |
| "Recency of candidate" | Exponential decay (`recency_lambda: 0.03`) | Implemented in all versions |
| "Depth of engagement" | `engagement_weights: {bookmark: 2.0, listen: 1.5, click: 1.0}` | v1.3 increases to 5.0x bookmark |
| "Category overlap (v2)" | Not implemented | Deferred to future version |

## Key Milestones

### Phase 4 Progress (February 8, 2026)

1. **Config Loading Bug Fix**: Discovered algorithm configs weren't being loaded—all versions were using hardcoded defaults. Fixed in `server.py`.

2. **Auto-Exclusion**: Added server-side logic to exclude engaged episodes from new recommendations.

3. **Test Case 08**: Created high-quality bookmark weighting test to isolate quality gate effects.

4. **v1.3 Tuning**: Aggressive personalization tuning (5x bookmark, 85% similarity, sum-of-similarities).

## How to Add New Versions

When creating v1.4 or later:

1. Copy algorithm folder: `cp -r algorithms/v1_3_tuned algorithms/v1_4_*`
2. Update `manifest.json` and `config.json`
3. Run tests with LLM: `curl -X POST .../api/evaluation/run-all -d '{"with_llm": true}'`
4. Create `versions/v1_4_*.md` documenting changes
5. Update `CHANGELOG.md` with summary
6. Update `PERFORMANCE_COMPARISON.md` with new results

## Related Documents

- `/rec/FOR_YOU_V1_2_SPEC.md` - Full algorithm specification
- `/rec/evaluation/EVALUATION_STRATEGY.md` - Test methodology
- `/rec/misc_docs/RECOMMENDER_V1_BRIEF.md` - Original brief (superseded)
- `/rec/deep_dives/` - Detailed algorithm component documentation
