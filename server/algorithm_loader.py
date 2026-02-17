"""
Algorithm Loader

Loads the algorithm from the algorithm/ directory.
The algorithm must have a manifest.json and embedding_strategy.py.

Usage:
    loader = AlgorithmLoader(algorithm_dir)
    
    # List available algorithms
    algorithms = loader.list_algorithms()
    
    # Load the algorithm (pass empty string or folder name)
    algo = loader.load_algorithm("")
    print(algo.manifest)
    text = algo.get_embed_text(episode)
"""

import json
import importlib.util
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass


@dataclass
class AlgorithmManifest:
    """Parsed manifest.json for an algorithm version."""
    version: str
    name: str
    description: str
    created_at: str
    embedding_strategy_version: str
    embedding_model: str
    embedding_dimensions: int
    requires_schema: str
    required_fields: List[str]
    optional_fields: List[str]
    default_parameters: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict) -> "AlgorithmManifest":
        return cls(
            version=data.get("version", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            created_at=data.get("created_at", ""),
            embedding_strategy_version=data.get("embedding_strategy_version", "1.0"),
            embedding_model=data.get("embedding_model", "text-embedding-3-small"),
            embedding_dimensions=data.get("embedding_dimensions", 1536),
            requires_schema=data.get("requires_schema", "1.0"),
            required_fields=data.get("required_fields", []),
            optional_fields=data.get("optional_fields", []),
            default_parameters=data.get("default_parameters", {})
        )


@dataclass
class LoadedAlgorithm:
    """A loaded algorithm with its manifest and embedding strategy."""
    folder_name: str
    path: Path
    manifest: AlgorithmManifest
    config: Dict[str, Any]
    config_schema: Dict[str, Any]  # Schema for UI parameter tuning
    
    # Embedding strategy functions
    get_embed_text: Callable[[Dict], str]
    strategy_version: str
    embedding_model: str
    embedding_dimensions: int
    
    # Optional: recommendation engine module
    engine_module: Optional[Any] = None
    
    # Optional: computed parameters module (for base/computed split)
    compute_module: Optional[Any] = None


class AlgorithmLoader:
    """
    Loads the algorithm from the algorithm/ directory.
    
    Expected directory structure:
        algorithm/
        ├── manifest.json          (required)
        ├── embedding_strategy.py  (required)
        ├── config_schema.json     (required - for UI parameter tuning)
        ├── config.json            (optional - parameter values)
        ├── recommendation_engine.py (optional)
        └── computed_params.py     (optional)
    """
    
    def __init__(self, algorithms_dir: Path):
        """
        Initialize the algorithm loader.
        
        Args:
            algorithms_dir: Path to the algorithm/ directory
        """
        self.algorithms_dir = Path(algorithms_dir)
        self._loaded_algorithms: Dict[str, LoadedAlgorithm] = {}
    
    def list_algorithms(self) -> List[Dict[str, Any]]:
        """
        List all available algorithm versions.
        
        Returns:
            List of dicts with algorithm info (folder_name, version, name, etc.)
        """
        algorithms = []
        
        if not self.algorithms_dir.exists():
            return algorithms
        
        for folder in self.algorithms_dir.iterdir():
            if not folder.is_dir():
                continue
            
            # Skip archive folder
            if folder.name.startswith("_"):
                continue
            
            manifest_path = folder / "manifest.json"
            if not manifest_path.exists():
                continue
            
            try:
                with open(manifest_path) as f:
                    manifest_data = json.load(f)
                
                algorithms.append({
                    "folder_name": folder.name,
                    "version": manifest_data.get("version", ""),
                    "name": manifest_data.get("name", folder.name),
                    "description": manifest_data.get("description", ""),
                    "embedding_strategy_version": manifest_data.get("embedding_strategy_version", "1.0"),
                    "requires_schema": manifest_data.get("requires_schema", "1.0"),
                    "path": str(folder)
                })
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to read manifest for {folder.name}: {e}")
        
        return algorithms
    
    def load_algorithm(self, folder_name: str = "") -> LoadedAlgorithm:
        """
        Load the algorithm. Since the directory is now flattened, folder_name is ignored.
        
        Args:
            folder_name: Ignored (kept for backwards compatibility)
        
        Returns:
            LoadedAlgorithm with manifest, config, and embedding strategy
        
        Raises:
            FileNotFoundError: If algorithm folder or required files don't exist
            ValueError: If algorithm files are invalid
        """
        # Since directory is flattened, use a fixed cache key
        cache_key = "current"
        
        # Return cached if already loaded
        if cache_key in self._loaded_algorithms:
            return self._loaded_algorithms[cache_key]
        
        # The algorithm files are directly in algorithms_dir
        folder_path = self.algorithms_dir
        
        if not folder_path.exists():
            raise FileNotFoundError(f"Algorithm directory not found: {folder_path}")
        
        # Load manifest
        manifest_path = folder_path / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"manifest.json not found in {folder_path}")
        
        with open(manifest_path) as f:
            manifest_data = json.load(f)
        manifest = AlgorithmManifest.from_dict(manifest_data)
        
        # Load config (optional - may be empty for baseline algorithms)
        config = {}
        config_path = folder_path / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
        
        # Load config schema (required for UI parameter tuning)
        schema_path = folder_path / "config_schema.json"
        if not schema_path.exists():
            raise FileNotFoundError(
                f"config_schema.json not found in {folder_path}. "
                "All algorithm versions must have a config_schema.json file."
            )
        
        with open(schema_path) as f:
            config_schema = json.load(f)
        
        # Load embedding strategy module
        strategy_path = folder_path / "embedding_strategy.py"
        if not strategy_path.exists():
            raise FileNotFoundError(f"embedding_strategy.py not found in {folder_path}")
        
        strategy_module = self._load_module(
            f"algorithm_{folder_name}_strategy",
            strategy_path
        )
        
        # Extract required functions and constants
        if not hasattr(strategy_module, "get_embed_text"):
            raise ValueError(f"embedding_strategy.py must define get_embed_text() function")
        
        get_embed_text = strategy_module.get_embed_text
        strategy_version = getattr(strategy_module, "STRATEGY_VERSION", "1.0")
        embedding_model = getattr(strategy_module, "EMBEDDING_MODEL", manifest.embedding_model)
        embedding_dimensions = getattr(strategy_module, "EMBEDDING_DIMENSIONS", manifest.embedding_dimensions)
        
        # Optionally load recommendation engine
        engine_module = None
        engine_path = folder_path / "recommendation_engine.py"
        if engine_path.exists():
            engine_module = self._load_module(
                f"algorithm_{folder_name}_engine",
                engine_path
            )
        
        # Optionally load computed parameters module
        compute_module = None
        compute_path = folder_path / "computed_params.py"
        if compute_path.exists():
            compute_module = self._load_module(
                f"algorithm_{folder_name}_computed",
                compute_path
            )
        
        # Create loaded algorithm
        loaded = LoadedAlgorithm(
            folder_name=folder_path.name,  # Use directory name
            path=folder_path,
            manifest=manifest,
            config=config,
            config_schema=config_schema,
            get_embed_text=get_embed_text,
            strategy_version=strategy_version,
            embedding_model=embedding_model,
            embedding_dimensions=embedding_dimensions,
            engine_module=engine_module,
            compute_module=compute_module
        )
        
        # Cache it
        self._loaded_algorithms[cache_key] = loaded
        
        return loaded
    
    def _load_module(self, module_name: str, module_path: Path) -> Any:
        """Dynamically load a Python module from a file path."""
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"Could not load module from {module_path}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        return module
    
    def unload_algorithm(self, folder_name: str) -> bool:
        """
        Unload a cached algorithm.
        
        Returns:
            True if algorithm was unloaded, False if it wasn't loaded
        """
        if folder_name in self._loaded_algorithms:
            del self._loaded_algorithms[folder_name]
            return True
        return False
    
    def reload_algorithm(self, folder_name: str) -> LoadedAlgorithm:
        """Reload an algorithm, clearing any cached version."""
        self.unload_algorithm(folder_name)
        return self.load_algorithm(folder_name)
    
    def get_algorithm_path(self, folder_name: str) -> Optional[Path]:
        """Get the path to an algorithm folder."""
        path = self.algorithms_dir / folder_name
        return path if path.exists() else None
