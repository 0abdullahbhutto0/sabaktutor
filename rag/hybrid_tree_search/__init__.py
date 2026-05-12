"""
Hybrid Tree Search System - Production Ready
==============================================
A hybrid retrieval system combining LLM-based tree search with value-based prediction
using Monte Carlo Tree Search (MCTS) for optimal document retrieval.

Author: MiniMax Agent
"""

from .config import SearchConfig, EmbeddingConfig, MCTSConfig
from .tree import DocumentTree, TreeNode, Chunk, NodeType, NodeStatus
from .embeddings import EmbeddingManager
from .value_function import ValueFunction, NodeScorer
from .mcts import MonteCarloTreeSearch, MCTSNode, SearchResult
from .hybrid_search import HybridSearchEngine, SearchOptions, SearchResponse, SearchMode

__version__ = "1.0.0"

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