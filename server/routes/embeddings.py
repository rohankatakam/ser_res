"""Embedding status and generation endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Header

try:
    from ..state import get_state
    from ..services import EmbeddingGenerator, check_openai_available
    from ..models import GenerateEmbeddingsRequest
except ImportError:
    from state import get_state
    from services import EmbeddingGenerator, check_openai_available
    from models import GenerateEmbeddingsRequest

router = APIRouter()


@router.get("/status")
def embeddings_status():
    """Get status of embeddings for current configuration."""
    state = get_state()
    if not state.is_loaded:
        return {
            "loaded": False,
            "cached": False,
            "count": 0,
            "needs_generation": True,
            "message": "No algorithm/dataset loaded",
        }
    cached = state.has_embeddings_cached(
        state.current_algorithm.folder_name,
        state.current_algorithm.strategy_version,
        state.current_dataset.folder_name,
    )
    storage = "pinecone" if type(state.vector_store).__name__ == "PineconeVectorStore" else "none"
    return {
        "loaded": True,
        "cached": cached,
        "count": len(state.current_embeddings),
        "needs_generation": len(state.current_embeddings) < len(state.current_dataset.episodes),
        "storage": storage,
        "metadata": None,
        "openai_available": check_openai_available()[0],
    }


@router.post("/generate")
def generate_embeddings(
    request: GenerateEmbeddingsRequest,
    x_openai_key: Optional[str] = Header(None, alias="X-OpenAI-Key"),
):
    """Generate embeddings for an algorithm+dataset combination."""
    state = get_state()
    config = state.config
    api_key = x_openai_key or config.openai_api_key
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key required. Set OPENAI_API_KEY env var or pass X-OpenAI-Key header.",
        )
    try:
        algorithm = state.algorithm_loader.load_algorithm(request.algorithm)
        dataset = state.dataset_loader.load_dataset(request.dataset)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if not request.force:
        if state.has_embeddings_cached(
            algorithm.folder_name, algorithm.strategy_version, dataset.folder_name
        ):
            existing = state.load_cached_embeddings(
                algorithm.folder_name,
                algorithm.strategy_version,
                dataset.folder_name,
            )
            return {
                "status": "already_cached",
                "count": len(existing or {}),
                "message": "Embeddings already cached. Use force=true to regenerate.",
                "storage": "pinecone",
            }
    generator = EmbeddingGenerator(
        api_key=api_key,
        model=algorithm.embedding_model,
        dimensions=algorithm.embedding_dimensions,
    )

    def on_progress(p):
        pass

    result = generator.generate_for_episodes(
        episodes=dataset.episodes,
        get_embed_text=algorithm.get_embed_text,
        on_progress=on_progress,
    )
    if result.success:
        strategy_file = algorithm.path / "embedding" / "embedding_strategy.py" if algorithm.path else None
        state.save_embeddings(
            algorithm.folder_name,
            algorithm.strategy_version,
            dataset.folder_name,
            result.embeddings,
            algorithm.embedding_model,
            algorithm.embedding_dimensions,
            strategy_file_path=strategy_file,
        )
        if (
            state.current_algorithm
            and state.current_algorithm.folder_name == algorithm.folder_name
            and state.current_dataset
            and state.current_dataset.folder_name == dataset.folder_name
        ):
            state.current_embeddings = result.embeddings
    storage = "pinecone" if type(state.vector_store).__name__ == "PineconeVectorStore" else "none"
    return {
        "status": "success" if result.success else "partial",
        "generated": result.total_generated,
        "skipped": result.total_skipped,
        "total": len(result.embeddings),
        "estimated_cost": round(result.estimated_cost, 4),
        "errors": result.errors,
        "storage": storage,
    }
