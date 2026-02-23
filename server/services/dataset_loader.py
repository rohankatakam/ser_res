"""
Dataset Loader

Dynamically loads datasets from the fixtures directory (evaluation/fixtures).
Each dataset must have a manifest.json and episodes.json.

Usage:
    loader = DatasetLoader(datasets_dir)
    
    # List available datasets
    datasets = loader.list_datasets()
    
    # Load a specific dataset
    dataset = loader.load_dataset("eval_909_feb2026")
    print(dataset.manifest)
    print(f"Loaded {len(dataset.episodes)} episodes")
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class DatasetManifest:
    """Parsed manifest.json for a dataset."""
    version: str
    name: str
    description: str
    created_at: str
    schema_version: str
    episode_count: int
    unique_series: int
    source: Dict[str, str]
    statistics: Dict[str, Any]
    schema: Dict[str, List[str]]
    
    @classmethod
    def from_dict(cls, data: Dict) -> "DatasetManifest":
        return cls(
            version=data.get("version", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            created_at=data.get("created_at", ""),
            schema_version=data.get("schema_version", "1.0"),
            episode_count=data.get("episode_count", 0),
            unique_series=data.get("unique_series", 0),
            source=data.get("source", {}),
            statistics=data.get("statistics", {}),
            schema=data.get("schema", {})
        )


@dataclass
class LoadedDataset:
    """A loaded dataset with its manifest and data."""
    folder_name: str
    path: Path
    manifest: DatasetManifest
    episodes: List[Dict]
    series: List[Dict]
    
    # Derived lookups
    episode_map: Dict[str, Dict]  # id -> episode
    episode_by_content_id: Dict[str, Dict]  # content_id -> episode
    series_map: Dict[str, Dict]  # id -> series
    
    def get_episode(self, episode_id: str) -> Optional[Dict]:
        """Get episode by ID or content_id."""
        if episode_id in self.episode_map:
            return self.episode_map[episode_id]
        if episode_id in self.episode_by_content_id:
            return self.episode_by_content_id[episode_id]
        return None


class DatasetLoader:
    """
    Loads datasets from the fixtures directory.
    
    Expected directory structure:
        evaluation/fixtures/
        ├── eval_909_feb2026/
        │   ├── manifest.json
        │   ├── episodes.json
        │   └── series.json (optional)
        └── eval_1200_march2026/
            └── ...
    """
    
    def __init__(self, datasets_dir: Path):
        """
        Initialize the dataset loader.
        
        Args:
            datasets_dir: Path to the fixtures directory (e.g. evaluation/fixtures)
        """
        self.datasets_dir = Path(datasets_dir)
        self._loaded_datasets: Dict[str, LoadedDataset] = {}
    
    def list_datasets(self) -> List[Dict[str, Any]]:
        """
        List all available datasets.
        
        Returns:
            List of dicts with dataset info (folder_name, version, name, etc.)
        """
        datasets = []
        
        if not self.datasets_dir.exists():
            return datasets
        
        for folder in self.datasets_dir.iterdir():
            if not folder.is_dir():
                continue
            
            manifest_path = folder / "manifest.json"
            if not manifest_path.exists():
                continue
            
            try:
                with open(manifest_path) as f:
                    manifest_data = json.load(f)
                
                datasets.append({
                    "folder_name": folder.name,
                    "version": manifest_data.get("version", ""),
                    "name": manifest_data.get("name", folder.name),
                    "description": manifest_data.get("description", ""),
                    "schema_version": manifest_data.get("schema_version", "1.0"),
                    "episode_count": manifest_data.get("episode_count", 0),
                    "unique_series": manifest_data.get("unique_series", 0),
                    "path": str(folder)
                })
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to read manifest for {folder.name}: {e}")
        
        return datasets
    
    def load_dataset(self, folder_name: str) -> LoadedDataset:
        """
        Load a dataset.
        
        Args:
            folder_name: Name of the dataset folder (e.g., "eval_909_feb2026")
        
        Returns:
            LoadedDataset with manifest and episode data
        
        Raises:
            FileNotFoundError: If dataset folder or required files don't exist
            ValueError: If dataset files are invalid
        """
        # Return cached if already loaded
        if folder_name in self._loaded_datasets:
            return self._loaded_datasets[folder_name]
        
        folder_path = self.datasets_dir / folder_name
        
        if not folder_path.exists():
            raise FileNotFoundError(f"Dataset folder not found: {folder_path}")
        
        # Load manifest
        manifest_path = folder_path / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"manifest.json not found in {folder_path}")
        
        with open(manifest_path) as f:
            manifest_data = json.load(f)
        manifest = DatasetManifest.from_dict(manifest_data)
        
        # Load episodes
        episodes_file = manifest.source.get("episodes_file", "episodes.json")
        episodes_path = folder_path / episodes_file
        if not episodes_path.exists():
            raise FileNotFoundError(f"{episodes_file} not found in {folder_path}")
        
        with open(episodes_path) as f:
            episodes = json.load(f)
        
        # Load series (optional)
        series = []
        series_file = manifest.source.get("series_file", "series.json")
        series_path = folder_path / series_file
        if series_path.exists():
            with open(series_path) as f:
                series = json.load(f)
        
        # Build lookups
        episode_map = {ep["id"]: ep for ep in episodes}
        episode_by_content_id = {
            ep["content_id"]: ep for ep in episodes if ep.get("content_id")
        }
        series_map = {s["id"]: s for s in series}
        
        # Create loaded dataset
        loaded = LoadedDataset(
            folder_name=folder_name,
            path=folder_path,
            manifest=manifest,
            episodes=episodes,
            series=series,
            episode_map=episode_map,
            episode_by_content_id=episode_by_content_id,
            series_map=series_map
        )
        
        # Cache it
        self._loaded_datasets[folder_name] = loaded
        
        print(f"DatasetLoader: Loaded {len(episodes)} episodes, {len(series)} series from {folder_name}")
        
        return loaded
    
    def unload_dataset(self, folder_name: str) -> bool:
        """
        Unload a cached dataset to free memory.
        
        Returns:
            True if dataset was unloaded, False if it wasn't loaded
        """
        if folder_name in self._loaded_datasets:
            del self._loaded_datasets[folder_name]
            return True
        return False
    
    def reload_dataset(self, folder_name: str) -> LoadedDataset:
        """Reload a dataset, clearing any cached version."""
        self.unload_dataset(folder_name)
        return self.load_dataset(folder_name)
    
    def get_dataset_path(self, folder_name: str) -> Optional[Path]:
        """Get the path to a dataset folder."""
        path = self.datasets_dir / folder_name
        return path if path.exists() else None
    
    def validate_dataset_schema(
        self,
        folder_name: str,
        required_fields: List[str]
    ) -> tuple[bool, List[str]]:
        """
        Validate that a dataset has all required fields.
        
        Args:
            folder_name: Name of the dataset folder
            required_fields: List of required field names
        
        Returns:
            (is_valid, missing_fields)
        """
        dataset = self.load_dataset(folder_name)
        
        # Check a sample of episodes
        missing_fields = set()
        sample_size = min(10, len(dataset.episodes))
        
        for ep in dataset.episodes[:sample_size]:
            for field in required_fields:
                if field == "scores":
                    if not ep.get("scores"):
                        missing_fields.add("scores")
                elif "." in field:
                    # Handle nested fields like "scores.credibility"
                    parts = field.split(".")
                    value = ep
                    for part in parts:
                        if isinstance(value, dict):
                            value = value.get(part)
                        else:
                            value = None
                            break
                    if value is None:
                        missing_fields.add(field)
                else:
                    if not ep.get(field):
                        missing_fields.add(field)
        
        return len(missing_fields) == 0, list(missing_fields)
