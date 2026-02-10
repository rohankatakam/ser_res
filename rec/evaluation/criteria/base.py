"""
Base Classes for Criterion Types

Defines the data structures for LLM and Deterministic criteria.
These classes are used to parse and validate criterion definitions from JSON.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum


class CriterionType(Enum):
    """Type of criterion evaluation."""
    LLM = "llm"
    DETERMINISTIC = "deterministic"


@dataclass
class ScoringConfig:
    """Scoring configuration for a criterion."""
    scale: tuple[int, int] = (1, 10)  # (min, max) score range
    default_threshold: float = 6.0    # Pass threshold
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScoringConfig":
        """Create from dictionary (JSON parsing)."""
        return cls(
            scale=tuple(data.get("scale", [1, 10])),
            default_threshold=data.get("default_threshold", 6.0)
        )


@dataclass
class CriterionDefinition:
    """
    Base class for all criterion definitions.
    
    Common fields shared by both LLM and Deterministic criteria.
    Parsed from definition.json in each criterion folder.
    """
    id: str                          # Unique identifier (e.g., "relevance")
    type: CriterionType              # "llm" or "deterministic"
    name: str                        # Human-readable name
    version: str = "1.0"             # Criterion version
    description: str = ""            # What this criterion evaluates
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    tags: List[str] = field(default_factory=list)  # For filtering/grouping
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CriterionDefinition":
        """Create from dictionary. Subclasses override for additional fields."""
        return cls(
            id=data["id"],
            type=CriterionType(data["type"]),
            name=data["name"],
            version=data.get("version", "1.0"),
            description=data.get("description", ""),
            scoring=ScoringConfig.from_dict(data.get("scoring", {})),
            tags=data.get("tags", [])
        )


@dataclass
class LLMCriterion(CriterionDefinition):
    """
    LLM-based criterion that uses prompt templates for evaluation.
    
    The prompt_template is sent to LLM judges, and responses are parsed
    according to response_schema.
    
    Example definition.json:
        {
            "id": "relevance",
            "type": "llm",
            "name": "Relevance",
            "prompt_template": "Evaluate RELEVANCE on a scale of 1-10...",
            "response_schema": {"score": "number", "reasoning": "string"}
        }
    """
    prompt_template: str = ""        # Template with placeholders
    response_schema: Dict[str, str] = field(default_factory=dict)  # Expected response format
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMCriterion":
        """Create from dictionary (JSON parsing)."""
        base = CriterionDefinition.from_dict(data)
        return cls(
            id=base.id,
            type=base.type,
            name=base.name,
            version=base.version,
            description=base.description,
            scoring=base.scoring,
            tags=base.tags,
            prompt_template=data.get("prompt_template", ""),
            response_schema=data.get("response_schema", {"score": "number", "reasoning": "string"})
        )


@dataclass
class DeterministicCriterion(CriterionDefinition):
    """
    Deterministic criterion evaluated by a Python function.
    
    The function is loaded from logic.py in the criterion folder.
    It receives the API response and parameters, returning a score.
    
    Example definition.json:
        {
            "id": "avg_credibility",
            "type": "deterministic",
            "name": "Average Credibility",
            "function": "compute_avg_credibility",
            "parameters": {"top_n": 10}
        }
    """
    function: str = ""               # Name of function in logic.py
    parameters: Dict[str, Any] = field(default_factory=dict)  # Default params
    
    # Runtime: The actual callable (loaded from logic.py)
    _callable: Optional[Callable] = field(default=None, repr=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeterministicCriterion":
        """Create from dictionary (JSON parsing)."""
        base = CriterionDefinition.from_dict(data)
        return cls(
            id=base.id,
            type=base.type,
            name=base.name,
            version=base.version,
            description=base.description,
            scoring=base.scoring,
            tags=base.tags,
            function=data.get("function", ""),
            parameters=data.get("parameters", {})
        )
    
    def set_callable(self, func: Callable) -> None:
        """Set the callable function (loaded from logic.py)."""
        self._callable = func
    
    def evaluate(self, response: Dict[str, Any], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Evaluate the criterion using the loaded function.
        
        Args:
            response: API response with episodes
            params: Override parameters (merged with defaults)
        
        Returns:
            {"score": float, "passed": bool, "details": str}
        """
        if self._callable is None:
            raise RuntimeError(f"Criterion '{self.id}' has no callable loaded. "
                             f"Ensure logic.py exists and defines '{self.function}'.")
        
        # Merge default params with overrides
        merged_params = {**self.parameters, **(params or {})}
        merged_params["threshold"] = merged_params.get("threshold", self.scoring.default_threshold)
        
        return self._callable(response, merged_params)


@dataclass
class CriterionResult:
    """
    Result of evaluating a single criterion.
    
    Used by both LLM and Deterministic criteria to return standardized results.
    """
    criterion_id: str
    criterion_type: str              # "llm" or "deterministic"
    score: float                     # Final aggregated score
    passed: bool                     # score >= threshold
    threshold: float                 # The threshold used
    details: str = ""                # Human-readable details
    
    # LLM-specific fields (only populated for LLM criteria)
    model_results: Optional[Dict[str, Any]] = None  # Per-model breakdown
    cross_model_std: Optional[float] = None         # Standard deviation across models
    consensus_level: Optional[str] = None           # STRONG/GOOD/PARTIAL/LOW
    flag_for_review: bool = False                   # True if low consensus
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "criterion_id": self.criterion_id,
            "criterion_type": self.criterion_type,
            "score": self.score,
            "passed": self.passed,
            "threshold": self.threshold,
            "details": self.details
        }
        
        # Add LLM-specific fields if present
        if self.model_results is not None:
            result["model_results"] = self.model_results
        if self.cross_model_std is not None:
            result["cross_model_std"] = self.cross_model_std
        if self.consensus_level is not None:
            result["consensus_level"] = self.consensus_level
        if self.flag_for_review:
            result["flag_for_review"] = self.flag_for_review
        
        return result


def parse_criterion(data: Dict[str, Any]) -> CriterionDefinition:
    """
    Factory function to parse a criterion definition from JSON.
    
    Automatically selects the correct subclass based on the 'type' field.
    
    Args:
        data: Dictionary from definition.json
    
    Returns:
        LLMCriterion or DeterministicCriterion instance
    """
    criterion_type = data.get("type", "llm")
    
    if criterion_type == "deterministic":
        return DeterministicCriterion.from_dict(data)
    else:
        return LLMCriterion.from_dict(data)
