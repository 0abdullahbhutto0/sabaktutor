"""
Embedding Manager Module
========================
Handles embedding generation and caching using sentence transformers.
"""

from typing import List, Optional, Dict, Tuple, Union
import numpy as np
from sentence_transformers import SentenceTransformer
import torch
from pathlib import Path
import hashlib
import json
from functools import lru_cache
import threading


class EmbeddingCache:
    """Thread-safe cache for embeddings."""

    def __init__(self, max_size: int = 10000):
        self._cache: Dict[str, np.ndarray] = {}
        self._max_size = max_size
        self._lock = threading.RLock()
        self._access_count: Dict[str, int] = {}

    def get(self, key: str) -> Optional[np.ndarray]:
        """Get embedding from cache."""
        with self._lock:
            if key in self._cache:
                self._access_count[key] += 1
                return self._cache[key]
            return None

    def set(self, key: str, value: np.ndarray) -> None:
        """Set embedding in cache with LRU eviction."""
        with self._lock:
            if len(self._cache) >= self._max_size:
                # Evict least recently used
                lru_key = min(self._access_count, key=self._access_count.get)
                del self._cache[lru_key]
                del self._access_count[lru_key]

            self._cache[key] = value
            self._access_count[key] = 1

    def clear(self) -> None:
        """Clear the cache."""
        with self._lock:
            self._cache.clear()
            self._access_count.clear()

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)


class EmbeddingManager:
    """
    Manages text embeddings using sentence transformers.

    Features:
    - Batch processing for efficiency
    - Thread-safe caching
    - Multiple embedding models support
    - GPU acceleration when available
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/BAAI/bge-small-en-v1.5",
        device: Optional[str] = None,
        normalize: bool = True,
        cache_folder: Optional[str] = None,
        embedding_dim: int = 384,
    ):
        """
        Initialize the embedding manager.

        Args:
            model_name: Name of the sentence transformer model
            device: Device to use ("cpu", "cuda", "mps", or None for auto)
            normalize: Whether to normalize embeddings
            cache_folder: Optional folder for persistent caching
            embedding_dim: Expected embedding dimension
        """
        self.model_name = model_name
        self.normalize = normalize
        self.embedding_dim = embedding_dim

        # Determine device
        if device is None:
            if torch.cuda.is_available():
                self.device = "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"
        else:
            self.device = device

        # Load model
        self.model = SentenceTransformer(model_name, device=self.device, cache_folder=cache_folder)

        # Initialize cache
        self.cache = EmbeddingCache(max_size=10000)

        # Persistent cache
        self.cache_folder = Path(cache_folder) if cache_folder else None
        self._persistent_cache: Dict[str, List[float]] = {}
        if self.cache_folder:
            self.cache_folder.mkdir(parents=True, exist_ok=True)
            self._load_persistent_cache()

    def _load_persistent_cache(self) -> None:
        """Load persistent cache from disk."""
        cache_file = self.cache_folder / "embeddings_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    # Convert lists back to numpy arrays
                    for key, emb_list in data.items():
                        self._persistent_cache[key] = emb_list
            except Exception:
                pass

    def _save_persistent_cache(self) -> None:
        """Save persistent cache to disk."""
        if not self.cache_folder:
            return
        cache_file = self.cache_folder / "embeddings_cache.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(self._persistent_cache, f)
        except Exception:
            pass

    def _get_cache_key(self, text: str, prefix: str = "") -> str:
        """Generate a cache key for text."""
        key_input = f"{prefix}:{text}"
        return hashlib.md5(key_input.encode()).hexdigest()

    def _ensure_numpy(self, embeddings: Union[np.ndarray, List[float]]) -> np.ndarray:
        """Ensure embeddings are in numpy array format."""
        if isinstance(embeddings, list):
            return np.array(embeddings, dtype=np.float32)
        return embeddings.astype(np.float32)

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        show_progress: bool = False,
        convert_to_numpy: bool = True,
        normalize_embeddings: Optional[bool] = None,
    ) -> np.ndarray:
        """
        Encode texts to embeddings.

        Args:
            texts: Single text or list of texts
            batch_size: Batch size for processing
            show_progress: Whether to show progress bar
            convert_to_numpy: Whether to convert to numpy array
            normalize_embeddings: Override for normalize setting

        Returns:
            Embeddings as numpy array
        """
        # Handle single text
        if isinstance(texts, str):
            single_text = True
            texts = [texts]
        else:
            single_text = False

        # Check cache and batch requests
        uncached_texts = []
        uncached_indices = []
        results = [None] * len(texts)

        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text)
            cached = self.cache.get(cache_key)
            if cached is not None:
                results[i] = cached
            else:
                # Check persistent cache
                if cache_key in self._persistent_cache:
                    cached_arr = np.array(self._persistent_cache[cache_key], dtype=np.float32)
                    self.cache.set(cache_key, cached_arr)
                    results[i] = cached_arr
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)

        # Encode uncached texts
        if uncached_texts:
            norm = normalize_embeddings if normalize_embeddings is not None else self.normalize
            encoded = self.model.encode(
                uncached_texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=convert_to_numpy,
                normalize_embeddings=norm,
            )
            encoded = self._ensure_numpy(encoded)

            # Store in cache
            for idx, text in zip(uncached_indices, uncached_texts):
                cache_key = self._get_cache_key(text)
                if isinstance(encoded, np.ndarray) and len(encoded.shape) > 1:
                    emb = encoded[uncached_texts.index(text)]
                else:
                    emb = encoded if len(uncached_texts) == 1 else encoded[idx - uncached_indices[0]]
                self.cache.set(cache_key, emb)
                self._persistent_cache[cache_key] = emb.tolist()
                results[idx] = emb

        # Combine results
        if single_text:
            return results[0]
        return np.array(results, dtype=np.float32)

    def encode_chunks(
        self,
        chunks: List[Dict],
        content_field: str = "content",
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> List[Dict]:
        """
        Encode a list of chunks with their content.

        Args:
            chunks: List of chunk dictionaries
            content_field: Field name containing the text content
            batch_size: Batch size for encoding
            show_progress: Whether to show progress bar

        Returns:
            List of chunks with added 'embedding' field
        """
        if not chunks:
            return chunks

        # Extract texts
        texts = [chunk.get(content_field, "") for chunk in chunks]

        # Encode all texts
        embeddings = self.encode(texts, batch_size=batch_size, show_progress=show_progress)

        # Add embeddings to chunks
        for i, chunk in enumerate(chunks):
            chunk["embedding"] = embeddings[i].tolist()

        return chunks

    def compute_similarity(
        self,
        query_embedding: np.ndarray,
        document_embeddings: np.ndarray,
    ) -> np.ndarray:
        """
        Compute cosine similarity between query and documents.

        Args:
            query_embedding: Query embedding (1D or 2D array)
            document_embeddings: Document embeddings (2D array)

        Returns:
            Similarity scores
        """
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)

        # Cosine similarity
        similarities = np.dot(document_embeddings, query_embedding.T).flatten()

        # Normalize if not already normalized
        doc_norms = np.linalg.norm(document_embeddings, axis=1)
        query_norm = np.linalg.norm(query_embedding, axis=1)[0]

        if doc_norms.min() != 1.0 or query_norm != 1.0:
            similarities = similarities / (doc_norms * query_norm + 1e-8)

        return similarities

    def find_similar(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> List[Tuple[int, float]]:
        """
        Find most similar documents to a query.

        Args:
            query: Query text
            documents: List of document texts
            top_k: Number of results to return
            threshold: Minimum similarity threshold

        Returns:
            List of (document_index, similarity_score) tuples
        """
        # Encode query and documents
        query_emb = self.encode(query)
        doc_embs = self.encode(documents)

        # Compute similarities
        similarities = self.compute_similarity(query_emb, doc_embs)

        # Sort by similarity
        indices = np.argsort(similarities)[::-1]

        # Filter and return top k
        results = []
        for idx in indices:
            if similarities[idx] >= threshold:
                results.append((int(idx), float(similarities[idx])))
                if len(results) >= top_k:
                    break

        return results

    def batch_encode_for_search(
        self,
        chunks: List[str],
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Batch encode chunks for search operations.

        Args:
            chunks: List of chunk texts
            batch_size: Batch size for encoding
            show_progress: Whether to show progress bar

        Returns:
            Tuple of (embeddings array, chunk_ids)
        """
        # Generate IDs for chunks
        chunk_ids = [self._get_cache_key(chunk, f"search_{i}") for i, chunk in enumerate(chunks)]

        # Encode
        embeddings = self.encode(chunks, batch_size=batch_size, show_progress=show_progress)

        return embeddings, chunk_ids

    def save_embeddings(
        self,
        embeddings: np.ndarray,
        ids: List[str],
        filepath: str,
    ) -> None:
        """
        Save embeddings to disk.

        Args:
            embeddings: Embeddings array
            ids: Corresponding IDs
            filepath: Path to save file
        """
        save_path = Path(filepath)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        np.savez(
            save_path,
            embeddings=embeddings.astype(np.float32),
            ids=np.array(ids),
        )

    def load_embeddings(
        self,
        filepath: str,
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Load embeddings from disk.

        Args:
            filepath: Path to embeddings file

        Returns:
            Tuple of (embeddings array, ids)
        """
        data = np.load(filepath, allow_pickle=True)
        embeddings = data["embeddings"]
        ids = data["ids"].tolist()
        return embeddings, ids

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model."""
        return self.embedding_dim

    def clear_cache(self) -> None:
        """Clear all caches."""
        self.cache.clear()

    def save_cache(self) -> None:
        """Save persistent cache to disk."""
        self._save_persistent_cache()

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.save_cache()
        except Exception:
            pass