"""
Embedding Manager Module
========================
Handles embedding generation using sentence transformers.
"""

from typing import List, Union, Dict
import numpy as np
from sentence_transformers import SentenceTransformer, util


class EmbeddingManager:
    """
    Manages text embeddings using sentence transformers.

    Features:
    - Batch encoding
    - GPU/CPU auto device selection
    - Similarity search utilities
    - Query embedding cache to avoid re-encoding
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        normalize: bool = True,
        embedding_dim: int = 384,
        max_cache_size: int = 100,
    ):
        self.model_name = model_name
        self.normalize = normalize
        self.embedding_dim = embedding_dim
        self.model = SentenceTransformer(model_name)
        self._cache: Dict[str, np.ndarray] = {}
        self._max_cache_size = max_cache_size

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        show_progress: bool = True
    ) -> np.ndarray:
        """Encode texts to embeddings with caching for single queries."""
        # Fast path: cached single query
        if isinstance(texts, str):
            cached = self._cache.get(texts)
            if cached is not None:
                return cached

            embedding = self.model.encode(
                texts,
                show_progress_bar=False,  # Never show progress for single cached queries
                normalize_embeddings=self.normalize,
            )
            # Simple LRU: evict oldest if at capacity
            if len(self._cache) >= self._max_cache_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[texts] = embedding
            return embedding

        # Batch path: no caching, use provided batch_size
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=self.normalize,
        )
        return embeddings

    def encode_query(self, query: str) -> np.ndarray:
        """Encode a query string, always using cache."""
        cached = self._cache.get(query)
        if cached is not None:
            return cached

        embedding = self.model.encode(
            query,
            show_progress_bar=False,
            normalize_embeddings=self.normalize,
        )
        if len(self._cache) >= self._max_cache_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[query] = embedding
        return embedding

    def clear_cache(self) -> None:
        """Clear the query embedding cache."""
        self._cache.clear()

    def compute_similarity(
        self,
        query_embedding: np.ndarray,
        document_embeddings: np.ndarray,
    ) -> np.ndarray:
        """Compute cosine similarity between query and documents."""
        return util.cos_sim(query_embedding, document_embeddings)[0].cpu().numpy()
