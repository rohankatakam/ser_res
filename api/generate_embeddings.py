#!/usr/bin/env python3
"""
Serafis Embedding Generator

Generates embeddings for all episodes using OpenAI's text-embedding-3-small model.
Embeddings are stored in embeddings.json for use by the recommendation API.

Usage:
    # Set your OpenAI API key
    export OPENAI_API_KEY="sk-..."
    
    # Generate embeddings for all episodes
    python generate_embeddings.py
    
    # Generate for specific episodes (by ID)
    python generate_embeddings.py --ids B7d9XwUOKOuoH7R8Tnzi lMI5IYECEDErYBlmWMSi
    
    # Regenerate all (force overwrite)
    python generate_embeddings.py --force

Output:
    data/embeddings.json - Dict mapping episode_id to embedding vector
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict, Optional

# Check for OpenAI
try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not installed.")
    print("Install with: pip install openai")
    sys.exit(1)

# ============================================================================
# Configuration
# ============================================================================

DATA_DIR = Path(__file__).parent / "data"
EPISODES_FILE = DATA_DIR / "episodes.json"
EMBEDDINGS_FILE = DATA_DIR / "embeddings.json"

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

# Batch size for API calls (OpenAI allows up to 2048 inputs per request)
BATCH_SIZE = 100

# Rate limiting
REQUESTS_PER_MINUTE = 500
DELAY_BETWEEN_BATCHES = 0.5  # seconds

# ============================================================================
# Embedding Logic
# ============================================================================

def get_embed_text(episode: dict) -> str:
    """
    Generate text for embedding - uses title + key_insight.
    
    This is the SAME formula used for user activity vectors to ensure
    apples-to-apples comparison in cosine similarity.
    """
    title = episode.get("title", "")
    key_insight = episode.get("key_insight") or ""
    
    # Truncate key_insight to first 500 chars to reduce noise
    if len(key_insight) > 500:
        key_insight = key_insight[:500]
    
    embed_text = f"{title}. {key_insight}".strip()
    
    # Ensure we have something to embed
    if not embed_text or embed_text == ".":
        embed_text = title or "Untitled episode"
    
    return embed_text


def load_episodes() -> List[dict]:
    """Load episodes from JSON file."""
    with open(EPISODES_FILE) as f:
        return json.load(f)


def load_existing_embeddings() -> Dict[str, List[float]]:
    """Load existing embeddings if file exists."""
    if EMBEDDINGS_FILE.exists():
        with open(EMBEDDINGS_FILE) as f:
            return json.load(f)
    return {}


def save_embeddings(embeddings: Dict[str, List[float]]):
    """Save embeddings to JSON file."""
    with open(EMBEDDINGS_FILE, 'w') as f:
        json.dump(embeddings, f)
    print(f"Saved {len(embeddings)} embeddings to {EMBEDDINGS_FILE}")


def generate_embeddings_batch(
    client: OpenAI,
    texts: List[str]
) -> List[List[float]]:
    """Generate embeddings for a batch of texts."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
        dimensions=EMBEDDING_DIMENSIONS
    )
    return [item.embedding for item in response.data]


def estimate_cost(num_episodes: int, avg_text_length: int = 300) -> float:
    """Estimate API cost for embedding generation."""
    # text-embedding-3-small costs $0.02 per 1M tokens
    # Rough estimate: 1 token ≈ 4 characters
    estimated_tokens = num_episodes * avg_text_length / 4
    cost = (estimated_tokens / 1_000_000) * 0.02
    return cost


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Generate embeddings for episodes")
    parser.add_argument("--ids", nargs="+", help="Specific episode IDs to embed")
    parser.add_argument("--force", action="store_true", help="Force regenerate all embeddings")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without calling API")
    args = parser.parse_args()
    
    # Check API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key and not args.dry_run:
        print("Error: OPENAI_API_KEY environment variable not set.")
        print("Set it with: export OPENAI_API_KEY='sk-...'")
        sys.exit(1)
    
    # Load data
    print(f"Loading episodes from {EPISODES_FILE}...")
    episodes = load_episodes()
    print(f"Loaded {len(episodes)} episodes")
    
    # Load existing embeddings
    existing = {} if args.force else load_existing_embeddings()
    print(f"Existing embeddings: {len(existing)}")
    
    # Determine which episodes need embeddings
    if args.ids:
        # Specific IDs requested
        episode_map = {ep["id"]: ep for ep in episodes}
        to_embed = [episode_map[id] for id in args.ids if id in episode_map]
        if len(to_embed) != len(args.ids):
            missing = set(args.ids) - set(episode_map.keys())
            print(f"Warning: {len(missing)} episode IDs not found: {missing}")
    else:
        # All episodes that don't have embeddings yet
        to_embed = [ep for ep in episodes if ep["id"] not in existing]
    
    print(f"Episodes to embed: {len(to_embed)}")
    
    if not to_embed:
        print("All episodes already have embeddings. Use --force to regenerate.")
        return
    
    # Show cost estimate
    avg_length = sum(len(get_embed_text(ep)) for ep in to_embed) / len(to_embed)
    cost = estimate_cost(len(to_embed), avg_length)
    print(f"Estimated cost: ${cost:.4f}")
    
    if args.dry_run:
        print("\n[DRY RUN] Would generate embeddings for:")
        for ep in to_embed[:5]:
            text = get_embed_text(ep)
            print(f"  - {ep['id']}: {text[:80]}...")
        if len(to_embed) > 5:
            print(f"  ... and {len(to_embed) - 5} more")
        return
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Generate embeddings in batches
    embeddings = existing.copy()
    total_batches = (len(to_embed) + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f"\nGenerating embeddings in {total_batches} batches...")
    
    for i in range(0, len(to_embed), BATCH_SIZE):
        batch = to_embed[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        
        print(f"Batch {batch_num}/{total_batches} ({len(batch)} episodes)...", end=" ")
        
        # Prepare texts
        texts = [get_embed_text(ep) for ep in batch]
        ids = [ep["id"] for ep in batch]
        
        try:
            # Generate embeddings
            vectors = generate_embeddings_batch(client, texts)
            
            # Store results
            for ep_id, vector in zip(ids, vectors):
                embeddings[ep_id] = vector
            
            print(f"Done")
            
            # Rate limiting
            if i + BATCH_SIZE < len(to_embed):
                time.sleep(DELAY_BETWEEN_BATCHES)
                
        except Exception as e:
            print(f"Error: {e}")
            # Save progress
            save_embeddings(embeddings)
            print("Saved progress. Re-run to continue.")
            sys.exit(1)
    
    # Save final results
    save_embeddings(embeddings)
    print(f"\nSuccess! Generated embeddings for {len(to_embed)} episodes.")
    print(f"Total embeddings: {len(embeddings)}")


if __name__ == "__main__":
    main()
