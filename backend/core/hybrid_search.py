"""
Hybrid Search Engine Module
"""

from typing import List, Dict, Optional, Set, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import threading
import time


from core.tree import DocumentTree
from core.embeddings import EmbeddingManager
from core.value_function import ValueFunction
from core.mcts import MonteCarloTreeSearch, SearchResult

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
    """Hybrid search engine combining value-based and MCTS-based tree search."""

    def __init__(
        self,
        config: Optional[Any] = None,
        embedding_manager: Optional[EmbeddingManager] = None,
        vector_store_path: str = "./vector_index",
        book_id: str = "default",
    ):
        self.book_id = book_id
        self.config = config or self._default_config()
        self.embedding_manager = embedding_manager or EmbeddingManager()

        self.value_function = ValueFunction(
            embedding_manager=self.embedding_manager,
            top_k=self.config.top_k_nodes, 
            use_sqrt_normalization=self.config.use_square_root_normalization,
            vector_store_path=vector_store_path,
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

    def _default_config(self):
        """Default configuration."""
        from config import SearchConfig
        return SearchConfig()

    def index_tree(self, tree: DocumentTree, show_progress: bool = False) -> Dict[str, Any]:
        """Index a document tree for search."""
        with self._lock:
            self.tree = tree
            timing = self.value_function.index_tree(tree, show_progress)
            self._indexed = True

            return {
                "total_nodes": tree.get_node_count(),
                "total_indexed": timing.nodes_processed,
                "new_embeddings": timing.nodes_embedded,
                "loaded_from_store": timing.nodes_loaded_from_store,
                "indexing_time_ms": timing.total_time_ms,
            }

    def search(self, query: str, options: Optional[SearchOptions] = None) -> SearchResponse:
        """Perform hybrid search."""
        options = options or SearchOptions()
        start_time = time.time()

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
                "book_id": self.book_id,
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

        path_prefixes = Counter(
            "/".join(r.get("path", [])[:2]) if len(r.get("path", [])) >= 2 else r["node_id"]
            for r in candidates
        )

        for candidate in candidates:
            path = candidate.get("path", [])
            prefix = "/".join(path[:2]) if len(path) >= 2 else candidate["node_id"]
            candidate["diversity_score"] = 1.0 / path_prefixes[prefix]

        for candidate in candidates:
            candidate["combined_score"] = (
                options.value_weight * candidate["score"] +
                options.diversity_weight * candidate.get("diversity_score", 0.0)
            )

        candidates.sort(key=lambda x: x["combined_score"], reverse=True)
        return candidates[:options.max_results]

    def _search_value_only(self, query: str, options: SearchOptions) -> List[Dict[str, Any]]:
        """Perform value-based search only using embeddings."""
        results = []
        if not self.tree:
            return results

        nodes_to_evaluate = [
            node.id for node in self.tree.get_all_nodes()
            if not node.is_root and len(node.content) > 50
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
                })
                self._visited_nodes.add(node_id)

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:options.max_results]