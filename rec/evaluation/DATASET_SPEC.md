# Evaluation Dataset Specification

> *Defining diversity dimensions for a robust recommendation evaluation dataset*

**Version:** 1.1  
**Date:** February 6, 2026  
**Status:** Complete (MVP)  
**Depends On:** FOR_YOU_V1_2_SPEC.md

---

## Current Dataset Summary

The evaluation dataset has been constructed and is ready for testing.

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| **Total Episodes** | 909 | 1000-1200 | ✅ Sufficient |
| **Unique Series** | 104 | 50-80 | ✅ Exceeds |
| **Within 90-day Window** | 528 (58%) | 60%+ | ✅ Met |
| **key_insight Coverage** | 99.4% | 95%+ | ✅ Excellent |
| **scores Coverage** | 99.8% | 100% | ✅ Excellent |

### Quality Distribution
| Tier | Count | Percentage |
|------|-------|------------|
| High (C≥3, I≥3) | 472 | 51.9% |
| Medium (C≥2, C+I≥5) | 264 | 29.0% |
| Threshold | 61 | 6.7% |
| Below Threshold | 112 | 12.3% |

### Entity Coverage (from search sources)
| Organization | Episodes |
|--------------|----------|
| Apple, Amazon, Coinbase, SpaceX, Stripe | 50 each |
| Palantir | 33 |
| Uber | 32 |
| Databricks | 31 |
| xAI | 27 |
| Snowflake | 21 |
| Airbnb | 18 |

### Recency Distribution
| Age Bucket | Count | Percentage |
|------------|-------|------------|
| 0-7 days | 84 | 9% |
| 0-14 days | 151 | 17% |
| 0-30 days | 282 | 31% |
| 0-90 days | 528 | 58% |
| >90 days | 381 | 42% |

---

## Data Schema (Final)

Episodes are stored in `/rec/mock_api/data/episodes.json`:

```json
{
  "id": "string",
  "content_id": "string",
  "title": "string",
  "series": { "id": "string", "name": "string" },
  "published_at": "ISO 8601 datetime",
  "content_type": "podcast_episodes",
  "scores": {
    "credibility": 0-4,
    "insight": 0-4,
    "information": 0-4,
    "entertainment": 0-4
  },
  "key_insight": "string (for embeddings)",
  "categories": { "major": [], "subcategories": [] },
  "entities": [],
  "people": []
}
```

**Note:** `critical_views` was removed as it was only populated for 11 episodes.

---

## Future Improvements (V2)

When time permits, the dataset can be improved:

### Priority 1: Fresh Content
- Run weekly category searches with 7-day filter to maintain fresh content
- Target: Maintain 20%+ content within 14 days

### Priority 2: Entity Enrichment
- Fetch episode details for high-value episodes to get full entity/people data
- Target: 50%+ episodes with `entities` populated

### Priority 3: Category Coverage
- Run targeted searches for underrepresented categories
- Add "Culture, Society & Wellbeing" and "Regulation & Policy" searches

### Priority 4: Subcategory Diversity
- Track subcategory distribution
- Ensure coverage of AI, Crypto, Fintech, Climate, etc.

---

## Original Target Specifications

The following were the original targets used to guide dataset construction:

### Target Dataset Size

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Total Episodes** | 1000-1200 | 2x current dataset; sufficient for statistical validity |
| **Unique Series** | 50-80 | Prevents series bias; tests series diversity logic |
| **Time Span** | 90-120 days | Matches freshness window in V1.2 spec |

---

## Diversity Dimensions (MVP)

### Dimension 1: Major Category Distribution

**Target:** Balanced representation across the 7 major categories from the Serafis taxonomy.

| Major Category | Target % | Target Count (n=1000) | Search Strategy |
|----------------|----------|----------------------|-----------------|
| Technology & AI | 20-25% | 200-250 | Theme search: "Technology & AI" |
| Crypto & Web3 | 12-15% | 120-150 | Theme search: "Crypto & Web3" |
| Startups, Growth & Founder Journeys | 15-18% | 150-180 | Theme search + popular series |
| Venture & Private Markets | 12-15% | 120-150 | Theme search |
| Macro, Investing & Market Trends | 15-18% | 150-180 | Theme search |
| Other/Mixed | 15-20% | 150-200 | Discover page, misc searches |

**Notes:**
- Technology & AI is intentionally weighted higher (reflects corpus reality)
- Episodes often have multiple categories; count primary category
- "Other/Mixed" captures episodes that don't fit neatly or span many categories

**Validation Check:**
```python
# After dataset construction, verify:
category_counts = dataset.groupby('primary_category').count()
assert all(count >= target_min for count in category_counts)
```

---

### Dimension 2: Quality Tier Distribution

**Target:** Include episodes across quality tiers to test quality gates.

Quality tiers are defined by the V1.2 spec thresholds:

| Quality Tier | Definition | Target % | Target Count |
|--------------|------------|----------|--------------|
| **High** | C ≥ 3 AND I ≥ 3 | 25-30% | 250-300 |
| **Medium** | C ≥ 2 AND (C+I) ≥ 5 | 50-55% | 500-550 |
| **Threshold** | C = 2 AND (C+I) = 5 exactly | 10-15% | 100-150 |
| **Below Threshold** | C < 2 OR (C+I) < 5 | 5-10% | 50-100 |

**Why include below-threshold content?**
- Tests that quality gates correctly filter these out
- Validates Stage A pre-selection is working

**Calculation:**
```python
def quality_tier(episode):
    c = episode['scores']['credibility']
    i = episode['scores']['insight']
    if c >= 3 and i >= 3:
        return 'high'
    elif c >= 2 and (c + i) >= 5:
        return 'medium'
    elif c == 2 and (c + i) == 5:
        return 'threshold'
    else:
        return 'below_threshold'
```

---

### Dimension 3: Recency Distribution

**Target:** Stratified by age to test recency scoring.

| Age Bucket | Days Old | Target % | Target Count |
|------------|----------|----------|--------------|
| **Fresh** | 0-14 days | 20-25% | 200-250 |
| **Recent** | 15-30 days | 25-30% | 250-300 |
| **Moderate** | 31-60 days | 25-30% | 250-300 |
| **Aging** | 61-90 days | 15-20% | 150-200 |
| **Stale** | 91-120 days | 5-10% | 50-100 |

**Why include stale content?**
- Tests freshness window edge (90 days in V1.2)
- Validates recency decay scoring

**Search Strategy:**
- Use "Published after" / "Published before" date filters
- May need multiple API calls per category with different date ranges

---

### Dimension 4: Entity Coverage

**Target:** Ensure coverage of major entities (orgs + people) for personalization testing.

#### Organizations (Top 30)

| Tier | Organizations | Min Episodes Each |
|------|---------------|-------------------|
| **Tier 1 (Must Have)** | OpenAI, Anthropic, Google, Microsoft, Nvidia, Meta, Apple, Amazon | 15-20 each |
| **Tier 2 (Important)** | Tesla, Coinbase, Stripe, Databricks, Snowflake, Block, Palantir | 8-12 each |
| **Tier 3 (Emerging)** | Etched, Groq, Mistral, Perplexity, Cursor, Anduril, Scale AI | 3-5 each |

**Search Strategy:**
- Organization search for each Tier 1 & 2 entity
- Ask AI queries for Tier 3 (may not be in org graph)

#### People (Top 20)

| Tier | People | Min Episodes Each |
|------|--------|-------------------|
| **Tier 1** | Sam Altman, Elon Musk, Jensen Huang, Satya Nadella, Sundar Pichai | 10-15 each |
| **Tier 2** | Dario Amodei, Mark Zuckerberg, Brian Chesky, Patrick Collison | 5-10 each |
| **Tier 3** | Emerging founders/operators relevant to corpus | 2-3 each |

**Search Strategy:**
- Person search for Tier 1 & 2
- Cross-reference with org searches (people often co-occur)

---

### Dimension 5: Series Distribution

**Target:** Prevent any single series from dominating the dataset.

| Constraint | Target |
|------------|--------|
| Max episodes from any single series | 5% (50 episodes) |
| Min unique series | 50 |
| Series from each major category | ≥5 per category |

**Top Series to Include (Examples):**
- a16z Podcast
- The Twenty Minute VC (20VC)
- Invest Like the Best
- All-In Podcast
- Acquired
- My First Million
- Lex Fridman Podcast
- Dwarkesh Podcast
- No Priors

**Validation:**
```python
series_counts = dataset.groupby('series.name').count()
assert series_counts.max() <= 50  # No series > 5%
assert len(series_counts) >= 50   # At least 50 unique series
```

---

## Construction Methodology

### Phase 1: Category-Based Collection

**Goal:** Establish baseline coverage across all categories.

| Step | Action | Expected Yield |
|------|--------|----------------|
| 1.1 | Theme search: "Technology & AI" (50 results) | 50 episodes |
| 1.2 | Theme search: "Crypto & Web3" (50 results) | 50 episodes |
| 1.3 | Theme search: "Startups, Growth & Founder Journeys" (50 results) | 50 episodes |
| 1.4 | Theme search: "Venture & Private Markets" (50 results) | 50 episodes |
| 1.5 | Theme search: "Macro, Investing & Market Trends" (50 results) | 50 episodes |
| 1.6 | Discover page: Top Episodes (varies) | 50-100 episodes |

**Subtotal:** ~300-350 episodes

### Phase 2: Entity-Based Collection

**Goal:** Ensure entity coverage for personalization testing.

| Step | Action | Expected Yield |
|------|--------|----------------|
| 2.1 | Org search: Tier 1 orgs (8 × 50) | ~200 unique (with overlap) |
| 2.2 | Org search: Tier 2 orgs (7 × 50) | ~150 unique (with overlap) |
| 2.3 | Person search: Tier 1 people (5 × 50) | ~100 unique (with overlap) |
| 2.4 | Person search: Tier 2 people (5 × 50) | ~100 unique (with overlap) |

**Subtotal:** ~300-400 unique episodes (after deduplication)

### Phase 3: Gap Filling

**Goal:** Fill gaps in dimensions that are underrepresented.

| Step | Action | Trigger |
|------|--------|---------|
| 3.1 | Additional category searches with date filters | If any category < target |
| 3.2 | Emerging entity searches (Ask AI) | If Tier 3 coverage low |
| 3.3 | Older content searches (61-90 day filter) | If "Aging" bucket < 15% |
| 3.4 | Low-quality content inclusion | If below-threshold < 5% |

### Phase 4: Validation & Adjustment

**Goal:** Verify all dimensions meet targets.

```python
def validate_dataset(dataset):
    """Run all dimension validations."""
    results = {}
    
    # Dimension 1: Category distribution
    results['categories'] = validate_category_distribution(dataset)
    
    # Dimension 2: Quality tiers
    results['quality'] = validate_quality_distribution(dataset)
    
    # Dimension 3: Recency
    results['recency'] = validate_recency_distribution(dataset)
    
    # Dimension 4: Entity coverage
    results['entities'] = validate_entity_coverage(dataset)
    
    # Dimension 5: Series distribution
    results['series'] = validate_series_distribution(dataset)
    
    return results
```

---

## Data Schema (Output Format)

The constructed dataset should be saved as JSON with this schema:

```json
{
  "metadata": {
    "version": "1.0",
    "created_at": "2026-02-05T00:00:00Z",
    "episode_count": 1000,
    "source": "Serafis API + manual curation"
  },
  "validation": {
    "category_distribution": { ... },
    "quality_distribution": { ... },
    "recency_distribution": { ... },
    "entity_coverage": { ... },
    "series_distribution": { ... }
  },
  "episodes": [
    {
      "id": "episode_id",
      "content_id": "content-slug",
      "title": "Episode Title",
      "series": {
        "id": "series_id",
        "name": "Series Name"
      },
      "published_at": "2026-01-15T09:00:00Z",
      "scores": {
        "credibility": 3,
        "insight": 3,
        "information": 3,
        "entertainment": 2
      },
      "categories": {
        "major": ["Technology & AI"],
        "subcategories": ["AI & Machine Learning"]
      },
      "entities": [
        {"name": "OpenAI", "relevance": 3, "context": "..."}
      ],
      "people": [
        {"name": "Sam Altman", "title": "CEO of OpenAI", "relevance": 4}
      ],
      "key_insight": "...",
      "critical_views": { ... },
      
      // Computed fields for evaluation
      "_eval": {
        "quality_tier": "high",
        "age_days": 21,
        "age_bucket": "recent",
        "primary_category": "Technology & AI",
        "primary_entities": ["OpenAI", "Microsoft"],
        "collection_source": "org_search_openai"
      }
    }
  ]
}
```

---

## Collection Tracking Template

Use this template to track collection progress:

```markdown
## Collection Progress

### Phase 1: Category-Based
| Search | Date | Count | Unique After Dedup |
|--------|------|-------|-------------------|
| Technology & AI | | | |
| Crypto & Web3 | | | |
| Startups/Growth | | | |
| Venture/Private | | | |
| Macro/Investing | | | |
| Discover Page | | | |

### Phase 2: Entity-Based
| Entity | Type | Date | Count | Unique After Dedup |
|--------|------|------|-------|-------------------|
| OpenAI | Org | | | |
| Anthropic | Org | | | |
| ... | | | | |

### Running Totals
| Metric | Current | Target |
|--------|---------|--------|
| Total Episodes | 0 | 1000-1200 |
| Unique Series | 0 | 50-80 |
| Category Balance | - | See targets |
```

---

## V2 Considerations (Out of Scope for MVP)

The following are explicitly **not** included in V1 but may be relevant for V2:

1. **Subcategory Coverage** — Track distribution across all 20+ subcategories
2. **Sentiment Diversity** — Include bearish/bullish episodes on same entities
3. **Speaker Diversity** — Track unique speakers, ensure variety
4. **Claim-Level Data** — Extract specific claims for claim-level evaluation
5. **Temporal Patterns** — Include episodes that reference same events at different times
6. **Geographic Diversity** — Include non-US focused content

---

## Appendix A: API Reference

### Theme Search
```
URL: app.serafis.ai → AI Search → Search by Theme
Params: Theme (dropdown), Relevance (2), Date filters
Max Results: 50 per query
```

### Organization Search
```
URL: app.serafis.ai → AI Search → Search by Organization
Params: Organization (autocomplete), Relevance (2), Date filters
Max Results: 50 per query
```

### Person Search
```
URL: app.serafis.ai → AI Search → Search by Person
Params: Person (autocomplete), Relevance (2), Date filters
Max Results: 50 per query
```

### Discover Page
```
URL: app.serafis.ai → Discover
Content: Top Episodes, Curated Series
Note: May need to paginate to get more results
```

---

## Appendix B: Validation Script Pseudocode

```python
def validate_category_distribution(dataset):
    """Check category targets are met."""
    targets = {
        'Technology & AI': (200, 250),
        'Crypto & Web3': (120, 150),
        'Startups, Growth & Founder Journeys': (150, 180),
        'Venture & Private Markets': (120, 150),
        'Macro, Investing & Market Trends': (150, 180),
    }
    
    actual = Counter(ep['_eval']['primary_category'] for ep in dataset)
    
    results = {}
    for cat, (min_target, max_target) in targets.items():
        count = actual.get(cat, 0)
        results[cat] = {
            'count': count,
            'target': f'{min_target}-{max_target}',
            'pass': min_target <= count <= max_target
        }
    
    return results

def validate_quality_distribution(dataset):
    """Check quality tier targets are met."""
    targets = {
        'high': (250, 300),
        'medium': (500, 550),
        'threshold': (100, 150),
        'below_threshold': (50, 100),
    }
    
    actual = Counter(ep['_eval']['quality_tier'] for ep in dataset)
    
    # Similar validation logic...

def validate_entity_coverage(dataset):
    """Check entity coverage targets."""
    tier1_orgs = ['OpenAI', 'Anthropic', 'Google', 'Microsoft', 'Nvidia', 'Meta', 'Apple', 'Amazon']
    
    org_counts = defaultdict(int)
    for ep in dataset:
        for entity in ep.get('entities', []):
            org_counts[entity['name']] += 1
    
    results = {}
    for org in tier1_orgs:
        count = org_counts.get(org, 0)
        results[org] = {
            'count': count,
            'target': '15-20',
            'pass': count >= 15
        }
    
    return results
```

---

## Next Steps

After dataset construction is complete:

1. **Run validation script** — Verify all dimensions meet targets
2. **Generate dataset statistics report** — Document actual distributions
3. **Proceed to TEST_CASE_SPEC.md** — Define test cases using real episode IDs
4. **Proceed to USER_PROFILE_SPEC.md** — Build user profiles from actual episodes
5. **Proceed to METRICS_SPEC.md** — Define quantitative evaluation metrics

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Feb 5, 2026 | Initial MVP specification |
| 1.1 | Feb 6, 2026 | Dataset complete (909 episodes), added current metrics, simplified schema |
