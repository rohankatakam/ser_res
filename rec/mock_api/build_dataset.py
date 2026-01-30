#!/usr/bin/env python3
"""
Serafis Mock Dataset Builder

Consolidates extracted API responses from org_search, people_search, theme_search,
and discover_page into a unified dataset for the recommendation engine.

Usage:
    python build_dataset.py
    
Output:
    - data/episodes.json    - Unified episode dataset
    - data/series.json      - Unique series metadata with Serafis scores
    - data/categories.json  - Category taxonomy
    - data/mock_users.json  - Test user profiles
    - data/stats.json       - Dataset statistics
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Set, Optional
from collections import defaultdict

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
ORG_SEARCH_DIR = SCRIPT_DIR / "org_search"
PEOPLE_SEARCH_DIR = SCRIPT_DIR / "people_search"
THEME_SEARCH_DIR = SCRIPT_DIR / "theme_search"
DISCOVER_PAGE_DIR = DATA_DIR / "discover_page"
EPISODE_DETAIL_DIR = DATA_DIR / "episode_detail"


def load_json_files(directory: Path) -> List[Dict]:
    """Load all JSON files from a directory."""
    results = []
    if not directory.exists():
        return results
    
    for json_file in directory.glob("**/*.json"):
        # Skip discover_page folder - handled separately
        if "discover_page" in str(json_file):
            continue
        try:
            with open(json_file, "r") as f:
                data = json.load(f)
                # Extract the results array from the response
                if "output" in data and "result" in data["output"]:
                    result = data["output"]["result"]
                    if "res" in result:
                        for item in result["res"]:
                            item["_source_file"] = str(json_file)
                            item["_search_params"] = result.get("params", {})
                            results.append(item)
        except Exception as e:
            print(f"Error loading {json_file}: {e}")
    
    return results


def load_discover_page_data() -> Dict[str, Any]:
    """Load data from the Discover page API responses."""
    data = {
        "top_episodes": {},      # By category
        "curated_series": [],
        "categories": {}
    }
    
    if not DISCOVER_PAGE_DIR.exists():
        return data
    
    # Load pageload_response.json - contains Top Episodes by category
    pageload_file = DISCOVER_PAGE_DIR / "pageload_response.json"
    if pageload_file.exists():
        try:
            with open(pageload_file, "r") as f:
                response = json.load(f)
                result = response.get("output", {}).get("result", {})
                # Top episodes are organized by category name
                for key, episodes in result.items():
                    if isinstance(episodes, list) and len(episodes) > 0:
                        # Check if it looks like episode data
                        if "episode_id" in episodes[0]:
                            data["top_episodes"][key] = episodes
        except Exception as e:
            print(f"Error loading pageload_response.json: {e}")
    
    # Load moredata_response.json - contains Curated Series
    moredata_file = DISCOVER_PAGE_DIR / "moredata_response.json"
    if moredata_file.exists():
        try:
            with open(moredata_file, "r") as f:
                response = json.load(f)
                result = response.get("output", {}).get("result", [])
                if isinstance(result, list):
                    data["curated_series"] = result
        except Exception as e:
            print(f"Error loading moredata_response.json: {e}")
    
    # Load anotha_page_response.json - contains Category Taxonomy
    taxonomy_file = DISCOVER_PAGE_DIR / "anotha_page_response.json"
    if taxonomy_file.exists():
        try:
            with open(taxonomy_file, "r") as f:
                response = json.load(f)
                result = response.get("output", {}).get("result", {})
                if "index" in result:
                    data["categories"] = result["index"]
        except Exception as e:
            print(f"Error loading anotha_page_response.json: {e}")
    
    return data


def build_curated_series_map(curated_series: List[Dict]) -> Dict[str, Dict]:
    """Build a map of series_id -> series metadata from curated series."""
    series_map = {}
    for series in curated_series:
        series_id = series.get("id", "")
        if series_id:
            # Calculate tier from popv (e.g., 0.1 = Top 0.1%, 5 = Top 5%)
            popv = series.get("popv")
            if popv is None:
                popv = 100
            if popv <= 0.1:
                tier = "Top 0.1%"
            elif popv <= 0.3:
                tier = "Top 0.3%"
            elif popv <= 1:
                tier = "Top 1%"
            elif popv <= 5:
                tier = "Top 5%"
            elif popv <= 20:
                tier = "Top 20%"
            else:
                tier = None
            
            series_map[series_id] = {
                "id": series_id,
                "name": series.get("name", ""),
                "serafis_score": series.get("serafis_score", 0),
                "serafis_tier": series.get("serafis_tier"),
                "popv": popv,
                "tier_label": tier,
                "description": series.get("description", ""),
                "image_url": series.get("image", ""),
                "publisher_type": series.get("publisher_type", ""),
                "popularity": series.get("taddy", {}).get("popularity", "")
            }
    return series_map


def build_top_episodes_map(top_episodes: Dict[str, List[Dict]]) -> Dict[str, Dict]:
    """Build a map of episode_id -> episode data from top episodes."""
    episode_map = {}
    for category, episodes in top_episodes.items():
        for ep in episodes:
            episode_id = ep.get("episode_id", "")
            if episode_id:
                if episode_id not in episode_map:
                    episode_map[episode_id] = {
                        "episode_id": episode_id,
                        "aggregate_score": ep.get("aggregate_score", 0),
                        "high_relevance_categories": ep.get("high_relevance_categories", []),
                        "individual_scores": ep.get("individual_scores", {}),
                        "description": ep.get("description", ""),
                        "duration": ep.get("duration", 0),
                        "top_in_categories": [category]
                    }
                else:
                    # Add this category to the list
                    if category not in episode_map[episode_id]["top_in_categories"]:
                        episode_map[episode_id]["top_in_categories"].append(category)
    return episode_map


def load_episode_detail_data() -> Dict[str, Dict]:
    """Load episode detail data including critical views/new ideas."""
    episode_details = {}
    
    if not EPISODE_DETAIL_DIR.exists():
        return episode_details
    
    for json_file in EPISODE_DETAIL_DIR.glob("*.json"):
        try:
            with open(json_file, "r") as f:
                data = json.load(f)
                result = data.get("output", {}).get("result", {})
                
                # Get episode ID from the new_ideas or insights section
                episode_id = None
                for section in ["new_ideas", "insights", "data_points", "top_quotes"]:
                    if section in result and "podcast_episode_id" in result[section]:
                        episode_id = result[section]["podcast_episode_id"]
                        break
                
                if not episode_id:
                    continue
                
                # Parse new_ideas for non-consensus rating
                new_ideas = result.get("new_ideas", {})
                new_ideas_text = new_ideas.get("assembly_response", "")
                
                # Determine non-consensus level
                non_consensus_level = None
                if "highly non-consensus" in new_ideas_text.lower():
                    non_consensus_level = "highly_non_consensus"
                elif "somewhat insightful" in new_ideas_text.lower() or "somewhat contrarian" in new_ideas_text.lower():
                    non_consensus_level = "somewhat_insightful"
                elif "aligned with commonly held views" in new_ideas_text.lower():
                    non_consensus_level = "consensus"
                elif "non-consensus" in new_ideas_text.lower() or "contrarian" in new_ideas_text.lower():
                    non_consensus_level = "non_consensus"
                
                # Parse insights
                insights = result.get("insights", {})
                insights_text = insights.get("assembly_response", "")
                
                # Parse top quotes
                top_quotes = result.get("top_quotes", {})
                quotes_text = top_quotes.get("assembly_response", "")
                
                # Parse data points
                data_points = result.get("data_points", {})
                data_points_text = data_points.get("assembly_response", "")
                
                episode_details[episode_id] = {
                    "episode_id": episode_id,
                    "episode_name": new_ideas.get("podcast_episode_name", ""),
                    "series_name": new_ideas.get("podcast_series_name", ""),
                    "non_consensus_level": non_consensus_level,
                    "new_ideas_summary": new_ideas_text[:500] if new_ideas_text else None,
                    "key_insights": insights_text[:500] if insights_text else None,
                    "top_quotes": quotes_text[:500] if quotes_text else None,
                    "data_points": data_points_text[:500] if data_points_text else None,
                    "has_critical_views": non_consensus_level in ["highly_non_consensus", "non_consensus"]
                }
                
        except Exception as e:
            print(f"Error loading episode detail {json_file}: {e}")
    
    return episode_details


def extract_categories_from_tag(item: Dict) -> Dict[str, List[str]]:
    """Extract category information from tag data."""
    categories = {"major": [], "subcategories": []}
    
    tag_type = item.get("tag_type", "")
    tag_value = item.get("tag_value", "")
    tag_meta = item.get("tag_meta", {})
    
    if tag_type == "categories":
        # Check if it's a subcategory based on tag_meta or search params
        search_params = item.get("_search_params", {})
        if search_params.get("tag_type") == "v1_sub_categories" or "sub_categories" in item.get("_source_file", ""):
            categories["subcategories"].append(tag_value)
        else:
            categories["major"].append(tag_value)
    
    return categories


def build_episode_record(item: Dict, all_items: List[Dict], top_episodes_map: Dict[str, Dict] = None, episode_details: Dict[str, Dict] = None) -> Dict:
    """Build a unified episode record from raw API data."""
    content_id = item.get("content_id", "")
    
    # Find all items for this episode to aggregate data
    related_items = [i for i in all_items if i.get("content_id") == content_id]
    
    # Aggregate entities from org searches
    entities = []
    for related in related_items:
        if related.get("tag_type") == "organizations":
            entities.append({
                "name": related.get("tag_value", ""),
                "relevance": related.get("tag_relevance", 0),
                "context": related.get("tag_context", "")
            })
    
    # Aggregate people from people searches
    people = []
    for related in related_items:
        if related.get("tag_type") == "people":
            people.append({
                "name": related.get("tag_value", ""),
                "relevance": related.get("tag_relevance", 0),
                "context": related.get("tag_context", ""),
                "title": related.get("tag_meta", {}).get("title", "")
            })
    
    # Aggregate categories
    major_categories = set()
    subcategories = set()
    for related in related_items:
        if related.get("tag_type") == "categories":
            source_file = related.get("_source_file", "")
            if "sub_categories" in source_file:
                subcategories.add(related.get("tag_value", ""))
            else:
                major_categories.add(related.get("tag_value", ""))
    
    # Get content scores (handle None values)
    content_scores = item.get("content_scores", {}) or {}
    
    # Check if we have enhanced data from top_episodes
    top_episodes_map = top_episodes_map or {}
    top_ep_data = top_episodes_map.get(content_id, {})
    
    # Check if we have episode detail data (critical views, etc.)
    episode_details = episode_details or {}
    detail_data = episode_details.get(content_id, {})
    
    # Use top episodes data for better scores if available
    if top_ep_data:
        individual_scores = top_ep_data.get("individual_scores", {})
        if individual_scores:
            content_scores = {
                "v1_insight": individual_scores.get("insight", content_scores.get("v1_insight", 0)),
                "v1_credibility": individual_scores.get("credibility", content_scores.get("v1_credibility", 0)),
                "v1_info_density": individual_scores.get("info_density", content_scores.get("v1_info_density", 0)),
                "v1_entertainment": individual_scores.get("entertainment", content_scores.get("v1_entertainment", 0))
            }
        
        # Add high_relevance_categories to major categories
        for cat_info in top_ep_data.get("high_relevance_categories", []):
            cat_name = cat_info.get("name", "")
            if cat_name and cat_name not in major_categories:
                major_categories.add(cat_name)
    
    # Build the episode record
    return {
        "id": item.get("id", ""),
        "content_id": content_id,
        "title": item.get("content_title", ""),
        "series": {
            "id": item.get("series_id", ""),
            "name": item.get("series_name", "")
        },
        "published_at": item.get("publish_date", ""),
        "content_type": item.get("content_type", "podcast_episodes"),
        "scores": {
            "insight": content_scores.get("v1_insight") or content_scores.get("insight") or 0,
            "credibility": content_scores.get("v1_credibility") or content_scores.get("credibility") or 0,
            "information": content_scores.get("v1_info_density") or content_scores.get("info_density") or 0,
            "entertainment": content_scores.get("v1_entertainment") or content_scores.get("entertainment") or 0
        },
        "categories": {
            "major": list(major_categories),
            "subcategories": list(subcategories)
        },
        "entities": entities,
        "people": people,
        # Use tag_context as a proxy for key_insight when available
        "key_insight": item.get("tag_context", "")[:200] if item.get("tag_context") else None,
        # Critical views data from episode detail extraction
        "critical_views": {
            "non_consensus_level": detail_data.get("non_consensus_level"),
            "has_critical_views": detail_data.get("has_critical_views", False),
            "new_ideas_summary": detail_data.get("new_ideas_summary"),
            "key_insights": detail_data.get("key_insights"),
        } if detail_data else None,
        "search_relevance_score": item.get("score", 0),
        # New: aggregate score from top episodes (0-1 scale, e.g., 0.81 = 81%)
        "aggregate_score": top_ep_data.get("aggregate_score"),
        # New: is this episode in the "Top Episodes" for any category?
        "top_in_categories": top_ep_data.get("top_in_categories", [])
    }


def deduplicate_episodes(episodes: List[Dict]) -> List[Dict]:
    """Deduplicate episodes by content_id, merging metadata."""
    episode_map: Dict[str, Dict] = {}
    
    for ep in episodes:
        content_id = ep["content_id"]
        
        if content_id not in episode_map:
            episode_map[content_id] = ep
        else:
            # Merge entities
            existing = episode_map[content_id]
            existing_entity_names = {e["name"] for e in existing["entities"]}
            for entity in ep["entities"]:
                if entity["name"] not in existing_entity_names:
                    existing["entities"].append(entity)
            
            # Merge people
            existing_people_names = {p["name"] for p in existing["people"]}
            for person in ep["people"]:
                if person["name"] not in existing_people_names:
                    existing["people"].append(person)
            
            # Merge categories
            existing["categories"]["major"] = list(
                set(existing["categories"]["major"]) | set(ep["categories"]["major"])
            )
            existing["categories"]["subcategories"] = list(
                set(existing["categories"]["subcategories"]) | set(ep["categories"]["subcategories"])
            )
    
    return list(episode_map.values())


def extract_series(episodes: List[Dict], curated_series_map: Dict[str, Dict]) -> List[Dict]:
    """Extract unique series from episodes, enriched with curated series data."""
    series_map: Dict[str, Dict] = {}
    series_episode_count: Dict[str, int] = defaultdict(int)
    
    for ep in episodes:
        series_id = ep["series"]["id"]
        series_episode_count[series_id] += 1
        
        if series_id not in series_map:
            # Start with basic info from episode
            series_map[series_id] = {
                "id": series_id,
                "name": ep["series"]["name"],
                "popularity": 0,
                "serafis_score": 0,
                "tier_label": None,
                "is_curated": False
            }
            
            # Enrich with curated series data if available
            if series_id in curated_series_map:
                curated = curated_series_map[series_id]
                series_map[series_id].update({
                    "serafis_score": curated.get("serafis_score", 0),
                    "tier_label": curated.get("tier_label"),
                    "popv": curated.get("popv"),
                    "description": curated.get("description", ""),
                    "image_url": curated.get("image_url", ""),
                    "publisher_type": curated.get("publisher_type", ""),
                    "is_curated": True
                })
    
    # Set popularity based on serafis_score (if available) or episode count
    for series_id, series in series_map.items():
        series["episode_count"] = series_episode_count[series_id]
        
        # Use serafis_score if available, otherwise estimate from episode count
        if series.get("serafis_score", 0) > 0:
            series["popularity"] = series["serafis_score"]
        else:
            max_count = max(series_episode_count.values()) if series_episode_count else 1
            series["popularity"] = int((series_episode_count[series_id] / max_count) * 100)
    
    return sorted(series_map.values(), key=lambda s: s["popularity"], reverse=True)


def create_mock_users(episodes: List[Dict], series: List[Dict]) -> List[Dict]:
    """Create mock user profiles for testing."""
    # Get top series by popularity
    top_series = [s["id"] for s in series[:10]]
    
    # Get unique categories
    all_major_cats = set()
    all_subcats = set()
    for ep in episodes:
        all_major_cats.update(ep["categories"]["major"])
        all_subcats.update(ep["categories"]["subcategories"])
    
    return [
        {
            "id": "user_prosumer_ai",
            "name": "AI Prosumer",
            "category_interests": ["Technology & AI", "Startups, Growth & Founder Journeys"],
            "subscribed_series": top_series[:3],
            "seen_episode_ids": [],
            "bookmarked_episode_ids": [],
            "not_interested_ids": []
        },
        {
            "id": "user_prosumer_crypto",
            "name": "Crypto Prosumer",
            "category_interests": ["Crypto & Web3", "Technology & AI"],
            "subscribed_series": top_series[3:6] if len(top_series) > 3 else top_series[:3],
            "seen_episode_ids": [],
            "bookmarked_episode_ids": [],
            "not_interested_ids": []
        },
        {
            "id": "user_prosumer_markets",
            "name": "Markets Prosumer",
            "category_interests": ["Public Markets", "Macroeconomics"],
            "subscribed_series": top_series[6:9] if len(top_series) > 6 else top_series[:3],
            "seen_episode_ids": [],
            "bookmarked_episode_ids": [],
            "not_interested_ids": []
        },
        {
            "id": "user_cold_start",
            "name": "New User (Cold Start)",
            "category_interests": [],
            "subscribed_series": [],
            "seen_episode_ids": [],
            "bookmarked_episode_ids": [],
            "not_interested_ids": []
        }
    ]


def calculate_stats(episodes: List[Dict], series: List[Dict], categories_taxonomy: Dict = None) -> Dict:
    """Calculate dataset statistics."""
    # Score distributions (filter out None values)
    insight_scores = [ep["scores"]["insight"] for ep in episodes if ep["scores"]["insight"] is not None]
    credibility_scores = [ep["scores"]["credibility"] for ep in episodes if ep["scores"]["credibility"] is not None]
    
    # Category counts
    major_cat_counts = defaultdict(int)
    subcat_counts = defaultdict(int)
    for ep in episodes:
        for cat in ep["categories"]["major"]:
            major_cat_counts[cat] += 1
        for cat in ep["categories"]["subcategories"]:
            subcat_counts[cat] += 1
    
    # Entity counts
    entity_counts = defaultdict(int)
    for ep in episodes:
        for entity in ep["entities"]:
            entity_counts[entity["name"]] += 1
    
    # People counts
    people_counts = defaultdict(int)
    for ep in episodes:
        for person in ep["people"]:
            people_counts[person["name"]] += 1
    
    # Count curated series and top episodes
    curated_series_count = sum(1 for s in series if s.get("is_curated"))
    episodes_with_aggregate_score = sum(1 for ep in episodes if ep.get("aggregate_score") is not None)
    
    # Count critical views
    episodes_with_critical_views = sum(
        1 for ep in episodes 
        if ep.get("critical_views") and ep["critical_views"].get("has_critical_views")
    )
    non_consensus_levels = defaultdict(int)
    for ep in episodes:
        if ep.get("critical_views") and ep["critical_views"].get("non_consensus_level"):
            non_consensus_levels[ep["critical_views"]["non_consensus_level"]] += 1
    
    # Top series by serafis_score
    top_series = sorted(
        [s for s in series if s.get("serafis_score", 0) > 0],
        key=lambda s: s.get("serafis_score", 0),
        reverse=True
    )[:10]
    
    return {
        "total_episodes": len(episodes),
        "total_series": len(series),
        "curated_series": curated_series_count,
        "episodes_with_aggregate_score": episodes_with_aggregate_score,
        "episodes_with_critical_views": episodes_with_critical_views,
        "non_consensus_levels": dict(non_consensus_levels),
        "avg_insight_score": sum(insight_scores) / len(insight_scores) if insight_scores else 0,
        "avg_credibility_score": sum(credibility_scores) / len(credibility_scores) if credibility_scores else 0,
        "major_categories": dict(sorted(major_cat_counts.items(), key=lambda x: x[1], reverse=True)),
        "subcategories": dict(sorted(subcat_counts.items(), key=lambda x: x[1], reverse=True)),
        "category_taxonomy_count": len(categories_taxonomy) if categories_taxonomy else 0,
        "top_entities": dict(sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:20]),
        "top_people": dict(sorted(people_counts.items(), key=lambda x: x[1], reverse=True)[:20]),
        "top_series_by_serafis_score": [
            {"name": s["name"], "serafis_score": s["serafis_score"], "tier": s.get("tier_label")}
            for s in top_series
        ],
        "extraction_date": datetime.now().isoformat()
    }


def main():
    print("=" * 60)
    print("Serafis Mock Dataset Builder")
    print("=" * 60)
    
    # Create data directory
    DATA_DIR.mkdir(exist_ok=True)
    
    # Load discover page data first (for enrichment)
    print("\n📂 Loading discover page data...")
    discover_data = load_discover_page_data()
    
    curated_series_map = build_curated_series_map(discover_data["curated_series"])
    print(f"  - Curated series: {len(curated_series_map)} series")
    
    top_episodes_map = build_top_episodes_map(discover_data["top_episodes"])
    print(f"  - Top episodes: {len(top_episodes_map)} episodes across {len(discover_data['top_episodes'])} categories")
    
    # Load episode detail data (critical views, insights, etc.)
    print("\n📂 Loading episode detail data...")
    episode_details = load_episode_detail_data()
    print(f"  - Episode details: {len(episode_details)} episodes")
    non_consensus_count = sum(1 for ep in episode_details.values() if ep.get("has_critical_views"))
    print(f"  - Non-consensus episodes: {non_consensus_count}")
    
    categories_taxonomy = discover_data["categories"]
    print(f"  - Categories: {len(categories_taxonomy)} major categories")
    
    # Load all extracted data from searches
    print("\n📂 Loading search data...")
    all_items = []
    
    org_items = load_json_files(ORG_SEARCH_DIR)
    print(f"  - Org search: {len(org_items)} items")
    all_items.extend(org_items)
    
    people_items = load_json_files(PEOPLE_SEARCH_DIR)
    print(f"  - People search: {len(people_items)} items")
    all_items.extend(people_items)
    
    theme_items = load_json_files(THEME_SEARCH_DIR)
    print(f"  - Theme search: {len(theme_items)} items")
    all_items.extend(theme_items)
    
    print(f"  Total raw items: {len(all_items)}")
    
    # Build episode records (with top_episodes enrichment)
    print("\n🔨 Building episode records...")
    episodes = []
    seen_content_ids = set()
    
    for item in all_items:
        content_id = item.get("content_id", "")
        if content_id and content_id not in seen_content_ids:
            episode = build_episode_record(item, all_items, top_episodes_map, episode_details)
            episodes.append(episode)
            seen_content_ids.add(content_id)
    
    # Also add episodes from top_episodes that aren't in search results
    print("  Adding top episodes not in search results...")
    for category, cat_episodes in discover_data["top_episodes"].items():
        for ep in cat_episodes:
            content_id = ep.get("episode_id", "")
            if content_id and content_id not in seen_content_ids:
                # Build episode from top_episodes data
                individual_scores = ep.get("individual_scores", {})
                
                # Check for episode detail data
                detail_data = episode_details.get(content_id, {})
                
                episode = {
                    "id": content_id,  # Use episode_id as id
                    "content_id": content_id,
                    "title": ep.get("episode_title", ""),
                    "series": {
                        "id": ep.get("series_id", ""),
                        "name": ep.get("series_name", "")
                    },
                    "published_at": ep.get("publish_date", ""),
                    "content_type": "podcast_episodes",
                    "scores": {
                        "insight": individual_scores.get("insight", 0),
                        "credibility": individual_scores.get("credibility", 0),
                        "information": individual_scores.get("info_density", 0),
                        "entertainment": individual_scores.get("entertainment", 0)
                    },
                    "categories": {
                        "major": [cat.get("name") for cat in ep.get("high_relevance_categories", [])],
                        "subcategories": []
                    },
                    "entities": [],
                    "people": [],
                    "key_insight": ep.get("description", "")[:200] if ep.get("description") else None,
                    "critical_views": {
                        "non_consensus_level": detail_data.get("non_consensus_level"),
                        "has_critical_views": detail_data.get("has_critical_views", False),
                        "new_ideas_summary": detail_data.get("new_ideas_summary"),
                        "key_insights": detail_data.get("key_insights"),
                    } if detail_data else None,
                    "search_relevance_score": 0,
                    "aggregate_score": ep.get("aggregate_score"),
                    "top_in_categories": [category],
                    "duration": ep.get("duration", 0)
                }
                episodes.append(episode)
                seen_content_ids.add(content_id)
    
    # Deduplicate and merge
    print("🔄 Deduplicating and merging metadata...")
    episodes = deduplicate_episodes(episodes)
    print(f"  Unique episodes: {len(episodes)}")
    
    # Extract series (enriched with curated series data)
    print("\n📺 Extracting series...")
    series = extract_series(episodes, curated_series_map)
    print(f"  Unique series: {len(series)}")
    print(f"  Curated series in dataset: {sum(1 for s in series if s.get('is_curated'))}")
    
    # Create mock users
    print("\n👤 Creating mock users...")
    mock_users = create_mock_users(episodes, series)
    print(f"  Mock users: {len(mock_users)}")
    
    # Calculate stats
    print("\n📊 Calculating statistics...")
    stats = calculate_stats(episodes, series, categories_taxonomy)
    
    # Save outputs
    print("\n💾 Saving outputs...")
    
    with open(DATA_DIR / "episodes.json", "w") as f:
        json.dump(episodes, f, indent=2)
    print(f"  ✅ data/episodes.json ({len(episodes)} episodes)")
    
    with open(DATA_DIR / "series.json", "w") as f:
        json.dump(series, f, indent=2)
    print(f"  ✅ data/series.json ({len(series)} series)")
    
    # Save categories taxonomy
    if categories_taxonomy:
        with open(DATA_DIR / "categories.json", "w") as f:
            json.dump(categories_taxonomy, f, indent=2)
        print(f"  ✅ data/categories.json ({len(categories_taxonomy)} categories)")
    
    with open(DATA_DIR / "mock_users.json", "w") as f:
        json.dump(mock_users, f, indent=2)
    print(f"  ✅ data/mock_users.json ({len(mock_users)} users)")
    
    with open(DATA_DIR / "stats.json", "w") as f:
        json.dump(stats, f, indent=2)
    print(f"  ✅ data/stats.json")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📈 DATASET SUMMARY")
    print("=" * 60)
    print(f"Total episodes:         {stats['total_episodes']}")
    print(f"Total series:           {stats['total_series']}")
    print(f"Curated series:         {stats['curated_series']}")
    print(f"Episodes w/ agg score:  {stats['episodes_with_aggregate_score']}")
    print(f"Episodes w/ crit views: {stats['episodes_with_critical_views']}")
    print(f"Category taxonomy:      {stats['category_taxonomy_count']} major categories")
    print(f"Avg insight score:      {stats['avg_insight_score']:.2f}")
    print(f"Avg credibility score:  {stats['avg_credibility_score']:.2f}")
    
    if stats.get('non_consensus_levels'):
        print(f"\nNon-consensus breakdown:")
        for level, count in stats['non_consensus_levels'].items():
            print(f"  - {level}: {count} episodes")
    
    print(f"\nTop categories:")
    for cat, count in list(stats['major_categories'].items())[:5]:
        print(f"  - {cat}: {count} episodes")
    
    print(f"\nTop series (by Serafis Score):")
    for s in stats.get('top_series_by_serafis_score', [])[:5]:
        tier = f" ({s['tier']})" if s.get('tier') else ""
        print(f"  - {s['name']}: {s['serafis_score']}{tier}")
    
    print(f"\nTop entities:")
    for entity, count in list(stats['top_entities'].items())[:5]:
        print(f"  - {entity}: {count} mentions")
    
    print(f"\nTop people:")
    for person, count in list(stats['top_people'].items())[:5]:
        print(f"  - {person}: {count} mentions")
    
    print("\n✅ Dataset build complete!")
    print(f"   Output directory: {DATA_DIR}")


if __name__ == "__main__":
    main()
