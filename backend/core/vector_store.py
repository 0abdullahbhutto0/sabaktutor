"""
Vector Store Module
===================
Handles embedding storage and retrieval using FAISS.
"""

import os
import json
import pickle
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class VectorRecord:
    """Single vector record with metadata."""
    id: str 
    vector: np.ndarray
    content: str = ""
    metadata: Dict = field(default_factory=dict)


class FaissVectorStore:
    """FAISS-based vector store for embeddings. Persists to disk."""

    def __init__(
        self,
        index_path: str = "./vector_index",
        embedding_dim: int = 384,
    ):
        self.index_path = index_path
        self.embedding_dim = embedding_dim
        self._records: Dict[str, VectorRecord] = {} 
        self._id_to_index: Dict[str, int] = {}       
        self._index_to_id: Dict[int, str] = {}
        
        self._init_empty_index()
        self._load()

    def _get_paths(self) -> Tuple[str, str, str]:
        """Get file paths for index components."""
        os.makedirs(self.index_path, exist_ok=True)
        return (
            os.path.join(self.index_path, "faiss.index"),
            os.path.join(self.index_path, "records.pkl"),
            os.path.join(self.index_path, "metadata.json"),
        )

    def _load(self) -> bool:
        """Load existing index from disk."""
        faiss_path, records_path, meta_path = self._get_paths()
        
        if not os.path.exists(faiss_path):
            print(f"No existing index at {self.index_path}, starting fresh")
            return False

        try:
            import faiss
            self._faiss_index = faiss.read_index(faiss_path)
            
            with open(records_path, "rb") as f:
                self._records = pickle.load(f)
            
            self._id_to_index.clear()
            self._index_to_id.clear()
            for i, record_id in enumerate(self._records.keys()):
                self._id_to_index[record_id] = i
                self._index_to_id[i] = record_id
            
            print(f"Loaded {len(self._records)} vectors from {self.index_path}")
            return True
            
        except Exception as e:
            print(f"Failed to load index: {e}")
            self._records.clear()
            self._id_to_index.clear()
            self._index_to_id.clear()
            return False

    def _init_empty_index(self):
        """Initialize empty FAISS index."""
        import faiss
        self._faiss_index = faiss.IndexFlatIP(self.embedding_dim)

    def save(self) -> None:
        """Persist index to disk."""
        if self._faiss_index.ntotal == 0:
            print("Nothing to save, index is empty")
            return
            
        faiss_path, records_path, meta_path = self._get_paths()
        
        import faiss
        faiss.write_index(self._faiss_index, faiss_path)
        
        with open(records_path, "wb") as f:
            pickle.dump(self._records, f)
        
        with open(meta_path, "w") as f:
            json.dump({
                "count": len(self._records),
                "dim": self.embedding_dim,
            }, f)
        
        print(f"Saved {len(self._records)} vectors to {self.index_path}")

    def add(self, record_id: str, vector: np.ndarray, content: str = "", metadata: Dict = None) -> None:
        """Add a vector to the store."""
        if metadata is None:
            metadata = {}
        
        if record_id in self._records:
            return
        
        vector = np.array(vector, dtype=np.float32).reshape(1, -1)
        
        import faiss
        faiss.normalize_L2(vector)
        
        self._faiss_index.add(vector)
        index_pos = self._faiss_index.ntotal - 1
        
        self._records[record_id] = VectorRecord(
            id=record_id,
            vector=vector[0],
            content=content,
            metadata=metadata,
        )
        self._id_to_index[record_id] = index_pos
        self._index_to_id[index_pos] = record_id

    def get(self, record_id: str) -> Optional[np.ndarray]:
        """Get vector by ID."""
        record = self._records.get(record_id)
        return record.vector if record else None

    def get_content(self, record_id: str) -> str:
        """Get content by ID."""
        record = self._records.get(record_id)
        return record.content if record else ""

    def exists(self, record_id: str) -> bool:
        """Check if vector exists."""
        return record_id in self._records

    def search(self, query_vector: np.ndarray, top_k: int = 10) -> List[Tuple[str, float, str]]:
        """
        Search for similar vectors.
        Returns: [(id, score, content), ...] sorted by score desc
        """
        if self._faiss_index.ntotal == 0:
            return []
        
        query = np.array(query_vector, dtype=np.float32).reshape(1, -1)
        import faiss
        faiss.normalize_L2(query)
        
        scores, indices = self._faiss_index.search(query, min(top_k, self._faiss_index.ntotal))
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            record_id = self._index_to_id.get(int(idx))
            if record_id:
                record = self._records[record_id]
                results.append((record_id, float(score), record.content))
        
        return results

    def count(self) -> int:
        """Get total vectors stored."""
        return len(self._records)

    def clear(self) -> None:
        """Clear all vectors."""
        self._records.clear()
        self._id_to_index.clear()
        self._index_to_id.clear()
        self._init_empty_index()