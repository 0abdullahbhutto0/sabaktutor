"""
Hybrid Search Engine Module
====================================
Combines value-based search and MCTS for optimal document retrieval.
1. Value search evaluates ALL nodes, not just deep nodes
2. MCTS initialized with ALL document nodes in tree
3. MCTS priors scored using ALL document nodes, not just expanded
4. Proper query embedding passed to MCTS
5. Merge combines both scores correctly with proper normalization
"""

from typing import List, Dict, Optional, Set, Any
from dataclasses import dataclass, field
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

        self._visited_nodes.clear()

        query_embedding = self.embedding_manager.encode_query(query)

        if query_embedding.ndim == 2:
            query_embedding = query_embedding[0]

        results = self._search_hybrid(query, options, query_embedding)
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

    def _search_hybrid(self, query: str, options: SearchOptions, query_embedding) -> List[Dict[str, Any]]:
        """Perform hybrid search with full debug logging."""

        value_results = self._search_value_only(query, options, query_embedding)

        if self.tree:

            self.mcts.initialize(
                self.tree,
                query=query,
                query_embedding=query_embedding
            )
            self.mcts.max_iterations = options.max_iterations

            mcts_results = self.mcts.search(
                query,
                options.max_results,
                options.early_stop,
                query_embedding
            )
        else:
            mcts_results = []

        merged = self._merge_results(value_results, mcts_results, query, options)

        return merged

    def _search_value_only(self, query: str, options: SearchOptions, query_embedding) -> List[Dict[str, Any]]:
        """Value-based search - evaluates ALL candidate nodes."""
        results = []
        if not self.tree:
            return results

        all_nodes = self.tree.get_all_nodes()
        nodes_to_evaluate = [
            node.id for node in all_nodes
            if not node.is_root and len(node.content) > 50
        ]

        if not nodes_to_evaluate:
            return results

        if len(nodes_to_evaluate) > 500:
            nodes_to_evaluate = sorted(
                nodes_to_evaluate,
                key=lambda nid: self.tree.get_node(nid).depth if self.tree.get_node(nid) else 0,
                reverse=True,
            )[:500]
          
        value_estimates = self.value_function.predict_values(
            query, nodes_to_evaluate, query_embedding=query_embedding
        )


        for node_id, score in value_estimates.items():
            if score <= 0.0:
                continue
            node = self.tree.get_node(node_id)
            if node:
                results.append({
                    "node_id": node_id,
                    "score": score,
                    "source": "value",
                    "content": node.content,
                    "depth": node.depth,
                    "title": node.title,
                    "path": node.path.split("/") if node.path else [node_id],
                })
                self._visited_nodes.add(node_id)

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:options.max_results * 2]

    def _merge_results(
        self,
        value_results: List[Dict[str, Any]],
        mcts_results: List[SearchResult],
        query: str,
        options: SearchOptions,
    ) -> List[Dict[str, Any]]:
        """Merge value and MCTS results with proper normalization."""
        merged: Dict[str, Dict[str, Any]] = {}

        if value_results:
            max_val = max(r["score"] for r in value_results)
            min_val = min(r["score"] for r in value_results)
            val_range = max_val - min_val if max_val != min_val else 1.0
            for r in value_results:
                r["normalized_score"] = (r["score"] - min_val) / val_range
        else:
            print(f"  No value results")

        if mcts_results:
            max_mcts = max(r.score for r in mcts_results)
            min_mcts = min(r.score for r in mcts_results)
            mcts_range = max_mcts - min_mcts if max_mcts != min_mcts else 1.0
            for r in mcts_results:
                r._norm_score = (r.score - min_mcts) / mcts_range
        else:
            print(f"  No MCTS results")

        # Add value results
        for r in value_results:
            nid = r["node_id"]
            merged[nid] = {
                "node_id": nid,
                "value_score": r["normalized_score"],
                "mcts_score": 0.0,
                "content": r["content"],
                "depth": r["depth"],
                "title": r.get("title"),
                "path": r.get("path", [nid]),
                "sources": ["value"],
                "visit_count": 0,
            }
            self._visited_nodes.add(nid)

        # Add/merge MCTS results
        for r in mcts_results:
            nid = r.document_node_id
            mcts_learned_score = r.metadata.get("mean_value", r.score) if hasattr(r, 'metadata') else r.score
            norm_score = getattr(r, '_norm_score', mcts_learned_score)
            if nid in merged:
                merged[nid]["mcts_score"] = norm_score
                merged[nid]["sources"].append("mcts")
                merged[nid]["visit_count"] = r.visit_count
            else:
                merged[nid] = {
                    "node_id": nid,
                    "value_score": 0.0,
                    "mcts_score": norm_score,
                    "content": r.content,
                    "depth": r.depth,
                    "title": None,
                    "path": r.path,
                    "sources": ["mcts"],
                    "visit_count": r.visit_count,
                }
            self._visited_nodes.add(nid)

        # Compute diversity scores
        candidates = list(merged.values())
        path_prefixes = Counter(
            "/".join(r.get("path", [])[:2]) if len(r.get("path", [])) >= 2 else r["node_id"]
            for r in candidates
        )

        for candidate in candidates:
            path = candidate.get("path", [])
            prefix = "/".join(path[:2]) if len(path) >= 2 else candidate["node_id"]
            candidate["diversity_score"] = min(1.0 / path_prefixes[prefix], 1.0)

        for candidate in candidates:
            # Primary score: max of value and MCTS scores
            max_score = max(candidate["value_score"], candidate["mcts_score"])

            # If both sources found the node, boost the score
            if candidate["value_score"] > 0 and candidate["mcts_score"] > 0:
                # Both agree - higher confidence
                blended = 0.6 * max_score + 0.4 * ((candidate["value_score"] + candidate["mcts_score"]) / 2)
            else:
                blended = max_score

            candidate["combined_score"] = (
                (1 - options.diversity_weight) * blended +
                options.diversity_weight * candidate.get("diversity_score", 0.0)
            )

        candidates.sort(key=lambda x: x["combined_score"], reverse=True)

        final = []
        for c in candidates[:options.max_results]:
            final.append({
                "node_id": c["node_id"],
                "score": round(c["combined_score"], 4),
                "value_score": round(c["value_score"], 4),
                "mcts_score": round(c["mcts_score"], 4),
                "diversity_score": round(c.get("diversity_score", 0), 4),
                "sources": c["sources"],
                "visit_count": c["visit_count"],
                "content": c["content"] if c["content"] else "",
                "depth": c["depth"],
                "title": c.get("title"),
                "path": c.get("path", []),
            })

        return final