#!/usr/bin/env python3
"""
Dataset Analysis Script for Evaluation Dataset Spec

Analyzes the current episodes.json against the 5 diversity dimensions
defined in DATASET_SPEC.md and outputs a gap analysis report.
"""

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Paths
DATA_DIR = Path(__file__).parent.parent / "mock_api" / "data"
EPISODES_PATH = DATA_DIR / "episodes.json"

# Targets from DATASET_SPEC.md
CATEGORY_TARGETS = {
    "Technology & AI": (200, 250),
    "Crypto & Web3": (120, 150),
    "Startups, Growth and Founder Journeys": (150, 180),
    "Venture & Private Markets": (120, 150),
    "Macro, Investing & Market Trends": (150, 180),
}

QUALITY_TIER_TARGETS = {
    "high": (250, 300),        # C >= 3 AND I >= 3
    "medium": (500, 550),      # C >= 2 AND (C+I) >= 5 (but not high)
    "threshold": (100, 150),   # C = 2 AND (C+I) = 5 exactly
    "below_threshold": (50, 100),  # C < 2 OR (C+I) < 5
}

RECENCY_TARGETS = {
    "fresh": (200, 250),       # 0-14 days
    "recent": (250, 300),      # 15-30 days
    "moderate": (250, 300),    # 31-60 days
    "aging": (150, 200),       # 61-90 days
    "stale": (50, 100),        # 91-120 days
}

TIER1_ORGS = ["OpenAI", "Anthropic", "Google", "Microsoft", "Nvidia", "Meta", "Apple", "Amazon"]
TIER2_ORGS = ["Tesla", "Coinbase", "Stripe", "Databricks", "Snowflake", "Block", "Palantir"]
TIER3_ORGS = ["Etched", "Groq", "Mistral", "Perplexity", "Cursor", "Anduril", "Scale AI"]

TIER1_PEOPLE = ["Sam Altman", "Elon Musk", "Jensen Huang", "Satya Nadella", "Sundar Pichai"]
TIER2_PEOPLE = ["Dario Amodei", "Mark Zuckerberg", "Brian Chesky", "Patrick Collison"]

# Reference date for recency calculation
REFERENCE_DATE = datetime.now(timezone.utc)


def load_episodes():
    """Load episodes from JSON file."""
    with open(EPISODES_PATH, "r") as f:
        return json.load(f)


def get_quality_tier(episode):
    """Determine quality tier based on credibility and insight scores."""
    scores = episode.get("scores", {})
    c = scores.get("credibility", 0) or 0
    i = scores.get("insight", 0) or 0
    
    if c >= 3 and i >= 3:
        return "high"
    elif c >= 2 and (c + i) >= 5:
        if c == 2 and (c + i) == 5:
            return "threshold"
        return "medium"
    else:
        return "below_threshold"


def get_age_bucket(episode):
    """Determine age bucket based on published_at date."""
    pub_str = episode.get("published_at", "")
    if not pub_str:
        return "unknown"
    
    try:
        # Parse ISO timestamp
        pub_date = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
        days_old = (REFERENCE_DATE - pub_date).days
        
        if days_old <= 14:
            return "fresh"
        elif days_old <= 30:
            return "recent"
        elif days_old <= 60:
            return "moderate"
        elif days_old <= 90:
            return "aging"
        elif days_old <= 120:
            return "stale"
        else:
            return "very_old"
    except Exception:
        return "unknown"


def get_primary_category(episode):
    """Get the primary (first) major category."""
    categories = episode.get("categories", {})
    major = categories.get("major", [])
    return major[0] if major else "Unknown"


def analyze_categories(episodes):
    """Analyze category distribution."""
    category_counts = Counter()
    for ep in episodes:
        # Count all major categories (episodes can have multiple)
        cats = ep.get("categories", {}).get("major", [])
        for cat in cats:
            category_counts[cat] += 1
    
    # Also count primary category
    primary_counts = Counter(get_primary_category(ep) for ep in episodes)
    
    return {
        "all_categories": dict(category_counts),
        "primary_category": dict(primary_counts),
    }


def analyze_quality(episodes):
    """Analyze quality tier distribution."""
    tier_counts = Counter(get_quality_tier(ep) for ep in episodes)
    
    # Also get score distributions (handle None values)
    credibility_dist = Counter((ep.get("scores", {}).get("credibility") or 0) for ep in episodes)
    insight_dist = Counter((ep.get("scores", {}).get("insight") or 0) for ep in episodes)
    
    return {
        "tier_counts": dict(tier_counts),
        "credibility_distribution": dict(sorted(credibility_dist.items())),
        "insight_distribution": dict(sorted(insight_dist.items())),
    }


def analyze_recency(episodes):
    """Analyze recency distribution."""
    bucket_counts = Counter(get_age_bucket(ep) for ep in episodes)
    
    # Get age statistics
    ages = []
    for ep in episodes:
        pub_str = ep.get("published_at", "")
        if pub_str:
            try:
                pub_date = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                ages.append((REFERENCE_DATE - pub_date).days)
            except Exception:
                pass
    
    age_stats = {}
    if ages:
        age_stats = {
            "min_days": min(ages),
            "max_days": max(ages),
            "mean_days": sum(ages) / len(ages),
            "median_days": sorted(ages)[len(ages) // 2],
        }
    
    return {
        "bucket_counts": dict(bucket_counts),
        "age_stats": age_stats,
    }


def analyze_entities(episodes):
    """Analyze entity coverage."""
    org_counts = defaultdict(int)
    org_episodes = defaultdict(list)  # Track which episodes mention each org
    
    for ep in episodes:
        entities = ep.get("entities", [])
        for entity in entities:
            name = entity.get("name", "")
            if name:
                org_counts[name] += 1
                org_episodes[name].append(ep.get("id", ""))
    
    # Check tier coverage
    tier1_coverage = {org: org_counts.get(org, 0) for org in TIER1_ORGS}
    tier2_coverage = {org: org_counts.get(org, 0) for org in TIER2_ORGS}
    tier3_coverage = {org: org_counts.get(org, 0) for org in TIER3_ORGS}
    
    # Top orgs overall
    top_orgs = dict(Counter(org_counts).most_common(20))
    
    return {
        "tier1_orgs": tier1_coverage,
        "tier2_orgs": tier2_coverage,
        "tier3_orgs": tier3_coverage,
        "top_20_orgs": top_orgs,
        "total_unique_orgs": len(org_counts),
    }


def analyze_people(episodes):
    """Analyze people coverage."""
    people_counts = defaultdict(int)
    
    for ep in episodes:
        people = ep.get("people", [])
        for person in people:
            name = person.get("name", "")
            if name:
                people_counts[name] += 1
    
    tier1_coverage = {p: people_counts.get(p, 0) for p in TIER1_PEOPLE}
    tier2_coverage = {p: people_counts.get(p, 0) for p in TIER2_PEOPLE}
    
    top_people = dict(Counter(people_counts).most_common(20))
    
    return {
        "tier1_people": tier1_coverage,
        "tier2_people": tier2_coverage,
        "top_20_people": top_people,
        "total_unique_people": len(people_counts),
    }


def analyze_series(episodes):
    """Analyze series distribution."""
    series_counts = Counter()
    for ep in episodes:
        series_name = ep.get("series", {}).get("name", "Unknown")
        series_counts[series_name] += 1
    
    top_series = dict(series_counts.most_common(15))
    
    return {
        "total_unique_series": len(series_counts),
        "top_15_series": top_series,
        "max_episodes_per_series": max(series_counts.values()) if series_counts else 0,
        "series_over_50": [s for s, c in series_counts.items() if c > 50],
    }


def compare_to_targets(actual, targets, total_episodes):
    """Compare actual counts to targets and compute gaps."""
    gaps = {}
    for key, (min_target, max_target) in targets.items():
        actual_count = actual.get(key, 0)
        actual_pct = (actual_count / total_episodes * 100) if total_episodes > 0 else 0
        
        if actual_count < min_target:
            gap = min_target - actual_count
            status = "BELOW"
        elif actual_count > max_target:
            gap = actual_count - max_target
            status = "ABOVE"
        else:
            gap = 0
            status = "OK"
        
        gaps[key] = {
            "actual": actual_count,
            "actual_pct": round(actual_pct, 1),
            "target": f"{min_target}-{max_target}",
            "gap": gap,
            "status": status,
        }
    
    return gaps


def print_section(title, char="="):
    """Print a section header."""
    print(f"\n{char * 60}")
    print(f" {title}")
    print(f"{char * 60}")


def main():
    # Load data
    print("Loading episodes...")
    episodes = load_episodes()
    total = len(episodes)
    print(f"Loaded {total} episodes")
    
    # Target is 1000-1200
    target_total = 1000
    
    print_section("DATASET OVERVIEW")
    print(f"Current episode count: {total}")
    print(f"Target episode count: 1000-1200")
    print(f"Gap to minimum target: {max(0, target_total - total)} episodes needed")
    
    # Dimension 1: Categories
    print_section("DIMENSION 1: CATEGORY DISTRIBUTION")
    cat_analysis = analyze_categories(episodes)
    
    print("\nAll category mentions (episodes can have multiple):")
    for cat, count in sorted(cat_analysis["all_categories"].items(), key=lambda x: -x[1]):
        pct = count / total * 100
        print(f"  {cat}: {count} ({pct:.1f}%)")
    
    print("\nPrimary category (first listed):")
    primary = cat_analysis["primary_category"]
    for cat, count in sorted(primary.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        print(f"  {cat}: {count} ({pct:.1f}%)")
    
    # Dimension 2: Quality
    print_section("DIMENSION 2: QUALITY TIER DISTRIBUTION")
    quality_analysis = analyze_quality(episodes)
    
    print("\nQuality tier distribution:")
    tier_gaps = compare_to_targets(quality_analysis["tier_counts"], QUALITY_TIER_TARGETS, total)
    for tier, data in tier_gaps.items():
        print(f"  {tier:20s}: {data['actual']:4d} ({data['actual_pct']:5.1f}%)  Target: {data['target']:10s}  [{data['status']}]  Gap: {data['gap']}")
    
    print("\nCredibility score distribution:")
    for score, count in sorted(quality_analysis["credibility_distribution"].items()):
        pct = count / total * 100
        print(f"  C={score}: {count:4d} ({pct:.1f}%)")
    
    print("\nInsight score distribution:")
    for score, count in sorted(quality_analysis["insight_distribution"].items()):
        pct = count / total * 100
        print(f"  I={score}: {count:4d} ({pct:.1f}%)")
    
    # Dimension 3: Recency
    print_section("DIMENSION 3: RECENCY DISTRIBUTION")
    recency_analysis = analyze_recency(episodes)
    
    print(f"\nReference date: {REFERENCE_DATE.strftime('%Y-%m-%d')}")
    if recency_analysis["age_stats"]:
        stats = recency_analysis["age_stats"]
        print(f"Age range: {stats['min_days']}-{stats['max_days']} days")
        print(f"Mean age: {stats['mean_days']:.1f} days")
        print(f"Median age: {stats['median_days']} days")
    
    print("\nRecency bucket distribution:")
    bucket_gaps = compare_to_targets(recency_analysis["bucket_counts"], RECENCY_TARGETS, total)
    for bucket in ["fresh", "recent", "moderate", "aging", "stale"]:
        if bucket in bucket_gaps:
            data = bucket_gaps[bucket]
            print(f"  {bucket:12s}: {data['actual']:4d} ({data['actual_pct']:5.1f}%)  Target: {data['target']:10s}  [{data['status']}]  Gap: {data['gap']}")
    
    # Also show very_old and unknown
    for bucket in ["very_old", "unknown"]:
        count = recency_analysis["bucket_counts"].get(bucket, 0)
        if count > 0:
            pct = count / total * 100
            print(f"  {bucket:12s}: {count:4d} ({pct:.1f}%)  [Outside 120-day window]")
    
    # Dimension 4: Entities
    print_section("DIMENSION 4: ENTITY COVERAGE")
    entity_analysis = analyze_entities(episodes)
    
    print(f"\nTotal unique organizations: {entity_analysis['total_unique_orgs']}")
    
    print("\nTier 1 orgs (target: 15-20 each):")
    for org, count in sorted(entity_analysis["tier1_orgs"].items(), key=lambda x: -x[1]):
        status = "OK" if count >= 15 else "BELOW"
        gap = max(0, 15 - count)
        print(f"  {org:15s}: {count:3d}  [{status}]  Gap: {gap}")
    
    print("\nTier 2 orgs (target: 8-12 each):")
    for org, count in sorted(entity_analysis["tier2_orgs"].items(), key=lambda x: -x[1]):
        status = "OK" if count >= 8 else "BELOW"
        gap = max(0, 8 - count)
        print(f"  {org:15s}: {count:3d}  [{status}]  Gap: {gap}")
    
    print("\nTier 3 orgs - emerging (target: 3-5 each):")
    for org, count in sorted(entity_analysis["tier3_orgs"].items(), key=lambda x: -x[1]):
        status = "OK" if count >= 3 else "BELOW"
        gap = max(0, 3 - count)
        print(f"  {org:15s}: {count:3d}  [{status}]  Gap: {gap}")
    
    print("\nTop 20 orgs overall:")
    for org, count in entity_analysis["top_20_orgs"].items():
        print(f"  {org:20s}: {count}")
    
    # Dimension 4b: People
    print_section("DIMENSION 4b: PEOPLE COVERAGE")
    people_analysis = analyze_people(episodes)
    
    print(f"\nTotal unique people: {people_analysis['total_unique_people']}")
    
    print("\nTier 1 people (target: 10-15 each):")
    for person, count in sorted(people_analysis["tier1_people"].items(), key=lambda x: -x[1]):
        status = "OK" if count >= 10 else "BELOW"
        gap = max(0, 10 - count)
        print(f"  {person:20s}: {count:3d}  [{status}]  Gap: {gap}")
    
    print("\nTier 2 people (target: 5-10 each):")
    for person, count in sorted(people_analysis["tier2_people"].items(), key=lambda x: -x[1]):
        status = "OK" if count >= 5 else "BELOW"
        gap = max(0, 5 - count)
        print(f"  {person:20s}: {count:3d}  [{status}]  Gap: {gap}")
    
    print("\nTop 20 people overall:")
    for person, count in people_analysis["top_20_people"].items():
        print(f"  {person:25s}: {count}")
    
    # Dimension 5: Series
    print_section("DIMENSION 5: SERIES DISTRIBUTION")
    series_analysis = analyze_series(episodes)
    
    print(f"\nTotal unique series: {series_analysis['total_unique_series']} (target: 50-80)")
    print(f"Max episodes from single series: {series_analysis['max_episodes_per_series']} (target: max 50 = 5%)")
    
    if series_analysis["series_over_50"]:
        print(f"\nWARNING: Series with >50 episodes: {series_analysis['series_over_50']}")
    
    print("\nTop 15 series:")
    for series, count in series_analysis["top_15_series"].items():
        pct = count / total * 100
        print(f"  {series[:40]:40s}: {count:3d} ({pct:.1f}%)")
    
    # Summary
    print_section("GAP SUMMARY", "=")
    print("\nPriority gaps to fill:")
    
    # Check total
    if total < 1000:
        print(f"\n1. TOTAL EPISODES: Need {1000 - total} more episodes")
    
    # Check categories (simplified - just check if any major category is missing)
    all_cats = cat_analysis["all_categories"]
    missing_cats = [cat for cat in CATEGORY_TARGETS.keys() if all_cats.get(cat, 0) < CATEGORY_TARGETS[cat][0]]
    if missing_cats:
        print(f"\n2. CATEGORIES: Underrepresented categories:")
        for cat in missing_cats:
            actual = all_cats.get(cat, 0)
            target = CATEGORY_TARGETS[cat][0]
            print(f"   - {cat}: have {actual}, need {target} (gap: {target - actual})")
    
    # Check entities
    missing_tier1 = [org for org, count in entity_analysis["tier1_orgs"].items() if count < 15]
    if missing_tier1:
        print(f"\n3. TIER 1 ORGS: Need more episodes for: {', '.join(missing_tier1)}")
    
    # Check people
    missing_people = [p for p, count in people_analysis["tier1_people"].items() if count < 10]
    if missing_people:
        print(f"\n4. TIER 1 PEOPLE: Need more episodes for: {', '.join(missing_people)}")
    
    # Check recency
    fresh_count = recency_analysis["bucket_counts"].get("fresh", 0)
    if fresh_count < 200:
        print(f"\n5. RECENCY: Need more fresh content (0-14 days): have {fresh_count}, target 200+")
    
    print("\n" + "=" * 60)
    print(" END OF ANALYSIS")
    print("=" * 60)


if __name__ == "__main__":
    main()
