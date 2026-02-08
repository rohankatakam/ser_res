#!/usr/bin/env python3
"""
Serafis Evaluation Framework Server

A comprehensive FastAPI server that provides:
1. Algorithm and dataset version management
2. Embedding caching and generation
3. Recommendation engine endpoints
4. Evaluation test runner endpoints

Usage:
    cd server
    uvicorn server:app --reload --port 8000
    
    # Or from rec/ directory:
    uvicorn server.server:app --reload --port 8000
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

from fastapi import FastAPI, HTTPException, Query, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# LLM evaluation
import google.generativeai as genai

# Local modules - use absolute imports for Docker compatibility
try:
    # When running as package (uvicorn server.server:app)
    from .config import get_config, ServerConfig
    from .algorithm_loader import AlgorithmLoader, LoadedAlgorithm
    from .dataset_loader import DatasetLoader, LoadedDataset
    from .embedding_cache import EmbeddingCache
    from .embedding_generator import EmbeddingGenerator, EmbeddingProgress, check_openai_available
    from .validator import Validator, CompatibilityResult
    from .qdrant_store import QdrantEmbeddingStore, check_qdrant_available, compute_strategy_hash
except ImportError:
    # When running standalone (uvicorn server:app)
    from config import get_config, ServerConfig
    from algorithm_loader import AlgorithmLoader, LoadedAlgorithm
    from dataset_loader import DatasetLoader, LoadedDataset
    from embedding_cache import EmbeddingCache
    from embedding_generator import EmbeddingGenerator, EmbeddingProgress, check_openai_available
    from validator import Validator, CompatibilityResult
    from qdrant_store import QdrantEmbeddingStore, check_qdrant_available, compute_strategy_hash


# ============================================================================
# Configuration
# ============================================================================

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 20


# ============================================================================
# Pydantic Models
# ============================================================================

class SeriesInfo(BaseModel):
    id: str
    name: str


class EpisodeScores(BaseModel):
    insight: Optional[int] = None
    credibility: Optional[int] = None
    information: Optional[int] = None
    entertainment: Optional[int] = None


class EpisodeCard(BaseModel):
    id: str
    content_id: str
    title: str
    series: SeriesInfo
    published_at: str
    scores: EpisodeScores
    badges: List[str] = []
    key_insight: Optional[str] = None
    categories: Dict = {}
    similarity_score: Optional[float] = None
    quality_score: Optional[float] = None
    recency_score: Optional[float] = None
    final_score: Optional[float] = None
    queue_position: Optional[int] = None


class Engagement(BaseModel):
    episode_id: str
    type: str = "click"
    timestamp: Optional[str] = None


class CreateSessionRequest(BaseModel):
    engagements: List[Engagement] = []
    excluded_ids: List[str] = []


class LoadMoreRequest(BaseModel):
    limit: int = DEFAULT_PAGE_SIZE


class EngageRequest(BaseModel):
    episode_id: str
    type: str = "click"


class SessionDebugInfo(BaseModel):
    candidates_count: int
    user_vector_episodes: int
    embeddings_available: bool
    top_similarity_scores: List[float] = []
    top_quality_scores: List[float] = []
    top_final_scores: List[float] = []
    scoring_weights: Dict[str, float] = {}


class SessionResponse(BaseModel):
    session_id: str
    episodes: List[EpisodeCard]
    total_in_queue: int
    shown_count: int
    remaining_count: int
    cold_start: bool
    algorithm: str
    debug: Optional[SessionDebugInfo] = None


class LoadConfigRequest(BaseModel):
    algorithm: str
    dataset: str


class GenerateEmbeddingsRequest(BaseModel):
    algorithm: str
    dataset: str
    force: bool = False


class RunTestRequest(BaseModel):
    test_id: str
    profile_id: Optional[str] = None


class RunAllTestsRequest(BaseModel):
    with_llm: bool = False


# ============================================================================
# Global State
# ============================================================================

class AppState:
    """Global application state."""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        
        # Loaders
        self.algorithm_loader = AlgorithmLoader(config.algorithms_dir)
        self.dataset_loader = DatasetLoader(config.datasets_dir)
        self.embedding_cache = EmbeddingCache(config.cache_dir / "embeddings")  # JSON fallback
        self.validator = Validator(self.algorithm_loader, self.dataset_loader)
        
        # Qdrant store (primary storage, with fallback to JSON cache)
        self.qdrant_store: Optional[QdrantEmbeddingStore] = None
        self.qdrant_available = False
        self._init_qdrant(config.qdrant_url)
        
        # Currently loaded
        self.current_algorithm: Optional[LoadedAlgorithm] = None
        self.current_dataset: Optional[LoadedDataset] = None
        self.current_embeddings: Dict[str, List[float]] = {}
        
        # Session storage
        self.sessions: Dict[str, Dict] = {}
    
    def _init_qdrant(self, qdrant_url: Optional[str]):
        """Initialize Qdrant connection with graceful fallback."""
        if qdrant_url:
            try:
                self.qdrant_store = QdrantEmbeddingStore(qdrant_url=qdrant_url)
                self.qdrant_available = self.qdrant_store.is_available
                if self.qdrant_available:
                    print(f"Qdrant connected at {qdrant_url}")
                else:
                    print(f"Qdrant not responding at {qdrant_url}, using JSON cache fallback")
            except Exception as e:
                print(f"Qdrant connection failed: {e}, using JSON cache fallback")
                self.qdrant_available = False
        else:
            print("No QDRANT_URL configured, using JSON cache only")
    
    @property
    def is_loaded(self) -> bool:
        return self.current_algorithm is not None and self.current_dataset is not None
    
    def has_embeddings_cached(
        self,
        algorithm_folder: str,
        strategy_version: str,
        dataset_folder: str
    ) -> bool:
        """Check if embeddings are cached (Qdrant or JSON)."""
        # Try Qdrant first
        if self.qdrant_available and self.qdrant_store:
            if self.qdrant_store.has_cache(algorithm_folder, strategy_version, dataset_folder):
                return True
        # Fall back to JSON cache
        return self.embedding_cache.has_cache(algorithm_folder, strategy_version, dataset_folder)
    
    def load_cached_embeddings(
        self,
        algorithm_folder: str,
        strategy_version: str,
        dataset_folder: str,
        strategy_file_path: Optional[Path] = None
    ) -> Optional[Dict[str, List[float]]]:
        """Load embeddings from cache (Qdrant or JSON) with hash verification."""
        # Try Qdrant first
        if self.qdrant_available and self.qdrant_store:
            # Verify strategy hash if we have the strategy file
            if strategy_file_path:
                current_hash = compute_strategy_hash(strategy_file_path)
                if current_hash:
                    matches, stored_hash = self.qdrant_store.verify_strategy_hash(
                        algorithm_folder, strategy_version, dataset_folder, current_hash
                    )
                    if not matches and stored_hash:
                        print(f"WARNING: embedding_strategy.py has changed!")
                        print(f"  Stored hash: {stored_hash}")
                        print(f"  Current hash: {current_hash}")
                        print(f"  Consider regenerating embeddings with force=true")
            
            embeddings = self.qdrant_store.load_embeddings(
                algorithm_folder, strategy_version, dataset_folder
            )
            if embeddings is not None:
                print(f"Loaded {len(embeddings)} embeddings from Qdrant")
                return embeddings
        
        # Fall back to JSON cache
        embeddings = self.embedding_cache.load_embeddings(
            algorithm_folder, strategy_version, dataset_folder
        )
        if embeddings:
            print(f"Loaded {len(embeddings)} embeddings from JSON cache")
            # Migrate to Qdrant if available
            if self.qdrant_available and self.qdrant_store:
                try:
                    self._migrate_to_qdrant(
                        algorithm_folder, strategy_version, dataset_folder, embeddings,
                        strategy_file_path
                    )
                except Exception as e:
                    print(f"Migration to Qdrant failed: {e}")
        return embeddings
    
    def save_embeddings(
        self,
        algorithm_folder: str,
        strategy_version: str,
        dataset_folder: str,
        embeddings: Dict[str, List[float]],
        embedding_model: str,
        embedding_dimensions: int,
        strategy_file_path: Optional[Path] = None
    ):
        """Save embeddings to cache (Qdrant primary, JSON backup)."""
        # Compute strategy hash if we have the file path
        strategy_hash = None
        if strategy_file_path:
            strategy_hash = compute_strategy_hash(strategy_file_path)
        
        # Save to Qdrant if available
        if self.qdrant_available and self.qdrant_store:
            try:
                self.qdrant_store.save_embeddings(
                    algorithm_folder, strategy_version, dataset_folder,
                    embeddings, embedding_model, embedding_dimensions,
                    strategy_hash=strategy_hash
                )
            except Exception as e:
                print(f"Qdrant save failed: {e}, saving to JSON cache only")
        
        # Always save to JSON cache as backup
        self.embedding_cache.save_embeddings(
            algorithm_folder, strategy_version, dataset_folder,
            embeddings, embedding_model, embedding_dimensions
        )
    
    def _migrate_to_qdrant(
        self,
        algorithm_folder: str,
        strategy_version: str,
        dataset_folder: str,
        embeddings: Dict[str, List[float]],
        strategy_file_path: Optional[Path] = None
    ):
        """Migrate JSON cache embeddings to Qdrant."""
        if not embeddings:
            return
        
        # Infer dimensions from first embedding
        first_embedding = next(iter(embeddings.values()))
        dimensions = len(first_embedding)
        
        # Compute strategy hash if we have the file path
        strategy_hash = None
        if strategy_file_path:
            strategy_hash = compute_strategy_hash(strategy_file_path)
        
        self.qdrant_store.save_embeddings(
            algorithm_folder, strategy_version, dataset_folder,
            embeddings, "migrated", dimensions,
            strategy_hash=strategy_hash
        )
        print(f"Migrated {len(embeddings)} embeddings to Qdrant")


# Initialize state
_state: Optional[AppState] = None


def get_state() -> AppState:
    global _state
    if _state is None:
        config = get_config()
        _state = AppState(config)
    return _state


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="Serafis Evaluation Framework API",
    description="Versioned recommendation algorithm evaluation with dynamic loading",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Root & Status
# ============================================================================

@app.get("/")
def root():
    state = get_state()
    config = state.config
    
    return {
        "name": "Serafis Evaluation Framework API",
        "version": "2.0.0",
        "status": "loaded" if state.is_loaded else "not_configured",
        "current": {
            "algorithm": state.current_algorithm.folder_name if state.current_algorithm else None,
            "dataset": state.current_dataset.folder_name if state.current_dataset else None,
            "embeddings_count": len(state.current_embeddings),
        },
        "available": {
            "algorithms": len(state.algorithm_loader.list_algorithms()),
            "datasets": len(state.dataset_loader.list_datasets()),
        },
        "endpoints": {
            "config": ["/api/config/algorithms", "/api/config/datasets", "/api/config/load"],
            "embeddings": ["/api/embeddings/status", "/api/embeddings/generate"],
            "recommendations": ["/api/sessions/create", "/api/sessions/{id}/next"],
            "evaluation": ["/api/evaluation/profiles", "/api/evaluation/test-cases", "/api/evaluation/run"],
        }
    }


@app.get("/api/health")
def health():
    state = get_state()
    openai_ok, openai_msg = check_openai_available()
    qdrant_ok, qdrant_msg = check_qdrant_available(state.config.qdrant_url)
    
    return {
        "status": "healthy",
        "loaded": state.is_loaded,
        "openai": {"available": openai_ok, "message": openai_msg},
        "qdrant": {"available": qdrant_ok, "message": qdrant_msg},
    }


# ============================================================================
# Configuration Endpoints
# ============================================================================

@app.get("/api/config/algorithms")
def list_algorithms():
    """List all available algorithm versions."""
    state = get_state()
    algorithms = state.algorithm_loader.list_algorithms()
    
    return {
        "algorithms": algorithms,
        "current": state.current_algorithm.folder_name if state.current_algorithm else None
    }


@app.get("/api/config/datasets")
def list_datasets():
    """List all available datasets."""
    state = get_state()
    datasets = state.dataset_loader.list_datasets()
    
    return {
        "datasets": datasets,
        "current": state.current_dataset.folder_name if state.current_dataset else None
    }


@app.get("/api/config/validate")
def validate_compatibility(
    algorithm_folder: str = Query(..., description="Algorithm folder name"),
    dataset_folder: str = Query(..., description="Dataset folder name")
):
    """Check if algorithm is compatible with dataset."""
    state = get_state()
    result = state.validator.check_compatibility(algorithm_folder, dataset_folder)
    
    return {
        "compatible": result.is_compatible,
        "is_compatible": result.is_compatible,
        "algorithm_version": result.algorithm_version,
        "dataset_version": result.dataset_version,
        "schema_match": result.schema_match,
        "required_fields_present": result.required_fields_present,
        "missing_fields": result.missing_fields,
        "warnings": result.warnings,
        "errors": result.errors,
        "reason": result.errors[0] if result.errors else ("Compatible" if result.is_compatible else "Unknown issue"),
    }


@app.post("/api/config/load")
def load_configuration(request: LoadConfigRequest):
    """Load an algorithm and dataset combination."""
    state = get_state()
    
    # Validate compatibility first
    compat = state.validator.check_compatibility(request.algorithm, request.dataset)
    if not compat.is_compatible:
        raise HTTPException(
            status_code=400,
            detail=f"Incompatible: {compat.errors}"
        )
    
    # Load algorithm
    try:
        algorithm = state.algorithm_loader.load_algorithm(request.algorithm)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Load dataset
    try:
        dataset = state.dataset_loader.load_dataset(request.dataset)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Check for cached embeddings (Qdrant or JSON)
    embeddings = {}
    embeddings_cached = state.has_embeddings_cached(
        algorithm.folder_name,
        algorithm.strategy_version,
        dataset.folder_name
    )
    
    if embeddings_cached:
        # Pass strategy file path for hash verification
        strategy_file = algorithm.path / "embedding_strategy.py" if algorithm.path else None
        embeddings = state.load_cached_embeddings(
            algorithm.folder_name,
            algorithm.strategy_version,
            dataset.folder_name,
            strategy_file_path=strategy_file
        ) or {}
    
    # Update state
    state.current_algorithm = algorithm
    state.current_dataset = dataset
    state.current_embeddings = embeddings
    state.sessions.clear()  # Clear old sessions
    
    return {
        "status": "loaded",
        "algorithm": {
            "folder_name": algorithm.folder_name,
            "version": algorithm.manifest.version,
            "name": algorithm.manifest.name,
        },
        "dataset": {
            "folder_name": dataset.folder_name,
            "version": dataset.manifest.version,
            "name": dataset.manifest.name,
            "episode_count": len(dataset.episodes),
        },
        "embeddings": {
            "cached": embeddings_cached,
            "count": len(embeddings),
            "needs_generation": not embeddings_cached,
        }
    }


@app.get("/api/config/status")
def get_config_status():
    """Get current configuration status (simple format for frontend)."""
    state = get_state()
    
    if not state.is_loaded:
        return {
            "loaded": False,
            "algorithm_folder": None,
            "dataset_folder": None,
        }
    
    return {
        "loaded": True,
        "algorithm_folder": state.current_algorithm.folder_name,
        "dataset_folder": state.current_dataset.folder_name,
        "algorithm_name": state.current_algorithm.manifest.name,
        "dataset_name": state.current_dataset.manifest.name,
        "embeddings_count": len(state.current_embeddings),
    }


@app.get("/api/config/current")
def get_current_config():
    """Get currently loaded configuration (detailed format)."""
    state = get_state()
    
    if not state.is_loaded:
        return {
            "loaded": False,
            "algorithm": None,
            "dataset": None,
            "embeddings": None,
        }
    
    return {
        "loaded": True,
        "algorithm": {
            "folder_name": state.current_algorithm.folder_name,
            "version": state.current_algorithm.manifest.version,
            "name": state.current_algorithm.manifest.name,
            "embedding_strategy_version": state.current_algorithm.strategy_version,
        },
        "dataset": {
            "folder_name": state.current_dataset.folder_name,
            "version": state.current_dataset.manifest.version,
            "name": state.current_dataset.manifest.name,
            "episode_count": len(state.current_dataset.episodes),
        },
        "embeddings": {
            "count": len(state.current_embeddings),
            "coverage": len(state.current_embeddings) / len(state.current_dataset.episodes) if state.current_dataset.episodes else 0,
        }
    }


# ============================================================================
# Embedding Endpoints
# ============================================================================

@app.get("/api/embeddings/status")
def embeddings_status():
    """Get status of embeddings for current configuration."""
    state = get_state()
    
    if not state.is_loaded:
        return {
            "loaded": False,
            "cached": False,
            "count": 0,
            "needs_generation": True,
            "message": "No algorithm/dataset loaded"
        }
    
    cached = state.has_embeddings_cached(
        state.current_algorithm.folder_name,
        state.current_algorithm.strategy_version,
        state.current_dataset.folder_name
    )
    
    metadata = None
    if cached:
        # Try Qdrant metadata first, then JSON
        if state.qdrant_available and state.qdrant_store:
            metadata = state.qdrant_store.load_metadata(
                state.current_algorithm.folder_name,
                state.current_algorithm.strategy_version,
                state.current_dataset.folder_name
            )
        if not metadata:
            metadata = state.embedding_cache.load_metadata(
                state.current_algorithm.folder_name,
                state.current_algorithm.strategy_version,
                state.current_dataset.folder_name
            )
    
    return {
        "loaded": True,
        "cached": cached,
        "count": len(state.current_embeddings),
        "needs_generation": len(state.current_embeddings) < len(state.current_dataset.episodes),
        "storage": "qdrant" if state.qdrant_available else "json",
        "metadata": {
            "created_at": metadata.created_at if metadata else None,
            "episode_count": metadata.episode_count if metadata else 0,
            "embedding_model": metadata.embedding_model if metadata else None,
        } if metadata else None,
        "openai_available": check_openai_available()[0],
        "qdrant_available": state.qdrant_available,
    }


@app.post("/api/embeddings/generate")
def generate_embeddings(
    request: GenerateEmbeddingsRequest,
    x_openai_key: Optional[str] = Header(None, alias="X-OpenAI-Key")
):
    """
    Generate embeddings for an algorithm+dataset combination.
    
    Pass OpenAI API key via X-OpenAI-Key header or use OPENAI_API_KEY env var.
    """
    state = get_state()
    config = state.config
    
    # Use header key or env var
    api_key = x_openai_key or config.openai_api_key
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key required. Set OPENAI_API_KEY env var or pass X-OpenAI-Key header."
        )
    
    # Load algorithm and dataset if not already loaded
    try:
        algorithm = state.algorithm_loader.load_algorithm(request.algorithm)
        dataset = state.dataset_loader.load_dataset(request.dataset)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Check if already cached (unless force)
    if not request.force:
        if state.has_embeddings_cached(
            algorithm.folder_name,
            algorithm.strategy_version,
            dataset.folder_name
        ):
            existing = state.load_cached_embeddings(
                algorithm.folder_name,
                algorithm.strategy_version,
                dataset.folder_name
            )
            
            return {
                "status": "already_cached",
                "count": len(existing or {}),
                "message": "Embeddings already cached. Use force=true to regenerate.",
                "storage": "qdrant" if state.qdrant_available else "json"
            }
    
    # Generate embeddings
    generator = EmbeddingGenerator(
        api_key=api_key,
        model=algorithm.embedding_model,
        dimensions=algorithm.embedding_dimensions
    )
    
    # Track progress
    progress_updates = []
    
    def on_progress(p: EmbeddingProgress):
        progress_updates.append({
            "current": p.current,
            "total": p.total,
            "batch": p.batch_num,
            "total_batches": p.total_batches,
            "error": p.error or None
        })
    
    result = generator.generate_for_episodes(
        episodes=dataset.episodes,
        get_embed_text=algorithm.get_embed_text,
        on_progress=on_progress
    )
    
    if result.success:
        # Save to cache (Qdrant + JSON backup) with strategy hash
        strategy_file = algorithm.path / "embedding_strategy.py" if algorithm.path else None
        state.save_embeddings(
            algorithm.folder_name,
            algorithm.strategy_version,
            dataset.folder_name,
            result.embeddings,
            algorithm.embedding_model,
            algorithm.embedding_dimensions,
            strategy_file_path=strategy_file
        )
        
        # Update current state if this is the loaded config
        if (state.current_algorithm and 
            state.current_algorithm.folder_name == algorithm.folder_name and
            state.current_dataset and
            state.current_dataset.folder_name == dataset.folder_name):
            state.current_embeddings = result.embeddings
    
    return {
        "status": "success" if result.success else "partial",
        "generated": result.total_generated,
        "skipped": result.total_skipped,
        "total": len(result.embeddings),
        "estimated_cost": round(result.estimated_cost, 4),
        "errors": result.errors,
        "storage": "qdrant" if state.qdrant_available else "json"
    }


# ============================================================================
# Session Endpoints (Recommendation Engine)
# ============================================================================

def get_badges(ep: Dict) -> List[str]:
    """Determine badges for an episode based on its scores."""
    badges = []
    scores = ep.get("scores", {})
    
    if (scores.get("insight") or 0) >= 3:
        badges.append("high_insight")
    if (scores.get("credibility") or 0) >= 3:
        badges.append("high_credibility")
    if (scores.get("information") or 0) >= 3:
        badges.append("data_rich")
    if (scores.get("entertainment") or 0) >= 3:
        badges.append("engaging")
    
    return badges[:2]


def to_episode_card(ep: Dict, scored=None, queue_position: int = None) -> EpisodeCard:
    """Convert raw episode dict to EpisodeCard."""
    return EpisodeCard(
        id=ep["id"],
        content_id=ep.get("content_id", ep["id"]),
        title=ep["title"],
        series=SeriesInfo(**ep["series"]),
        published_at=ep["published_at"],
        scores=EpisodeScores(**ep["scores"]),
        badges=get_badges(ep),
        key_insight=ep.get("key_insight"),
        categories=ep.get("categories", {"major": [], "subcategories": []}),
        similarity_score=round(scored.similarity_score, 4) if scored else None,
        quality_score=round(scored.quality_score, 4) if scored else None,
        recency_score=round(scored.recency_score, 4) if scored else None,
        final_score=round(scored.final_score, 4) if scored else None,
        queue_position=queue_position
    )


@app.post("/api/sessions/create", response_model=SessionResponse)
def create_session(request: CreateSessionRequest):
    """Create a new recommendation session."""
    state = get_state()
    
    if not state.is_loaded:
        raise HTTPException(
            status_code=400,
            detail="No algorithm/dataset loaded. Call /api/config/load first."
        )
    
    # Import recommendation engine from loaded algorithm
    engine = state.current_algorithm.engine_module
    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Algorithm does not have a recommendation engine"
        )
    
    # Prepare data
    engagements = [e.model_dump() for e in request.engagements]
    excluded_ids = set(request.excluded_ids)
    
    # Create recommendation queue
    queue, cold_start, user_vector_episodes = engine.create_recommendation_queue(
        engagements=engagements,
        excluded_ids=excluded_ids,
        episodes=state.current_dataset.episodes,
        embeddings=state.current_embeddings,
        episode_by_content_id=state.current_dataset.episode_by_content_id,
    )
    
    # Create session
    session_id = str(uuid.uuid4())[:8]
    session = {
        "session_id": session_id,
        "queue": queue,
        "shown_indices": set(),
        "engaged_ids": set(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cold_start": cold_start,
        "user_vector_episodes": user_vector_episodes,
        "excluded_ids": excluded_ids.copy(),
    }
    state.sessions[session_id] = session
    
    # Get first page
    first_page = []
    for i, scored_ep in enumerate(queue[:DEFAULT_PAGE_SIZE]):
        first_page.append((scored_ep, i + 1))
        session["shown_indices"].add(i)
    
    episodes = [
        to_episode_card(scored.episode, scored, pos)
        for scored, pos in first_page
    ]
    
    total_in_queue = len(queue)
    shown_count = len(session["shown_indices"])
    
    # Debug info
    debug = SessionDebugInfo(
        candidates_count=total_in_queue,
        user_vector_episodes=user_vector_episodes,
        embeddings_available=len(state.current_embeddings) > 0,
        top_similarity_scores=[round(s.similarity_score, 3) for s, _ in first_page[:5]],
        top_quality_scores=[round(s.quality_score, 3) for s, _ in first_page[:5]],
        top_final_scores=[round(s.final_score, 3) for s, _ in first_page[:5]],
        scoring_weights={
            "similarity": 0.55,
            "quality": 0.30,
            "recency": 0.15,
        }
    )
    
    return SessionResponse(
        session_id=session_id,
        episodes=episodes,
        total_in_queue=total_in_queue,
        shown_count=shown_count,
        remaining_count=total_in_queue - shown_count,
        cold_start=cold_start,
        algorithm=f"v{state.current_algorithm.manifest.version}",
        debug=debug
    )


@app.get("/api/sessions/{session_id}")
def get_session_info(session_id: str):
    """Get session info."""
    state = get_state()
    session = state.sessions.get(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    total = len(session["queue"])
    shown = len(session["shown_indices"])
    
    return {
        "session_id": session_id,
        "total_in_queue": total,
        "shown_count": shown,
        "remaining_count": total - shown,
        "cold_start": session["cold_start"],
        "created_at": session["created_at"],
        "engaged_count": len(session["engaged_ids"]),
    }


@app.post("/api/sessions/{session_id}/next", response_model=SessionResponse)
def load_more(session_id: str, request: LoadMoreRequest = None):
    """Load more recommendations from session."""
    state = get_state()
    session = state.sessions.get(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    limit = min(request.limit if request else DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)
    
    queue = session["queue"]
    shown = session["shown_indices"]
    engaged = session["engaged_ids"]
    
    next_page = []
    for i, scored_ep in enumerate(queue):
        if i in shown:
            continue
        
        ep = scored_ep.episode
        if ep["id"] in engaged or ep.get("content_id") in engaged:
            continue
        
        next_page.append((scored_ep, i + 1))
        shown.add(i)
        
        if len(next_page) >= limit:
            break
    
    episodes = [
        to_episode_card(scored.episode, scored, pos)
        for scored, pos in next_page
    ]
    
    total_in_queue = len(queue)
    shown_count = len(shown)
    
    return SessionResponse(
        session_id=session_id,
        episodes=episodes,
        total_in_queue=total_in_queue,
        shown_count=shown_count,
        remaining_count=total_in_queue - shown_count,
        cold_start=session["cold_start"],
        algorithm=f"v{state.current_algorithm.manifest.version}" if state.current_algorithm else "unknown",
    )


@app.post("/api/sessions/{session_id}/engage")
def engage_episode(session_id: str, request: EngageRequest):
    """Record an engagement."""
    state = get_state()
    session = state.sessions.get(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session["engaged_ids"].add(request.episode_id)
    session["excluded_ids"].add(request.episode_id)
    
    return {
        "status": "ok",
        "session_id": session_id,
        "episode_id": request.episode_id,
        "type": request.type,
        "engaged_count": len(session["engaged_ids"]),
    }


# ============================================================================
# Episode Endpoints
# ============================================================================

@app.get("/api/episodes")
def list_episodes(limit: int = Query(None), offset: int = Query(0)):
    """List episodes from current dataset."""
    state = get_state()
    
    if not state.current_dataset:
        raise HTTPException(status_code=400, detail="No dataset loaded")
    
    episodes = state.current_dataset.episodes
    paginated = episodes[offset:offset + limit] if limit else episodes[offset:]
    
    return {
        "episodes": paginated,
        "total": len(episodes),
        "offset": offset,
        "limit": limit
    }


@app.get("/api/episodes/{episode_id}")
def get_episode(episode_id: str):
    """Get episode details."""
    state = get_state()
    
    if not state.current_dataset:
        raise HTTPException(status_code=400, detail="No dataset loaded")
    
    ep = state.current_dataset.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    
    return ep


# ============================================================================
# Evaluation Endpoints
# ============================================================================

@app.get("/api/evaluation/profiles")
def list_profiles():
    """List available evaluation profiles."""
    state = get_state()
    profiles_dir = state.config.evaluation_dir / "profiles"
    
    if not profiles_dir.exists():
        return {"profiles": []}
    
    profiles = []
    for path in profiles_dir.glob("*.json"):
        try:
            with open(path) as f:
                profile = json.load(f)
            profiles.append({
                "id": profile.get("profile_id", path.stem),
                "name": profile.get("name", path.stem),
                "description": profile.get("description", ""),
                "engagements_count": len(profile.get("engagements", [])),
            })
        except (json.JSONDecodeError, IOError):
            continue
    
    return {"profiles": profiles}


@app.get("/api/evaluation/test-cases")
def list_test_cases():
    """List available test cases."""
    state = get_state()
    tests_dir = state.config.evaluation_dir / "test_cases"
    
    if not tests_dir.exists():
        return {"test_cases": []}
    
    test_cases = []
    for path in tests_dir.glob("*.json"):
        try:
            with open(path) as f:
                test = json.load(f)
            test_cases.append({
                "id": test.get("test_id", path.stem),
                "name": test.get("name", path.stem),
                "type": test.get("type", ""),
                "evaluation_method": test.get("evaluation_method", "deterministic"),
                "description": test.get("description", ""),
            })
        except (json.JSONDecodeError, IOError):
            continue
    
    return {"test_cases": sorted(test_cases, key=lambda x: x["id"])}


@app.get("/api/evaluation/reports")
def list_reports():
    """List saved test reports."""
    state = get_state()
    reports_dir = state.config.evaluation_dir / "reports"
    
    if not reports_dir.exists():
        return {"reports": []}
    
    reports = []
    for path in reports_dir.glob("*.json"):
        try:
            with open(path) as f:
                report = json.load(f)
            reports.append({
                "id": path.stem,
                "timestamp": report.get("timestamp", ""),
                "total_tests": report.get("total_tests", 0),
                "passed": report.get("passed", 0),
                "failed": report.get("failed", 0),
                "context": report.get("context", {}),
            })
        except (json.JSONDecodeError, IOError):
            continue
    
    return {"reports": sorted(reports, key=lambda x: x["timestamp"], reverse=True)}


@app.get("/api/evaluation/reports/{report_id}")
def get_report(report_id: str):
    """Get a specific test report."""
    state = get_state()
    report_path = state.config.evaluation_dir / "reports" / f"{report_id}.json"
    
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    
    with open(report_path) as f:
        return json.load(f)


# ============================================================================
# Test Execution Endpoints
# ============================================================================

@app.get("/api/evaluation/profiles/{profile_id}")
def get_profile(profile_id: str):
    """Get a specific profile."""
    state = get_state()
    profile_path = state.config.evaluation_dir / "profiles" / f"{profile_id}.json"
    
    if not profile_path.exists():
        raise HTTPException(status_code=404, detail="Profile not found")
    
    with open(profile_path) as f:
        return json.load(f)


@app.get("/api/evaluation/test-cases/{test_id}")
def get_test_case(test_id: str):
    """Get a specific test case."""
    state = get_state()
    test_path = state.config.evaluation_dir / "test_cases" / f"{test_id}.json"
    
    if not test_path.exists():
        raise HTTPException(status_code=404, detail="Test case not found")
    
    with open(test_path) as f:
        return json.load(f)


class RunTestRequest(BaseModel):
    test_id: str
    with_llm: bool = False


class RunAllTestsRequest(BaseModel):
    with_llm: bool = False
    save_report: bool = True


@app.post("/api/evaluation/run")
def run_single_test(
    request: RunTestRequest,
    x_gemini_key: Optional[str] = Header(None, alias="X-Gemini-Key")
):
    """
    Run a single test case.
    
    Pass Gemini API key via X-Gemini-Key header for LLM evaluation.
    """
    state = get_state()
    
    if not state.is_loaded:
        raise HTTPException(
            status_code=400,
            detail="No algorithm/dataset loaded. Call /api/config/load first."
        )
    
    # Load test case
    test_path = state.config.evaluation_dir / "test_cases" / f"{request.test_id}.json"
    if not test_path.exists():
        raise HTTPException(status_code=404, detail=f"Test case not found: {request.test_id}")
    
    with open(test_path) as f:
        test_case = json.load(f)
    
    # Load required profiles
    profiles = {}
    profiles_dir = state.config.evaluation_dir / "profiles"
    for path in profiles_dir.glob("*.json"):
        try:
            with open(path) as f:
                profile = json.load(f)
                profiles[profile["profile_id"]] = profile
        except (json.JSONDecodeError, IOError, KeyError):
            continue
    
    # Run the test
    result = _execute_test(
        test_id=request.test_id,
        test_case=test_case,
        profiles=profiles,
        state=state,
        with_llm=request.with_llm,
        gemini_key=x_gemini_key or state.config.gemini_api_key
    )
    
    return result


@app.post("/api/evaluation/run-all")
def run_all_tests(
    request: RunAllTestsRequest,
    x_gemini_key: Optional[str] = Header(None, alias="X-Gemini-Key")
):
    """
    Run all test cases sequentially.
    
    Results are saved to a report file if save_report is true.
    """
    state = get_state()
    
    if not state.is_loaded:
        raise HTTPException(
            status_code=400,
            detail="No algorithm/dataset loaded. Call /api/config/load first."
        )
    
    # Load all profiles
    profiles = {}
    profiles_dir = state.config.evaluation_dir / "profiles"
    for path in profiles_dir.glob("*.json"):
        try:
            with open(path) as f:
                profile = json.load(f)
                profiles[profile["profile_id"]] = profile
        except (json.JSONDecodeError, IOError, KeyError):
            continue
    
    # Load all test cases
    test_cases = {}
    tests_dir = state.config.evaluation_dir / "test_cases"
    for path in tests_dir.glob("*.json"):
        try:
            with open(path) as f:
                test = json.load(f)
                test_cases[test["test_id"]] = test
        except (json.JSONDecodeError, IOError, KeyError):
            continue
    
    # Run tests sequentially
    results = []
    for test_id in sorted(test_cases.keys()):
        result = _execute_test(
            test_id=test_id,
            test_case=test_cases[test_id],
            profiles=profiles,
            state=state,
            with_llm=request.with_llm,
            gemini_key=x_gemini_key or state.config.gemini_api_key
        )
        results.append(result)
    
    # Build report with aggregate scoring
    passed = sum(1 for r in results if r.get("passed", False))
    failed = len(results) - passed
    
    # Compute overall algorithm score (weighted by test type)
    # MFT tests (quality gates, exclusions) are weighted higher
    mft_tests = ["03_quality_gates_credibility", "04_excluded_episodes"]
    
    total_weight = 0.0
    weighted_score = 0.0
    total_confidence = 0.0
    
    for r in results:
        test_scores = r.get("scores", {})
        if test_scores and test_scores.get("aggregate_score") is not None:
            # MFT tests get 2x weight
            weight = 2.0 if r.get("test_id") in mft_tests else 1.0
            weighted_score += test_scores.get("aggregate_score", 0) * weight
            total_confidence += test_scores.get("aggregate_confidence", 1.0) * weight
            total_weight += weight
    
    overall_score = round(weighted_score / total_weight, 2) if total_weight > 0 else 0.0
    overall_confidence = round(total_confidence / total_weight, 2) if total_weight > 0 else 0.0
    
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context": {
            "algorithm_version": state.current_algorithm.folder_name if state.current_algorithm else None,
            "algorithm_name": state.current_algorithm.manifest.name if state.current_algorithm else None,
            "dataset_version": state.current_dataset.folder_name if state.current_dataset else None,
            "dataset_episode_count": len(state.current_dataset.episodes) if state.current_dataset else 0,
        },
        "summary": {
            "total_tests": len(results),
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / len(results), 3) if results else 0,
            "overall_score": overall_score,
            "overall_confidence": overall_confidence,
            "score_breakdown": {
                r.get("test_id"): r.get("scores", {}).get("aggregate_score", 0)
                for r in results
            }
        },
        "results": results
    }
    
    # Save report if requested
    if request.save_report:
        reports_dir = state.config.evaluation_dir / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        algo = state.current_algorithm.folder_name if state.current_algorithm else "unknown"
        dataset = state.current_dataset.folder_name if state.current_dataset else "unknown"
        report_filename = f"{timestamp}_{algo}__{dataset}.json"
        report_path = reports_dir / report_filename
        
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        report["report_id"] = report_filename.replace(".json", "")
        report["report_path"] = str(report_path)
    
    return report


def _llm_evaluate(
    test_case: Dict,
    result: Dict,
    gemini_key: str
) -> Dict:
    """
    Use Gemini to provide qualitative evaluation of test results.
    
    Returns a dict with:
    - summary: Brief overall assessment
    - quality_score: 1-5 rating
    - observations: List of specific insights
    - suggestions: Improvement recommendations
    """
    try:
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Build prompt with test context
        prompt = f"""You are evaluating the results of a recommendation system test.

TEST CASE: {test_case.get('name', 'Unknown')}
DESCRIPTION: {test_case.get('description', 'No description')}
TEST TYPE: {test_case.get('type', 'Unknown')}

DETERMINISTIC RESULTS:
- Overall Passed: {result.get('passed', False)}
- Criteria Results:
{json.dumps(result.get('criteria_results', []), indent=2)}

Based on these test results, provide a qualitative evaluation:

1. SUMMARY: A 1-2 sentence overall assessment
2. QUALITY_SCORE: Rate 1-5 (1=poor, 5=excellent)
3. OBSERVATIONS: 2-3 specific insights about the recommendation quality
4. SUGGESTIONS: 1-2 actionable improvements if any

Respond in JSON format:
{{
    "summary": "...",
    "quality_score": N,
    "observations": ["...", "..."],
    "suggestions": ["..."]
}}"""

        response = model.generate_content(prompt)
        
        # Parse JSON from response
        response_text = response.text.strip()
        # Handle markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])
        
        llm_result = json.loads(response_text)
        llm_result["evaluated_at"] = datetime.now(timezone.utc).isoformat()
        
        return llm_result
        
    except Exception as e:
        return {
            "summary": f"LLM evaluation failed: {str(e)}",
            "quality_score": None,
            "observations": [],
            "suggestions": [],
            "error": str(e)
        }


def _add_criterion(
    result: Dict,
    criterion_id: str,
    description: str,
    score: float,
    threshold: float = 7.0,
    confidence: float = 1.0,
    details: str = "",
    weight: float = 1.0
) -> None:
    """
    Add a criterion result with scalar scoring.
    
    Args:
        result: The test result dict to add to
        criterion_id: Unique identifier for this criterion
        description: Human-readable description
        score: Score on 1-10 scale
        threshold: Minimum score to pass (default 7.0)
        confidence: 0.0-1.0 confidence in the score (1.0 for deterministic)
        details: Additional details string
        weight: Weight for aggregate scoring (default 1.0)
    """
    passed = score >= threshold
    result["criteria_results"].append({
        "criterion_id": criterion_id,
        "description": description,
        "score": round(score, 2),
        "threshold": threshold,
        "confidence": confidence,
        "passed": passed,
        "details": details,
        "weight": weight
    })
    if not passed:
        result["passed"] = False


def _compute_aggregate_score(result: Dict) -> Dict:
    """
    Compute aggregate scores for a test result.
    
    Returns dict with:
        - aggregate_score: Weighted mean of all criteria (1-10)
        - aggregate_confidence: Weighted mean confidence
        - criteria_count: Number of criteria
        - passed_count: Number of passing criteria
    """
    criteria = result.get("criteria_results", [])
    if not criteria:
        return {
            "aggregate_score": 0.0,
            "aggregate_confidence": 0.0,
            "criteria_count": 0,
            "passed_count": 0
        }
    
    total_weight = sum(c.get("weight", 1.0) for c in criteria)
    weighted_score = sum(c.get("score", 0) * c.get("weight", 1.0) for c in criteria)
    weighted_confidence = sum(c.get("confidence", 1.0) * c.get("weight", 1.0) for c in criteria)
    passed_count = sum(1 for c in criteria if c.get("passed", False))
    
    return {
        "aggregate_score": round(weighted_score / total_weight, 2) if total_weight > 0 else 0.0,
        "aggregate_confidence": round(weighted_confidence / total_weight, 2) if total_weight > 0 else 0.0,
        "criteria_count": len(criteria),
        "passed_count": passed_count
    }


def _execute_test(
    test_id: str,
    test_case: Dict,
    profiles: Dict[str, Dict],
    state: AppState,
    with_llm: bool = False,
    gemini_key: Optional[str] = None
) -> Dict:
    """
    Execute a single test and return the result.
    
    This implements the core test validation logic.
    Returns results with scalar scoring (1-10 scale).
    """
    result = {
        "test_id": test_id,
        "name": test_case.get("name", test_id),
        "type": test_case.get("type", ""),
        "evaluation_method": test_case.get("evaluation_method", "deterministic"),
        "passed": True,
        "criteria_results": [],
        "error": None,
        "llm_evaluation": None,
        "scores": None  # Will be populated with aggregate scores
    }
    
    try:
        # Get engine module
        engine = state.current_algorithm.engine_module
        if not engine:
            result["error"] = "Algorithm engine not loaded"
            result["passed"] = False
            return result
        
        # Execute based on test type
        if test_id == "01_cold_start_quality":
            result = _test_cold_start_quality(test_case, profiles, engine, state, result)
        
        elif test_id == "02_personalization_differs":
            result = _test_personalization_differs(test_case, profiles, engine, state, result)
        
        elif test_id == "03_quality_gates_credibility":
            result = _test_quality_gates(test_case, profiles, engine, state, result)
        
        elif test_id == "04_excluded_episodes":
            result = _test_excluded_episodes(test_case, profiles, engine, state, result)
        
        elif test_id == "05_category_personalization":
            result = _test_category_personalization(test_case, profiles, engine, state, result)
        
        elif test_id == "06_bookmark_weighting":
            result = _test_bookmark_weighting(test_case, profiles, engine, state, result)
        
        elif test_id == "07_recency_scoring":
            result = _test_recency_scoring(test_case, profiles, engine, state, result)
        
        else:
            result["error"] = f"Unknown test: {test_id}"
            result["passed"] = False
        
    except Exception as e:
        result["error"] = str(e)
        result["passed"] = False
    
    # Compute aggregate scores
    result["scores"] = _compute_aggregate_score(result)
    
    # Run LLM evaluation if requested and applicable
    eval_method = test_case.get("evaluation_method", "deterministic")
    if with_llm and gemini_key and "llm" in eval_method:
        result["llm_evaluation"] = _llm_evaluate(test_case, result, gemini_key)
    
    return result


def _call_recommendation_api(engagements: List[Dict], excluded_ids: set, state: AppState) -> Dict:
    """Helper to call the recommendation engine directly."""
    engine = state.current_algorithm.engine_module
    
    queue, cold_start, user_vector_episodes = engine.create_recommendation_queue(
        engagements=engagements,
        excluded_ids=excluded_ids,
        episodes=state.current_dataset.episodes,
        embeddings=state.current_embeddings,
        episode_by_content_id=state.current_dataset.episode_by_content_id,
    )
    
    # Convert to response format
    episodes = []
    for i, scored_ep in enumerate(queue[:10]):
        ep = scored_ep.episode.copy()
        ep["similarity_score"] = scored_ep.similarity_score
        ep["quality_score"] = scored_ep.quality_score
        ep["recency_score"] = scored_ep.recency_score
        ep["final_score"] = scored_ep.final_score
        ep["queue_position"] = i + 1
        episodes.append(ep)
    
    return {
        "episodes": episodes,
        "cold_start": cold_start,
        "user_vector_episodes": user_vector_episodes,
        "total_in_queue": len(queue)
    }


def _test_cold_start_quality(test_case, profiles, engine, state, result):
    """Test 01: Cold Start Returns Quality Content
    
    Scoring approach:
    - cold_start_flag: Binary (10 if true, 1 if false)
    - avg_credibility: Map credibility 2.0-4.0 to score 5-10
    - min_credibility: Binary gate (10 if >=2, 1 otherwise)
    - top_quality_score: Map avg quality 0.5-1.0 to score 5-10
    """
    response = _call_recommendation_api([], set(), state)
    episodes = response.get("episodes", [])
    
    # Criterion 1: cold_start flag (binary)
    cold_start = response.get("cold_start", False)
    _add_criterion(
        result,
        criterion_id="cold_start_flag",
        description="API response includes cold_start: true",
        score=10.0 if cold_start else 1.0,
        threshold=7.0,
        confidence=1.0,
        details=f"cold_start={cold_start}",
        weight=1.0
    )
    
    # Criterion 2: Average credibility >= 3.0
    # Score mapping: 2.0 → 5, 3.0 → 7.5, 4.0 → 10
    if episodes:
        credibilities = [ep["scores"]["credibility"] for ep in episodes[:10]]
        avg_cred = sum(credibilities) / len(credibilities)
        # Map [2.0, 4.0] to [5, 10]
        score = 5.0 + (avg_cred - 2.0) * 2.5
        score = max(1.0, min(10.0, score))
        
        _add_criterion(
            result,
            criterion_id="avg_credibility",
            description="Average credibility of top 10 >= 3.0",
            score=score,
            threshold=7.5,  # Corresponds to avg_cred >= 3.0
            confidence=1.0,
            details=f"avg_credibility={avg_cred:.2f}",
            weight=1.5  # Higher weight - core quality metric
        )
    
    # Criterion 3: No episode with credibility < 2 (gate check)
    if episodes:
        min_cred = min(ep["scores"]["credibility"] for ep in episodes[:10])
        # Binary: either passes the gate or doesn't
        score = 10.0 if min_cred >= 2 else 1.0
        
        _add_criterion(
            result,
            criterion_id="min_credibility",
            description="No episode in top 10 has credibility < 2",
            score=score,
            threshold=7.0,
            confidence=1.0,
            details=f"min_credibility={min_cred}",
            weight=1.0
        )
    
    # Criterion 4: Top 3 quality scores >= 0.7
    # Map avg quality [0.5, 1.0] to score [5, 10]
    if episodes:
        top_3_quality = [ep.get("quality_score", 0) for ep in episodes[:3]]
        avg_quality = sum(top_3_quality) / len(top_3_quality) if top_3_quality else 0
        # Map [0.5, 1.0] to [5, 10]
        score = 5.0 + (avg_quality - 0.5) * 10.0
        score = max(1.0, min(10.0, score))
        
        _add_criterion(
            result,
            criterion_id="top_quality_score",
            description="Top 3 episodes have quality_score >= 0.7",
            score=score,
            threshold=7.0,  # Corresponds to avg_quality >= 0.7
            confidence=1.0,
            details=f"top_3_quality_scores={[round(q, 3) for q in top_3_quality]}",
            weight=1.5  # Higher weight - core quality metric
        )
    
    return result


def _test_personalization_differs(test_case, profiles, engine, state, result):
    """Test 02: Personalization Differs from Cold Start
    
    Scoring approach:
    - episode_difference: Map different count [0, 10] to score [1, 10]
    - similarity_increase: Map delta [0, 0.2+] to score [5, 10]
    - cold_start_flag_off: Binary (10 if false, 1 if true)
    """
    cold_response = _call_recommendation_api([], set(), state)
    
    vc_profile = profiles.get("02_vc_partner_ai_tech", {})
    vc_engagements = [
        {"episode_id": e["episode_id"], "type": e.get("type", "click"), "timestamp": e.get("timestamp", "")}
        for e in vc_profile.get("engagements", [])
    ]
    vc_response = _call_recommendation_api(vc_engagements, set(vc_profile.get("excluded_ids", [])), state)
    
    cold_ids = set(ep["id"] for ep in cold_response.get("episodes", [])[:10])
    vc_ids = set(ep["id"] for ep in vc_response.get("episodes", [])[:10])
    
    # Criterion 1: Episode difference
    # Map [0, 10] different episodes to score [1, 10]
    different_count = len(vc_ids - cold_ids)
    score = 1.0 + different_count * 0.9  # 0 → 1, 5 → 5.5, 10 → 10
    score = max(1.0, min(10.0, score))
    
    _add_criterion(
        result,
        criterion_id="episode_difference",
        description="At least 5 of top 10 episodes are different",
        score=score,
        threshold=5.5,  # Corresponds to 5 different episodes
        confidence=1.0,
        details=f"different_episodes={different_count}",
        weight=1.5  # Core personalization metric
    )
    
    # Criterion 2: VC has higher similarity scores
    cold_sim = [ep.get("similarity_score", 0) or 0 for ep in cold_response.get("episodes", [])[:10]]
    vc_sim = [ep.get("similarity_score", 0) or 0 for ep in vc_response.get("episodes", [])[:10]]
    avg_cold_sim = sum(cold_sim) / len(cold_sim) if cold_sim else 0
    avg_vc_sim = sum(vc_sim) / len(vc_sim) if vc_sim else 0
    
    # Map delta [-0.1, 0.2+] to score [3, 10]
    delta = avg_vc_sim - avg_cold_sim
    if delta <= 0:
        score = 3.0 + delta * 20  # Negative delta reduces score
    else:
        score = 5.0 + delta * 25  # Positive delta increases score
    score = max(1.0, min(10.0, score))
    
    _add_criterion(
        result,
        criterion_id="similarity_increase",
        description="VC Partner has higher avg similarity_score than cold start",
        score=score,
        threshold=5.0,  # Pass if any positive delta
        confidence=1.0,
        details=f"cold_avg={avg_cold_sim:.3f}, vc_avg={avg_vc_sim:.3f}, delta={delta:.3f}",
        weight=1.0
    )
    
    # Criterion 3: VC cold_start flag is false (binary)
    vc_cold_start = vc_response.get("cold_start", True)
    score = 10.0 if not vc_cold_start else 1.0
    
    _add_criterion(
        result,
        criterion_id="cold_start_flag_off",
        description="VC Partner cold_start flag is false",
        score=score,
        threshold=7.0,
        confidence=1.0,
        details=f"vc_cold_start={vc_cold_start}",
        weight=1.0
    )
    
    return result


def _test_quality_gates(test_case, profiles, engine, state, result):
    """Test 03: Quality Gates Enforce Credibility Floor
    
    This is a MFT (Minimum Functionality Test) - binary by nature.
    Scoring: 10 if gate holds, 1 if any violations.
    
    We also add a "violations ratio" as a gradual metric for debugging.
    """
    all_episodes = []
    
    for profile_id, profile in profiles.items():
        engagements = [
            {"episode_id": e["episode_id"], "type": e.get("type", "click"), "timestamp": e.get("timestamp", "")}
            for e in profile.get("engagements", [])
        ]
        response = _call_recommendation_api(engagements, set(profile.get("excluded_ids", [])), state)
        all_episodes.extend(response.get("episodes", []))
    
    total_episodes = len(all_episodes)
    
    # Criterion 1: No credibility < 2 (quality gate - binary)
    low_cred = [ep for ep in all_episodes if ep["scores"]["credibility"] < 2]
    violation_ratio = len(low_cred) / total_episodes if total_episodes > 0 else 0
    # Score: 10 if no violations, decrease proportionally
    score = 10.0 * (1.0 - violation_ratio)
    score = max(1.0, score)
    
    _add_criterion(
        result,
        criterion_id="credibility_floor",
        description="No episode with credibility < 2 in any response",
        score=score,
        threshold=10.0,  # Must be perfect (no violations)
        confidence=1.0,
        details=f"low_credibility_count={len(low_cred)}/{total_episodes}",
        weight=2.0  # Higher weight - critical gate
    )
    
    # Criterion 2: All C + I >= 5 (quality gate - binary)
    low_combined = [
        ep for ep in all_episodes 
        if ep["scores"]["credibility"] + ep["scores"]["insight"] < 5
    ]
    violation_ratio = len(low_combined) / total_episodes if total_episodes > 0 else 0
    score = 10.0 * (1.0 - violation_ratio)
    score = max(1.0, score)
    
    _add_criterion(
        result,
        criterion_id="combined_floor",
        description="All episodes have C + I >= 5",
        score=score,
        threshold=10.0,  # Must be perfect (no violations)
        confidence=1.0,
        details=f"low_combined_count={len(low_combined)}/{total_episodes}",
        weight=2.0  # Higher weight - critical gate
    )
    
    return result


def _test_excluded_episodes(test_case, profiles, engine, state, result):
    """Test 04: Excluded Episodes Never Reappear
    
    This is a MFT (Minimum Functionality Test) - binary by nature.
    Scoring: 10 if exclusions work, 1 if any violations.
    """
    profile = profiles.get("02_vc_partner_ai_tech", {}).copy()
    excluded_ids = test_case.get("setup", {}).get("modifications", {}).get("excluded_ids", [])
    
    engagements = [
        {"episode_id": e["episode_id"], "type": e.get("type", "click"), "timestamp": e.get("timestamp", "")}
        for e in profile.get("engagements", [])
    ]
    response = _call_recommendation_api(engagements, set(excluded_ids), state)
    
    episode_ids = [ep["id"] for ep in response.get("episodes", [])]
    
    # Criterion 1: No excluded IDs appear (binary gate)
    excluded_found = [eid for eid in excluded_ids if eid in episode_ids]
    violation_ratio = len(excluded_found) / len(excluded_ids) if excluded_ids else 0
    score = 10.0 * (1.0 - violation_ratio)
    score = max(1.0, score)
    
    _add_criterion(
        result,
        criterion_id="exclusions_respected",
        description="None of the excluded episode IDs appear",
        score=score,
        threshold=10.0,  # Must be perfect
        confidence=1.0,
        details=f"excluded_found={len(excluded_found)}/{len(excluded_ids)}",
        weight=2.0  # Critical gate
    )
    
    # Criterion 2: Still returns 10 results
    episode_count = len(response.get("episodes", []))
    # Map [0, 10] to [1, 10]
    score = episode_count if episode_count <= 10 else 10.0
    
    _add_criterion(
        result,
        criterion_id="still_returns_results",
        description="System still returns 10 valid recommendations",
        score=score,
        threshold=10.0,  # Must return exactly 10
        confidence=1.0,
        details=f"episode_count={episode_count}",
        weight=1.0
    )
    
    return result


def _test_category_personalization(test_case, profiles, engine, state, result):
    """Test 05: Category Engagement → Category Recommendations
    
    Scoring approach:
    - category_match: Map match count [0, 10] to score [1, 10]
    - Threshold at 5 matches = score 5.5
    """
    category_config = test_case.get("category_detection", {})
    
    def count_category_matches(episodes, category):
        config = category_config.get(category, {})
        series_keywords = [k.lower() for k in config.get("series_keywords", [])]
        content_keywords = [k.lower() for k in config.get("content_keywords", [])]
        
        count = 0
        for ep in episodes[:10]:
            series_name = ep.get("series", {}).get("name", "").lower()
            key_insight = (ep.get("key_insight") or "").lower()
            
            series_match = any(kw in series_name for kw in series_keywords)
            content_match = any(kw in key_insight for kw in content_keywords)
            
            if series_match or content_match:
                count += 1
        
        return count
    
    # AI/Tech profile
    ai_profile = profiles.get("02_vc_partner_ai_tech", {})
    ai_engagements = [
        {"episode_id": e["episode_id"], "type": e.get("type", "click"), "timestamp": e.get("timestamp", "")}
        for e in ai_profile.get("engagements", [])
    ]
    ai_response = _call_recommendation_api(ai_engagements, set(ai_profile.get("excluded_ids", [])), state)
    
    # Crypto profile
    crypto_profile = profiles.get("03_crypto_web3_investor", {})
    crypto_engagements = [
        {"episode_id": e["episode_id"], "type": e.get("type", "click"), "timestamp": e.get("timestamp", "")}
        for e in crypto_profile.get("engagements", [])
    ]
    crypto_response = _call_recommendation_api(crypto_engagements, set(crypto_profile.get("excluded_ids", [])), state)
    
    # Criterion 1: AI/Tech profile gets AI content
    # Map [0, 10] matches to [1, 10] score
    ai_match_count = count_category_matches(ai_response.get("episodes", []), "ai_tech")
    score = 1.0 + ai_match_count * 0.9  # 0 → 1, 5 → 5.5, 10 → 10
    
    _add_criterion(
        result,
        criterion_id="ai_tech_category_match",
        description="Profile 02 (AI/Tech): At least 5 of top 10 are AI/Tech related",
        score=score,
        threshold=5.5,  # Corresponds to 5 matches
        confidence=1.0,
        details=f"ai_tech_matches={ai_match_count}/10",
        weight=1.5  # Core personalization metric
    )
    
    # Criterion 2: Crypto profile gets crypto content
    crypto_match_count = count_category_matches(crypto_response.get("episodes", []), "crypto_web3")
    score = 1.0 + crypto_match_count * 0.9
    
    _add_criterion(
        result,
        criterion_id="crypto_category_match",
        description="Profile 03 (Crypto): At least 5 of top 10 are Crypto/Web3 related",
        score=score,
        threshold=5.5,  # Corresponds to 5 matches
        confidence=1.0,
        details=f"crypto_matches={crypto_match_count}/10",
        weight=1.5  # Core personalization metric
    )
    
    return result


def _test_bookmark_weighting(test_case, profiles, engine, state, result):
    """Test 06: Bookmarks Outweigh Clicks in Mixed History
    
    Scoring approach:
    - different_results: Map [0, 10] different to [1, 10] score
    - crypto_dominance: Map delta [-10, 10] to [1, 10] score
    """
    setup = test_case.get("setup", {})
    
    scenario_a_engagements = setup.get("scenario_a", {}).get("engagements", [])
    scenario_b_engagements = setup.get("scenario_b", {}).get("engagements", [])
    
    response_a = _call_recommendation_api(scenario_a_engagements, set(setup.get("scenario_a", {}).get("excluded_ids", [])), state)
    response_b = _call_recommendation_api(scenario_b_engagements, set(setup.get("scenario_b", {}).get("excluded_ids", [])), state)
    
    scenario_a_ids = set(ep["id"] for ep in response_a.get("episodes", [])[:10])
    scenario_b_ids = set(ep["id"] for ep in response_b.get("episodes", [])[:10])
    
    # Criterion 1: Different results
    # Map [0, 10] different episodes to [1, 10] score
    different_count = len(scenario_a_ids ^ scenario_b_ids)
    score = 1.0 + different_count * 0.9  # 0 → 1, 2 → 2.8, 10 → 10
    
    _add_criterion(
        result,
        criterion_id="different_results",
        description="Scenarios produce different recommendations (at least 2 different episodes)",
        score=score,
        threshold=2.8,  # Corresponds to 2 different episodes
        confidence=1.0,
        details=f"different_episodes={different_count}",
        weight=1.0
    )
    
    # Criterion 2: Crypto presence higher in Scenario B (bookmark crypto)
    crypto_keywords = ["crypto", "bitcoin", "ethereum", "web3", "defi", "blockchain", "btc", "eth"]
    
    def count_crypto(episodes):
        count = 0
        for ep in episodes[:10]:
            title = ep.get("title", "").lower()
            key_insight = (ep.get("key_insight") or "").lower()
            series = ep.get("series", {}).get("name", "").lower()
            text = f"{title} {key_insight} {series}"
            if any(kw in text for kw in crypto_keywords):
                count += 1
        return count
    
    crypto_count_a = count_crypto(response_a.get("episodes", []))
    crypto_count_b = count_crypto(response_b.get("episodes", []))
    
    # Map delta [-10, 10] to score [1, 10], with 0 delta → 5.5
    delta = crypto_count_b - crypto_count_a
    score = 5.5 + delta * 0.45  # -10 → 1, 0 → 5.5, +10 → 10
    score = max(1.0, min(10.0, score))
    
    _add_criterion(
        result,
        criterion_id="crypto_dominance_in_b",
        description="Scenario B (bookmark crypto) has more crypto episodes than Scenario A",
        score=score,
        threshold=5.5,  # Pass if B has more crypto (positive delta)
        confidence=1.0,
        details=f"scenario_a_crypto={crypto_count_a}/10, scenario_b_crypto={crypto_count_b}/10, delta={delta}",
        weight=1.5  # Core weighting test
    )
    
    return result


def _test_recency_scoring(test_case, profiles, engine, state, result):
    """Test 07: Recency Scoring Works
    
    Scoring approach:
    - both_in_top_10: Binary (10 if both found, 1 otherwise)
    - recency_score_ordering: Map score delta to 1-10
    - ranking_reflects_recency: Map position delta to 1-10
    """
    response = _call_recommendation_api([], set(), state)
    episodes = response.get("episodes", [])
    
    test_pair = test_case.get("setup", {}).get("test_episode_pair", {})
    recent_id = test_pair.get("recent", {}).get("id", "")
    older_id = test_pair.get("older", {}).get("id", "")
    
    recent_ep = next((ep for ep in episodes if ep["id"] == recent_id), None)
    older_ep = next((ep for ep in episodes if ep["id"] == older_id), None)
    
    # Criterion 1: Both episodes found in top 10 (binary)
    both_found = recent_ep is not None and older_ep is not None
    score = 10.0 if both_found else 1.0
    
    _add_criterion(
        result,
        criterion_id="both_in_top_10",
        description="Both test episodes found in top 10 cold start results",
        score=score,
        threshold=7.0,
        confidence=1.0,
        details=f"recent_found={recent_ep is not None}, older_found={older_ep is not None}",
        weight=1.0
    )
    
    if both_found:
        # Criterion 2: Recency score ordering
        recent_rec_score = recent_ep.get("recency_score", 0) or 0
        older_rec_score = older_ep.get("recency_score", 0) or 0
        
        # Map delta [-1, 1] to score [1, 10], with 0 → 5.5
        delta = recent_rec_score - older_rec_score
        score = 5.5 + delta * 4.5  # Positive delta → higher score
        score = max(1.0, min(10.0, score))
        
        _add_criterion(
            result,
            criterion_id="recency_score_ordering",
            description="Recent episode has higher recency_score than older",
            score=score,
            threshold=5.5,  # Pass if recent > older (positive delta)
            confidence=1.0,
            details=f"recent={recent_rec_score:.4f}, older={older_rec_score:.4f}, delta={delta:.4f}",
            weight=1.5
        )
        
        # Criterion 3: Ranking order (position delta)
        recent_pos = recent_ep.get("queue_position", 999)
        older_pos = older_ep.get("queue_position", 999)
        
        # Position delta: older_pos - recent_pos (positive means recent ranks higher)
        pos_delta = older_pos - recent_pos
        # Map [-10, 10] to [1, 10]
        score = 5.5 + pos_delta * 0.45
        score = max(1.0, min(10.0, score))
        
        _add_criterion(
            result,
            criterion_id="ranking_reflects_recency",
            description="Recent episode ranks higher (lower position) than older",
            score=score,
            threshold=5.5,  # Pass if recent ranks higher (positive delta)
            confidence=1.0,
            details=f"recent_pos={recent_pos}, older_pos={older_pos}, delta={pos_delta}",
            weight=1.5
        )
    else:
        # Add placeholder criteria so aggregate scoring works
        _add_criterion(
            result,
            criterion_id="recency_score_ordering",
            description="Recent episode has higher recency_score than older",
            score=1.0,
            threshold=5.5,
            confidence=1.0,
            details="Could not test - episodes not found in top 10",
            weight=1.5
        )
        _add_criterion(
            result,
            criterion_id="ranking_reflects_recency",
            description="Recent episode ranks higher (lower position) than older",
            score=1.0,
            threshold=5.5,
            confidence=1.0,
            details="Could not test - episodes not found in top 10",
            weight=1.5
        )
    
    return result


# ============================================================================
# Stats
# ============================================================================

@app.get("/api/stats")
def get_stats():
    """Get current statistics."""
    state = get_state()
    
    if not state.is_loaded:
        return {
            "loaded": False,
            "message": "No configuration loaded"
        }
    
    return {
        "loaded": True,
        "algorithm": state.current_algorithm.folder_name,
        "dataset": state.current_dataset.folder_name,
        "total_episodes": len(state.current_dataset.episodes),
        "total_embeddings": len(state.current_embeddings),
        "active_sessions": len(state.sessions),
    }


# ============================================================================
# Startup
# ============================================================================

@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    state = get_state()
    print(f"Serafis Evaluation Framework API starting...")
    print(f"Algorithms: {state.config.algorithms_dir}")
    print(f"Datasets: {state.config.datasets_dir}")
    print(f"Cache: {state.config.cache_dir}")


if __name__ == "__main__":
    import uvicorn
    config = get_config()
    uvicorn.run(app, host=config.host, port=config.port)
