#!/usr/bin/env python3
"""
Transform Search Results to Episodes Format (Simplified)

Takes raw search result JSON files from Serafis API and transforms them into
the simplified episodes.json format needed for the recommendation engine.

Based on DATA_MAPPING.md - uses only fields actually available from bulk searches.

Usage:
    python transform_search_results.py --input-dir ./data/raw --output ./data/episodes_combined.json
    
    # With existing data:
    python transform_search_results.py --input-dir ./data/raw --output ./data/episodes_combined.json --existing ../mock_api/data/episodes.json
"""

import json
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any, Optional


def transform_bulk_search_result(result: Dict) -> Dict:
    """
    Transform a single result from org/people/category search.
    
    All bulk search types have the same core structure.
    """
    scores = result.get("content_scores", {})
    
    episode = {
        "id": result.get("id", ""),
        "content_id": result.get("content_id", ""),
        "title": result.get("content_title", ""),
        "series": {
            "id": result.get("series_id", ""),
            "name": result.get("series_name", "")
        },
        "published_at": result.get("publish_date", ""),
        "content_type": result.get("content_type", "podcast_episodes"),
        "scores": {
            "credibility": scores.get("v1_credibility", 0),
            "insight": scores.get("v1_insight", 0),
            "information": scores.get("v1_info_density", 0),
            "entertainment": scores.get("v1_entertainment", 0)
        },
        # tag_context is used as key_insight for embeddings
        "key_insight": result.get("tag_context", ""),
        "search_relevance_score": result.get("score", 0),
        # Categories left empty - only filled from discover page
        "categories": {"major": [], "subcategories": []},
        # Track search sources for debugging/analysis
        "_search_sources": [
            {
                "type": result.get("tag_type", ""),
                "value": result.get("tag_value", ""),
                "relevance": result.get("tag_relevance", 0),
                "meta": result.get("tag_meta", {})
            }
        ]
    }
    
    return episode


def transform_discover_result(result: Dict, category_section: str) -> Dict:
    """
    Transform a single result from discover/top episodes page.
    
    Discover page provides high_relevance_categories which gives us REAL category data.
    """
    scores = result.get("individual_scores", {})
    high_rel_cats = result.get("high_relevance_categories", [])
    
    # Extract major categories from high_relevance_categories (relevance >= 2)
    major_cats = [cat["name"] for cat in high_rel_cats if cat.get("relevance", 0) >= 2]
    
    episode = {
        "id": result.get("episode_id", "").replace("-", "_"),  # Normalize ID
        "content_id": result.get("episode_id", ""),
        "title": result.get("episode_title", ""),
        "series": {
            "id": result.get("series_id", ""),
            "name": result.get("series_name", "")
        },
        "published_at": result.get("publish_date", ""),
        "content_type": "podcast_episodes",
        "scores": {
            "credibility": scores.get("credibility", 0),
            "insight": scores.get("insight", 0),
            "information": scores.get("info_density", 0),
            "entertainment": scores.get("entertainment", 0)
        },
        # Description can be used as key_insight fallback
        "key_insight": "",  # Discover doesn't have tag_context
        "aggregate_score": result.get("aggregate_score"),
        # REAL category data from high_relevance_categories
        "categories": {
            "major": major_cats,
            "subcategories": []
        },
        "_search_sources": [
            {
                "type": "discover",
                "value": category_section,
                "relevance": 0,
                "meta": {}
            }
        ]
    }
    
    return episode


def merge_episode_data(existing: Dict, new: Dict) -> Dict:
    """
    Merge new data into existing episode.
    
    Strategy:
    - Accumulate search sources
    - Use longer key_insight
    - Merge categories (accumulate)
    - Keep higher scores if different
    """
    merged = existing.copy()
    
    # Accumulate search sources
    existing_sources = merged.get("_search_sources", [])
    new_sources = new.get("_search_sources", [])
    
    # Avoid duplicate sources
    existing_source_keys = {(s.get("type"), s.get("value")) for s in existing_sources}
    for source in new_sources:
        key = (source.get("type"), source.get("value"))
        if key not in existing_source_keys:
            existing_sources.append(source)
    
    merged["_search_sources"] = existing_sources
    
    # Use longer key_insight (more context is better for embeddings)
    if len(new.get("key_insight", "") or "") > len(merged.get("key_insight", "") or ""):
        merged["key_insight"] = new["key_insight"]
    
    # Merge categories (accumulate unique)
    existing_cats = set(merged.get("categories", {}).get("major", []))
    new_cats = new.get("categories", {}).get("major", [])
    for cat in new_cats:
        if cat:
            existing_cats.add(cat)
    merged["categories"] = {
        "major": list(existing_cats),
        "subcategories": merged.get("categories", {}).get("subcategories", [])
    }
    
    return merged


def detect_and_process_file(filepath: Path) -> List[Dict]:
    """
    Detect file type and process accordingly.
    
    File types:
    1. Bulk search (org/people/category) - has output.result.res[]
    2. Discover page - has output.result with category keys containing episode arrays
    """
    with open(filepath, "r") as f:
        data = json.load(f)
    
    # Navigate to result
    output = data.get("output", data)
    result = output.get("result", output)
    
    episodes = []
    
    # Check for bulk search format (has 'res' array and 'params')
    if "res" in result and "params" in result:
        for item in result["res"]:
            episodes.append(transform_bulk_search_result(item))
        return episodes
    
    # Check for discover page format (has category keys with episode arrays)
    for key, value in result.items():
        if isinstance(value, list) and len(value) > 0:
            # Check if it looks like an episode array
            first_item = value[0]
            if isinstance(first_item, dict) and "episode_id" in first_item:
                for item in value:
                    episodes.append(transform_discover_result(item, key))
    
    if episodes:
        return episodes
    
    # Try direct array (if the file is just an array of episodes)
    if isinstance(data, list):
        for item in data:
            if "content_title" in item:  # Bulk search format
                episodes.append(transform_bulk_search_result(item))
            elif "episode_title" in item:  # Discover format
                episodes.append(transform_discover_result(item, "unknown"))
    
    return episodes


def get_merge_key(episode: Dict) -> str:
    """
    Get consistent merge key for an episode.
    
    content_id is the reliable key that exists in both org search and discover page.
    """
    return episode.get("content_id", "") or episode.get("id", "")


def main():
    parser = argparse.ArgumentParser(description="Transform search results to episodes format")
    parser.add_argument("--input-dir", type=str, required=True, help="Directory containing raw search JSON files")
    parser.add_argument("--output", type=str, required=True, help="Output file path for combined episodes.json")
    parser.add_argument("--existing", type=str, help="Existing episodes.json to merge with (optional)")
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    output_path = Path(args.output)
    
    # Load existing episodes if provided - use content_id as key
    episodes_by_content_id: Dict[str, Dict] = {}
    if args.existing:
        existing_path = Path(args.existing)
        if existing_path.exists():
            with open(existing_path, "r") as f:
                existing = json.load(f)
            for ep in existing:
                key = get_merge_key(ep)
                if key:
                    episodes_by_content_id[key] = ep
            print(f"Loaded {len(episodes_by_content_id)} existing episodes")
    
    # Process all JSON files in input directory
    json_files = sorted(input_dir.glob("*.json"))
    print(f"Found {len(json_files)} JSON files to process")
    
    total_results = 0
    new_episodes = 0
    merged_episodes = 0
    errors = []
    
    for filepath in json_files:
        try:
            results = detect_and_process_file(filepath)
            total_results += len(results)
            
            for ep in results:
                key = get_merge_key(ep)
                if not key:
                    continue
                    
                if key in episodes_by_content_id:
                    episodes_by_content_id[key] = merge_episode_data(episodes_by_content_id[key], ep)
                    merged_episodes += 1
                else:
                    episodes_by_content_id[key] = ep
                    new_episodes += 1
            
            print(f"  ✓ {filepath.name}: {len(results)} results")
        except Exception as e:
            errors.append(f"{filepath.name}: {e}")
            print(f"  ✗ {filepath.name}: {e}")
    
    # Convert to list and sort by published_at (newest first)
    episodes = list(episodes_by_content_id.values())
    episodes.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    
    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(episodes, f, indent=2)
    
    # Print summary
    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"{'='*50}")
    print(f"Files processed:        {len(json_files)}")
    print(f"Total results parsed:   {total_results}")
    print(f"New episodes added:     {new_episodes}")
    print(f"Existing eps enriched:  {merged_episodes}")
    print(f"Final episode count:    {len(episodes)}")
    print(f"Output written to:      {output_path}")
    
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for err in errors:
            print(f"  - {err}")
    
    # Quick stats on output
    with_key_insight = sum(1 for e in episodes if e.get("key_insight"))
    with_categories = sum(1 for e in episodes if e.get("categories", {}).get("major"))
    
    print(f"\nData coverage:")
    print(f"  Episodes with key_insight: {with_key_insight}/{len(episodes)}")
    print(f"  Episodes with categories:  {with_categories}/{len(episodes)}")


if __name__ == "__main__":
    main()
