#!/usr/bin/env python3
"""
Populate Pinecone with episode embeddings using the algorithm's get_embed_text (no truncation).

Reads episodes from Firestore or a dataset, generates embeddings via OpenAI, and upserts
to Pinecone with vector id = episode id (same as Firestore) for lookup.

Requires:
  - PINECONE_API_KEY in env (or --pinecone-key)
  - OPENAI_API_KEY in env (or --openai-key)
  - For Firestore: GOOGLE_APPLICATION_CREDENTIALS or --credentials

Usage:
  From repo root:
    # From dataset (e.g. eval_909_feb2026)
    python -m server.scripts.populate_pinecone --source dataset --dataset eval_909_feb2026

    # From Firestore
    python -m server.scripts.populate_pinecone --source firestore

  Optional:
    --algorithm-dir algorithm
    --limit 500
    --credentials path/to/serviceAccountKey.json
"""

import argparse
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from server.services.algorithm_loader import AlgorithmLoader
from server.services.dataset_loader import DatasetLoader
from server.services.embedding_generator import EmbeddingGenerator
from server.services.episode_provider import DatasetEpisodeProvider, FirestoreEpisodeProvider
from server.services.pinecone_store import PineconeEmbeddingStore


def _normalize_episode_id(ep: dict) -> dict:
    """Ensure episode has 'id' for embedding key and Pinecone vector id."""
    if ep.get("id"):
        return ep
    cid = ep.get("content_id")
    if cid:
        ep = dict(ep)
        ep["id"] = cid
    return ep


def main() -> int:
    parser = argparse.ArgumentParser(description="Populate Pinecone with episode embeddings")
    parser.add_argument(
        "--source",
        choices=("dataset", "firestore"),
        default="dataset",
        help="Where to load episodes from",
    )
    parser.add_argument(
        "--dataset",
        default="eval_909_feb2026",
        help="Dataset name when --source=dataset (e.g. eval_909_feb2026)",
    )
    parser.add_argument(
        "--algorithm-dir",
        type=Path,
        default=None,
        help="Path to algorithm directory (default: repo root / algorithm)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max episodes to process (default: all)",
    )
    parser.add_argument(
        "--credentials",
        type=Path,
        default=None,
        help="Path to Firebase service account JSON (for --source firestore)",
    )
    parser.add_argument(
        "--openai-key",
        default=os.environ.get("OPENAI_API_KEY"),
        help="OpenAI API key (default: OPENAI_API_KEY env)",
    )
    parser.add_argument(
        "--pinecone-key",
        default=os.environ.get("PINECONE_API_KEY"),
        help="Pinecone API key (default: PINECONE_API_KEY env)",
    )
    args = parser.parse_args()

    algorithm_dir = args.algorithm_dir or (_REPO_ROOT / "algorithm")
    if not algorithm_dir.exists():
        print(f"Algorithm dir not found: {algorithm_dir}", file=sys.stderr)
        return 1

    # Load algorithm (get_embed_text, strategy_version, dimensions)
    loader = AlgorithmLoader(algorithm_dir)
    algo = loader.load_algorithm("")
    print(f"Algorithm: {algo.manifest.name} v{algo.manifest.version} strategy {algo.strategy_version}")

    # Load episodes
    if args.source == "firestore":
        try:
            from server.config import get_config
            cfg = get_config()
            provider = FirestoreEpisodeProvider(
                credentials_path=args.credentials,
                episodes_collection=cfg.episodes_collection,
                series_collection=cfg.series_collection,
            )
        except Exception:
            provider = FirestoreEpisodeProvider(credentials_path=args.credentials)
        episodes = provider.get_episodes(limit=args.limit or 2000)
        dataset_version = "firestore"
    else:
        fixtures_dir = _REPO_ROOT / "evaluation" / "fixtures"
        if not fixtures_dir.exists():
            print(f"Fixtures dir not found: {fixtures_dir}", file=sys.stderr)
            return 1
        ds_loader = DatasetLoader(fixtures_dir)
        dataset = ds_loader.load_dataset(args.dataset)
        provider = DatasetEpisodeProvider(dataset)
        episodes = provider.get_episodes(limit=args.limit)
        dataset_version = args.dataset

    # Normalize id for datasets that use content_id
    episodes = [_normalize_episode_id(ep) for ep in episodes]
    bad = [ep for ep in episodes if not ep.get("id")]
    if bad:
        print(f"Skipping {len(bad)} episodes without id", file=sys.stderr)
        episodes = [ep for ep in episodes if ep.get("id")]

    if not episodes:
        print("No episodes to embed.", file=sys.stderr)
        return 0

    print(f"Episodes to embed: {len(episodes)} (source={args.source}, dataset_version={dataset_version})")

    if not args.openai_key:
        print("OPENAI_API_KEY (or --openai-key) required.", file=sys.stderr)
        return 1
    if not args.pinecone_key:
        print("PINECONE_API_KEY (or --pinecone-key) required.", file=sys.stderr)
        return 1

    # Generate embeddings
    generator = EmbeddingGenerator(
        api_key=args.openai_key,
        model=algo.embedding_model,
        dimensions=algo.embedding_dimensions,
    )
    result = generator.generate_for_episodes(
        episodes,
        get_embed_text=algo.get_embed_text,
        on_progress=lambda p: print(f"  Embedding {p.current}/{p.total} (batch {p.batch_num}/{p.total_batches})"),
    )
    if result.errors:
        for e in result.errors:
            print(f"  Error: {e}", file=sys.stderr)
    print(f"Generated {result.total_generated}, skipped {result.total_skipped}, errors {len(result.errors)}")

    if not result.embeddings:
        print("No embeddings to save.", file=sys.stderr)
        return 0

    # Upsert to rec_for_you index (separate from RAG indexes). Use folder_name so namespace matches the server.
    index_name = os.environ.get("PINECONE_REC_FOR_YOU_INDEX", "rec-for-you")
    store = PineconeEmbeddingStore(
        api_key=args.pinecone_key,
        index_name=index_name,
        dimension=algo.embedding_dimensions,
    )
    algorithm_version = getattr(algo, "folder_name", None) or algo.manifest.version
    store.save_embeddings(
        algorithm_version=algorithm_version,
        strategy_version=algo.strategy_version,
        dataset_version=dataset_version,
        embeddings=result.embeddings,
        embedding_model=algo.embedding_model,
        embedding_dimensions=algo.embedding_dimensions,
    )
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
