# Archived Algorithm Versions

This directory contains algorithm versions that have been archived because they are redundant with active versions. These are kept for historical reference and reproducibility of past experiments.

## Archived Versions

### v1_0_default
- **Status:** Archived (redundant with v1_2_blended)
- **Created:** 2026-02-08
- **Architecture:** Blended scoring (2-stage pipeline)
- **Why Archived:** Identical architecture to v1_2, just with hardcoded default parameters. v1_2 is more configurable and represents the same architectural approach.
- **Key Parameters:**
  - weight_similarity: 0.55
  - weight_quality: 0.30
  - weight_recency: 0.15
  - bookmark_weight: 2.0

### v1_3_tuned
- **Status:** Archived (redundant with v1_2_blended)
- **Created:** 2026-02-08
- **Architecture:** Blended scoring (2-stage pipeline) - identical to v1_2
- **Why Archived:** Parameter tuning experiment only - no architectural changes. Used to test high personalization (0.85 similarity) and stronger bookmark weighting (5.0). These parameter values can be reproduced in v1_2 through config tuning.
- **Key Parameters:**
  - weight_similarity: 0.85 (increased from 0.55)
  - weight_quality: 0.10 (decreased from 0.30)
  - weight_recency: 0.05 (decreased from 0.15)
  - bookmark_weight: 5.0 (increased from 2.0)
  - use_sum_similarities: true (new)

### v1_4_optimized
- **Status:** Archived (IDENTICAL to v1_3_tuned)
- **Created:** 2026-02-09
- **Architecture:** Blended scoring - exact duplicate of v1_3
- **Why Archived:** Completely redundant - the recommendation_engine.py is identical to v1_3 (only 1 blank line difference). This was likely created as a planned iteration but no actual changes were made.
- **Key Parameters:** Same as v1_3

## Reproduction

To reproduce results from any archived version:

1. Use v1_2_blended as the base algorithm
2. Load the archived version's config parameters from its `config.json`
3. Apply those parameters through the parameter tuning UI or API

Example:
```bash
# Load v1_2 algorithm
# Then update config with v1_3 parameters:
curl -X POST http://localhost:8000/api/algorithm/config/update \
  -H "Content-Type: application/json" \
  -d '{"stage_b": {"weight_similarity": 0.85, "weight_quality": 0.10, "weight_recency": 0.05}, "engagement_weights": {"bookmark": 5.0}}'
```

## Active Algorithms

The following algorithm versions remain active:

- **v1_2_blended**: Base blended scoring architecture (representative of v1_0-v1_4 lineage)
- **v1_5_diversified**: Enhanced with cold start category diversity (architecturally distinct)

These two versions represent the architecturally distinct approaches in the codebase.
