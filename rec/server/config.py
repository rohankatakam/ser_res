"""
Server Configuration

Loads configuration from environment variables and provides defaults.
Supports loading from .env file using python-dotenv.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Try to load dotenv
try:
    from dotenv import load_dotenv
    
    # Load .env from server directory
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    
    # Also try parent directory
    parent_env = Path(__file__).parent.parent / ".env"
    if parent_env.exists():
        load_dotenv(parent_env)
        
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
    
    # Paths
    algorithms_dir: Path = Path(__file__).parent.parent / "algorithms"
    datasets_dir: Path = Path(__file__).parent.parent / "datasets"
    cache_dir: Path = Path(__file__).parent.parent / "cache"
    evaluation_dir: Path = Path(__file__).parent.parent / "evaluation"
    
    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Load configuration from environment variables."""
        base_dir = Path(__file__).parent.parent
        
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            algorithms_dir=Path(os.getenv("ALGORITHMS_DIR", base_dir / "algorithms")),
            datasets_dir=Path(os.getenv("DATASETS_DIR", base_dir / "datasets")),
            cache_dir=Path(os.getenv("CACHE_DIR", base_dir / "cache")),
            evaluation_dir=Path(os.getenv("EVALUATION_DIR", base_dir / "evaluation")),
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
