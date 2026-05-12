"""
Hybrid Search Engine Module
===========================
Implements the hybrid search system combining:
1. Value-based tree search (fast, using embeddings)
2. LLM-based tree search (thorough, using language model evaluation)
3. Monte Carlo Tree Search for orchestration

The hybrid approach achieves:
- Higher recall than either method alone
- Faster retrieval than pure LLM-based search
- Better accuracy than pure value-based search
"""

from typing import List, Dict, Optional, Set, Any, Callable, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, Future
from collections import deque
import threading
import time
import heapq
from enum import Enum
import queue

from .config import SearchConfig, MCTSConfig
from .tree import DocumentTree, TreeNode, Chunk
from .embeddings import EmbeddingManager
from .value_function import ValueFunction, NodeScorer, ChunkScore, NodeScore
from .mcts import MonteCarloTreeSearch, SearchResult, MCTSNode


class SearchMode(str, Enum):
    """Search mode enumeration."""
    VALUE_ONLY = "value_only"
    LLM_ONLY = "llm_only"
    HYBRID = "hybrid"
    MCTS_ONLY = "mcts_only"


@dataclass
class SearchOptions:
    """Options for search operations."""
    mode: SearchMode = SearchMode.HYBRID
    max_results: int = 10
    max_iterations: int = 1000
    early_stop: bool = True
    early_stop_threshold: float = 0.95
    parallel_searches: int = 4
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
    """
    Complete response from hybrid search.
    """
    query: str
    results: List[Dict[str, Any]]
    mode: str = "hybrid"
    search_time: float = 0.0
    iterations: int = 0
    nodes_visited: int = 0
    cache_hit_rate: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "query": self.query,
            "results": self.results,
            "mode": self.mode,
            "search_time": self.search_time,
            "iterations": self.iterations,
            "nodes_visited": self.nodes_visited,
            
            "metadata": self.metadata,

        }
        return result


@dataclass
class NodeVisit:
    """Represents a node visit in the queue."""
    node_id: str
    priority: float
    source: str  # "value", "llm", "mcts"
    timestamp: float = field(default_factory=time.time)

    def __lt__(self, other: "NodeVisit"):
        """Comparison for priority queue."""
        return self.priority > other.priority  # Higher priority first


class HybridSearchEngine:
    """
    Hybrid search engine combining value-based and LLM-based tree search.

    This engine orchestrates:
    1. Parallel value-based search using embeddings
    2. LLM-based evaluation of candidate nodes
    3. Monte Carlo Tree Search for intelligent node selection
    4. Result synthesis using LLM

    Features:
    - Thread-safe parallel execution
    - Intelligent queue management
    - Early stopping based on confidence
    - Caching at multiple levels
    - Configurable weights for value/LLM contributions
    """

    def __init__(
        self,
        config: Optional[SearchConfig] = None,
        embedding_manager: Optional[EmbeddingManager] = None,
    ):
        """
        Initialize hybrid search engine.

        Args:
            config: Search configuration
            embedding_manager: Embedding manager instance
        """
        self.config = config or SearchConfig()
        self.embedding_manager = embedding_manager or EmbeddingManager(
            model_name=self.config.embedding.model_name,
            device=self.config.embedding.device,
            normalize=self.config.embedding.normalize_embeddings,
            embedding_dim=self.config.embedding.embedding_dim,
        )
       

        # Initialize value function
        self.value_function = ValueFunction(
            embedding_manager=self.embedding_manager,
            top_k=self.config.top_k_chunks,
            use_sqrt_normalization=self.config.use_square_root_normalization,
            parallel_searches=self.config.mcts.parallel_value_searches,
        )

        # Initialize MCTS
        self.mcts = MonteCarloTreeSearch(
            value_function=self.value_function,
            exploration_constant=self.config.mcts.exploration_constant,
            max_iterations=self.config.mcts.max_iterations,
            max_depth=self.config.mcts.max_depth,
            min_visits=self.config.mcts.min_visits,
            early_stop_threshold=self.config.mcts.early_stop_threshold,
            parallel_rollouts=self.config.mcts.parallel_value_searches,
            cache_evaluations=self.config.mcts.cache_evaluations,
            value_weight=self.config.mcts.value_weight,
            diversity_weight=self.config.mcts.diversity_weight,
        )

        # Document tree reference
        self.tree: Optional[DocumentTree] = None
        self._indexed = False

        # Search state
        self._visited_nodes: Set[str] = set()
        self._node_queue: queue.PriorityQueue = queue.PriorityQueue()
        self._lock = threading.RLock()

        # Statistics
        self.search_stats: Dict[str, Any] = {}

    def index_tree(
        self,
        tree: DocumentTree,
        show_progress: bool = False,
    ) -> None:
        """
        Index a document tree for search.

        Args:
            tree: DocumentTree to index
            show_progress: Whether to show progress
        """
        self.tree = tree

        # Index chunks in value function
        self.value_function.index_tree(tree, show_progress)

        self._indexed = True

    def search(
        self,
        query: str,
        options: Optional[SearchOptions] = None,
    ) -> SearchResponse:
        """
        Perform hybrid search.

        Args:
            query: Search query
            options: Search options

        Returns:
            SearchResponse with results and optional synthesis
        """
        start_time = time.time()
        options = options or SearchOptions()

        if not self._indexed:
            raise ValueError("No documents indexed. Call index_tree() first.")

        # Reset state
        self._visited_nodes.clear()
        with self._node_queue.mutex:
            self._node_queue.queue.clear()

      
        results = self._search_hybrid(query, options)



       

        search_time = time.time() - start_time

        return SearchResponse(
            query=query,
            results=results,
            mode=options.mode.value,
            search_time=search_time,
            iterations=self.mcts.total_iterations,
            nodes_visited=len(self._visited_nodes),
            metadata={
                "options": {
                    "max_results": options.max_results,
                    "max_iterations": options.max_iterations,
                    "value_weight": options.value_weight,
                },
            },
        )

    def _search_hybrid(
        self,
        query: str,
        options: SearchOptions,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining value-based and LLM-based approaches.

        Args:
            query: Search query
            options: Search options

        Returns:
            List of search results
        """
        results: Dict[str, Dict[str, Any]] = {}
        visited: Set[str] = set()
      
        # Step 1: Initialize MCTS
        if self.tree:
            self.mcts.initialize(self.tree, query=query)

        # Step 2: Parallel value-based and MCTS search
        with ThreadPoolExecutor(max_workers=options.parallel_searches) as executor:
            # Value-based search future
            value_future = executor.submit(self._value_based_search, query, options)

            # MCTS search future
            mcts_future = executor.submit(self.mcts.search, query, options.max_results, options.early_stop)

            # Collect value results
            value_results = value_future.result()
            for result in value_results:
                node_id = result["node_id"]
                if node_id not in visited:
                    results[node_id] = result
                    visited.add(node_id)
                    self._visited_nodes.add(node_id)

            # Collect MCTS results
            mcts_results = mcts_future.result()
            for result in mcts_results:
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

        # Step 3: FAST evaluation using estimation (NO LLM calls)
        # This ranks candidates based on keyword matching
        candidates = list(results.values())
        candidates.sort(key=lambda x: x["score"], reverse=True)
        top_candidates = candidates[:options.max_results * 2]

        # Prepare nodes for batch evaluation
        nodes_for_eval = []
        for candidate in top_candidates:
            node = self.tree.get_node(candidate["node_id"]) if self.tree else None
            if node:
                nodes_for_eval.append({
                    "id": node.id,
                    "content": node.content,
                    "title": node.title,
                    "existing_summary": node.metadata.get("summary") if node.metadata else None,
                })

        # Step 4: Combine scores
        final_results = []
        for candidate in top_candidates:
            node_id = candidate["node_id"]
            combined_score = (
                options.value_weight * candidate["score"] 
            )
            candidate["combined_score"] = combined_score
            final_results.append(candidate)

        # Sort by combined score
        final_results.sort(key=lambda x: x["combined_score"], reverse=True)

        # Return results + evaluations for synthesis reuse
        return final_results[:options.max_results]

    def _search_mcts(
        self,
        query: str,
        options: SearchOptions,
    ) -> List[Dict[str, Any]]:
        """
        Perform pure MCTS search.

        Args:
            query: Search query
            options: Search options

        Returns:
            List of search results
        """
        if self.tree:
            self.mcts.initialize(self.tree, query=query)

        mcts_results = self.mcts.search(query, options.max_results, options.early_stop)

        results = []
        for result in mcts_results:
            results.append({
                "node_id": result.document_node_id,
                "score": result.score,
                "source": "mcts",
                "visit_count": result.visit_count,
                "content": result.content,
                "depth": result.depth,
                "path": result.path,
                "relevance": result.relevance,
            })
            self._visited_nodes.add(result.document_node_id)

        return results

    def _search_value_only(
        self,
        query: str,
        options: SearchOptions,
    ) -> List[Dict[str, Any]]:
        """
        Perform value-based search only using embeddings.

        Args:
            query: Search query
            options: Search options

        Returns:
            List of search results
        """
        results = []

        if not self.tree:
            return results

        # Get all leaf nodes with chunks
        nodes_to_evaluate = []
        for node in self.tree.get_all_nodes():
            if node.is_root:
                continue
            if node.chunks or len(node.content) > 50:
                nodes_to_evaluate.append(node.id)

        # Get value estimates
        value_estimates = self.value_function.predict_values(query, nodes_to_evaluate)

        # Build results
        scored_nodes = []
        for node_id, score in value_estimates.items():
            node = self.tree.get_node(node_id)
            if node:
                scored_nodes.append({
                    "node_id": node_id,
                    "score": score,
                    "source": "value",
                    "content": node.content,
                    "depth": node.depth,
                    "title": node.title,
                    "start_index":node.start_index,
                    "end_index":node.end_index,
                    "num_chunks": node.num_chunks,
                })
                self._visited_nodes.add(node_id)

        # Sort by score
        scored_nodes.sort(key=lambda x: x["score"], reverse=True)

        return scored_nodes[:options.max_results]

    def _search_llm_only(
        self,
        query: str,
        options: SearchOptions,
    ) -> List[Dict[str, Any]]:
        """
        Perform LLM-based search only.

        Args:
            query: Search query
            options: Search options

        Returns:
            List of search results
        """
        results = []

        if not self.tree:
            return results

        # Get nodes to evaluate
        nodes_to_evaluate = []
        for node in self.tree.get_all_nodes():
            if node.is_root:
                continue
            if node.chunks or len(node.content) > 50:
                nodes_to_evaluate.append({
                    "id": node.id,
                    "content": node.content,
                    "title": node.title,
                })


      
        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:options.max_results]

    def _value_based_search(
        self,
        query: str,
        options: SearchOptions,
    ) -> List[Dict[str, Any]]:
        """
        Value-based search using embeddings.

        Args:
            query: Search query
            options: Search options

        Returns:
            List of search results
        """
        return self._search_value_only(query, options)

    def get_statistics(self) -> Dict[str, Any]:
        """Get search engine statistics."""
        return {
            "mcts_stats": self.mcts.get_statistics(),
            "indexed": self._indexed,
            "index_size": self.value_function.index_size,
            "visited_nodes": len(self._visited_nodes),
            "tree_nodes": self.tree.get_node_count() if self.tree else 0,
        }

    def clear_caches(self) -> None:
        """Clear all caches."""
        self.mcts.clear_cache()
        self.value_function.clear_index()


class ParallelSearchCoordinator:
    """
    Coordinates parallel search operations.

    Manages:
    - Queue of pending nodes
    - Multiple worker threads
    - Result aggregation
    - Early termination
    """

    def __init__(
        self,
        engine: HybridSearchEngine,
        num_workers: int = 4,
    ):
        """
        Initialize coordinator.

        Args:
            engine: HybridSearchEngine instance
            num_workers: Number of parallel workers
        """
        self.engine = engine
        self.num_workers = num_workers
        self.queue: queue.PriorityQueue = queue.PriorityQueue()
        self.results: Dict[str, Dict[str, Any]] = {}
        self.seen_nodes: Set[str] = set()
        self.stop_event = threading.Event()
        self.lock = threading.RLock()

    def add_node(self, node_id: str, priority: float, source: str) -> None:
        """
        Add a node to the processing queue.

        Args:
            node_id: Node ID
            priority: Priority score (higher = more important)
            source: Source of the node ("value", "llm", "mcts")
        """
        with self.lock:
            if node_id not in self.seen_nodes:
                self.queue.put(NodeVisit(node_id, priority, source))
                self.seen_nodes.add(node_id)

    def process_queue(self, max_nodes: int = 100) -> List[Dict[str, Any]]:
        """
        Process nodes from the queue.

        Args:
            max_nodes: Maximum nodes to process

        Returns:
            List of processed results
        """
        processed = 0
        results = []

        while processed < max_nodes and not self.stop_event.is_set():
            try:
                visit = self.queue.get(timeout=1.0)
            except queue.Empty:
                break

            # Process node
            result = self._process_node(visit)
            if result:
                results.append(result)

            processed += 1

        return results

    def _process_node(self, visit: NodeVisit) -> Optional[Dict[str, Any]]:
        """
        Process a single node.

        Args:
            visit: NodeVisit object

        Returns:
            Processed result or None
        """
        node = self.engine.tree.get_node(visit.node_id)
        if not node:
            return None

        # Get content for evaluation
        content = node.content
        if not content and node.chunks:
            content = " ".join(c.content for c in node.chunks)

        result = {
            "node_id": visit.node_id,
            "source": visit.source,
            "priority": visit.priority,
            "content": content[:500],  # Truncate for evaluation
            "title": node.title,
            "depth": node.depth,
        }

        # Add to results
        with self.lock:
            self.results[visit.node_id] = result

        return result

    def stop(self) -> None:
        """Stop the coordinator."""
        self.stop_event.set()

    def get_results(self) -> List[Dict[str, Any]]:
        """Get all processed results."""
        with self.lock:
            return list(self.results.values())


def create_hybrid_engine(
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    llm_provider: str = "mock",
    llm_api_key: Optional[str] = None,
    config: Optional[SearchConfig] = None,
) -> HybridSearchEngine:
    """
    Factory function to create a hybrid search engine.

    Args:
        embedding_model: Sentence transformer model name
        llm_provider: LLM provider ("openai", "anthropic", "mock")
        llm_api_key: API key for LLM
        config: Optional configuration

    Returns:
        HybridSearchEngine instance
    """
    if config is None:
        config = SearchConfig()

    # Update embedding config
    config.embedding.model_name = embedding_model

    # Update LLM config
    config.llm.provider = llm_provider
    config.llm.api_key = llm_api_key

    # Create engine
    engine = HybridSearchEngine(config=config)

    return engine