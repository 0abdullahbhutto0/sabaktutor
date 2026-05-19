"""
Value Function and Node Scorer Module
=====================================
Now uses FAISS vector store to persist embeddings.
Falls back to computing if not in store.
"""

from typing import List, Dict, Optional, Any
import numpy as np
from dataclasses import dataclass
import threading
import time
from core.vector_store import FaissVectorStore


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
    """Unchanged — business logic stays the same."""
    
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


@dataclass
class IndexTiming:
    """Tracks timing for index_tree operations."""
    total_time_ms: float = 0.0
    node_iteration_time_ms: float = 0.0
    text_chunking_time_ms: float = 0.0
    embedding_generation_time_ms: float = 0.0
    index_build_time_ms: float = 0.0
    nodes_processed: int = 0
    chunks_created: int = 0
    chunks_embedded: int = 0
    chunks_pre_embedded: int = 0
    chunks_loaded_from_store: int = 0  

    def report(self) -> str:
        """Pretty print timing report."""
        return f"""
╔══════════════════════════════════════════════════════════════╗
║                    INDEXING TIMING REPORT                    ║
╠══════════════════════════════════════════════════════════════╣
║  Total Time              : {self.total_time_ms:.2f} ms ({self.total_time_ms/1000:.2f}s)
║  Node Iteration          : {self.node_iteration_time_ms:.2f} ms
║  Text Chunking           : {self.text_chunking_time_ms:.2f} ms
║  Embedding Generation    : {self.embedding_generation_time_ms:.2f} ms
║  Index Build             : {self.index_build_time_ms:.2f} ms
╠══════════════════════════════════════════════════════════════╣
║  Nodes Processed         : {self.nodes_processed}
║  Chunks Created          : {self.chunks_created}
║  Chunks Embedded         : {self.chunks_embedded}
║  Pre-embedded Chunks     : {self.chunks_pre_embedded}
║  Loaded from Store       : {self.chunks_loaded_from_store}  ← NEW
╚══════════════════════════════════════════════════════════════╝
        """


class ValueFunction:
    """
    Main value function for predicting node relevance using embeddings.
    NOW USES FAISS VECTOR STORE for persistence.
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
            embedding_dim=getattr(embedding_manager, 'embedding_dim', 384),
        )

        self._document_tree: Optional[Any] = None
        self._lock = threading.Lock()

        self._query_embedding_cache: Optional[np.ndarray] = None
        self._cached_query: Optional[str] = None
        
        self.last_timing: Optional[IndexTiming] = None

    def index_chunks(self, chunks: List[Dict], node_ids: List[str]) -> None:
        """Index chunks — now adds to FAISS store."""
        if not chunks:
            return

        with self._lock:
            for chunk, node_id in zip(chunks, node_ids):
                content = chunk.get("content", "")
                embedding = chunk.get("embedding")
                
                if embedding is not None:
                    self.vector_store.add(
                        record_id=node_id,
                        vector=embedding if isinstance(embedding, np.ndarray) else np.array(embedding),
                        content=content,
                        metadata={"node_id": node_id},
                    )

    def index_tree(self, tree, show_progress: bool = False) -> IndexTiming:
        """
        Index all chunks from a document tree.
        Uses vector store — loads existing embeddings, computes only missing ones.
        """
        timing = IndexTiming()
        start_total = time.perf_counter()
        
        print("\n🚀 [INDEX TREE START]")
        print(f"Total nodes in tree: {tree.get_node_count()}")
        self._document_tree = tree

        all_chunks = []
        all_node_ids = []
        contents_to_encode = []
        contents_map = {}

        chunk_size = 200
        chunk_overlap = 30
        
        start_nodes = time.perf_counter()

        for i, node in enumerate(tree.get_all_nodes()):
            if node.is_root:
                continue

            content = node.content.strip()
            if not content:
                continue

            timing.nodes_processed += 1

            if node.chunks:
                for chunk in node.chunks:
                    if chunk.content.strip():
                        if self.vector_store.exists(node.id):
                            timing.chunks_pre_embedded += 1
                            timing.chunks_loaded_from_store += 1                       
                        else:
                            contents_to_encode.append(chunk.content)
                            contents_map[chunk.content] = node.id
            else:
                node_chunks = self._chunk_text(content, chunk_size, chunk_overlap)
                timing.chunks_created += len(node_chunks)
                
                for chunk_text in node_chunks:
                    if not chunk_text.strip():
                        continue
                    if self.vector_store.exists(node.id):
                        timing.chunks_loaded_from_store += 1
                    else:
                        contents_to_encode.append(chunk_text)
                        contents_map[chunk_text] = node.id

        timing.node_iteration_time_ms = (time.perf_counter() - start_nodes) * 1000

        print(f"\n📊 PRE-EMBEDDING SUMMARY")
        print(f"To embed: {len(contents_to_encode)}")
        print(f"Already in store: {timing.chunks_loaded_from_store}")
        
        if contents_to_encode:
            print(f"\nGENERATING {len(contents_to_encode)} NEW EMBEDDINGS...")
            
            start_embed = time.perf_counter()
            embeddings = self.embedding_manager.encode(
                contents_to_encode,
                batch_size=32,
                show_progress=show_progress
            )
            timing.embedding_generation_time_ms = (time.perf_counter() - start_embed) * 1000
            timing.chunks_embedded = len(contents_to_encode)
            for i, content in enumerate(contents_to_encode):
                node_id = contents_map[content]
                embedding = embeddings[i] if len(embeddings.shape) > 1 else embeddings
             
                if not self.vector_store.exists(node_id):
                    self.vector_store.add(
                        record_id=node_id,
                        vector=embedding if isinstance(embedding, np.ndarray) else np.array(embedding),
                        content=content,
                        metadata={"node_id": node_id},
                    )
        self.vector_store.save()
                
        timing.total_time_ms = (time.perf_counter() - start_total) * 1000
        self.last_timing = timing

        return timing

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
        """
        Predict value estimates for candidate nodes.
        NOW USES FAISS SEARCH instead of manual cosine similarity.
        """
        if not candidate_nodes or self.vector_store.count() == 0:
            return {node_id: 0.5 for node_id in candidate_nodes}

        query_embedding = self._get_query_embedding(query)

        results = self.vector_store.search(query_embedding, top_k=self.top_k)
        chunk_scores_map: Dict[str, List[ChunkScore]] = {}
        for node_id, score, content in results:
            chunk_score = ChunkScore(
                node_id=node_id,
                score=score,
                content=content,
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
            self.vector_store.clear()
            self._document_tree = None
            self._query_embedding_cache = None
            self._cached_query = None

    @property
    def index_size(self) -> int:
        """Get the number of indexed chunks."""
        return self.vector_store.count()