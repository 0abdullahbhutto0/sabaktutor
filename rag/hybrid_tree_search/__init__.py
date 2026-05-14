"""
Hybrid Tree Search System 
==============================================
A hybrid retrieval system combining LLM-based tree search with value-based prediction
using Monte Carlo Tree Search (MCTS) for optimal document retrieval.

"""

from .config import SearchConfig, EmbeddingConfig, MCTSConfig
from .tree import DocumentTree, TreeNode, Chunk
from .embeddings import EmbeddingManager
from .value_function import ValueFunction, NodeScorer
from .mcts import MonteCarloTreeSearch, MCTSNode, SearchResult
from .hybrid_search import HybridSearchEngine, SearchOptions, SearchResponse


__all__ = [
    # Config
    "SearchConfig",
    "EmbeddingConfig",
    "MCTSConfig",
    # Tree
    "DocumentTree",
    "TreeNode",
    "Chunk",
    # Core components
    "EmbeddingManager",
    "ValueFunction",
    "NodeScorer",
    # MCTS
    "MonteCarloTreeSearch",
    "MCTSNode",
    "SearchResult",
    # Hybrid search
    "HybridSearchEngine",
    "SearchOptions",
    "SearchResponse",
]