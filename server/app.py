"""
Serafis Evaluation Framework — FastAPI app factory.

Use: uvicorn server.app:app
Or:  from server import app
"""

import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from .config import get_config
    from .state import get_state
    from .services import (
        DatasetEpisodeProvider,
        EmbeddingGenerator,
        FirestoreEpisodeProvider,
        JsonEpisodeProvider,
    )
except ImportError:
    from config import get_config
    from state import get_state
    from services import (
        DatasetEpisodeProvider,
        EmbeddingGenerator,
        FirestoreEpisodeProvider,
        JsonEpisodeProvider,
    )

# Evaluation dir on path before routes.evaluation (runner) is loaded
evaluation_dir = os.getenv("EVALUATION_DIR")
if evaluation_dir:
    sys.path.insert(0, str(Path(evaluation_dir)))
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evaluation"))

try:
    from .routes import register_routes
except ImportError:
    from routes import register_routes


def create_app() -> FastAPI:
    """Build FastAPI app with CORS, routes, and startup."""
    app = FastAPI(
        title="Serafis Evaluation Framework API",
        description="Versioned recommendation algorithm evaluation with dynamic loading",
        version="2.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_routes(app)

    @app.on_event("startup")
    def auto_load_config():
        try:
            state = get_state()
            config = state.config
            try:
                algorithm = state.algorithm_loader.load_algorithm("")
                state.current_algorithm = algorithm
                print(f"[startup] Loaded algorithm: {algorithm.manifest.name} v{algorithm.manifest.version}")
            except Exception as e:
                print(f"[startup] WARNING: Failed to load algorithm: {e}")
                return
            datasets = state.dataset_loader.list_datasets()
            if not datasets:
                print("[startup] WARNING: No datasets found")
                return
            dataset_folder = datasets[0]["folder_name"]
            try:
                dataset = state.dataset_loader.load_dataset(dataset_folder)
                state.current_dataset = dataset
                config = state.config
                if config.data_source == "firebase" and config.firebase_credentials_path:
                    state.current_episode_provider = FirestoreEpisodeProvider(
                        project_id=config.firebase_project_id,
                        credentials_path=config.firebase_credentials_path,
                    )
                    print("[startup] Episode provider: Firestore")
                elif config.data_source == "json" and config.episodes_json_path and config.series_json_path:
                    state.current_episode_provider = JsonEpisodeProvider(
                        config.episodes_json_path,
                        config.series_json_path,
                    )
                    print(f"[startup] Episode provider: JSON ({config.episodes_json_path})")
                else:
                    state.current_episode_provider = DatasetEpisodeProvider(dataset)
                print(f"[startup] Loaded dataset: {dataset.manifest.name} ({len(dataset.episodes)} episodes)")
            except Exception as e:
                print(f"[startup] WARNING: Failed to load dataset '{dataset_folder}': {e}")
                return
            embeddings_cached = state.has_embeddings_cached(
                algorithm.folder_name, algorithm.strategy_version, dataset_folder
            )
            if embeddings_cached:
                strategy_file = algorithm.path / "embedding" / "embedding_strategy.py" if algorithm.path else None
                embeddings = state.load_cached_embeddings(
                    algorithm.folder_name,
                    algorithm.strategy_version,
                    dataset_folder,
                    strategy_file_path=strategy_file,
                ) or {}
                state.current_embeddings = embeddings
                print(f"[startup] Loaded {len(embeddings)} cached embeddings")
            else:
                api_key = config.openai_api_key
                if api_key:
                    try:
                        generator = EmbeddingGenerator(
                            api_key=api_key,
                            model=algorithm.embedding_model,
                            dimensions=algorithm.embedding_dimensions,
                        )
                        result = generator.generate_for_episodes(
                            episodes=dataset.episodes,
                            get_embed_text=algorithm.get_embed_text,
                        )
                        if result.success:
                            state.current_embeddings = result.embeddings
                            state.save_embeddings(
                                algorithm.folder_name,
                                algorithm.strategy_version,
                                dataset_folder,
                                result.embeddings,
                                algorithm.embedding_model,
                                algorithm.embedding_dimensions,
                            )
                            print(f"[startup] Generated {result.total_generated} embeddings")
                        else:
                            print(f"[startup] Embedding generation had errors: {result.errors}")
                    except Exception as e:
                        print(f"[startup] WARNING: Failed to generate embeddings: {e}")
                else:
                    print("[startup] No OpenAI API key available, skipping embedding generation")
            print(f"[startup] Auto-load complete. Status: loaded={state.is_loaded}")
        except Exception as e:
            print(f"[startup] ERROR during auto-load: {e}")
            import traceback
            traceback.print_exc()

    @app.on_event("startup")
    async def _startup_logging():
        state = get_state()
        print("Serafis Evaluation Framework API starting...")
        print(f"Algorithms: {state.config.algorithms_dir}")
        print(f"Datasets: {state.config.datasets_dir}")
        print(f"Cache: {state.config.cache_dir}")

    return app


app = create_app()
