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
import os
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

# Import runner library for test execution
import sys
from pathlib import Path

# Add evaluation directory to Python path
# In Docker: /data/evaluation, Local: ../evaluation
evaluation_dir = os.getenv("EVALUATION_DIR")
if evaluation_dir:
    sys.path.insert(0, str(Path(evaluation_dir)))
else:
    sys.path.insert(0, str(Path(__file__).parent.parent / "evaluation"))

from runner import run_test_async, run_all_tests_async, EngineContext, load_all_profiles, load_test_case


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
    generate_embeddings: bool = True


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


# ============================================================================
# Algorithm Config Management (for UI parameter tuning)
# ============================================================================

@app.get("/api/algorithm/config")
def get_algorithm_config():
    """
    Get current algorithm config and schema for UI parameter tuning.
    
    Returns:
        - algorithm: Current algorithm folder name
        - config: Current parameter values (runtime state)
        - schema: Parameter schema for UI rendering (types, ranges, labels)
    """
    state = get_state()
    
    if not state.current_algorithm:
        raise HTTPException(
            status_code=400,
            detail="No algorithm loaded. Call /api/config/load first."
        )
    
    return {
        "algorithm": state.current_algorithm.folder_name,
        "algorithm_name": state.current_algorithm.manifest.name,
        "algorithm_version": state.current_algorithm.manifest.version,
        "config": state.current_algorithm.config,
        "schema": state.current_algorithm.config_schema
    }


def deep_merge(base: dict, updates: dict) -> dict:
    """Deep merge updates into base dict, returning new dict."""
    result = base.copy()
    for key, value in updates.items():
        if key.startswith("_"):
            # Skip metadata keys like _comment
            continue
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def validate_config_against_schema(config: dict, schema: dict) -> list:
    """
    Validate config values against schema constraints.
    
    Returns list of validation errors (empty if valid).
    """
    errors = []
    
    for group in schema.get("groups", []):
        for param in group.get("params", []):
            key_path = param["key"]
            parts = key_path.split(".")
            
            # Navigate to value in config
            value = config
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    value = None
                    break
            
            if value is None:
                continue  # Missing values use defaults, not an error
            
            param_type = param.get("type", "float")
            min_val = param.get("min")
            max_val = param.get("max")
            
            # Type validation
            if param_type == "int":
                if not isinstance(value, int) or isinstance(value, bool):
                    errors.append(f"{key_path}: expected int, got {type(value).__name__}")
                elif min_val is not None and value < min_val:
                    errors.append(f"{key_path}: {value} is below minimum {min_val}")
                elif max_val is not None and value > max_val:
                    errors.append(f"{key_path}: {value} exceeds maximum {max_val}")
            
            elif param_type == "float":
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    errors.append(f"{key_path}: expected float, got {type(value).__name__}")
                elif min_val is not None and value < min_val:
                    errors.append(f"{key_path}: {value} is below minimum {min_val}")
                elif max_val is not None and value > max_val:
                    errors.append(f"{key_path}: {value} exceeds maximum {max_val}")
            
            elif param_type == "boolean":
                if not isinstance(value, bool):
                    errors.append(f"{key_path}: expected boolean, got {type(value).__name__}")
    
    return errors


class ConfigUpdateRequest(BaseModel):
    """Request body for config update."""
    config: Dict[str, Any]


class ComputeParamsRequest(BaseModel):
    """Request body for computing derived parameters."""
    base_params: Dict[str, Any]
    profile: Optional[Dict[str, Any]] = None


@app.post("/api/algorithm/config/update")
def update_algorithm_config(request: ConfigUpdateRequest):
    """
    Update algorithm config at runtime (not persisted to file).
    
    Changes are applied to the current algorithm state and affect
    new recommendation sessions. Existing sessions are cleared.
    
    Args:
        config: Partial config update (will be merged with current config)
    
    Returns:
        - success: Whether update was applied
        - config: New merged config
    """
    state = get_state()
    
    if not state.current_algorithm:
        raise HTTPException(
            status_code=400,
            detail="No algorithm loaded. Call /api/config/load first."
        )
    
    # Deep merge updates into current config
    current_config = state.current_algorithm.config
    merged_config = deep_merge(current_config, request.config)
    
    # Validate against schema
    errors = validate_config_against_schema(
        merged_config, 
        state.current_algorithm.config_schema
    )
    
    if errors:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Config validation failed",
                "validation_errors": errors
            }
        )
    
    # Apply to runtime state
    state.current_algorithm.config = merged_config
    
    # Clear existing sessions (they use old config)
    state.sessions.clear()
    
    return {
        "success": True,
        "message": "Config updated. Existing sessions cleared.",
        "config": merged_config
    }


@app.get("/api/algorithm/config/diff")
def get_algorithm_config_diff():
    """
    Compare current algorithm config with defaults.
    
    Returns diff showing which parameters have been changed from their default values.
    Used by UI to show tuning warnings and parameter modifications.
    
    Returns:
        - has_changes: bool
        - changed_params: List of dicts with {key, default, current, diff_percent, type}
        - change_count: int
        - algorithm: str
        - algorithm_version: str
    """
    state = get_state()
    
    if not state.current_algorithm:
        raise HTTPException(
            status_code=400,
            detail="No algorithm loaded. Call /api/config/load first."
        )
    
    current_config = state.current_algorithm.config
    default_params = state.current_algorithm.manifest.default_parameters
    
    changed_params = []
    
    def compare_nested(current, defaults, prefix=""):
        """Recursively compare nested config dictionaries."""
        for key, default_value in defaults.items():
            current_value = current.get(key)
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(default_value, dict) and isinstance(current_value, dict):
                # Recurse into nested dicts
                compare_nested(current_value, default_value, full_key)
            elif current_value != default_value:
                # Parameter has changed
                diff_pct = None
                if isinstance(default_value, (int, float)) and isinstance(current_value, (int, float)):
                    if default_value != 0:
                        diff_pct = ((current_value - default_value) / default_value) * 100
                
                changed_params.append({
                    "key": full_key,
                    "default": default_value,
                    "current": current_value,
                    "diff_percent": diff_pct,
                    "type": type(default_value).__name__
                })
    
    compare_nested(current_config, default_params)
    
    return {
        "has_changes": len(changed_params) > 0,
        "changed_params": changed_params,
        "change_count": len(changed_params),
        "algorithm": state.current_algorithm.folder_name,
        "algorithm_version": state.current_algorithm.manifest.version
    }


@app.post("/api/algorithm/compute")
def compute_derived_parameters(request: ComputeParamsRequest):
    """
    Compute derived parameters from base parameters in real-time.
    
    This endpoint is used by the UI to show computed values as user adjusts
    base parameters. Computed parameters include normalized weights,
    quality score ranges, recency half-life, etc.
    
    Args:
        base_params: Base parameter values from user input
        profile: Optional user profile for computing user vector metrics
    
    Returns:
        - computed: Dictionary of computed parameter values
        - success: Whether computation succeeded
        - timestamp: When computation was performed
    """
    state = get_state()
    
    if not state.current_algorithm:
        raise HTTPException(
            status_code=400,
            detail="No algorithm loaded. Call /api/config/load first."
        )
    
    # Check if algorithm has computed_params module
    if not state.current_algorithm.compute_module:
        # Algorithm doesn't have computed params - return empty
        return {
            "computed": {},
            "success": True,
            "message": "This algorithm version does not have computed parameters",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    try:
        # Call the compute_parameters function from the algorithm's module
        computed = state.current_algorithm.compute_module.compute_parameters(
            base_params=request.base_params,
            profile=request.profile
        )
        
        return {
            "computed": computed,
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Computation failed: {str(e)}"
        )


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
def load_configuration(
    request: LoadConfigRequest,
    x_openai_key: Optional[str] = Header(None, alias="X-OpenAI-Key")
):
    """Load an algorithm and dataset combination, optionally generating embeddings."""
    state = get_state()
    config = state.config
    
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
    
    embedding_generation_result = None
    
    if embeddings_cached:
        # Pass strategy file path for hash verification
        strategy_file = algorithm.path / "embedding_strategy.py" if algorithm.path else None
        embeddings = state.load_cached_embeddings(
            algorithm.folder_name,
            algorithm.strategy_version,
            dataset.folder_name,
            strategy_file_path=strategy_file
        ) or {}
    elif request.generate_embeddings:
        # Generate embeddings inline
        api_key = x_openai_key or config.openai_api_key
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="OpenAI API key required for embedding generation. Set OPENAI_API_KEY env var or pass X-OpenAI-Key header."
            )
        
        try:
            # Generate embeddings
            generator = EmbeddingGenerator(
                api_key=api_key,
                model=algorithm.embedding_model,
                dimensions=algorithm.embedding_dimensions
            )
            
            result = generator.generate_for_episodes(
                episodes=dataset.episodes,
                get_embed_text=algorithm.get_embed_text,
                on_progress=None  # No progress callback for inline generation
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
                embeddings = result.embeddings
                embeddings_cached = True
                
                embedding_generation_result = {
                    "generated": True,
                    "count": len(result.embeddings),
                    "estimated_cost": round(result.estimated_cost, 4),
                }
            else:
                embedding_generation_result = {
                    "generated": False,
                    "error": "Partial generation failure",
                    "count": len(result.embeddings),
                }
        except Exception as e:
            # Log error but continue - embeddings will be empty
            print(f"Embedding generation failed: {e}")
            embedding_generation_result = {
                "generated": False,
                "error": str(e),
            }
    
    # Update state
    state.current_algorithm = algorithm
    state.current_dataset = dataset
    state.current_embeddings = embeddings
    state.sessions.clear()  # Clear old sessions
    
    response = {
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
    
    if embedding_generation_result:
        response["embeddings"]["generation_result"] = embedding_generation_result
    
    return response


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
    
    # Auto-exclude engaged episodes from recommendations
    # Users should not see episodes they've already interacted with in new sessions
    # Note: Within a session, engaged items remain visible until refresh
    for eng in request.engagements:
        excluded_ids.add(eng.episode_id)
    
    # Load algorithm-specific config
    algo_config = None
    if state.current_algorithm.config and hasattr(engine, 'RecommendationConfig'):
        algo_config = engine.RecommendationConfig.from_dict(state.current_algorithm.config)
    
    # Create recommendation queue
    queue, cold_start, user_vector_episodes = engine.create_recommendation_queue(
        engagements=engagements,
        excluded_ids=excluded_ids,
        episodes=state.current_dataset.episodes,
        embeddings=state.current_embeddings,
        episode_by_content_id=state.current_dataset.episode_by_content_id,
        config=algo_config,
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
    # Note: LLM evaluation always runs (no with_llm flag)


class RunAllTestsRequest(BaseModel):
    save_report: bool = True
    # Note: LLM evaluation always runs (no with_llm flag)


@app.post("/api/evaluation/run")
async def run_single_test(
    request: RunTestRequest,
    x_openai_key: Optional[str] = Header(None, alias="X-OpenAI-Key"),
    x_gemini_key: Optional[str] = Header(None, alias="X-Gemini-Key"),
    x_anthropic_key: Optional[str] = Header(None, alias="X-Anthropic-Key")
):
    """
    Run a single test case with multi-LLM evaluation.
    
    Pass API keys via headers:
    - X-OpenAI-Key: For OpenAI judge (optional, falls back to env var)
    - X-Gemini-Key: For Gemini judge (optional, falls back to env var)
    - X-Anthropic-Key: For Anthropic judge (optional, falls back to env var)
    
    LLM evaluation always runs (based on judges/config.json).
    """
    state = get_state()
    
    if not state.is_loaded:
        raise HTTPException(
            status_code=400,
            detail="No algorithm/dataset loaded. Call /api/config/load first."
        )
    
    # Set API keys as environment variables for judges package
    if x_openai_key:
        os.environ["OPENAI_API_KEY"] = x_openai_key
    if x_gemini_key:
        os.environ["GEMINI_API_KEY"] = x_gemini_key
    if x_anthropic_key:
        os.environ["ANTHROPIC_API_KEY"] = x_anthropic_key
    
    # Load profiles
    profiles = load_all_profiles()
    
    # Create engine context from loaded state
    engine_context = EngineContext(
        engine_module=state.current_algorithm.engine_module,
        episodes=state.current_dataset.episodes,
        embeddings=state.current_embeddings,
        episode_by_content_id=state.current_dataset.episode_by_content_id,
        algo_config=state.current_algorithm.config
    )
    
    # Run test using runner library
    result = await run_test_async(
        test_id=request.test_id,
        profiles=profiles,
        verbose=False,
        skip_llm=False,
        legacy_mode=False,
        engine_context=engine_context
    )
    
    return result.to_dict()


@app.post("/api/evaluation/run-all")
async def run_all_tests_endpoint(
    request: RunAllTestsRequest,
    x_openai_key: Optional[str] = Header(None, alias="X-OpenAI-Key"),
    x_gemini_key: Optional[str] = Header(None, alias="X-Gemini-Key"),
    x_anthropic_key: Optional[str] = Header(None, alias="X-Anthropic-Key")
):
    """
    Run all test cases with multi-LLM evaluation.
    
    Pass API keys via headers:
    - X-OpenAI-Key: For OpenAI judge (optional, falls back to env var)
    - X-Gemini-Key: For Gemini judge (optional, falls back to env var)
    - X-Anthropic-Key: For Anthropic judge (optional, falls back to env var)
    
    LLM evaluation always runs (based on judges/config.json).
    Results are saved to a report file if save_report is true.
    """
    state = get_state()
    
    if not state.is_loaded:
        raise HTTPException(
            status_code=400,
            detail="No algorithm/dataset loaded. Call /api/config/load first."
        )
    
    # Set API keys as environment variables for judges package
    if x_openai_key:
        os.environ["OPENAI_API_KEY"] = x_openai_key
    if x_gemini_key:
        os.environ["GEMINI_API_KEY"] = x_gemini_key
    if x_anthropic_key:
        os.environ["ANTHROPIC_API_KEY"] = x_anthropic_key
    
    # Load profiles
    profiles = load_all_profiles()
    
    # Create engine context from loaded state
    engine_context = EngineContext(
        engine_module=state.current_algorithm.engine_module,
        episodes=state.current_dataset.episodes,
        embeddings=state.current_embeddings,
        episode_by_content_id=state.current_dataset.episode_by_content_id,
        algo_config=state.current_algorithm.config
    )
    
    # Run all tests using runner library
    results = await run_all_tests_async(
        verbose=False,
        skip_llm=False,
        method_filter=None,
        legacy_mode=False,
        engine_context=engine_context
    )
    
    # Convert TestResult objects to dicts
    results_dicts = [r.to_dict() for r in results]
    
    # Build report with aggregate scoring
    passed = sum(1 for r in results_dicts if r.get("passed", False))
    failed = len(results_dicts) - passed
    
    # Compute overall algorithm score (weighted by test type)
    # MFT tests (quality gates, exclusions) are weighted higher
    mft_tests = ["03_quality_gates_credibility", "04_excluded_episodes"]
    
    total_weight = 0.0
    weighted_score = 0.0
    total_confidence = 0.0
    
    for r in results_dicts:
        test_scores = r.get("scores", {})
        if test_scores and test_scores.get("aggregate_score") is not None:
            # MFT tests get 2x weight
            weight = 2.0 if r.get("test_id") in mft_tests else 1.0
            weighted_score += test_scores.get("aggregate_score", 0) * weight
            total_confidence += test_scores.get("aggregate_confidence", 1.0) * weight
            total_weight += weight
    
    overall_score = round(weighted_score / total_weight, 2) if total_weight > 0 else 0.0
    overall_confidence = round(total_confidence / total_weight, 2) if total_weight > 0 else 0.0
    
    # Get active LLM providers from judge config
    try:
        from judges import get_available_providers
        llm_providers = get_available_providers()
    except:
        llm_providers = []
    
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context": {
            "algorithm_version": state.current_algorithm.folder_name if state.current_algorithm else None,
            "algorithm_name": state.current_algorithm.manifest.name if state.current_algorithm else None,
            "dataset_version": state.current_dataset.folder_name if state.current_dataset else None,
            "dataset_episode_count": len(state.current_dataset.episodes) if state.current_dataset else 0,
            "llm_providers": llm_providers,
            "evaluation_mode": "multi_llm"
        },
        "algorithm_config": {
            "config_snapshot": state.current_algorithm.config if state.current_algorithm else {},
            "manifest_defaults": state.current_algorithm.manifest.default_parameters if state.current_algorithm else {},
            "embedding_strategy_version": state.current_algorithm.manifest.embedding_strategy_version if state.current_algorithm else None,
            "embedding_model": state.current_algorithm.manifest.embedding_model if state.current_algorithm else None
        },
        "summary": {
            "total_tests": len(results_dicts),
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / len(results_dicts), 3) if results_dicts else 0,
            "overall_score": overall_score,
            "overall_confidence": overall_confidence,
            "score_breakdown": {
                r.get("test_id"): r.get("scores", {}).get("aggregate_score", 0)
                for r in results_dicts
            }
        },
        "results": results_dicts
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


# ============================================================================
# Judge Configuration Endpoints
# ============================================================================

@app.get("/api/evaluation/judge-config")
def get_judge_config():
    """
    Get current judge configuration from judges/config.json.
    
    Returns configuration for which LLM providers are enabled,
    number of samples per judge (N), temperature, etc.
    """
    state = get_state()
    config_path = state.config.evaluation_dir / "judges" / "config.json"
    
    if not config_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Judge configuration file not found"
        )
    
    try:
        with open(config_path) as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse judge configuration: {str(e)}"
        )


@app.post("/api/evaluation/judge-config")
def update_judge_config(config: Dict[str, Any]):
    """
    Update judge configuration in judges/config.json.
    
    Expects a JSON object with:
    - judges: Array of judge configurations
    - default_n: Number of samples per judge
    - temperature: LLM sampling temperature
    - etc.
    """
    state = get_state()
    config_path = state.config.evaluation_dir / "judges" / "config.json"
    
    # Validate basic structure
    if "judges" not in config:
        raise HTTPException(
            status_code=400,
            detail="Configuration must include 'judges' array"
        )
    
    if not isinstance(config["judges"], list):
        raise HTTPException(
            status_code=400,
            detail="'judges' must be an array"
        )
    
    # Validate each judge has required fields
    for judge in config["judges"]:
        if not isinstance(judge, dict):
            raise HTTPException(
                status_code=400,
                detail="Each judge must be an object"
            )
        if "provider" not in judge or "model" not in judge or "enabled" not in judge:
            raise HTTPException(
                status_code=400,
                detail="Each judge must have 'provider', 'model', and 'enabled' fields"
            )
    
    # Write to disk
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        return {"status": "success", "message": "Judge configuration updated"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to write configuration: {str(e)}"
        )


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
