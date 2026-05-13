"""
Monte Carlo Tree Search Module
===============================
Implements the MCTS algorithm for optimal document retrieval.
Uses Upper Confidence Bound (UCB) for node selection and
value-based rollouts for evaluation.
"""

from typing import List, Dict, Optional, Set, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import math
import random
import threading
from collections import defaultdict
import heapq
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


class NodeState(str, Enum):
    """State of an MCTS node."""
    UNVISITED = "unvisited"
    EXPANDED = "expanded"
    TERMINAL = "terminal"


@dataclass
class MCTSNode:
    """
    Represents a node in the Monte Carlo Tree Search tree.

    Each MCTS node wraps a document tree node and maintains:
    - Visit statistics for UCB calculation
    - Value estimates from rollouts
    - Prior probability from value function
    """
    id: str
    document_node_id: str  # ID in the document tree
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    depth: int = 0

    # Statistics
    visit_count: int = 0
    total_value: float = 0.0
    prior_probability: float = 0.0

    # State
    state: NodeState = NodeState.UNVISITED

    # Rollout statistics
    rollout_rewards: List[float] = field(default_factory=list)
    rollout_count: int = 0

    # Cached values
    cached_ucb: Optional[float] = None
    last_ucb_update: float = 0.0

    # LLM evaluation results
    llm_relevance: Optional[float] = None
    llm_summary: Optional[str] = None

    def __post_init__(self):
        """Ensure unique ID generation."""
        if not self.id:
            import uuid
            self.id = str(uuid.uuid4())

    @property
    def mean_value(self) -> float:
        """Get the mean value from rollouts."""
        if self.visit_count == 0:
            return self.prior_probability
        return self.total_value / self.visit_count

    @property
    def q_value(self) -> float:
        """Get Q-value for UCB calculation."""
        return self.mean_value

    def update(self, value: float) -> None:
        """Update node with a new value observation."""
        self.visit_count += 1
        self.total_value += value
        self.cached_ucb = None  # Invalidate cache

    def get_ucb_score(self, exploration_constant: float = 1.414) -> float:
        """
        Calculate Upper Confidence Bound score.

        UCB = Q + c * sqrt(ln(N_parent) / N_node)

        Args:
            exploration_constant: Exploration constant (typically sqrt(2))

        Returns:
            UCB score
        """
        if self.cached_ucb is not None:
            return self.cached_ucb

        # Parent visit count (use 1 if unvisited)
        parent_visits = max(1, self.visit_count)

        # UCB formula with exploration
        exploration = exploration_constant * math.sqrt(
            math.log(parent_visits + 1) / (self.visit_count + 1)
        )

        ucb = self.mean_value + exploration
        self.cached_ucb = ucb
        self.last_ucb_update = time.time()

        return ucb

    def get_uct_score(
        self,
        parent_visits: int,
        exploration_constant: float = 1.414,
    ) -> float:
        """
        Calculate UCT (Upper Confidence bound for Trees) score.

        This is used during selection phase.

        Args:
            parent_visits: Visit count of parent node
            exploration_constant: Exploration constant

        Returns:
            UCT score
        """
        if self.visit_count == 0:
            # Unvisited nodes get high exploration bonus
            return float('inf')

        exploitation = self.mean_value
        exploration = exploration_constant * math.sqrt(
            math.log(parent_visits) / self.visit_count
        )

        return exploitation + exploration

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "document_node_id": self.document_node_id,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "depth": self.depth,
            "visit_count": self.visit_count,
            "total_value": self.total_value,
            "mean_value": self.mean_value,
            "prior_probability": self.prior_probability,
            "state": self.state.value,
            "rollout_count": self.rollout_count,
            "llm_relevance": self.llm_relevance,
        }


@dataclass
class SearchResult:
    """
    Represents a search result from MCTS.
    """
    node_id: str
    document_node_id: str
    score: float
    visit_count: int
    path: List[str]  # Path of node IDs from root
    content: str
    depth: int
    source: str = "mcts"  # "mcts" or "value_based"
    relevance: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "document_node_id": self.document_node_id,
            "score": self.score,
            "visit_count": self.visit_count,
            "path": self.path,
            "content": self.content,
            "depth": self.depth,
            "source": self.source,
            "relevance": self.relevance,
            "metadata": self.metadata,
        }


@dataclass
class RolloutResult:
    """Result from a single rollout."""
    path: List[str]  # Node IDs visited during rollout
    reward: float  # Final reward
    depth_reached: int
    nodes_visited: int


class MonteCarloTreeSearch:
    """
    Monte Carlo Tree Search implementation for document retrieval.

    This implementation uses:
    - UCB1 for node selection
    - Value-based prior probabilities from embedding similarity
    - Rollout-based evaluation using value function
    - Parallel execution for performance
    """

    def __init__(
        self,
        value_function,
        exploration_constant: float = 1.414,
        max_iterations: int = 1000,
        max_depth: int = 10,
        min_visits: int = 5,
        early_stop_threshold: float = 0.95,
        parallel_rollouts: int = 4,
        cache_evaluations: bool = True,
        value_weight: float = 0.4,
        diversity_weight: float = 0.2,
    ):
        """
        Initialize MCTS.

        Args:
            value_function: ValueFunction instance for scoring
            exploration_constant: UCB exploration constant
            max_iterations: Maximum MCTS iterations
            max_depth: Maximum tree depth
            min_visits: Minimum visits before considering node for selection
            early_stop_threshold: Stop early if confidence is high
            parallel_rollouts: Number of parallel rollouts
            cache_evaluations: Whether to cache evaluations
            value_weight: Weight for value-based scores
            diversity_weight: Weight for diversity bonus
        """
        self.value_function = value_function
        self.exploration_constant = exploration_constant
        self.max_iterations = max_iterations
        self.max_depth = max_depth
        self.min_visits = min_visits
        self.early_stop_threshold = early_stop_threshold
        self.parallel_rollouts = parallel_rollouts
        self.cache_evaluations = cache_evaluations
        self.value_weight = value_weight
        self.diversity_weight = diversity_weight

        # Tree state
        self.nodes: Dict[str, MCTSNode] = {}
        self.root_id: Optional[str] = None
        self.document_tree: Optional[Any] = None

        # Evaluation cache
        self._evaluation_cache: Dict[str, float] = {}
        self._cache_lock = threading.RLock()

        # Statistics
        self.total_iterations = 0
        self.iteration_times: List[float] = []

        # Best node tracking
        self._best_node_id: Optional[str] = None
        self._best_score: float = 0.0

    def initialize(
        self,
        document_tree,
        root_node_id: Optional[str] = None,
        query: Optional[str] = None,
    ) -> str:
        """
        Initialize MCTS with document tree.

        Args:
            document_tree: DocumentTree instance
            root_node_id: ID of root node (uses tree root if None)
            query: Optional query for initial value estimation

        Returns:
            ID of the root MCTS node
        """
        self.document_tree = document_tree

        if root_node_id is None:
            root_node_id = document_tree.root_id

        # Create MCTS root
        root_mcts = MCTSNode(
            id=f"mcts_root_{root_node_id}",
            document_node_id=root_node_id,
            parent_id=None,
            depth=0,
            state=NodeState.EXPANDED,
            prior_probability=1.0,
        )

        self.nodes = {root_mcts.id: root_mcts}
        self.root_id = root_mcts.id

        # Expand root with children
        self._expand_node(root_mcts.id)

        # Initialize prior probabilities if query provided
        if query:
            self._initialize_priors(query)

        return root_mcts.id

    def _expand_node(self, node_id: str) -> None:
        """
        Expand a node with its children from the document tree.

        Args:
            node_id: MCTS node ID to expand
        """
        mcts_node = self.nodes.get(node_id)
        if not mcts_node:
            return

        doc_node = self.document_tree.get_node(mcts_node.document_node_id)
        if not doc_node:
            return

        # Get children from document tree
        for child_doc_id in doc_node.children_ids:
            child_doc = self.document_tree.get_node(child_doc_id)
            if not child_doc:
                continue

            # Check if child already exists
            existing = self._get_node_by_doc_id(child_doc_id)
            if existing:
                child_mcts_id = existing
            else:
                # Create new MCTS node
                child_mcts = MCTSNode(
                    id=f"mcts_{child_doc_id}",
                    document_node_id=child_doc_id,
                    parent_id=node_id,
                    depth=mcts_node.depth + 1,
                    state=NodeState.UNVISITED,
                )
                self.nodes[child_mcts.id] = child_mcts
                child_mcts_id = child_mcts.id

            # Add to parent's children
            if child_mcts_id not in mcts_node.children_ids:
                mcts_node.children_ids.append(child_mcts_id)

        mcts_node.state = NodeState.EXPANDED

    def _get_node_by_doc_id(self, doc_id: str) -> Optional[str]:
        """Get MCTS node ID by document node ID."""
        for mcts_id, node in self.nodes.items():
            if node.document_node_id == doc_id:
                return mcts_id
        return None

    def _initialize_priors(self, query: str) -> None:
        """
        Initialize prior probabilities using value function.

        Args:
            query: Search query
        """
        # Get all document node IDs
        doc_node_ids = [
            node.document_node_id
            for node in self.nodes.values()
            if not node.document_node_id.startswith("mcts_")
        ]

        # Get value estimates
        value_estimates = self.value_function.predict_values(query, doc_node_ids)

        # Update prior probabilities
        for mcts_node in self.nodes.values():
            doc_id = mcts_node.document_node_id
            if doc_id in value_estimates:
                mcts_node.prior_probability = value_estimates[doc_id]

    def search(
        self,
        query: str,
        max_results: int = 10,
        early_stop: bool = True,
    ) -> List[SearchResult]:
        """
        Perform MCTS search.

        Args:
            query: Search query
            max_results: Maximum number of results
            early_stop: Whether to stop early on high confidence

        Returns:
            List of SearchResult objects
        """
        if not self.root_id:
            raise ValueError("MCTS not initialized. Call initialize() first.")

        start_time = time.time()
        self.total_iterations = 0

        # Reset best tracking
        self._best_node_id = None
        self._best_score = 0.0

        for iteration in range(self.max_iterations):
            iter_start = time.time()

            # Selection: traverse tree using UCB
            path = self._select(self.root_id)

            # Expansion: expand if not fully expanded
            leaf_id = path[-1]
            if self.nodes[leaf_id].state == NodeState.UNVISITED:
                self._expand_node(leaf_id)

            # Simulation: perform rollout
            reward = self._rollout(leaf_id, query)

            # Backpropagation: update path statistics
            self._backpropagate(path, reward)

            # Update best
            self._update_best()

            self.total_iterations += 1
            self.iteration_times.append(time.time() - iter_start)

            # Early stopping
            if early_stop and self._best_score >= self.early_stop_threshold:
                if self.nodes[self.root_id].visit_count >= self.min_visits:
                    break

            # Check iteration time
            if time.time() - start_time > 60:  # 60 second timeout
                break

        # Extract results
        results = self._extract_results(query, max_results)

        return results

    def _select(self, node_id: str) -> List[str]:
        """
        Select path from node to leaf using UCB.

        Args:
            node_id: Starting node ID

        Returns:
            List of node IDs forming the path
        """
        path = [node_id]
        current = self.nodes[node_id]

        while current.state == NodeState.EXPANDED and current.children_ids:
            # Get best child by UCT
            best_child = self._select_best_child(current.id)
            if best_child is None:
                break

            path.append(best_child)
            current = self.nodes[best_child]

        return path

    def _select_best_child(self, node_id: str) -> Optional[str]:
        """
        Select best child using UCB1/UCT with prior probability.

        Selection strategy:
        - Unvisited: use prior_probability (from value function) as score
        - Visited: use UCT with exploitation + exploration

        Args:
            node_id: Parent node ID

        Returns:
            Best child node ID
        """
        node = self.nodes[node_id]
        if not node.children_ids:
            return None

        parent_visits = node.visit_count or 1

        best_score = float('-inf')
        best_child = None

        for child_id in node.children_ids:
            child = self.nodes[child_id]

            # Selection based on visit count
            if child.visit_count == 0:
                # Unvisited: use prior probability as primary score
                # Add small exploration bonus based on prior
                score = child.prior_probability + child.prior_probability * 0.5
            else:
                # Visited: UCT score with exploitation from mean_value
                score = child.get_uct_score(parent_visits, self.exploration_constant)

            if score > best_score:
                best_score = score
                best_child = child_id

        return best_child

    def _rollout(self, node_id: str, query: str) -> float:
        """
        Perform rollout from node.

        Args:
            node_id: Starting node ID
            query: Search query

        Returns:
            Rollout reward
        """
        node = self.nodes[node_id]
        depth = node.depth
        max_rollout_depth = min(depth + 5, self.max_depth)

        # Get candidate children
        if not node.children_ids:
            return node.prior_probability

        # Sample based on prior probabilities (not random)
        candidates = []
        for child_id in node.children_ids:
            child = self.nodes[child_id]
            candidates.append((child_id, child.prior_probability))

        # Sort by probability and pick top
        candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = candidates[:3]

        # Weighted random selection
        if top_candidates:
            weights = [c[1] for c in top_candidates]
            total = sum(weights)

            # Handle case where all weights are 0
            if total <= 0:
                # Fall back to uniform random selection
                selected_id = random.choice([c[0] for c in top_candidates])
            else:
                weights = [w / total for w in weights]
                selected_id = random.choices([c[0] for c in top_candidates], weights=weights)[0]

            # Get value estimate for selected child
            selected_node = self.nodes[selected_id]
            doc_node = self.document_tree.get_node(selected_node.document_node_id)

            if doc_node:
                # Calculate reward based on content relevance
                # This is a simplified evaluation
                reward = self._evaluate_node(selected_node.document_node_id, query)
            else:
                reward = 0.5

            return reward

        return node.prior_probability

    def _evaluate_node(self, doc_node_id: str, query: str) -> float:
        """
        Evaluate a node's relevance to the query.

        Args:
            doc_node_id: Document node ID
            query: Search query

        Returns:
            Relevance score [0, 1]
        """
        # Check cache
        cache_key = f"{doc_node_id}:{query}"
        if self.cache_evaluations:
            with self._cache_lock:
                if cache_key in self._evaluation_cache:
                    return self._evaluation_cache[cache_key]

        # Get value estimate
        values = self.value_function.predict_values(query, [doc_node_id])
        score = values.get(doc_node_id, 0.5)

        # Cache result
        if self.cache_evaluations:
            with self._cache_lock:
                self._evaluation_cache[cache_key] = score

        return score

    def _backpropagate(self, path: List[str], reward: float) -> None:
        """
        Backpropagate reward through the path.

        Args:
            path: Node IDs from root to leaf
            reward: Rollout reward
        """
        for node_id in reversed(path):
            node = self.nodes[node_id]
            node.update(reward)

            # Discount reward for depth
            reward *= 0.95

    def _update_best(self) -> None:
        """Update the best node found so far."""
        if not self.root_id:
            return

        root = self.nodes[self.root_id]
        if root.visit_count < self.min_visits:
            return

        # Find node with highest mean value among visited
        best = None
        best_value = -float('inf')

        for node in self.nodes.values():
            if node.visit_count >= self.min_visits:
                value = node.mean_value
                if value > best_value:
                    best_value = value
                    best = node

        if best:
            self._best_node_id = best.id
            self._best_score = best_value

    def _extract_results(
        self,
        query: str,
        max_results: int,
    ) -> List[SearchResult]:
        """
        Extract final results from the search tree.

        Args:
            query: Search query
            max_results: Maximum results

        Returns:
            List of SearchResult
        """
        results = []

        # Get all nodes sorted by visit count and mean value
        scored_nodes = []
        for node in self.nodes.values():
            if node.id == self.root_id:
                continue  # Skip root
            if node.visit_count == 0:
                continue

            # Combined score
            score = (
                self.value_weight * node.mean_value +
                self.diversity_weight * min(node.visit_count / 10.0, 1.0)
            )

            scored_nodes.append((score, node))

        # Sort by score
        scored_nodes.sort(key=lambda x: x[0], reverse=True)

        # Build results
        for score, node in scored_nodes[:max_results]:
            doc_node = self.document_tree.get_node(node.document_node_id)
            if not doc_node:
                continue

            # Build path
            path = self._build_path(node.id)

            result = SearchResult(
                node_id=node.id,
                document_node_id=node.document_node_id,
                score=score,
                visit_count=node.visit_count,
                path=path,
                content=doc_node.content,
                depth=node.depth,
                source="mcts",
                relevance=node.mean_value,
                metadata={
                    "prior_probability": node.prior_probability,
                    "mean_value": node.mean_value,
                    "total_value": node.total_value,
                },
            )
            results.append(result)

        return results

    def _build_path(self, node_id: str) -> List[str]:
        """Build path from root to node."""
        path = []
        current = self.nodes.get(node_id)
        while current:
            path.append(current.id)
            if current.parent_id:
                current = self.nodes.get(current.parent_id)
            else:
                break
        return list(reversed(path))

    def get_best_node(self) -> Optional[MCTSNode]:
        """Get the best node found."""
        if self._best_node_id:
            return self.nodes.get(self._best_node_id)
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get MCTS statistics."""
        return {
            "total_iterations": self.total_iterations,
            "total_nodes": len(self.nodes),
            "best_score": self._best_score,
            "root_visits": self.nodes[self.root_id].visit_count if self.root_id else 0,
            "avg_iteration_time": sum(self.iteration_times) / len(self.iteration_times) if self.iteration_times else 0,
            "iteration_times": self.iteration_times,
        }

    def clear_cache(self) -> None:
        """Clear evaluation cache."""
        with self._cache_lock:
            self._evaluation_cache.clear()