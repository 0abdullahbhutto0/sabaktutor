"""
Value Function and Node Scorer Module
=====================================
Implements the value prediction function for Monte Carlo Tree Search
using embedding-based relevance scoring.
"""

from typing import List, Dict, Optional, Any
import numpy as np
from dataclasses import dataclass
import threading


@dataclass
class ChunkScore:
    """Represents a chunk's relevance score."""
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
    """Scores nodes based on their associated chunks using vector search."""

    def __init__(self, use_sqrt_normalization: bool = True):
        self.use_sqrt_normalization = use_sqrt_normalization

    def compute_node_score(
        self,
        chunk_scores: List[ChunkScore],
        node_id: str,
        depth: int = 0,
        query: Optional[str] = None,
    ) -> NodeScore:
        """Compute the score for a node based on its chunks."""
        if not chunk_scores:
            return NodeScore(node_id=node_id, raw_score=0.0)

        N = len(chunk_scores)
        max_score = max(cs.score for cs in chunk_scores)

        keyword_boost = 0.0
        if query:
            query_words = set(query.lower().split())
            for cs in chunk_scores:
                content_words = set(cs.content.lower().split())
                overlap = len(query_words & content_words)
                if overlap >= 2:
                    keyword_boost = max(keyword_boost, 0.15)

        depth_boost = 0.2 if depth >= 2 else 0.0
        raw_score = max_score + keyword_boost + depth_boost

        if self.use_sqrt_normalization and N > 0:
            raw_score = raw_score / np.sqrt(N + 1)

        return NodeScore(node_id=node_id, raw_score=raw_score)

    def normalize_scores(self, node_scores: List[NodeScore]) -> List[NodeScore]:
        """Normalize scores across all nodes using min-max normalization."""
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


class ValueFunction:
    """Main value function for predicting node relevance using embeddings."""

    def __init__(
        self,
        embedding_manager,
        top_k: int = 10,
        use_sqrt_normalization: bool = True,
    ):
        self.embedding_manager = embedding_manager
        self.top_k = top_k
        self.scorer = NodeScorer(use_sqrt_normalization=use_sqrt_normalization)

        self._chunk_embeddings: Optional[np.ndarray] = None
        self._chunk_node_map: List[str] = []
        self._chunk_contents: List[str] = []
        self._document_tree: Optional[Any] = None
        self._lock = threading.Lock()

        # Cache for query embeddings to avoid re-encoding across MCTS iterations
        self._query_embedding_cache: Optional[np.ndarray] = None
        self._cached_query: Optional[str] = None

    def index_chunks(self, chunks: List[Dict], node_ids: List[str]) -> None:
        """Index chunks for fast vector search."""
        if not chunks:
            return

        with self._lock:
            embeddings = []
            self._chunk_contents = []
            self._chunk_node_map = []

            for chunk, node_id in zip(chunks, node_ids):
                content = chunk.get("content", "")
                embedding = chunk.get("embedding")

                if embedding is not None:
                    if isinstance(embedding, list):
                        embeddings.append(embedding)
                    else:
                        embeddings.append(embedding.tolist())
                    self._chunk_contents.append(content)
                    self._chunk_node_map.append(node_id)

            if embeddings:
                self._chunk_embeddings = np.array(embeddings, dtype=np.float32)
            else:
                self._chunk_embeddings = None

    def index_tree(self, tree, show_progress: bool = False) -> None:
        """Index all chunks from a document tree."""
        self._document_tree = tree

        all_chunks = []
        all_node_ids = []
        contents_to_encode = []
        contents_map = {}

        chunk_size = 200
        chunk_overlap = 30

        for node in tree.get_all_nodes():
            if node.is_root:
                continue

            content = node.content.strip()
            if not content:
                continue

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
                node_chunks = self._chunk_text(content, chunk_size, chunk_overlap)
                for chunk_text in node_chunks:
                    if not chunk_text.strip():
                        continue
                    if chunk_text in contents_map:
                        continue
                    contents_to_encode.append(chunk_text)
                    contents_map[chunk_text] = node.id

        if show_progress:
            print(f"Total chunks to encode: {len(contents_to_encode)}")

        if contents_to_encode:
            if show_progress:
                print(f"Encoding {len(contents_to_encode)} chunks...")

            embeddings = self.embedding_manager.encode(
                contents_to_encode,
                batch_size=32,
                show_progress=show_progress
            )

            for i, content in enumerate(contents_to_encode):
                node_id = contents_map[content]
                embedding = embeddings[i] if len(embeddings.shape) > 1 else embeddings
                all_chunks.append({
                    "content": content,
                    "embedding": embedding.tolist() if hasattr(embedding, 'tolist') else embedding,
                })
                all_node_ids.append(node_id)

        self.index_chunks(all_chunks, all_node_ids)

        if show_progress:
            print(f"Indexed {len(all_chunks)} chunks from tree")

    def _chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks."""
        if len(text) <= chunk_size:
            return [text] if text.strip() else []

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            if end < len(text):
                for punct in ['. ', '! ', '? ', '\n\n', '\n']:
                    last_break = text.rfind(punct, start + chunk_size // 2, end)
                    if last_break > start:
                        end = last_break + len(punct)
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap
            if start >= len(text) - overlap:
                break

        return chunks

    def _get_query_embedding(self, query: str) -> np.ndarray:
        """Get query embedding, using cache if available."""
        if self._cached_query == query and self._query_embedding_cache is not None:
            return self._query_embedding_cache

        # Use the embedding manager's cache for single queries
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
    ) -> Dict[str, float]:
        """Predict value estimates for candidate nodes."""
        if not candidate_nodes or self._chunk_embeddings is None:
            return {node_id: 0.5 for node_id in candidate_nodes}

        # Use cached query embedding (avoids re-encoding in MCTS loops)
        query_embedding = self._get_query_embedding(query)

        similarities = self.embedding_manager.compute_similarity(
            query_embedding, self._chunk_embeddings
        )

        top_indices = np.argsort(similarities)[::-1][:self.top_k]

        chunk_scores_map: Dict[str, List[ChunkScore]] = {}
        for idx in top_indices:
            similarity = float(similarities[idx])
            if similarity <= 0:
                continue

            node_id = self._chunk_node_map[idx]
            chunk_score = ChunkScore(
                node_id=node_id,
                score=similarity,
                content=self._chunk_contents[idx],
            )
            if node_id not in chunk_scores_map:
                chunk_scores_map[node_id] = []
            chunk_scores_map[node_id].append(chunk_score)

        node_scores = []
        for node_id in candidate_nodes:
            if node_id in chunk_scores_map:
                chunk_scores = chunk_scores_map[node_id]
                doc_node = self._document_tree.get_node(node_id) if self._document_tree else None
                node_depth = doc_node.depth if doc_node else 0
                node_score = self.scorer.compute_node_score(
                    chunk_scores, node_id, depth=node_depth, query=query
                )
                node_scores.append(node_score)
            else:
                node_scores.append(NodeScore(node_id=node_id, raw_score=0.0))

        node_scores = self.scorer.normalize_scores(node_scores)
        return {ns.node_id: ns.normalized_score for ns in node_scores}

    def clear_index(self) -> None:
        """Clear the chunk index and document tree reference."""
        with self._lock:
            self._chunk_embeddings = None
            self._chunk_node_map = []
            self._chunk_contents = []
            self._document_tree = None
            self._query_embedding_cache = None
            self._cached_query = None

    @property
    def index_size(self) -> int:
        """Get the number of indexed chunks."""
        if self._chunk_embeddings is None:
            return 0
        return len(self._chunk_embeddings)
