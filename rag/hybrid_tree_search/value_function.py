"""
Value Function and Node Scorer Module
=====================================
Implements the value prediction function for Monte Carlo Tree Search
using embedding-based relevance scoring.
"""

from typing import List, Dict, Tuple, Optional, Set
import numpy as np
from dataclasses import dataclass, field
from collections import defaultdict
import math
from concurrent.futures import ThreadPoolExecutor
import threading


@dataclass
class ChunkScore:
    """Represents a chunk's relevance score."""
    chunk_id: str
    node_id: str
    score: float
    content: str
    position: int = 0  # Position in the chunk list


@dataclass
class NodeScore:
    """Represents a node's aggregated score."""
    node_id: str
    raw_score: float
    num_chunks: int
    chunk_scores: List[ChunkScore]
    normalized_score: float = 0.0
    depth_penalty: float = 1.0

    @property
    def final_score(self) -> float:
        """Get the final score including depth penalty."""
        return self.normalized_score * self.depth_penalty


class NodeScorer:
    """
    Scores nodes based on their associated chunks using vector search.

    Implements the node scoring formula:
    NodeScore = (1 / sqrt(N + 1)) * sum(ChunkScore(n))

    Where:
    - N is the number of content chunks associated with a node
    - ChunkScore is the relevance score from vector similarity
    - The square root normalization rewards nodes with more relevant chunks
      while preventing large nodes from dominating
    """

    def __init__(
        self,
        top_k: int = 10,
        use_sqrt_normalization: bool = True,
        depth_decay: float = 0.95,
        min_score_threshold: float = 0.0,
    ):
        """
        Initialize the node scorer.

        Args:
            top_k: Number of top chunks to retrieve per query
            use_sqrt_normalization: Whether to use sqrt(N+1) normalization
            depth_decay: Depth penalty factor (1.0 = no penalty)
            min_score_threshold: Minimum chunk score to consider
        """
        self.top_k = top_k
        self.use_sqrt_normalization = use_sqrt_normalization
        self.depth_decay = depth_decay
        self.min_score_threshold = min_score_threshold
        self._score_history: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def compute_node_score(
        self,
        chunk_scores: List[ChunkScore],
        node_id: str,
        depth: int = 0,
        query: Optional[str] = None,
    ) -> NodeScore:
        """
        Compute the score for a node based on its chunks.

        Scoring strategy (PageIndex-style):
        - Use MAX chunk score as primary signal
        - Add keyword boost for exact phrase matches
        - ADD depth boost: nodes deeper in tree (with actual content) should rank higher
        - This ensures child nodes with actual content rank above parent headers

        Args:
            chunk_scores: List of chunk scores for this node
            node_id: The node ID
            depth: Node depth in the tree
            query: Optional query for keyword boosting

        Returns:
            Computed NodeScore
        """
        if not chunk_scores:
            return NodeScore(
                node_id=node_id,
                raw_score=0.0,
                num_chunks=0,
                chunk_scores=[],
                normalized_score=0.0,
                depth_penalty=1.0,
            )

        N = len(chunk_scores)

        # PRIMARY: Max chunk score
        max_score = max(cs.score for cs in chunk_scores)

        # Keyword boost - check if content has specific terms from query
        keyword_boost = 0.0
        if query:
            query_words = set(query.lower().split())
            for cs in chunk_scores:
                content_words = set(cs.content.lower().split())
                overlap = len(query_words & content_words)
                if overlap >= 2:
                    keyword_boost = max(keyword_boost, 0.15)

        # DEPTH BOOST: Nodes at depth > 1 (with actual content) get a bonus
        # Root = 0, first children = 1, grandchildren = 2, etc.
        # Parent headers at depth 1 get no boost, content nodes at depth 2+ get boost
        depth_boost = 0.0
        if depth >= 2:
            depth_boost = 0.2  # Child nodes with actual content

        # Combine all signals
        raw_score = max_score + keyword_boost + depth_boost

        node_score = NodeScore(
            node_id=node_id,
            raw_score=raw_score,
            num_chunks=N,
            chunk_scores=chunk_scores,
            depth_penalty=1.0,  # No additional penalty
        )

        return node_score

    def aggregate_scores(
        self,
        node_scores: List[NodeScore],
        method: str = "mean",
    ) -> Dict[str, float]:
        """
        Aggregate scores across multiple query passes.

        Args:
            node_scores: List of node scores
            method: Aggregation method ("mean", "max", "sum")

        Returns:
            Dictionary mapping node_id to aggregated score
        """
        node_totals: Dict[str, List[float]] = defaultdict(list)

        for ns in node_scores:
            node_totals[ns.node_id].append(ns.final_score)

        aggregated = {}
        for node_id, scores in node_totals.items():
            if method == "mean":
                aggregated[node_id] = np.mean(scores)
            elif method == "max":
                aggregated[node_id] = max(scores)
            elif method == "sum":
                aggregated[node_id] = sum(scores)
            else:
                aggregated[node_id] = np.mean(scores)

        return aggregated

    def normalize_scores(self, node_scores: List[NodeScore]) -> List[NodeScore]:
        """
        Normalize scores across all nodes using min-max normalization.

        Args:
            node_scores: List of node scores to normalize

        Returns:
            List of normalized node scores
        """
        if not node_scores:
            return []

        raw_scores = [ns.raw_score for ns in node_scores]
        min_score = min(raw_scores)
        max_score = max(raw_scores)

        if max_score == min_score:
            # All scores are the same
            for ns in node_scores:
                ns.normalized_score = 0.5
        else:
            score_range = max_score - min_score
            for ns in node_scores:
                ns.normalized_score = (ns.raw_score - min_score) / score_range

        return node_scores


class ValueFunction:
    """
    Main value function for predicting node relevance using embeddings.

    This function combines:
    1. Vector similarity between query and chunks
    2. Node-level aggregation using the scoring formula
    3. Prior probabilities based on node statistics
    """

    def __init__(
        self,
        embedding_manager,
        top_k: int = 10,
        use_sqrt_normalization: bool = True,
        parallel_searches: int = 4,
    ):
        """
        Initialize the value function.

        Args:
            embedding_manager: EmbeddingManager instance
            top_k: Number of top chunks to retrieve
            use_sqrt_normalization: Whether to use sqrt normalization
            parallel_searches: Number of parallel searches to perform
        """
        self.embedding_manager = embedding_manager
        self.top_k = top_k
        self.scorer = NodeScorer(use_sqrt_normalization=use_sqrt_normalization)
        self.parallel_searches = parallel_searches

        # Chunk index
        self._chunk_embeddings: Optional[np.ndarray] = None
        self._chunk_node_map: List[str] = []  # Maps chunk index to node ID
        self._chunk_contents: List[str] = []
        self._node_chunks: Dict[str, List[int]] = defaultdict(list)  # node_id -> chunk indices

        # Reference to document tree for depth info
        self._document_tree: Optional[Any] = None

        self._lock = threading.Lock()

    def index_chunks(
        self,
        chunks: List[Dict],
        node_ids: List[str],
        show_progress: bool = False,
    ) -> None:
        """
        Index chunks for fast vector search.

        Args:
            chunks: List of chunk dictionaries with 'content' and 'embedding' fields
            node_ids: Corresponding node IDs for each chunk
            show_progress: Whether to show progress
        """
        if not chunks:
            return

        with self._lock:
            # Extract embeddings and contents
            embeddings = []
            self._chunk_contents = []
            self._chunk_node_map = []
            self._node_chunks = defaultdict(list)

            for i, (chunk, node_id) in enumerate(zip(chunks, node_ids)):
                content = chunk.get("content", "")
                embedding = chunk.get("embedding")

                if embedding is not None:
                    if isinstance(embedding, list):
                        embeddings.append(embedding)
                    else:
                        embeddings.append(embedding.tolist())

                    self._chunk_contents.append(content)
                    self._chunk_node_map.append(node_id)
                    self._node_chunks[node_id].append(i)

            if embeddings:
                self._chunk_embeddings = np.array(embeddings, dtype=np.float32)
            else:
                self._chunk_embeddings = None

    def index_tree(self, tree, show_progress: bool = False) -> None:
        """
        Index all chunks from a document tree.

        Args:
            tree: DocumentTree instance
            show_progress: Whether to show progress
        """
        # Store reference to tree for depth info
        self._document_tree = tree

        all_chunks = []
        all_node_ids = []
        contents_to_encode = []
        contents_map = {}  # Map content to node_id

        # Chunking parameters (PageIndex style)
        chunk_size = 200  # chars per chunk (not tokens)
        chunk_overlap = 30  # chars overlap

        # First pass: collect all chunks
        for node in tree.get_all_nodes():
            if node.is_root:
                continue

            # Get content to chunk
            content = node.content.strip()
            if not content:
                continue

            # If node already has chunks, use them
            if node.chunks:
                for chunk in node.chunks:
                    if chunk.embedding is not None:
                        all_chunks.append({
                            "content": chunk.content,
                            "embedding": chunk.embedding,
                        })
                        all_node_ids.append(node.id)
                    else:
                        content_to_encode = chunk.content
                        if content_to_encode:
                            contents_to_encode.append(content_to_encode)
                            contents_map[content_to_encode] = node.id
            else:
                # Split content into chunks (PageIndex-style chunking)
                node_chunks = self._chunk_text(content, chunk_size, chunk_overlap)

                for chunk_text in node_chunks:
                    if not chunk_text.strip():
                        continue

                    # Check if content already encoded
                    if chunk_text in contents_map:
                        continue

                    contents_to_encode.append(chunk_text)
                    contents_map[chunk_text] = node.id

        if show_progress:
            print(f"Total chunks to encode: {len(contents_to_encode)}")

        # Encode chunks that don't have embeddings
        if contents_to_encode:
            if show_progress:
                print(f"Encoding {len(contents_to_encode)} chunks...")

            embeddings = self.embedding_manager.encode(
                contents_to_encode,
                batch_size=32,
                show_progress=show_progress
            )

            # Add encoded chunks
            for i, content in enumerate(contents_to_encode):
                node_id = contents_map[content]
                embedding = embeddings[i] if len(embeddings.shape) > 1 else embeddings
                all_chunks.append({
                    "content": content,
                    "embedding": embedding.tolist() if hasattr(embedding, 'tolist') else embedding,
                })
                all_node_ids.append(node_id)

        self.index_chunks(all_chunks, all_node_ids, show_progress)

        if show_progress:
            print(f"Indexed {len(all_chunks)} chunks from tree")

    def _chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: Text to chunk
            chunk_size: Target size for each chunk (in chars)
            overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text] if text.strip() else []

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence or paragraph boundary
            if end < len(text):
                # Look for sentence end
                for punct in ['. ', '! ', '? ', '\n\n', '\n']:
                    last_break = text.rfind(punct, start + chunk_size // 2, end)
                    if last_break > start:
                        end = last_break + len(punct)
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Move start with overlap
            start = end - overlap
            if start >= len(text) - overlap:
                break

        return chunks

    def predict_values(
        self,
        query: str,
        candidate_nodes: List[str],
        use_cache: bool = True,
    ) -> Dict[str, float]:
        """
        Predict value estimates for candidate nodes.

        Args:
            query: The search query
            candidate_nodes: List of candidate node IDs to evaluate
            use_cache: Whether to use cached results

        Returns:
            Dictionary mapping node_id to value estimate [0, 1]
        """
        if not candidate_nodes or self._chunk_embeddings is None:
            return {node_id: 0.5 for node_id in candidate_nodes}

        # Encode query
        query_embedding = self.embedding_manager.encode(query)
        if query_embedding.ndim == 2:
            query_embedding = query_embedding[0]

        # Compute similarities with all chunks
        similarities = self.embedding_manager.compute_similarity(
            query_embedding, self._chunk_embeddings
        )

        # Find top-k chunks
        top_indices = np.argsort(similarities)[::-1][:self.top_k]

        # Build chunk scores
        chunk_scores_map: Dict[str, List[ChunkScore]] = defaultdict(list)
        for rank, idx in enumerate(top_indices):
            similarity = float(similarities[idx])
            if similarity <= 0:
                continue

            node_id = self._chunk_node_map[idx]
            chunk_score = ChunkScore(
                chunk_id=f"chunk_{idx}",
                node_id=node_id,
                score=similarity,
                content=self._chunk_contents[idx],
                position=rank,
            )
            chunk_scores_map[node_id].append(chunk_score)

        # Compute node scores with keyword boosting and depth boost
        node_scores = []
        for node_id in candidate_nodes:
            if node_id in chunk_scores_map:
                chunk_scores = chunk_scores_map[node_id]
                # Get node depth from tree
                doc_node = self._document_tree.get_node(node_id) if self._document_tree else None
                node_depth = doc_node.depth if doc_node else 0
                node_score = self.scorer.compute_node_score(
                    chunk_scores, node_id, depth=node_depth, query=query
                )
                node_scores.append(node_score)
            else:
                node_scores.append(NodeScore(
                    node_id=node_id,
                    raw_score=0.0,
                    num_chunks=0,
                    chunk_scores=[],
                    normalized_score=0.0,
                ))

        # Use raw scores directly (no min-max normalization which distorts ranking)
        return {ns.node_id: ns.raw_score for ns in node_scores}

    def predict_batch(
        self,
        queries: List[str],
        candidate_nodes: List[str],
    ) -> Dict[str, Dict[str, float]]:
        """
        Predict values for multiple queries in batch.

        Args:
            queries: List of queries
            candidate_nodes: List of candidate node IDs

        Returns:
            Dictionary mapping query to node value estimates
        """
        results = {}

        for query in queries:
            results[query] = self.predict_values(query, candidate_nodes)

        return results

    def get_relevant_chunks_for_node(
        self,
        node_id: str,
        query: str,
        top_k: int = 5,
    ) -> List[Tuple[ChunkScore, float]]:
        """
        Get the most relevant chunks for a specific node.

        Args:
            node_id: The node ID
            query: The search query
            top_k: Number of top chunks to return

        Returns:
            List of (ChunkScore, similarity) tuples
        """
        if self._chunk_embeddings is None:
            return []

        # Get chunk indices for this node
        chunk_indices = self._node_chunks.get(node_id, [])
        if not chunk_indices:
            return []

        # Encode query
        query_embedding = self.embedding_manager.encode(query)
        if query_embedding.ndim == 2:
            query_embedding = query_embedding[0]

        # Get embeddings for this node's chunks
        node_embeddings = self._chunk_embeddings[chunk_indices]

        # Compute similarities
        similarities = self.embedding_manager.compute_similarity(
            query_embedding, node_embeddings
        )

        # Sort and return top k
        sorted_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for local_idx in sorted_indices:
            global_idx = chunk_indices[local_idx]
            similarity = float(similarities[local_idx])
            chunk_score = ChunkScore(
                chunk_id=f"chunk_{global_idx}",
                node_id=node_id,
                score=similarity,
                content=self._chunk_contents[global_idx],
                position=local_idx,
            )
            results.append((chunk_score, similarity))

        return results

    def get_prior_probability(
        self,
        node_id: str,
        tree,
    ) -> float:
        """
        Calculate prior probability for a node based on tree statistics.

        Args:
            node_id: The node ID
            tree: The document tree

        Returns:
            Prior probability [0, 1]
        """
        node = tree.get_node(node_id)
        if not node:
            return 0.5

        # Factors:
        # 1. Number of chunks (more chunks = more likely to be relevant)
        # 2. Depth in tree (shallower nodes often more general)
        # 3. Node type (higher-level nodes might be more important)

        # Chunk factor
        num_chunks = len(node.chunks)
        chunk_factor = min(num_chunks / 10.0, 1.0)  # Normalize to 0-1

        # Depth factor (shallower = higher prior)
        depth_factor = 1.0 / (node.depth + 1)

        # Type factor
        type_factors = {
            "document": 0.9,
            "chapter": 0.8,
            "section": 0.7,
            "paragraph": 0.6,
            "chunk": 0.5,
        }
        type_factor = type_factors.get(node.node_type.value, 0.5)

        # Combine factors
        prior = (chunk_factor * 0.3 + depth_factor * 0.3 + type_factor * 0.4)

        return min(max(prior, 0.0), 1.0)

    def update_with_feedback(
        self,
        node_id: str,
        relevance_feedback: float,
    ) -> None:
        """
        Update value function with relevance feedback.

        Args:
            node_id: The node ID
            relevance_feedback: User feedback (0-1 scale)
        """
        with self._lock:
            self._score_history[node_id].append(relevance_feedback)

    def clear_index(self) -> None:
        """Clear the chunk index."""
        with self._lock:
            self._chunk_embeddings = None
            self._chunk_node_map = []
            self._chunk_contents = []
            self._node_chunks.clear()

    @property
    def index_size(self) -> int:
        """Get the number of indexed chunks."""
        if self._chunk_embeddings is None:
            return 0
        return len(self._chunk_embeddings)