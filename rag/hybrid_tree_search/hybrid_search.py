"""
Hybrid Search Engine Module
===========================
Implements the hybrid search system combining:
1. Value-based tree search (fast, using embeddings)
2. Monte Carlo Tree Search for orchestration
"""

from typing import List, Dict, Optional, Set, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import threading
import time

from .config import SearchConfig
from .tree import DocumentTree
from .embeddings import EmbeddingManager
from .value_function import ValueFunction
from .mcts import MonteCarloTreeSearch, SearchResult


@dataclass
class SearchOptions:
    """Options for search operations."""
    max_results: int = 10
    max_iterations: int = 1000
    early_stop: bool = True
    early_stop_threshold: float = 0.95
    value_weight: float = 0.7
    diversity_weight: float = 0.3
    timeout: int = 60
    include_metadata: bool = True

    def __post_init__(self):
        """Validate options."""
        total = self.value_weight + self.diversity_weight
        if abs(total - 1.0) > 0.01:
            self.value_weight /= total
            self.diversity_weight /= total


@dataclass
class SearchResponse:
    """Complete response from hybrid search."""
    query: str
    results: List[Dict[str, Any]]
    search_time: float = 0.0
    iterations: int = 0
    nodes_visited: int = 0
    cache_hit_rate: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "results": self.results,
            "search_time": self.search_time,
            "iterations": self.iterations,
            "nodes_visited": self.nodes_visited,
            "cache_hit_rate": self.cache_hit_rate,
            "metadata": self.metadata,
        }


class HybridSearchEngine:
    """
    Hybrid search engine combining value-based and MCTS-based tree search.

    Orchestrates parallel value-based search and MCTS with diversity-aware ranking.
    """

    def __init__(
        self,
        config: Optional[SearchConfig] = None,
        embedding_manager: Optional[EmbeddingManager] = None,
    ):
        self.config = config or SearchConfig()
        self.embedding_manager = embedding_manager or EmbeddingManager(
            model_name=self.config.embedding.model_name,
            normalize=self.config.embedding.normalize_embeddings,
            embedding_dim=self.config.embedding.embedding_dim,
        )

        self.value_function = ValueFunction(
            embedding_manager=self.embedding_manager,
            top_k=self.config.top_k_chunks,
            use_sqrt_normalization=self.config.use_square_root_normalization,
        )

        self.mcts = MonteCarloTreeSearch(
            value_function=self.value_function,
            exploration_constant=self.config.mcts.exploration_constant,
            max_iterations=self.config.mcts.max_iterations,
            max_depth=self.config.mcts.max_depth,
            min_visits=self.config.mcts.min_visits,
            early_stop_threshold=self.config.mcts.early_stop_threshold,
            value_weight=self.config.mcts.value_weight,
            diversity_weight=self.config.mcts.diversity_weight,
        )

        self.tree: Optional[DocumentTree] = None
        self._indexed = False
        self._visited_nodes: Set[str] = set()
        self._lock = threading.RLock()
        self.search_stats: Dict[str, Any] = {}

    def index_tree(self, tree: DocumentTree, show_progress: bool = False) -> None:
        """Index a document tree for search."""
        with self._lock:
            self.tree = tree
            self.value_function.index_tree(tree, show_progress)
            self._indexed = True

    def search(self, query: str, options: Optional[SearchOptions] = None) -> SearchResponse:
        """Perform hybrid search."""
        start_time = time.time()
        options = options or SearchOptions()

        if not self._indexed:
            raise ValueError("No documents indexed. Call index_tree() first.")

        with self._lock:
            self._visited_nodes.clear()

        results = self._search_hybrid(query, options)
        search_time = time.time() - start_time

        return SearchResponse(
            query=query,
            results=results,
            search_time=search_time,
            iterations=self.mcts.total_iterations,
            nodes_visited=len(self._visited_nodes),
            metadata={
                "options": {
                    "max_results": options.max_results,
                    "max_iterations": options.max_iterations,
                    "value_weight": options.value_weight,
                    "diversity_weight": options.diversity_weight,
                },
            },
        )

    def _search_hybrid(self, query: str, options: SearchOptions) -> List[Dict[str, Any]]:
        """Perform hybrid search combining value-based and MCTS-based approaches."""
        results: Dict[str, Dict[str, Any]] = {}
        visited: Set[str] = set()

        if self.tree:
            self.mcts.initialize(self.tree, query=query)

        with ThreadPoolExecutor(max_workers=2) as executor:
            value_future = executor.submit(self._search_value_only, query, options)
            mcts_future = executor.submit(
                self.mcts.search, query, options.max_results, options.early_stop
            )

            for result in value_future.result():
                node_id = result["node_id"]
                if node_id not in visited:
                    results[node_id] = result
                    visited.add(node_id)
                    self._visited_nodes.add(node_id)

            for result in mcts_future.result():
                node_id = result.document_node_id
                if node_id not in visited:
                    results[node_id] = {
                        "node_id": node_id,
                        "score": result.score * options.value_weight,
                        "source": "mcts",
                        "visit_count": result.visit_count,
                        "content": result.content,
                        "depth": result.depth,
                        "path": result.path,
                    }
                    visited.add(node_id)
                    self._visited_nodes.add(node_id)

        candidates = list(results.values())

        # Apply diversity bonus based on path prefixes
        path_prefixes = {}
        for candidate in candidates:
            path = candidate.get("path", [])
            prefix = "/".join(path[:2]) if len(path) >= 2 else candidate["node_id"]
            path_prefixes[prefix] = path_prefixes.get(prefix, 0) + 1

        for candidate in candidates:
            path = candidate.get("path", [])
            prefix = "/".join(path[:2]) if len(path) >= 2 else candidate["node_id"]
            diversity_penalty = 1.0 / path_prefixes[prefix]
            candidate["diversity_score"] = diversity_penalty

        final_results = []
        for candidate in candidates:
            combined_score = (
                options.value_weight * candidate["score"] +
                options.diversity_weight * candidate.get("diversity_score", 0.0)
            )
            candidate["combined_score"] = combined_score
            final_results.append(candidate)

        final_results.sort(key=lambda x: x["combined_score"], reverse=True)
        return final_results[:options.max_results]

    def _search_value_only(self, query: str, options: SearchOptions) -> List[Dict[str, Any]]:
        """Perform value-based search only using embeddings."""
        results = []
        if not self.tree:
            return results

        nodes_to_evaluate = [
            node.id for node in self.tree.get_all_nodes()
            if not node.is_root and (node.chunks or len(node.content) > 50)
        ]

        value_estimates = self.value_function.predict_values(query, nodes_to_evaluate)

        for node_id, score in value_estimates.items():
            node = self.tree.get_node(node_id)
            if node:
                results.append({
                    "node_id": node_id,
                    "score": score,
                    "source": "value",
                    "content": node.content,
                    "depth": node.depth,
                    "title": node.title,
                    "start_index": node.start_index,
                    "end_index": node.end_index,
                    "num_chunks": node.num_chunks,
                })
                self._visited_nodes.add(node_id)

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:options.max_results]

    def get_statistics(self) -> Dict[str, Any]:
        """Get search engine statistics."""
        with self._lock:
            return {
                "mcts_stats": self.mcts.get_statistics(),
                "indexed": self._indexed,
                "index_size": self.value_function.index_size,
                "visited_nodes": len(self._visited_nodes),
                "tree_nodes": self.tree.get_node_count() if self.tree else 0,
            }

    def clear_caches(self) -> None:
        """Clear all caches."""
        with self._lock:
            self.value_function.clear_index()
            self.mcts.clear_cache()
            self.embedding_manager.clear_cache()
            self._visited_nodes.clear()


def create_hybrid_engine(
    embedding_model: str = "BAAI/bge-small-en-v1.5",
    config: Optional[SearchConfig] = None,
) -> HybridSearchEngine:
    """Factory function to create a hybrid search engine."""
    if config is None:
        config = SearchConfig()
    config.embedding.model_name = embedding_model
    return HybridSearchEngine(config=config)
