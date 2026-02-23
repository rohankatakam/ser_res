#!/usr/bin/env python3
"""
Cleanup Episodes Schema

Cleans up episodes.json to have a consistent, honest schema.
Removes misleading fields and standardizes the format.

Usage:
    python cleanup_episodes.py --input fixtures/eval_909_feb2026/episodes.json --output fixtures/eval_909_feb2026/episodes_clean.json
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List


def clean_episode(episode: Dict) -> Dict:
    """
    Clean an episode to the canonical schema.
    
    Essential fields (required for algorithm):
    - id, content_id, title, series, published_at, scores, key_insight
    
    Optional fields (keep if populated, useful for evaluation):
    - categories, entities, people
    
    Remove (misleading or unused):
    - critical_views (only 11/561 populated)
    - search_relevance_score (from original search, not useful)
    - aggregate_score (only from discover page)
    - top_in_categories (computed, can regenerate)
    """
    scores = episode.get("scores", {})
    
    cleaned = {
        # Essential fields
        "id": episode.get("id", ""),
        "content_id": episode.get("content_id", ""),
        "title": episode.get("title", ""),
        "series": {
            "id": episode.get("series", {}).get("id", ""),
            "name": episode.get("series", {}).get("name", "")
        },
        "published_at": episode.get("published_at", ""),
        "content_type": episode.get("content_type", "podcast_episodes"),
        "scores": {
            "credibility": scores.get("credibility", 0),
            "insight": scores.get("insight", 0),
            "information": scores.get("information", 0),
            "entertainment": scores.get("entertainment", 0)
        },
        "key_insight": episode.get("key_insight", ""),
        
        # Optional fields - keep if populated
        "categories": episode.get("categories", {"major": [], "subcategories": []}),
        "entities": episode.get("entities", []),
        "people": episode.get("people", []),
    }
    
    return cleaned


def main():
    parser = argparse.ArgumentParser(description="Cleanup episodes schema")
    parser.add_argument("--input", type=str, required=True, help="Input episodes.json path")
    parser.add_argument("--output", type=str, required=True, help="Output path for cleaned JSON")
    parser.add_argument("--backup", action="store_true", help="Create backup of original")
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    # Load
    with open(input_path, "r") as f:
        episodes = json.load(f)
    
    print(f"Loaded {len(episodes)} episodes from {input_path}")
    
    # Create backup if requested
    if args.backup:
        backup_path = input_path.with_suffix(".backup.json")
        with open(backup_path, "w") as f:
            json.dump(episodes, f, indent=2)
        print(f"Backup created at {backup_path}")
    
    # Clean
    cleaned = [clean_episode(ep) for ep in episodes]
    
    # Sort by published_at (newest first)
    cleaned.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    
    # Write
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(cleaned, f, indent=2)
    
    # Stats
    print(f"\n{'='*50}")
    print("CLEANUP SUMMARY")
    print(f"{'='*50}")
    print(f"Episodes processed: {len(cleaned)}")
    print(f"Output written to: {output_path}")
    
    # Coverage stats
    with_key_insight = sum(1 for e in cleaned if e.get("key_insight"))
    with_categories = sum(1 for e in cleaned if e.get("categories", {}).get("major"))
    with_entities = sum(1 for e in cleaned if e.get("entities"))
    with_people = sum(1 for e in cleaned if e.get("people"))
    
    print(f"\nData coverage:")
    print(f"  key_insight:   {with_key_insight}/{len(cleaned)} ({100*with_key_insight/len(cleaned):.0f}%)")
    print(f"  categories:    {with_categories}/{len(cleaned)} ({100*with_categories/len(cleaned):.0f}%)")
    print(f"  entities:      {with_entities}/{len(cleaned)} ({100*with_entities/len(cleaned):.0f}%)")
    print(f"  people:        {with_people}/{len(cleaned)} ({100*with_people/len(cleaned):.0f}%)")
    
    print(f"\nRemoved fields:")
    print("  - critical_views (only 11 populated)")
    print("  - search_relevance_score")
    print("  - aggregate_score")
    print("  - top_in_categories")


if __name__ == "__main__":
    main()
