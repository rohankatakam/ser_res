"""Configuration endpoints: algorithms, datasets, load, validate, status."""

import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Query

try:
    from ..state import get_state
    from ..services import DatasetEpisodeProvider, EmbeddingGenerator
    from ..models import LoadConfigRequest
except ImportError:
    from state import get_state
    from services import DatasetEpisodeProvider, EmbeddingGenerator
    from models import LoadConfigRequest

router = APIRouter()


@router.get("/algorithms")
def list_algorithms():
    """List all available algorithm versions."""
    state = get_state()
    algorithms = state.algorithm_loader.list_algorithms()
    return {
        "algorithms": algorithms,
        "current": state.current_algorithm.folder_name if state.current_algorithm else None,
    }


@router.get("/datasets")
def list_datasets():
    """List all available datasets."""
    state = get_state()
    datasets = state.dataset_loader.list_datasets()
    return {
        "datasets": datasets,
        "current": state.current_dataset.folder_name if state.current_dataset else None,
    }


@router.get("/api-keys/status")
def get_api_key_status():
    """Check which API keys are configured in environment."""
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    openai_configured = bool(openai_key)
    gemini_configured = bool(gemini_key)
    anthropic_configured = bool(anthropic_key)
    missing_keys = []
    if not openai_configured:
        missing_keys.append("openai")
    return {
        "openai_configured": openai_configured,
        "gemini_configured": gemini_configured,
        "anthropic_configured": anthropic_configured,
        "missing_keys": missing_keys,
        "notes": {
            "openai": "Required for embeddings and recommendations",
            "gemini": "Optional for LLM-as-a-judge evaluation",
            "anthropic": "Optional for LLM-as-a-judge evaluation",
        },
    }


@router.get("/validate")
def validate_compatibility(
    algorithm_folder: str = Query(..., description="Algorithm folder name"),
    dataset_folder: str = Query(..., description="Dataset folder name"),
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


@router.post("/load")
def load_configuration(
    request: LoadConfigRequest,
    x_openai_key: Optional[str] = Header(None, alias="X-OpenAI-Key"),
):
    """Load an algorithm and dataset combination, optionally generating embeddings."""
    state = get_state()
    config = state.config
    compat = state.validator.check_compatibility(request.algorithm, request.dataset)
    if not compat.is_compatible:
        raise HTTPException(status_code=400, detail=f"Incompatible: {compat.errors}")
    try:
        algorithm = state.algorithm_loader.load_algorithm(request.algorithm)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    try:
        dataset = state.dataset_loader.load_dataset(request.dataset)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    embeddings = {}
    embeddings_cached = state.has_embeddings_cached(
        algorithm.folder_name, algorithm.strategy_version, dataset.folder_name
    )
    embedding_generation_result = None
    if embeddings_cached:
        strategy_file = algorithm.path / "embedding_strategy.py" if algorithm.path else None
        embeddings = state.load_cached_embeddings(
            algorithm.folder_name,
            algorithm.strategy_version,
            dataset.folder_name,
            strategy_file_path=strategy_file,
        ) or {}
    elif request.generate_embeddings:
        api_key = x_openai_key or config.openai_api_key
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="OpenAI API key required for embedding generation. Set OPENAI_API_KEY env var or pass X-OpenAI-Key header.",
            )
        try:
            generator = EmbeddingGenerator(
                api_key=api_key,
                model=algorithm.embedding_model,
                dimensions=algorithm.embedding_dimensions,
            )
            result = generator.generate_for_episodes(
                episodes=dataset.episodes,
                get_embed_text=algorithm.get_embed_text,
                on_progress=None,
            )
            if result.success:
                strategy_file = algorithm.path / "embedding_strategy.py" if algorithm.path else None
                state.save_embeddings(
                    algorithm.folder_name,
                    algorithm.strategy_version,
                    dataset.folder_name,
                    result.embeddings,
                    algorithm.embedding_model,
                    algorithm.embedding_dimensions,
                    strategy_file_path=strategy_file,
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
            print(f"Embedding generation failed: {e}")
            embedding_generation_result = {"generated": False, "error": str(e)}
    state.current_algorithm = algorithm
    state.current_dataset = dataset
    state.current_episode_provider = DatasetEpisodeProvider(dataset)
    state.current_embeddings = embeddings
    state.sessions.clear()
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
        },
    }
    if embedding_generation_result:
        response["embeddings"]["generation_result"] = embedding_generation_result
    return response


@router.get("/status")
def get_config_status():
    """Get current configuration status (simple format for frontend)."""
    state = get_state()
    if not state.is_loaded:
        return {"loaded": False, "algorithm_folder": None, "dataset_folder": None}
    return {
        "loaded": True,
        "algorithm_folder": state.current_algorithm.folder_name,
        "dataset_folder": state.current_dataset.folder_name,
        "algorithm_name": state.current_algorithm.manifest.name,
        "dataset_name": state.current_dataset.manifest.name,
        "embeddings_count": len(state.current_embeddings),
    }


@router.get("/current")
def get_current_config():
    """Get currently loaded configuration (detailed format)."""
    state = get_state()
    if not state.is_loaded:
        return {"loaded": False, "algorithm": None, "dataset": None, "embeddings": None}
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
            "coverage": len(state.current_embeddings) / len(state.current_dataset.episodes)
            if state.current_dataset.episodes
            else 0,
        },
    }
