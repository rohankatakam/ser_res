# Algorithm Development Guidelines

## Overview

This document explains how to create new algorithm versions for the Serafis recommendation engine. Each algorithm version is a self-contained module that defines its own embedding strategy, recommendation logic, configuration parameters, and UI schema.

## Algorithm Structure

Each algorithm version lives in its own folder under `rec/algorithms/` with a naming convention of `vX_Y_description`:

```
rec/algorithms/v1_5_diversified/
├── __init__.py                   # Python package marker
├── manifest.json                 # Metadata and default parameters
├── config.json                   # Runtime configuration (overrides defaults)
├── config_schema.json            # UI parameter tuning schema (REQUIRED)
├── embedding_strategy.py         # How to generate embeddings
└── recommendation_engine.py      # Recommendation logic
```

## Required Files

### 1. `manifest.json`

Defines algorithm metadata, version info, and default parameters.

**Required fields:**
- `version`: Algorithm version (e.g., "1.5")
- `name`: Human-readable name
- `description`: What makes this algorithm unique
- `created_at`: Creation date (YYYY-MM-DD)
- `embedding_strategy_version`: Embedding strategy version used
- `embedding_model`: Model name (e.g., "text-embedding-3-small")
- `embedding_dimensions`: Embedding vector dimensions
- `requires_schema`: Config schema version (currently "1.0")
- `required_fields`: Episode fields the algorithm needs
- `default_parameters`: All tunable parameters with defaults

**Example:**
```json
{
  "version": "1.5",
  "name": "Diversified Cold Start + Enhanced Bookmarks",
  "description": "V1.5 diversified: Increased bookmark weight and added category diversity",
  "created_at": "2026-02-10",
  "based_on": "v1_4_optimized",
  "tuning_rationale": {
    "bookmark_weight_10.0": "Increased from 7.0 to strengthen bookmark signal",
    "cold_start_category_diversity": "NEW: Ensures balanced category representation"
  },
  "embedding_strategy_version": "1.0",
  "embedding_model": "text-embedding-3-small",
  "embedding_dimensions": 1536,
  "requires_schema": "1.0",
  "required_fields": ["id", "title", "scores", "key_insight", "published_at"],
  "default_parameters": {
    "credibility_floor": 2,
    "combined_floor": 5,
    "weight_similarity": 0.85,
    "engagement_weights": {
      "bookmark": 10.0,
      "click": 1.0
    }
  }
}
```

### 2. `config.json`

Runtime configuration that overrides `default_parameters` from manifest. Can be empty `{}` if using all defaults.

**Structure:** Same as `default_parameters` in manifest, but only include parameters you want to override.

**Example:**
```json
{
  "weight_similarity": 0.90,
  "engagement_weights": {
    "bookmark": 12.0
  }
}
```

### 3. `config_schema.json` (REQUIRED)

Defines the UI schema for parameter tuning. This file is **mandatory** for all algorithm versions.

**Structure:**
```json
{
  "schema_version": "1.0",
  "groups": [
    {
      "id": "stage_a",
      "label": "Stage A: Quality Filtering",
      "description": "Parameters controlling quality gate",
      "collapsed": false,
      "params": [
        {
          "key": "stage_a.credibility_floor",
          "label": "Credibility Floor",
          "description": "Minimum credibility score (1-5)",
          "type": "int",
          "min": 0,
          "max": 5,
          "step": 1,
          "default": 2
        },
        {
          "key": "weight_similarity",
          "label": "Similarity Weight",
          "description": "Weight for semantic similarity (0-1)",
          "type": "float",
          "min": 0,
          "max": 1,
          "step": 0.05,
          "default": 0.85
        },
        {
          "key": "cold_start.category_diversity.enabled",
          "label": "Enable Category Diversity",
          "description": "Ensure balanced categories in cold start",
          "type": "boolean",
          "default": true
        }
      ]
    }
  ]
}
```

**Parameter types:**
- `int`: Integer with min/max/step
- `float`: Decimal with min/max/step
- `boolean`: True/false toggle

**Parameter keys:** Use dot notation to reference nested config values (e.g., `cold_start.weight_quality`).

### 4. `embedding_strategy.py`

Defines how to generate text for embeddings.

**Required exports:**
- `STRATEGY_VERSION`: String version (e.g., "1.0")
- `EMBEDDING_MODEL`: Model name
- `EMBEDDING_DIMENSIONS`: Vector dimensions
- `get_embed_text(episode: Dict) -> str`: Function that extracts text from episode

**Example:**
```python
"""Embedding strategy for v1.5 - title + key_insight"""

STRATEGY_VERSION = "1.0"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

def get_embed_text(episode: dict) -> str:
    """Combine title and key insight for embedding."""
    title = episode.get("title", "")
    insight = episode.get("key_insight", "")
    return f"{title} {insight}".strip()
```

### 5. `recommendation_engine.py`

Core recommendation logic.

**Required exports:**
- `RecommendationConfig`: Pydantic model for configuration
- `PersonalizedRecommendationEngine`: Main engine class

**Engine requirements:**
```python
from pydantic import BaseModel
from typing import List, Dict, Any

class RecommendationConfig(BaseModel):
    """Configuration for the recommendation engine."""
    credibility_floor: int = 2
    combined_floor: int = 5
    # ... all tunable parameters
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "RecommendationConfig":
        """Load config from dictionary (enables dynamic runtime updates)."""
        return cls(**config)

class PersonalizedRecommendationEngine:
    def __init__(self, qdrant_store, config: RecommendationConfig):
        self.qdrant_store = qdrant_store
        self.config = config
    
    def get_recommendations(
        self, 
        profile: Dict[str, Any],
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Generate recommendations for a user profile."""
        # Your recommendation logic here
        pass
```

**Key implementation details:**
- Must accept `config: RecommendationConfig` in constructor
- Must implement `get_recommendations(profile, limit)` method
- Should use `self.config` for all tunable parameters
- Profile contains: `engagements`, `excluded_ids`, `effective_weight`

### 6. `__init__.py`

Empty file to mark the directory as a Python package. Can be completely empty:

```python
# This file marks the directory as a Python package
```

## Creating a New Algorithm Version

### Step 1: Copy a Reference Version

Start with the closest existing version to your goals:

```bash
cd rec/algorithms
cp -r v1_5_diversified v1_6_my_new_algorithm
cd v1_6_my_new_algorithm
```

### Step 2: Update Manifest

Edit `manifest.json`:
- Change `version` to your new version number
- Update `name` and `description`
- Update `created_at` to today's date
- Set `based_on` to the version you copied from
- Add `tuning_rationale` explaining your changes
- Update `default_parameters` with your new defaults

### Step 3: Create Config Schema

Edit `config_schema.json`:
- Define UI groups for logical parameter sections
- Add a schema entry for each tunable parameter
- Use descriptive labels and descriptions
- Set appropriate min/max/step values for numeric parameters
- Use dot notation for nested parameters (e.g., `cold_start.weight_quality`)

**Guidelines:**
- Group related parameters together (e.g., "Quality Filtering", "Personalization Weights")
- Use collapsed: true for advanced/less-frequently-changed groups
- Provide clear descriptions explaining what each parameter does
- Set sensible min/max ranges to prevent invalid values

### Step 4: Set Runtime Config

Edit `config.json`:
- Only include parameters that differ from manifest defaults
- Can be empty `{}` if using all defaults
- Use for your initial tuning/experimentation

### Step 5: Implement Core Logic

Edit `recommendation_engine.py`:
- Update `RecommendationConfig` class with your new parameters
- Implement recommendation logic in `get_recommendations()`
- Reference all tunable values via `self.config`
- Ensure `from_dict()` classmethod handles nested config properly

### Step 6: Test Your Algorithm

1. **Load the algorithm:**
   ```bash
   cd rec
   python -m server.server
   ```

2. **Test in the UI:**
   - Open http://localhost:3000
   - Go to Developer > Tests tab
   - Run evaluation tests to see how your algorithm performs

3. **Tune parameters:**
   - Click the settings icon to open parameter sidebar
   - Adjust your parameters in real-time
   - Click "Apply & Refresh" to see changes
   - Observe impact on "For You" recommendations

4. **Run full evaluation:**
   ```bash
   cd rec/evaluation
   python runner.py --algo-version v1_6_my_new_algorithm --save-report
   ```

## Best Practices

### Configuration Design

1. **Sensible Defaults:** Default parameters should produce reasonable results without tuning
2. **Clear Boundaries:** Use min/max ranges to prevent invalid configurations
3. **Incremental Changes:** When creating a new version, change 1-2 parameters at a time
4. **Document Rationale:** Always include `tuning_rationale` in manifest explaining why you changed each parameter

### Parameter Naming

- Use snake_case for parameter names
- Use clear, descriptive names: `weight_similarity` not `ws`
- Group related parameters under namespaces: `cold_start.weight_quality`
- Be consistent with existing parameter naming patterns

### Embedding Strategy

- Keep `get_embed_text()` deterministic (no randomness)
- Include only fields that are consistently available
- Balance between too little context (poor matching) and too much (noisy embeddings)
- Consider what users actually care about when engaging with content

### Evaluation-Driven Development

1. **Baseline:** Run evaluation on current best algorithm
2. **Hypothesis:** Identify what you want to improve and why
3. **Implement:** Create new version with targeted changes
4. **Evaluate:** Run full test suite and compare scores
5. **Iterate:** If worse, revert changes. If better, tune further.

### Version Naming

Use semantic versioning with descriptive suffixes:
- `v1_0_default`: Initial baseline
- `v1_1_basic`: Minor iteration
- `v1_2_blended`: Named feature (blended ranking)
- `v1_3_tuned`: Optimization pass
- `v2_0_major_change`: Major architectural change

## Common Patterns

### Two-Stage Ranking

Most algorithms use:
1. **Quality Gate:** Filter candidates by credibility/insight scores
2. **Personalized Ranking:** Score remaining candidates using similarity + quality + recency

### Cold Start Handling

Provide fallback behavior for new users with no history:
```python
if len(profile["engagements"]) == 0:
    # Use quality-based ranking with potential diversity constraints
    return self._cold_start_recommendations(limit)
```

### Bookmark Weighting

Weight engagement types differently to prioritize strong signals:
```python
engagement_weights = {
    "bookmark": 10.0,  # Strong positive signal
    "listen": 1.5,     # Medium signal
    "click": 1.0       # Base signal
}
```

### User Vector Construction

Build user interest vectors from recent engagements:
```python
user_embeddings = []
for eng in profile["engagements"][-10:]:  # Last 10 engagements
    weight = engagement_weights[eng["type"]]
    for _ in range(int(weight)):
        user_embeddings.append(get_episode_embedding(eng["episode_id"]))
```

## Troubleshooting

### Algorithm Not Loading

- Check that all 6 required files exist
- Verify `config_schema.json` is valid JSON
- Ensure `RecommendationConfig.from_dict()` is implemented
- Check logs for Python import errors

### Parameter Changes Not Applying

- Verify parameter key in schema matches config structure
- Check that `self.config` is used in recommendation logic (not hardcoded values)
- Ensure "Apply & Refresh" button was clicked
- Clear browser cache if using UI

### Poor Recommendation Quality

- Run evaluation tests to get objective metrics
- Check if quality gate is too restrictive (adjust floors)
- Verify embeddings are being generated correctly
- Compare against baseline algorithm to isolate impact

### Evaluation Tests Failing

- Read test definitions to understand expected behavior
- Check "If Fails, Adjust" guidance in test definition
- Verify your algorithm supports required profile fields
- Run tests individually to isolate failures

## Additional Resources

- **Evaluation Framework:** See `rec/evaluation/README.md`
- **Test Definitions:** Browse `rec/evaluation/test_cases/`
- **Profile Examples:** Browse `rec/evaluation/profiles/`
- **API Documentation:** Run server and visit http://localhost:8000/docs

## Getting Help

When creating new algorithms:
1. Start with small changes to existing algorithms
2. Use evaluation tests to measure impact objectively
3. Document your rationale and results in the manifest
4. Compare multi-LLM scores across versions to identify improvements

Remember: The goal is not perfection, but **measurable improvement** over the baseline, validated by evaluation tests and LLM judges.
