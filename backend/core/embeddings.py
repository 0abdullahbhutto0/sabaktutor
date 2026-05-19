"""
Embedding Manager Module
========================
Handles embedding generation using OpenRouter API.
Uses nvidia/llama-nemotron-embed-vl-1b-v2:free model.
LAZY LOADING: API client only initialized when needed.
"""

import os
import time
from typing import List, Union, Dict, Optional
import numpy as np
import requests


class EmbeddingManager:
    """Manages text embeddings using OpenRouter API (nvidia/llama-nemotron-embed-vl-1b-v2:free)."""

    DEFAULT_MODEL = "nvidia/llama-nemotron-embed-vl-1b-v2:free"
    DEFAULT_EMBEDDING_DIM = 2048
    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_TIMEOUT = 60
    DEFAULT_BATCH_SIZE = 32

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        embedding_dim: Optional[int] = None,
        base_url: Optional[str] = None,
        normalize: bool = True,
        max_cache_size: int = 100,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", self.DEFAULT_MODEL)
        self.embedding_dim = embedding_dim or self.DEFAULT_EMBEDDING_DIM
        self.base_url = base_url or os.getenv("OPENROUTER_BASE_URL", self.DEFAULT_BASE_URL)
        self.normalize = normalize
        self.max_retries = max_retries
        self.timeout = timeout
        self._max_cache_size = max_cache_size
        self._cache: Dict[str, np.ndarray] = {}
        self._session: Optional[requests.Session] = None

    @property
    def session(self) -> requests.Session:
        """Lazy initialize requests session."""
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def _make_embedding_request(self, texts: List[str], is_query: bool = False) -> np.ndarray:
        """
        Make embedding request to OpenRouter API.
        
        The nvidia/llama-nemotron-embed-vl-1b-v2 model uses query/passage prefixes
        for optimal retrieval performance.
        """
        if not self.api_key:
            raise RuntimeError(
                "OpenRouter API key not configured. "
                "Set OPENROUTER_API_KEY in .env or pass api_key to EmbeddingManager."
            )

        # Prefix texts for query vs document embedding
        prefix = "query: " if is_query else "passage: "
        prefixed_texts = [prefix + t for t in texts]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://localhost",
            "X-Title": "Sindh Board Quiz System",
        }

        payload = {
            "model": self.model_name,
            "input": prefixed_texts,
        }

        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    f"{self.base_url}/embeddings",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()

                embeddings = []
                for item in data.get("data", []):
                    embedding = item.get("embedding", [])
                    if not embedding:
                        raise RuntimeError(f"Empty embedding received from API for item: {item}")
                    embeddings.append(np.array(embedding, dtype=np.float32))

                result = np.array(embeddings, dtype=np.float32)

                if self.normalize:
                    # L2 normalize
                    norms = np.linalg.norm(result, axis=1, keepdims=True)
                    norms = np.where(norms == 0, 1, norms)  # avoid div by zero
                    result = result / norms

                return result

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429 and attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue

        raise RuntimeError(
            f"Embedding request failed after {self.max_retries} attempts: {last_error}"
        )

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        show_progress: bool = True
    ) -> np.ndarray:
        """Encode texts to embeddings with caching for single queries."""
        if isinstance(texts, str):
            cached = self._cache.get(texts)
            if cached is not None:
                return cached

            embedding = self._make_embedding_request([texts], is_query=False)
            result = embedding[0]
            self._add_to_cache(texts, result)
            return result

        if not texts:
            return np.array([], dtype=np.float32).reshape(0, self.embedding_dim)

        all_embeddings = []
        total = len(texts)

        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]
            if show_progress:
                print(f"Embedding batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size} "
                      f"({len(batch)} texts)...")

            batch_embeddings = self._make_embedding_request(batch, is_query=False)
            all_embeddings.append(batch_embeddings)

        result = np.vstack(all_embeddings)
        return result

    def encode_query(self, query: str) -> np.ndarray:
        """Encode a query string using query-specific prefix for better retrieval."""
        cached = self._cache.get(f"query:{query}")
        if cached is not None:
            return cached

        embedding = self._make_embedding_request([query], is_query=True)
        result = embedding[0]
        self._add_to_cache(f"query:{query}", result)
        return result

    def _add_to_cache(self, key: str, embedding: np.ndarray) -> None:
        """Add embedding to cache with LRU eviction."""
        if len(self._cache) >= self._max_cache_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[key] = embedding

    def clear_cache(self) -> None:
        """Clear the query embedding cache."""
        self._cache.clear()

    def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            self._session.close()
            self._session = None