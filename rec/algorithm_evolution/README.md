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
    ├── v1_3_tuned.md            # v1.3 implementation details
    └── v1_4_optimized.md        # v1.4 implementation details ✅ ACCEPTED
```

## Quick Reference

| Version | Name | Key Changes | Tests Passed | Overall Score | Status |
|---------|------|-------------|--------------|---------------|--------|
| **v1.0** | Default Baseline | Initial implementation of original spec | 4/7 | 7.65 | Baseline |
| **v1.2** | Blended Scoring | Fixed config loading, auto-exclusion | 6/7 | 8.29 | Bug fixes |
| **v1.3** | Tuned Personalization | 5x bookmark, 85% similarity, sum-of-similarities | 6/7 | 8.80 | Tuning |
| **v1.4** | Optimized Bookmark | 7x bookmark weight | 6-7/7* | ~8.5 | ✅ **ACCEPTED** |

*v1.4 Note: All deterministic tests pass consistently. Test 01 (Cold Start) experiences LLM evaluation variability (~50% pass rate), which is a test infrastructure issue, not an algorithm problem. See PERFORMANCE_COMPARISON.md for details.

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
| "Depth of engagement" | `engagement_weights: {bookmark: 2.0, listen: 1.5, click: 1.0}` | v1.4 increases to 7.0x bookmark |
| "Category overlap (v2)" | Not implemented | Deferred to future version |

## Key Milestones

### Phase 4 Complete (February 9, 2026)

1. **Config Loading Bug Fix**: Discovered algorithm configs weren't being loaded—all versions were using hardcoded defaults. Fixed in `server.py`.

2. **Auto-Exclusion**: Added server-side logic to exclude engaged episodes from new recommendations.

3. **Test Suite Reorganization**: Removed old Test 06 (conflated quality gates with bookmark weighting), renumbered to 7 tests.

4. **v1.3 Tuning**: Aggressive personalization tuning (5x bookmark, 85% similarity, sum-of-similarities).

5. **v1.4 Optimization**: Increased bookmark weight to 7.0x, achieving **Test 07 (Bookmark Weighting) pass**.

6. **LLM Variability Discovery**: Identified that Test 01 failures are caused by LLM evaluation non-determinism, not algorithm issues. Planned fix: Multi-LLM consensus in Phase 6.

## How to Add New Versions

When creating v1.5 or later:

1. Copy algorithm folder: `cp -r algorithms/v1_4_optimized algorithms/v1_5_*`
2. Update `manifest.json` and `config.json`
3. Load algorithm: `curl -X POST .../api/config/load -d '{"algorithm_id": "v1_5_..."}'`
4. Run tests with LLM: `python -m rec.evaluation.runner --with-llm`
5. Create `versions/v1_5_*.md` documenting changes
6. Update `CHANGELOG.md` with summary
7. Update `PERFORMANCE_COMPARISON.md` with new results

## Related Documents

- `/rec/FOR_YOU_V1_2_SPEC.md` - Full algorithm specification
- `/rec/evaluation/EVALUATION_STRATEGY.md` - Test methodology
- `/rec/misc_docs/RECOMMENDER_V1_BRIEF.md` - Original brief (superseded)
- `/rec/deep_dives/` - Detailed algorithm component documentation
