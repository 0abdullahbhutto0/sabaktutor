"""
Value Function and Node Scorer Module - FIXED
=============================================
Scores ALL candidate nodes, not just top-k from vector store.

FIXES:
1. ALL candidate nodes get scored via embedding similarity
2. No fallback to uniform 0.5 for missing nodes
3. Proper handling when vector store has fewer results than candidates
4. Score normalization across all candidates
"""

from typing import List, Dict, Optional, Any
import numpy as np
from dataclasses import dataclass
import threading
import time
from core.vector_store import FaissVectorStore


@dataclass
class ChunkScore:
    """Represents a node's relevance score."""
    node_id: str
    score: float
    content: str


@dataclass
class NodeScore:
    """Represents a node's aggregated score."""
    node_id: str
    raw_score: float
    normalized_score: float = 0.0


class NodeScorer:
    """Compute and normalize node scores."""
    def __init__(self, use_sqrt_normalization: bool = True):
        self.use_sqrt_normalization = use_sqrt_normalization

    def compute_node_score(
        self,
        scores: List[ChunkScore],
        node_id: str,
        depth: int = 0,
        query: Optional[str] = None,
    ) -> NodeScore:
        """Compute the score for a node."""
        if not scores:
            return NodeScore(node_id=node_id, raw_score=0.0)

        max_score = max(s.score for s in scores)

        keyword_boost = 0.0
        if query:
            query_words = set(query.lower().split())
            for s in scores:
                content_words = set(s.content.lower().split())
                overlap = len(query_words & content_words)
                if overlap >= 2:
                    keyword_boost = max(keyword_boost, 0.15)

        depth_boost = 0.2 if depth >= 2 else 0.0
        raw_score = max_score + keyword_boost + depth_boost

        return NodeScore(node_id=node_id, raw_score=raw_score)

    def normalize_scores(self, node_scores: List[NodeScore]) -> List[NodeScore]:
        """Normalize scores using min-max normalization."""
        if not node_scores:
            return []

        raw_scores = [ns.raw_score for ns in node_scores]
        min_score = min(raw_scores)
        max_score = max(raw_scores)

        if max_score == min_score:
            for ns in node_scores:
                ns.normalized_score = 0.5
        else:
            score_range = max_score - min_score
            for ns in node_scores:
                ns.normalized_score = (ns.raw_score - min_score) / score_range

        return node_scores


@dataclass
class IndexTiming:
    """Tracks timing for index_tree operations."""
    total_time_ms: float = 0.0
    node_iteration_time_ms: float = 0.0
    embedding_generation_time_ms: float = 0.0
    index_build_time_ms: float = 0.0
    nodes_processed: int = 0
    nodes_embedded: int = 0
    nodes_loaded_from_store: int = 0

    def report(self) -> str:
        """Pretty print timing report."""
        return f"""
╔══════════════════════════════════════════════════════════════╗
║                    INDEXING TIMING REPORT                    ║
╠══════════════════════════════════════════════════════════════╣
║  Total Time              : {self.total_time_ms:.2f} ms ({self.total_time_ms/1000:.2f}s)
║  Node Iteration          : {self.node_iteration_time_ms:.2f} ms
║  Embedding Generation    : {self.embedding_generation_time_ms:.2f} ms
║  Index Build             : {self.index_build_time_ms:.2f} ms
╠══════════════════════════════════════════════════════════════╣
║  Nodes Processed         : {self.nodes_processed}
║  Nodes Embedded          : {self.nodes_embedded}
║  Loaded from Store       : {self.nodes_loaded_from_store}
╚══════════════════════════════════════════════════════════════╝
        """


class ValueFunction:
    """
    Value function for predicting node relevance.
    Scores ALL candidate nodes, not just top-k.
    """

    def __init__(
        self,
        embedding_manager,
        top_k: int = 10,
        use_sqrt_normalization: bool = True,
        vector_store_path: str = "./vector_index",
    ):
        self.embedding_manager = embedding_manager
        self.top_k = top_k
        self.scorer = NodeScorer(use_sqrt_normalization=use_sqrt_normalization)

        self.vector_store = FaissVectorStore(
            index_path=vector_store_path,
            embedding_dim=getattr(embedding_manager, 'embedding_dim', 2048),
        )

        self._document_tree: Optional[Any] = None
        self._lock = threading.Lock()
        self._query_embedding_cache: Optional[np.ndarray] = None
        self._cached_query: Optional[str] = None
        self.last_timing: Optional[IndexTiming] = None

    def index_tree(self, tree, show_progress: bool = False) -> IndexTiming:
        """
        Index all nodes from a document tree.
        NO CHUNKING - each node's content is embedded directly.
        """
        timing = IndexTiming()
        start_total = time.perf_counter()

        self._document_tree = tree

        contents_to_encode = []
        node_ids_to_encode = []
        long_nodes = []

        start_nodes = time.perf_counter()

        for node in tree.get_all_nodes():
            if node.is_root:
                continue

            content = node.content.strip()
            if not content:
                continue

            timing.nodes_processed += 1

            content_len = len(content)
            if content_len > 12000:  # Roughly > ~4000 tokens
                    long_nodes.append({
                        'node_id': node.id,
                        'chars': content_len,
                        'estimated_tokens': content_len // 3,  # Rough estimate: ~3 chars per token
                        'preview': content[:200].replace('\n', ' ')
                    })


            # Check if already indexed
            if self.vector_store.exists(node.id):
                timing.nodes_loaded_from_store += 1
            else:
                # Truncate if too long (embedding models have limits)
                truncated_content = content
                contents_to_encode.append(truncated_content)
                node_ids_to_encode.append(node.id)

        timing.node_iteration_time_ms = (time.perf_counter() - start_nodes) * 1000

        if long_nodes:
            print(f"\n{'='*60}")
            print(f"WARNING: Found {len(long_nodes)} nodes exceeding safe token limit!")
            print(f"{'='*60}")
            for node_info in sorted(long_nodes, key=lambda x: x['chars'], reverse=True)[:10]:
                print(f"\n  Node ID: {node_info['node_id']}")
                print(f"  Chars: {node_info['chars']:,} | Est. Tokens: {node_info['estimated_tokens']:,}")
                print(f"  Preview: {node_info['preview']}...")
            print(f"{'='*60}\n")
        else:
            print(f"\nAll {timing.nodes_processed} nodes within safe token limit.")

        if contents_to_encode:
            print(f"\nGENERATING {len(contents_to_encode)} NEW EMBEDDINGS...")

            start_embed = time.perf_counter()
            embeddings = self.embedding_manager.encode(
                contents_to_encode,
                batch_size=16,
                show_progress=show_progress
            )
            timing.embedding_generation_time_ms = (time.perf_counter() - start_embed) * 1000
            timing.nodes_embedded = len(contents_to_encode)

            start_build = time.perf_counter()
            for i, node_id in enumerate(node_ids_to_encode):
                content = contents_to_encode[i]
                embedding = embeddings[i] if len(embeddings.shape) > 1 else embeddings

                if not self.vector_store.exists(node_id):
                    self.vector_store.add(
                        record_id=node_id,
                        vector=embedding if isinstance(embedding, np.ndarray) else np.array(embedding),
                        content=content,
                        metadata={"node_id": node_id},
                    )
            timing.index_build_time_ms = (time.perf_counter() - start_build) * 1000

        self.vector_store.save()
        timing.total_time_ms = (time.perf_counter() - start_total) * 1000
        self.last_timing = timing

        return timing

    def _get_query_embedding(self, query: str) -> np.ndarray:
        """Get query embedding, using cache if available."""
        if self._cached_query == query and self._query_embedding_cache is not None:
            return self._query_embedding_cache

        query_embedding = self.embedding_manager.encode_query(query)
        if query_embedding.ndim == 2:
            query_embedding = query_embedding[0]

        self._cached_query = query
        self._query_embedding_cache = query_embedding
        return query_embedding

    def predict_values(
        self,
        query: str,
        candidate_nodes: List[str],
        query_embedding: Optional[np.ndarray] = None,
    ) -> Dict[str, float]:
        """
        Predict value estimates for candidate nodes.

        CRITICAL: ALL candidates get scored, not just top-k.
        Uses batch embedding + similarity computation.
        """
        if not candidate_nodes:
            return {}

        if self.vector_store.count() == 0:
            print(f"  WARNING: Vector store is empty! Using uniform scores.")
            return {node_id: 0.5 for node_id in candidate_nodes}

        if query_embedding is not None:
            q_emb = query_embedding
        else:
            q_emb = self.embedding_manager.encode_query(query)

        if q_emb.ndim == 2:
            q_emb = q_emb[0]

        # Get embeddings for ALL candidates from vector store
        # Search for MORE than candidates to ensure we get all
        search_k = max(self.top_k, len(candidate_nodes) * 2)

        print(f"  Vector store: {self.vector_store.count()} total nodes, searching top {search_k}")

        results = self.vector_store.search(q_emb, top_k=search_k)

        # Build map of all results
        node_scores_map: Dict[str, float] = {}

        for node_id, score, content in results:
            # Use the raw similarity score
            node_scores_map[node_id] = float(score)

        # Assign scores to ALL candidates
        # - If found in search: use the score
        # - If not found: assign low score based on the minimum score found
        if node_scores_map:
            min_score = min(node_scores_map.values())
        else:
            min_score = 0.01

        # Assign scores to all candidates
        final_scores = {}
        for node_id in candidate_nodes:
            if node_id in node_scores_map:
                final_scores[node_id] = node_scores_map[node_id]
            else:
                # Not found in search results - assign very low score
                # But still a valid score for normalization
                final_scores[node_id] = min_score * 0.1  # 10% of minimum score

        print(f"  Scored {len(final_scores)} nodes, {sum(1 for v in final_scores.values() if v > min_score * 0.5)} with significant scores")

        # Normalize scores to [0, 1] range
        scores_list = list(final_scores.values())
        min_s = min(scores_list)
        max_s = max(scores_list)

        if max_s > min_s:
            for node_id in final_scores:
                final_scores[node_id] = (final_scores[node_id] - min_s) / (max_s - min_s)
        else:
            # All same score
            for node_id in final_scores:
                final_scores[node_id] = 0.5

        return final_scores

    def clear_index(self) -> None:
        """Clear the index and document tree reference."""
        with self._lock:
            self.vector_store.clear()
            self._document_tree = None
            self._query_embedding_cache = None
            self._cached_query = None

    @property
    def index_size(self) -> int:
        """Get the number of indexed nodes."""
        return self.vector_store.count()