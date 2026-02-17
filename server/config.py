"""
Server Configuration

Loads configuration from environment variables and provides defaults.
Supports loading from .env file using python-dotenv.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Try to load dotenv from project root (single .env for backend, evaluation, Docker)
try:
    from dotenv import load_dotenv

    root_env = Path(__file__).resolve().parent.parent / ".env"
    if root_env.exists():
        load_dotenv(root_env)
except ImportError:
    pass  # dotenv not installed


@dataclass
class ServerConfig:
    """Server configuration."""

    # API Keys
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # Database connections
    qdrant_url: Optional[str] = None

    # Paths
    algorithms_dir: Path = Path(__file__).parent.parent / "algorithm"
    datasets_dir: Path = Path(__file__).parent.parent / "datasets"
    cache_dir: Path = Path(__file__).parent.parent / "cache"
    evaluation_dir: Path = Path(__file__).parent.parent / "evaluation"

    # Data source: "json" | "firebase" | None (use dataset from config/load)
    data_source: Optional[str] = None
    # When data_source=json: paths to episodes, series, and users JSON files
    episodes_json_path: Optional[Path] = None
    series_json_path: Optional[Path] = None
    users_json_path: Optional[Path] = None
    # When data_source=firebase: path to service account JSON and optional project id
    firebase_credentials_path: Optional[Path] = None
    firebase_project_id: Optional[str] = None

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Load configuration from environment variables."""
        base_dir = Path(__file__).parent.parent
        data_source = os.getenv("DATA_SOURCE", "").strip().lower() or None
        if data_source and data_source not in ("json", "firebase"):
            data_source = None

        def _path_env(key: str, default: Optional[Path] = None) -> Optional[Path]:
            v = os.getenv(key)
            if not v:
                return default
            p = Path(v)
            return p if p.is_absolute() else (base_dir / p).resolve()

        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            qdrant_url=os.getenv("QDRANT_URL"),
            algorithms_dir=Path(os.getenv("ALGORITHMS_DIR", str(base_dir / "algorithm"))),
            datasets_dir=Path(os.getenv("DATASETS_DIR", str(base_dir / "datasets"))),
            cache_dir=Path(os.getenv("CACHE_DIR", str(base_dir / "cache"))),
            evaluation_dir=Path(os.getenv("EVALUATION_DIR", str(base_dir / "evaluation"))),
            data_source=data_source,
            episodes_json_path=_path_env("EPISODES_JSON_PATH"),
            series_json_path=_path_env("SERIES_JSON_PATH"),
            users_json_path=_path_env("USERS_JSON_PATH", base_dir / "data" / "users.json"),
            firebase_credentials_path=_path_env("FIREBASE_CREDENTIALS_PATH") or _path_env("GOOGLE_APPLICATION_CREDENTIALS"),
            firebase_project_id=os.getenv("FIREBASE_PROJECT_ID") or None,
        )
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate the configuration.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        if not self.algorithms_dir.exists():
            errors.append(f"Algorithms directory not found: {self.algorithms_dir}")
        
        if not self.datasets_dir.exists():
            errors.append(f"Datasets directory not found: {self.datasets_dir}")
        
        # Cache dir will be created if needed
        # Evaluation dir is optional
        
        return len(errors) == 0, errors
    
    def ensure_directories(self):
        """Create required directories if they don't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "embeddings").mkdir(exist_ok=True)


# Global config instance
_config: Optional[ServerConfig] = None


def get_config() -> ServerConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = ServerConfig.from_env()
        _config.ensure_directories()
    return _config


def reload_config() -> ServerConfig:
    """Reload configuration from environment."""
    global _config
    _config = None
    return get_config()
