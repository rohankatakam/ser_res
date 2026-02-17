"""
Compatibility Validator

Validates that an algorithm version is compatible with a dataset.
Checks schema versions and required fields.

Usage:
    validator = Validator(algorithm_loader, dataset_loader)
    result = validator.check_compatibility("v1_5_diversified", "eval_909_feb2026")
    
    if result.is_compatible:
        print("Ready to use!")
    else:
        print(f"Incompatible: {result.errors}")
"""

from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

from .algorithm_loader import AlgorithmLoader, LoadedAlgorithm
from .dataset_loader import DatasetLoader, LoadedDataset


@dataclass
class CompatibilityResult:
    """Result of a compatibility check."""
    is_compatible: bool
    algorithm_version: str
    dataset_version: str
    schema_match: bool
    required_fields_present: bool
    missing_fields: List[str]
    warnings: List[str]
    errors: List[str]
    
    def __bool__(self) -> bool:
        return self.is_compatible


class Validator:
    """
    Validates algorithm-dataset compatibility.
    
    Checks:
    1. Schema version compatibility (algorithm.requires_schema vs dataset.schema_version)
    2. Required fields present in dataset
    3. Optional fields coverage (warnings only)
    """
    
    def __init__(
        self,
        algorithm_loader: AlgorithmLoader,
        dataset_loader: DatasetLoader
    ):
        """
        Initialize the validator.
        
        Args:
            algorithm_loader: AlgorithmLoader instance
            dataset_loader: DatasetLoader instance
        """
        self.algorithm_loader = algorithm_loader
        self.dataset_loader = dataset_loader
    
    def check_compatibility(
        self,
        algorithm_folder: str,
        dataset_folder: str
    ) -> CompatibilityResult:
        """
        Check if an algorithm is compatible with a dataset.
        
        Args:
            algorithm_folder: Name of algorithm folder (e.g., "v1_5_diversified")
            dataset_folder: Name of dataset folder (e.g., "eval_909_feb2026")
        
        Returns:
            CompatibilityResult with detailed compatibility info
        """
        errors = []
        warnings = []
        
        # Load algorithm
        try:
            algorithm = self.algorithm_loader.load_algorithm(algorithm_folder)
        except FileNotFoundError as e:
            return CompatibilityResult(
                is_compatible=False,
                algorithm_version=algorithm_folder,
                dataset_version=dataset_folder,
                schema_match=False,
                required_fields_present=False,
                missing_fields=[],
                warnings=[],
                errors=[f"Failed to load algorithm: {e}"]
            )
        
        # Load dataset
        try:
            dataset = self.dataset_loader.load_dataset(dataset_folder)
        except FileNotFoundError as e:
            return CompatibilityResult(
                is_compatible=False,
                algorithm_version=algorithm_folder,
                dataset_version=dataset_folder,
                schema_match=False,
                required_fields_present=False,
                missing_fields=[],
                warnings=[],
                errors=[f"Failed to load dataset: {e}"]
            )
        
        # Check schema version compatibility
        algo_requires = algorithm.manifest.requires_schema
        dataset_schema = dataset.manifest.schema_version
        
        schema_match = self._check_schema_compatibility(algo_requires, dataset_schema)
        if not schema_match:
            errors.append(
                f"Schema version mismatch: algorithm requires {algo_requires}, "
                f"dataset has {dataset_schema}"
            )
        
        # Check required fields
        required_fields = algorithm.manifest.required_fields
        is_valid, missing_fields = self.dataset_loader.validate_dataset_schema(
            dataset_folder, required_fields
        )
        
        if not is_valid:
            errors.append(f"Missing required fields: {missing_fields}")
        
        # Check optional fields (warnings only)
        optional_fields = algorithm.manifest.optional_fields
        dataset_fields = set()
        if dataset.episodes:
            sample = dataset.episodes[0]
            dataset_fields = self._get_fields(sample)
        
        for field in optional_fields:
            if field not in dataset_fields and "." not in field:
                warnings.append(f"Optional field '{field}' not found in dataset")
        
        # Determine overall compatibility
        is_compatible = len(errors) == 0
        
        return CompatibilityResult(
            is_compatible=is_compatible,
            algorithm_version=algorithm_folder,
            dataset_version=dataset_folder,
            schema_match=schema_match,
            required_fields_present=is_valid,
            missing_fields=missing_fields,
            warnings=warnings,
            errors=errors
        )
    
    def _check_schema_compatibility(
        self,
        required_version: str,
        dataset_version: str
    ) -> bool:
        """
        Check if schema versions are compatible.
        
        Currently uses simple equality check.
        Future: Could support semantic versioning (e.g., 1.0 compatible with 1.1)
        """
        # Parse versions
        try:
            req_major, req_minor = map(int, required_version.split(".")[:2])
        except (ValueError, IndexError):
            req_major, req_minor = 1, 0
        
        try:
            data_major, data_minor = map(int, dataset_version.split(".")[:2])
        except (ValueError, IndexError):
            data_major, data_minor = 1, 0
        
        # Major version must match, dataset minor can be >= required minor
        return req_major == data_major and data_minor >= req_minor
    
    def _get_fields(self, obj: dict, prefix: str = "") -> set:
        """Recursively get all field names from a dict."""
        fields = set()
        
        for key, value in obj.items():
            full_key = f"{prefix}.{key}" if prefix else key
            fields.add(full_key)
            
            if isinstance(value, dict):
                fields.update(self._get_fields(value, full_key))
        
        return fields
    
    def validate_embeddings_needed(
        self,
        algorithm_folder: str,
        dataset_folder: str,
        cache_has_embeddings: bool
    ) -> tuple[bool, str]:
        """
        Check if embeddings need to be generated.
        
        Args:
            algorithm_folder: Name of algorithm folder
            dataset_folder: Name of dataset folder
            cache_has_embeddings: Whether embeddings are already cached
        
        Returns:
            (needs_generation, message)
        """
        if cache_has_embeddings:
            return False, "Embeddings already cached"
        
        # Load algorithm to check if it uses embeddings
        try:
            algorithm = self.algorithm_loader.load_algorithm(algorithm_folder)
        except FileNotFoundError:
            return False, "Algorithm not found"
        
        # Check if algorithm uses semantic similarity
        # (Look for embedding-related config or parameters)
        if algorithm.manifest.embedding_model:
            return True, f"Embeddings required (model: {algorithm.manifest.embedding_model})"
        
        return False, "Algorithm does not require embeddings"


def quick_validate(
    algorithms_dir: Path,
    datasets_dir: Path,
    algorithm_folder: str,
    dataset_folder: str
) -> CompatibilityResult:
    """
    Convenience function to quickly validate compatibility.
    
    Args:
        algorithms_dir: Path to algorithms directory
        datasets_dir: Path to datasets directory
        algorithm_folder: Algorithm folder name
        dataset_folder: Dataset folder name
    
    Returns:
        CompatibilityResult
    """
    algorithm_loader = AlgorithmLoader(algorithms_dir)
    dataset_loader = DatasetLoader(datasets_dir)
    validator = Validator(algorithm_loader, dataset_loader)
    
    return validator.check_compatibility(algorithm_folder, dataset_folder)
