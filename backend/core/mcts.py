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
        max_depth: int = 100,
        min_visits: int = 3,
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
        self._best_doc_id: Optional[str] = None

        self._query_embedding: Optional[np.ndarray] = None
        self._cached_query: Optional[str] = None

    def initialize(
        self,
        document_tree,
        root_node_id: Optional[str] = None,
        query: Optional[str] = None,
        query_embedding: Optional[np.ndarray] = None
    ) -> str:
        """Initialize MCTS with document tree."""
        self.document_tree = document_tree

        if root_node_id is None:
            root_node_id = document_tree.root_id

        self.nodes = {}
        self._doc_to_mcts = {}

        self._build_mcts_tree(root_node_id)

        if query:
            self._cached_query = query
            if query_embedding is not None:
                self._query_embedding = query_embedding
            else:
                self._query_embedding = self.value_function.embedding_manager.encode_query(query)
            self._initialize_priors(query, query_embedding=self._query_embedding)

        root_mcts_id = self._doc_to_mcts.get(root_node_id)
        self.root_id = root_mcts_id
        return root_mcts_id

    def _build_mcts_tree(self, doc_id: str, parent_doc_id: Optional[str] = None, depth: int = 0) -> None:
        """
        Recursively build MCTS nodes for ALL document nodes.
        This ensures MCTS tree mirrors document tree structure.
        """
        if doc_id in self._doc_to_mcts:
            return 

        doc_node = self.document_tree.get_node(doc_id)
        if not doc_node:
            return

        mcts_id = f"mcts_{doc_id}"
        mcts_node = MCTSNode(
            id=mcts_id,
            document_node_id=doc_id,
            parent_id=parent_doc_id,
            depth=depth,
            state=NodeState.EXPANDED,
            prior_probability=0.1,
        )

        self.nodes[mcts_id] = mcts_node
        self._doc_to_mcts[doc_id] = mcts_id

        for child_doc_id in doc_node.children_ids:
            child_doc = self.document_tree.get_node(child_doc_id)
            if child_doc:
                self._build_mcts_tree(child_doc_id, doc_id, depth + 1)

    def _get_mcts_node(self, doc_id: str) -> Optional[MCTSNode]:
        """Get MCTS node by document ID."""
        mcts_id = self._doc_to_mcts.get(doc_id)
        if mcts_id:
            return self.nodes.get(mcts_id)
        return None

    def _initialize_priors(self, query: str, query_embedding=None) -> None:
        """
        Initialize prior probabilities using value function.
        IMPORTANT: Score ALL document nodes, not just a subset.
        """
        if not self.document_tree:
            return

        all_doc_nodes = [
            node.id for node in self.document_tree.get_all_nodes()
            if node.id != self.document_tree.root_id and len(node.content) > 50
        ]

        if not all_doc_nodes:
            return

        value_estimates = self.value_function.predict_values(
            query, all_doc_nodes, query_embedding=query_embedding
        )

        # Update MCTS node priors with actual scores
        scored_count = 0
        for doc_id, score in value_estimates.items():
            mcts_node = self._get_mcts_node(doc_id)
            if mcts_node:
                mcts_node.prior_probability = score
                scored_count += 1

    def search(
        self,
        query: str,
        max_results: int = 10,
        early_stop: bool = True,
        query_embedding: Optional[np.ndarray] = None
    ) -> List[SearchResult]:
        """Perform MCTS search."""
        if not self.root_id or not self.document_tree:
            raise ValueError("MCTS not initialized. Call initialize() first.")

        start_time = time.time()
        self.total_iterations = 0
        self._best_score = 0.0
        self._best_doc_id = None

        self._cached_query = query
        if query_embedding is not None:
            self._query_embedding = query_embedding
        elif self._query_embedding is None:
            self._query_embedding = self.value_function.embedding_manager.encode_query(query)

        if self._query_embedding is not None and self._query_embedding.ndim == 2:
            self._query_embedding = self._query_embedding[0]

        root_doc_id = None
        root_mcts = self.nodes.get(self.root_id)
        if root_mcts:
            root_doc_id = root_mcts.document_node_id

        for iteration in range(self.max_iterations):
            path = self._select(root_doc_id)

            if not path:
                continue

            leaf_doc_id = path[-1]

            # Rollout: simulate from leaf
            reward = self._rollout(leaf_doc_id, query)

            # Backpropagate reward
            self._backpropagate(path, reward)

            # Update best node
            self._update_best()

            self.total_iterations += 1

            if early_stop and self._best_score >= self.early_stop_threshold:
                best_mcts = self._get_mcts_node(self._best_doc_id) if self._best_doc_id else None
                if best_mcts and best_mcts.visit_count >= self.min_visits:
                    break

            if time.time() - start_time > 60:
                break

        # Debug: show top nodes by prior
        top_nodes = sorted(
            [n for n in self.nodes.values() if n.document_node_id != root_doc_id],
            key=lambda n: n.prior_probability, reverse=True
        )[:5]
        
        return self._extract_results(max_results)

    def _select(self, start_doc_id: str) -> List[str]:
        """
        Select path from start to leaf using UCB selection.
        Returns list of document IDs from root to leaf.
        """
        path = [start_doc_id]
        current_doc_id = start_doc_id

        while True:
            current_mcts = self._get_mcts_node(current_doc_id)
            if not current_mcts:
                break

            # Get document node to find children
            doc_node = self.document_tree.get_node(current_doc_id)
            if not doc_node or not doc_node.children_ids:
                break

            # Select best child using UCB
            best_child_id = self._select_best_child_ucb(current_doc_id)
            if best_child_id is None:
                break

            path.append(best_child_id)
            current_doc_id = best_child_id

            # Safety: don't go too deep
            if len(path) >= self.max_depth:
                break

        return path

    def _select_best_child_ucb(self, parent_doc_id: str) -> Optional[str]:
        """Select best child using UCB formula."""
        parent_mcts = self._get_mcts_node(parent_doc_id)
        if not parent_mcts:
            return None

        doc_node = self.document_tree.get_node(parent_doc_id)
        if not doc_node or not doc_node.children_ids:
            return None

        parent_visits = max(parent_mcts.visit_count, 1)

        best_score = float('-inf')
        best_child_id = None

        for child_doc_id in doc_node.children_ids:
            child_mcts = self._get_mcts_node(child_doc_id)
            if not child_mcts:
                continue

            # UCB formula: exploitation + exploration
            if child_mcts.visit_count == 0:
                # Unvisited: use prior with exploration bonus
                score = child_mcts.prior_probability + self.exploration_constant
            else:
                # Visited: UCB = prior + C * sqrt(log(parent_visits) / child_visits)
                exploitation = child_mcts.prior_probability
                exploration = self.exploration_constant * math.sqrt(
                    math.log(parent_visits) / child_mcts.visit_count
                )
                score = exploitation + exploration

            # Add small random noise for tie-breaking
            score += random.random() * 0.001

            if score > best_score:
                best_score = score
                best_child_id = child_doc_id

        return best_child_id

    def _rollout(self, start_doc_id: str, query: str) -> float:
        """
        Perform rollout from node with depth limit.
        Uses softmax selection over children based on priors.
        """
        current_doc_id = start_doc_id
        current_mcts = self._get_mcts_node(current_doc_id)

        if not current_mcts:
            return 0.1

        current_depth = current_mcts.depth
        max_rollout_depth = min(current_depth + 5, self.max_depth)

        rollout_path = [current_doc_id]

        while current_depth < max_rollout_depth:
            doc_node = self.document_tree.get_node(current_doc_id)
            if not doc_node or not doc_node.children_ids:
                break

            # Get candidates with their prior scores
            candidates = []
            for child_doc_id in doc_node.children_ids:
                child_mcts = self._get_mcts_node(child_doc_id)
                if child_mcts:
                    score = max(child_mcts.prior_probability, 0.01)
                    candidates.append((child_doc_id, score))

            if not candidates:
                break

            # Softmax selection based on priors
            scores = np.array([c[1] for c in candidates])
            exp_scores = np.exp(scores - np.max(scores))  # Numerically stable
            probs = exp_scores / exp_scores.sum()

            # Choose based on probabilities
            selected_idx = np.random.choice(len(candidates), p=probs)
            current_doc_id = candidates[selected_idx][0]
            rollout_path.append(current_doc_id)
            current_depth += 1

        # Return the prior probability of the final node as the reward
        final_mcts = self._get_mcts_node(current_doc_id)
        if final_mcts:
            return max(final_mcts.prior_probability, 0.1)
        return 0.1

    def _backpropagate(self, path: List[str], reward: float) -> None:
        """Backpropagate reward through the path."""
        for doc_id in reversed(path):
            mcts_node = self._get_mcts_node(doc_id)
            if mcts_node:
                mcts_node.update(reward)
                reward *= 0.95  # Discount factor

    def _update_best(self) -> None:
        """Update the best node found so far."""
        if not self.root_id:
            return

        root_mcts = self.nodes.get(self.root_id)
        if not root_mcts or root_mcts.visit_count < self.min_visits:
            return

        best_value = -float('inf')
        best_doc_id = None

        for mcts_node in self.nodes.values():
            if mcts_node.visit_count >= self.min_visits:
                # Use prior_probability (embedding-based relevance) as the score
                value = mcts_node.prior_probability
                if value > best_value:
                    best_value = value
                    best_doc_id = mcts_node.document_node_id

        if best_value > self._best_score:
            self._best_score = best_value
            self._best_doc_id = best_doc_id

    def _extract_results(self, max_results: int) -> List[SearchResult]:
        """Extract final results from the search tree."""
        results = []
        scored_nodes = []

        for mcts_node in self.nodes.values():
            if mcts_node.document_node_id == self.document_tree.root_id:
                continue

            # Skip nodes with very low prior and no visits
            if mcts_node.visit_count == 0 and mcts_node.prior_probability < 0.3:
                continue

            # Primary score: prior_probability (embedding-based relevance)
            primary_score = mcts_node.prior_probability

            # Visit bonus: reward nodes that were explored more
            visit_bonus = 0.01 * min(mcts_node.visit_count / 20, 1.0)

            # Combined score
            score = primary_score + visit_bonus
                            
            scored_nodes.append((score, mcts_node))

        scored_nodes.sort(key=lambda x: x[0], reverse=True)

        for score, mcts_node in scored_nodes[:max_results]:
            doc_node = self.document_tree.get_node(mcts_node.document_node_id)
            if not doc_node:
                continue

            result = SearchResult(
                node_id=mcts_node.id,
                document_node_id=mcts_node.document_node_id,
                score=score,
                visit_count=mcts_node.visit_count,
                path=self._build_path(mcts_node.document_node_id),
                content=doc_node.content[:500] if doc_node.content else "",
                depth=mcts_node.depth,
                source="mcts",
                relevance=mcts_node.prior_probability,
                metadata={
                    "prior_probability": mcts_node.prior_probability,
                    "mean_value": mcts_node.mean_value,
                    "total_value": mcts_node.total_value,
                },
            )
            results.append(result)

        return results

    def _build_path(self, doc_id: str) -> List[str]:
        """Build path from root to node using document IDs."""
        path = []
        current_doc_id = doc_id

        while current_doc_id:
            path.append(current_doc_id)
            doc_node = self.document_tree.get_node(current_doc_id)
            if doc_node and doc_node.parent_id:
                current_doc_id = doc_node.parent_id
            else:
                break

        return list(reversed(path))

    def get_statistics(self) -> Dict[str, Any]:
        """Get MCTS statistics."""
        return {
            "total_iterations": self.total_iterations,
            "total_mcts_nodes": len(self.nodes),
            "total_doc_nodes": len(self._doc_to_mcts),
            "best_score": self._best_score,
            "best_doc_id": self._best_doc_id,
            "root_visits": self.nodes[self.root_id].visit_count if self.root_id and self.root_id in self.nodes else 0,
        }