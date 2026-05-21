"""
Monte Carlo Tree Search Module
===============================
Implements the MCTS algorithm for optimal document retrieval.
Uses Upper Confidence Bound (UCB) for node selection and
value-based rollouts for evaluation.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import math
import random
import time
import numpy as np


class NodeState(str, Enum):
    """State of an MCTS node."""
    UNVISITED = "unvisited"
    EXPANDED = "expanded"


@dataclass
class MCTSNode:
    """Represents a node in the Monte Carlo Tree Search tree."""
    id: str
    document_node_id: str
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    depth: int = 0

    visit_count: int = 0
    total_value: float = 0.0
    prior_probability: float = 0.0
    state: NodeState = NodeState.UNVISITED

    @property
    def mean_value(self) -> float:
        """Get the mean value from rollouts."""
        if self.visit_count == 0:
            return self.prior_probability
        return self.total_value / self.visit_count

    def update(self, value: float) -> None:
        """Update node with a new value observation."""
        self.visit_count += 1
        self.total_value += value

    def get_uct_score(
        self,
        parent_visits: int,
        exploration_constant: float = 1.414,
    ) -> float:
        """Calculate UCT (Upper Confidence bound for Trees) score."""
        if self.visit_count == 0:
            return float('inf')

        exploitation = self.mean_value
        exploration = exploration_constant * math.sqrt(
            math.log(parent_visits) / self.visit_count
        )
        return exploitation + exploration


@dataclass
class SearchResult:
    """Represents a search result from MCTS."""
    node_id: str
    document_node_id: str
    score: float
    visit_count: int
    path: List[str]
    content: str
    depth: int
    source: str = "mcts"
    relevance: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MonteCarloTreeSearch:
    """Monte Carlo Tree Search implementation for document retrieval."""

    def __init__(
        self,
        value_function,
        exploration_constant: float = 1.414,
        max_iterations: int = 1000,
        max_depth: int = 10,
        min_visits: int = 5,
        early_stop_threshold: float = 0.95,
        value_weight: float = 0.4,
        diversity_weight: float = 0.2,
    ):
        self.value_function = value_function
        self.exploration_constant = exploration_constant
        self.max_iterations = max_iterations
        self.max_depth = max_depth
        self.min_visits = min_visits
        self.early_stop_threshold = early_stop_threshold
        self.value_weight = value_weight
        self.diversity_weight = diversity_weight

        self.nodes: Dict[str, MCTSNode] = {}
        self.root_id: Optional[str] = None
        self.document_tree: Optional[Any] = None
        self._doc_to_mcts: Dict[str, str] = {}

        self.total_iterations = 0
        self._best_score: float = 0.0
        self._best_node_id: Optional[str] = None

        self._query_embedding: Optional[np.ndarray] = None
        self._cached_query: Optional[str] = None

    def initialize(
        self,
        document_tree,
        root_node_id: Optional[str] = None,
        query: Optional[str] = None,
    ) -> str:
        """Initialize MCTS with document tree."""
        self.document_tree = document_tree

        if root_node_id is None:
            root_node_id = document_tree.root_id

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
        self._doc_to_mcts = {root_node_id: root_mcts.id}

        self._expand_node(root_mcts.id)

        if query:
            self._initialize_priors(query)

        return root_mcts.id

    def _expand_node(self, node_id: str) -> None:
        """Expand a node with its children from the document tree."""
        mcts_node = self.nodes.get(node_id)
        if not mcts_node:
            return

        doc_node = self.document_tree.get_node(mcts_node.document_node_id)
        if not doc_node:
            return

        for child_doc_id in doc_node.children_ids:
            child_doc = self.document_tree.get_node(child_doc_id)
            if not child_doc:
                continue

            child_mcts_id = self._doc_to_mcts.get(child_doc_id)
            if not child_mcts_id:
                child_mcts = MCTSNode(
                    id=f"mcts_{child_doc_id}",
                    document_node_id=child_doc_id,
                    parent_id=node_id,
                    depth=mcts_node.depth + 1,
                    state=NodeState.UNVISITED,
                )
                self.nodes[child_mcts.id] = child_mcts
                self._doc_to_mcts[child_doc_id] = child_mcts.id
                child_mcts_id = child_mcts.id

            if child_mcts_id not in mcts_node.children_ids:
                mcts_node.children_ids.append(child_mcts_id)

        mcts_node.state = NodeState.EXPANDED

    def _initialize_priors(self, query: str) -> None:
        """Initialize prior probabilities using value function."""
        # FIXED: Get all document node IDs (not MCTS node IDs)
        doc_node_ids = list(self._doc_to_mcts.keys())

        # Remove root if present
        if self.document_tree and self.document_tree.root_id in doc_node_ids:
            doc_node_ids.remove(self.document_tree.root_id)

        if not doc_node_ids:
            return

        # FIXED: Cache query embedding for reuse
        self._cached_query = query
        self._query_embedding = self.value_function.embedding_manager.encode_query(query)
        if self._query_embedding.ndim == 2:
            self._query_embedding = self._query_embedding[0]

        value_estimates = self.value_function.predict_values(
            query, doc_node_ids, query_embedding=self._query_embedding
        )

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
        """Perform MCTS search."""
        if not self.root_id:
            raise ValueError("MCTS not initialized. Call initialize() first.")

        start_time = time.time()
        self.total_iterations = 0
        self._best_score = 0.0
        self._best_node_id = None

        # FIXED: Cache query embedding once for the entire search
        self._cached_query = query
        self._query_embedding = self.value_function.embedding_manager.encode_query(query)
        if self._query_embedding.ndim == 2:
            self._query_embedding = self._query_embedding[0]

        for iteration in range(self.max_iterations):
            path = self._select(self.root_id)

            leaf_id = path[-1]
            if self.nodes[leaf_id].state == NodeState.UNVISITED:
                self._expand_node(leaf_id)

            reward = self._rollout(leaf_id, query)
            self._backpropagate(path, reward)
            self._update_best()

            self.total_iterations += 1

            # FIXED: Early stop checks best NODE visits, not root visits
            if early_stop and self._best_score >= self.early_stop_threshold:
                if self._best_node_id and self.nodes[self._best_node_id].visit_count >= self.min_visits:
                    break

            if time.time() - start_time > 60:
                break

        return self._extract_results(query, max_results)

    def _select(self, node_id: str) -> List[str]:
        """Select path from node to leaf using UCB."""
        path = [node_id]
        current = self.nodes[node_id]

        while current.state == NodeState.EXPANDED and current.children_ids:
            best_child = self._select_best_child(current.id)
            if best_child is None:
                break
            path.append(best_child)
            current = self.nodes[best_child]

        return path

    def _select_best_child(self, node_id: str) -> Optional[str]:
        """Select best child using UCB1/UCT with prior probability."""
        node = self.nodes[node_id]
        if not node.children_ids:
            return None

        parent_visits = node.visit_count or 1
        best_score = float('-inf')
        best_child = None

        for child_id in node.children_ids:
            child = self.nodes[child_id]

            if child.visit_count == 0:
                # Use prior for unvisited nodes, with slight exploration bonus
                score = child.prior_probability * (1.0 + 0.5 / (parent_visits + 1))
            else:
                score = child.get_uct_score(parent_visits, self.exploration_constant)

            if score > best_score:
                best_score = score
                best_child = child_id

        return best_child

    def _rollout(self, node_id: str, query: str) -> float:
        """Perform rollout from node with depth limit."""
        node = self.nodes[node_id]
        current_depth = node.depth
        max_rollout_depth = min(current_depth + 5, self.max_depth)
        current_node_id = node_id

        while current_depth < max_rollout_depth:
            current_node = self.nodes[current_node_id]
            if not current_node.children_ids:
                break

            # FIXED: Use UCT-like selection during rollout too, not just priors
            # This makes rollouts adaptive based on visit statistics
            candidates = []
            for child_id in current_node.children_ids:
                child = self.nodes[child_id]
                if child.visit_count == 0:
                    # Unvisited: use prior with small randomization
                    score = child.prior_probability + random.random() * 0.1
                else:
                    # Visited: blend prior with empirical mean
                    score = (
                        0.3 * child.prior_probability +
                        0.7 * child.mean_value +
                        random.random() * 0.05  # small noise for exploration
                    )
                candidates.append((child_id, score))

            candidates.sort(key=lambda x: x[1], reverse=True)
            top_candidates = candidates[:3]

            if not top_candidates:
                break

            weights = [max(c[1], 0.01) for c in top_candidates]
            total = sum(weights)

            if total <= 0:
                selected_id = random.choice([c[0] for c in top_candidates])
            else:
                weights = [w / total for w in weights]
                selected_id = random.choices([c[0] for c in top_candidates], weights=weights)[0]

            current_node_id = selected_id
            current_depth += 1

        final_node = self.nodes[current_node_id]
        doc_node = self.document_tree.get_node(final_node.document_node_id)

        if doc_node:
            return self._evaluate_node(final_node.document_node_id, query)
        return 0.5

    def _evaluate_node(self, doc_node_id: str, query: str) -> float:
        """Evaluate a node's relevance to the query using embedding."""
        # FIXED: Pass cached query embedding to avoid re-encoding
        values = self.value_function.predict_values(
            query, [doc_node_id], query_embedding=self._query_embedding
        )
        return values.get(doc_node_id, 0.5)

    def _backpropagate(self, path: List[str], reward: float) -> None:
        """Backpropagate reward through the path."""
        for node_id in reversed(path):
            node = self.nodes[node_id]
            node.update(reward)
            reward *= 0.95

    def _update_best(self) -> None:
        """Update the best node found so far."""
        if not self.root_id:
            return

        root = self.nodes[self.root_id]
        if root.visit_count < self.min_visits:
            return

        best_value = -float('inf')
        best_node = None

        for node in self.nodes.values():
            if node.visit_count >= self.min_visits:
                value = node.mean_value
                if value > best_value:
                    best_value = value
                    best_node = node

        if best_value > self._best_score:
            self._best_score = best_value
            self._best_node_id = best_node.id if best_node else None

    def _extract_results(self, query: str, max_results: int) -> List[SearchResult]:
        """Extract final results from the search tree."""
        results = []
        scored_nodes = []

        for node in self.nodes.values():
            if node.id == self.root_id or node.visit_count == 0:
                continue

            # FIXED: Better scoring - use mean_value directly with visit confidence
            visit_confidence = min(node.visit_count / self.min_visits, 1.0)
            score = (
                self.value_weight * node.mean_value +
                self.diversity_weight * visit_confidence
            )
            scored_nodes.append((score, node))

        scored_nodes.sort(key=lambda x: x[0], reverse=True)

        for score, node in scored_nodes[:max_results]:
            doc_node = self.document_tree.get_node(node.document_node_id)
            if not doc_node:
                continue

            result = SearchResult(
                node_id=node.id,
                document_node_id=node.document_node_id,
                score=score,
                visit_count=node.visit_count,
                path=self._build_path(node.id),
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

    def get_statistics(self) -> Dict[str, Any]:
        """Get MCTS statistics."""
        return {
            "total_iterations": self.total_iterations,
            "total_nodes": len(self.nodes),
            "best_score": self._best_score,
            "root_visits": self.nodes[self.root_id].visit_count if self.root_id else 0,
        }

    def clear_cache(self) -> None:
        """Clear MCTS cache and reset state."""
        self.nodes.clear()
        self._doc_to_mcts.clear()
        self.root_id = None
        self.document_tree = None
        self._best_score = 0.0
        self._best_node_id = None
        self.total_iterations = 0
        self._query_embedding = None
        self._cached_query = None