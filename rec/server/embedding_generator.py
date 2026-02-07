"""
Embedding Generator

Generates embeddings for episodes using OpenAI's API.
Designed to work with the versioned algorithm architecture where each
algorithm version defines its own embedding strategy.

Usage:
    generator = EmbeddingGenerator(api_key="sk-...")
    
    # Generate embeddings for a list of episodes using an algorithm's strategy
    embeddings = generator.generate_for_episodes(
        episodes=episodes,
        get_embed_text=algorithm.get_embed_text,
        on_progress=lambda current, total: print(f"{current}/{total}")
    )
"""

import os
import time
from typing import Dict, List, Callable, Optional, Generator
from dataclasses import dataclass

# Check for OpenAI
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


@dataclass
class EmbeddingProgress:
    """Progress information for embedding generation."""
    current: int
    total: int
    batch_num: int
    total_batches: int
    episode_id: str = ""
    error: str = ""


@dataclass 
class EmbeddingResult:
    """Result of embedding generation."""
    success: bool
    embeddings: Dict[str, List[float]]
    total_generated: int
    total_skipped: int
    errors: List[str]
    estimated_cost: float


class EmbeddingGenerator:
    """
    Generates embeddings using OpenAI's embedding API.
    
    Features:
    - Batch processing for efficiency
    - Progress callbacks for UI updates
    - Cost estimation
    - Error handling with partial progress saving
    """
    
    # Default configuration
    DEFAULT_MODEL = "text-embedding-3-small"
    DEFAULT_DIMENSIONS = 1536
    BATCH_SIZE = 100
    DELAY_BETWEEN_BATCHES = 0.5  # seconds
    COST_PER_MILLION_TOKENS = 0.02  # USD for text-embedding-3-small
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        dimensions: int = DEFAULT_DIMENSIONS
    ):
        """
        Initialize the embedding generator.
        
        Args:
            api_key: OpenAI API key (falls back to OPENAI_API_KEY env var)
            model: Embedding model to use
            dimensions: Embedding dimensions
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self.dimensions = dimensions
        self._client: Optional[OpenAI] = None
    
    @property
    def client(self) -> OpenAI:
        """Get or create OpenAI client."""
        if not HAS_OPENAI:
            raise ImportError(
                "openai package not installed. Install with: pip install openai"
            )
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable "
                "or pass api_key to EmbeddingGenerator."
            )
        
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key)
        
        return self._client
    
    def estimate_cost(
        self,
        episodes: List[Dict],
        get_embed_text: Callable[[Dict], str]
    ) -> float:
        """
        Estimate the cost of generating embeddings.
        
        Args:
            episodes: List of episode dicts
            get_embed_text: Function to extract text for embedding
        
        Returns:
            Estimated cost in USD
        """
        total_chars = sum(len(get_embed_text(ep)) for ep in episodes)
        # Rough estimate: 1 token ≈ 4 characters
        estimated_tokens = total_chars / 4
        cost = (estimated_tokens / 1_000_000) * self.COST_PER_MILLION_TOKENS
        return cost
    
    def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of text strings to embed
        
        Returns:
            List of embedding vectors
        """
        response = self.client.embeddings.create(
            model=self.model,
            input=texts,
            dimensions=self.dimensions
        )
        return [item.embedding for item in response.data]
    
    def generate_for_episodes(
        self,
        episodes: List[Dict],
        get_embed_text: Callable[[Dict], str],
        on_progress: Optional[Callable[[EmbeddingProgress], None]] = None,
        existing_embeddings: Optional[Dict[str, List[float]]] = None
    ) -> EmbeddingResult:
        """
        Generate embeddings for a list of episodes.
        
        Args:
            episodes: List of episode dicts
            get_embed_text: Function to extract text for embedding from an episode
            on_progress: Optional callback for progress updates
            existing_embeddings: Optional dict of existing embeddings to skip
        
        Returns:
            EmbeddingResult with generated embeddings and statistics
        """
        existing = existing_embeddings or {}
        
        # Filter to episodes that need embeddings
        to_embed = [ep for ep in episodes if ep["id"] not in existing]
        
        if not to_embed:
            return EmbeddingResult(
                success=True,
                embeddings=existing.copy(),
                total_generated=0,
                total_skipped=len(episodes),
                errors=[],
                estimated_cost=0.0
            )
        
        # Calculate batches
        total_batches = (len(to_embed) + self.BATCH_SIZE - 1) // self.BATCH_SIZE
        estimated_cost = self.estimate_cost(to_embed, get_embed_text)
        
        embeddings = existing.copy()
        errors = []
        generated_count = 0
        
        for i in range(0, len(to_embed), self.BATCH_SIZE):
            batch = to_embed[i:i + self.BATCH_SIZE]
            batch_num = i // self.BATCH_SIZE + 1
            
            # Report progress
            if on_progress:
                on_progress(EmbeddingProgress(
                    current=i,
                    total=len(to_embed),
                    batch_num=batch_num,
                    total_batches=total_batches
                ))
            
            # Prepare texts and IDs
            texts = []
            ids = []
            for ep in batch:
                try:
                    text = get_embed_text(ep)
                    texts.append(text)
                    ids.append(ep["id"])
                except Exception as e:
                    errors.append(f"Failed to get embed text for {ep.get('id', 'unknown')}: {e}")
            
            if not texts:
                continue
            
            try:
                # Generate embeddings
                vectors = self.generate_batch(texts)
                
                # Store results
                for ep_id, vector in zip(ids, vectors):
                    embeddings[ep_id] = vector
                    generated_count += 1
                
                # Rate limiting
                if i + self.BATCH_SIZE < len(to_embed):
                    time.sleep(self.DELAY_BETWEEN_BATCHES)
                    
            except Exception as e:
                error_msg = f"Batch {batch_num} failed: {e}"
                errors.append(error_msg)
                
                # Report error progress
                if on_progress:
                    on_progress(EmbeddingProgress(
                        current=i,
                        total=len(to_embed),
                        batch_num=batch_num,
                        total_batches=total_batches,
                        error=error_msg
                    ))
        
        # Final progress report
        if on_progress:
            on_progress(EmbeddingProgress(
                current=len(to_embed),
                total=len(to_embed),
                batch_num=total_batches,
                total_batches=total_batches
            ))
        
        return EmbeddingResult(
            success=len(errors) == 0,
            embeddings=embeddings,
            total_generated=generated_count,
            total_skipped=len(episodes) - len(to_embed),
            errors=errors,
            estimated_cost=estimated_cost
        )
    
    def generate_streaming(
        self,
        episodes: List[Dict],
        get_embed_text: Callable[[Dict], str],
        existing_embeddings: Optional[Dict[str, List[float]]] = None
    ) -> Generator[EmbeddingProgress, None, Dict[str, List[float]]]:
        """
        Generate embeddings with streaming progress updates.
        
        This is a generator that yields progress updates and returns
        the final embeddings dict.
        
        Usage:
            gen = generator.generate_streaming(episodes, get_embed_text)
            for progress in gen:
                print(f"Progress: {progress.current}/{progress.total}")
            embeddings = gen.value  # Final result
        """
        existing = existing_embeddings or {}
        to_embed = [ep for ep in episodes if ep["id"] not in existing]
        
        if not to_embed:
            return existing.copy()
        
        total_batches = (len(to_embed) + self.BATCH_SIZE - 1) // self.BATCH_SIZE
        embeddings = existing.copy()
        
        for i in range(0, len(to_embed), self.BATCH_SIZE):
            batch = to_embed[i:i + self.BATCH_SIZE]
            batch_num = i // self.BATCH_SIZE + 1
            
            yield EmbeddingProgress(
                current=i,
                total=len(to_embed),
                batch_num=batch_num,
                total_batches=total_batches
            )
            
            texts = [get_embed_text(ep) for ep in batch]
            ids = [ep["id"] for ep in batch]
            
            try:
                vectors = self.generate_batch(texts)
                for ep_id, vector in zip(ids, vectors):
                    embeddings[ep_id] = vector
                
                if i + self.BATCH_SIZE < len(to_embed):
                    time.sleep(self.DELAY_BETWEEN_BATCHES)
                    
            except Exception as e:
                yield EmbeddingProgress(
                    current=i,
                    total=len(to_embed),
                    batch_num=batch_num,
                    total_batches=total_batches,
                    error=str(e)
                )
        
        yield EmbeddingProgress(
            current=len(to_embed),
            total=len(to_embed),
            batch_num=total_batches,
            total_batches=total_batches
        )
        
        return embeddings


def check_openai_available() -> tuple[bool, str]:
    """
    Check if OpenAI is available and configured.
    
    Returns:
        (is_available, message)
    """
    if not HAS_OPENAI:
        return False, "openai package not installed"
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return False, "OPENAI_API_KEY environment variable not set"
    
    return True, "OpenAI configured and ready"
