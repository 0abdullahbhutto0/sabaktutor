"""
Core RAG engine: trees, embeddings, search.

Usage:
    from backend.core import DocumentTree, HybridSearchEngine, EmbeddingManager, FaissVectorStore
"""

from .tree import DocumentTree, TreeNode, Chunk, NodeType
from .embeddings import EmbeddingManager
from .value_function import ValueFunction, NodeScorer, IndexTiming
from .vector_store import FaissVectorStore  
from .hybrid_search import HybridSearchEngine, SearchOptions, SearchResponse

__all__ = [
    "DocumentTree",
    "TreeNode",
    "Chunk",
    "NodeType",
    "EmbeddingManager",
    "ValueFunction",
    "NodeScorer",
    "IndexTiming",
    "FaissVectorStore",  
    "HybridSearchEngine",
    "SearchOptions",
    "SearchResponse",
]