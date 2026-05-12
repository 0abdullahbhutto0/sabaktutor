"""
Document Tree Structure Module
================================
Implements the hierarchical tree structure for documents with support for
chunks and node metadata.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set, Tuple
from enum import Enum
from datetime import datetime
import uuid
import hashlib


class NodeType(str, Enum):
    """Types of nodes in the document tree."""
    ROOT = "root"
    DOCUMENT = "document"
    CHAPTER = "chapter"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    CHUNK = "chunk"


class NodeStatus(str, Enum):
    """Status of a node during processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Chunk:
    """Represents a content chunk within a node."""
    id: str = ""
    content: str = ""
    start_char: int = 0
    end_char: int = 0
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize chunk with unique ID if not provided."""
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.end_char == 0:
            self.end_char = len(self.content)

    @property
    def length(self) -> int:
        """Get the length of the chunk content."""
        return self.end_char - self.start_char

    @property
    def text(self) -> str:
        """Get the chunk content."""
        return self.content

    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        """Create chunk from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            content=data["content"],
            start_char=data.get("start_char", 0),
            end_char=data.get("end_char", len(data["content"])),
            embedding=data.get("embedding"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TreeNode:
    """Represents a node in the document tree."""
    id: str = ""  # Default empty, UUID generated in __post_init__
    node_type: NodeType = NodeType.PARAGRAPH
    content: str = ""
    title: Optional[str] = None
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    chunks: List[Chunk] = field(default_factory=list)
    depth: int = 0
    path: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: NodeStatus = NodeStatus.PENDING
    embedding: Optional[List[float]] = None
    summary: Optional[str] = None
    start_index: int = 0
    end_index: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # MCTS-related attributes
    visit_count: int = 0
    value_estimate: float = 0.0
    prior_probability: float = 0.0

    def __post_init__(self):
        """Initialize node with unique ID if not provided."""
        if not self.id:
            import uuid
            self.id = str(uuid.uuid4())

    @property
    def is_leaf(self) -> bool:
        """Check if this is a leaf node."""
        return len(self.children_ids) == 0

    @property
    def is_root(self) -> bool:
        """Check if this is the root node."""
        return self.node_type == NodeType.ROOT

    @property
    def num_chunks(self) -> int:
        """Get the number of chunks in this node."""
        return len(self.chunks)

    @property
    def has_embedding(self) -> bool:
        """Check if node has an embedding."""
        return self.embedding is not None

    @property
    def full_path(self) -> str:
        """Get the full path to this node."""
        return self.path


    def get_all_text(self, include_chunks: bool = True) -> str:
        """Get all text content from this node and its descendants."""
        texts = [self.content]
        for chunk in self.chunks:
            if include_chunks and chunk.content not in texts:
                texts.append(chunk.content)
        return "\n".join(texts)

    def add_chunk(self, chunk: Chunk) -> None:
        """Add a chunk to this node."""
        if chunk not in self.chunks:
            self.chunks.append(chunk)
            self.updated_at = datetime.now()

    def remove_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """Remove a chunk from this node by ID."""
        for i, chunk in enumerate(self.chunks):
            if chunk.id == chunk_id:
                self.chunks.pop(i)
                self.updated_at = datetime.now()
                return chunk
        return None

    def get_chunk_by_id(self, chunk_id: str) -> Optional[Chunk]:
        """Get a chunk by its ID."""
        for chunk in self.chunks:
            if chunk.id == chunk_id:
                return chunk
        return None

    def get_chunk_embeddings(self) -> List[List[float]]:
        """Get embeddings for all chunks."""
        return [chunk.embedding for chunk in self.chunks if chunk.embedding is not None]

    def get_ancestor_ids(self, max_depth: Optional[int] = None) -> List[str]:
        """Get IDs of all ancestors up to max_depth levels."""
        ancestors = []
        current_depth = self.depth
        if max_depth is not None and max_depth >= 0:
            current_depth = min(self.depth, max_depth)
        for _ in range(current_depth):
            ancestors.append(self.parent_id or "")
        return ancestors

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary."""
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "content": self.content,
            "title": self.title,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "chunks": [c.to_dict() for c in self.chunks],
            "depth": self.depth,
            "path": self.path,
            "metadata": self.metadata,
            "status": self.status.value,
            "embedding": self.embedding,
            "summary": self.summary,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "visit_count": self.visit_count,
            "value_estimate": self.value_estimate,
            "prior_probability": self.prior_probability,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TreeNode":
        """Create node from dictionary."""
        chunks = [Chunk.from_dict(c) for c in data.get("chunks", [])]
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            node_type=NodeType(data.get("node_type", "paragraph")),
            content=data["content"],
            title=data.get("title"),
            parent_id=data.get("parent_id"),
            children_ids=data.get("children_ids", []),
            chunks=chunks,
            depth=data.get("depth", 0),
            path=data.get("path", ""),
            metadata=data.get("metadata", {}),
            status=NodeStatus(data.get("status", "pending")),
            embedding=data.get("embedding"),
            summary=data.get("summary"),
            start_index=data.get("start_index", 0),
            end_index=data.get("end_index", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
            visit_count=data.get("visit_count", 0),
            value_estimate=data.get("value_estimate", 0.0),
            prior_probability=data.get("prior_probability", 0.0),
        )

    def copy(self) -> "TreeNode":
        """Create a shallow copy of this node."""
        return TreeNode(
            id=self.id,
            node_type=self.node_type,
            content=self.content,
            title=self.title,
            parent_id=self.parent_id,
            children_ids=self.children_ids.copy(),
            chunks=self.chunks.copy(),
            depth=self.depth,
            path=self.path,
            metadata=self.metadata.copy(),
            status=self.status,
            embedding=self.embedding.copy() if self.embedding else None,
            summary=self.summary,
            start_index=self.start_index,
            end_index=self.end_index,
            created_at=self.created_at,
            updated_at=self.updated_at,
            visit_count=self.visit_count,
            value_estimate=self.value_estimate,
            prior_probability=self.prior_probability,
        )


@dataclass
class DocumentTree:
    """
    Hierarchical document tree structure with support for efficient
    retrieval operations.
    """

    root_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nodes: Dict[str, TreeNode] = field(default_factory=dict)
    node_index: Dict[str, List[str]] = field(default_factory=dict)  # depth -> node_ids
    content_hash: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize the tree with a root node."""
        if not self.nodes:
            root = TreeNode(
                id=self.root_id,
                node_type=NodeType.ROOT,
                content="",
                title="Root",
                depth=0,
                path="/",
            )
            self.nodes[self.root_id] = root
            self.node_index[0] = [self.root_id]

    def add_node(
        self,
        node: TreeNode,
        parent_id: Optional[str] = None,
        update_index: bool = True
    ) -> TreeNode:
        """
        Add a node to the tree.

        Args:
            node: The node to add
            parent_id: Optional parent node ID (defaults to root)
            update_index: Whether to update the node index

        Returns:
            The added node
        """
        if parent_id is None:
            parent_id = self.root_id

        parent = self.nodes.get(parent_id)
        if parent is None:
            raise ValueError(f"Parent node {parent_id} not found")

        node.parent_id = parent_id
        node.depth = parent.depth + 1

        # Update path
        if parent.path == "/":
            node.path = f"/{node.id}"
        else:
            node.path = f"{parent.path}/{node.id}"

        # Add to parent's children
        if node.id not in parent.children_ids:
            parent.children_ids.append(node.id)

        # Add node to tree
        self.nodes[node.id] = node

        # Update index
        if update_index:
            if node.depth not in self.node_index:
                self.node_index[node.depth] = []
            if node.id not in self.node_index[node.depth]:
                self.node_index[node.depth].append(node.id)

        return node

    def remove_node(self, node_id: str, recursive: bool = False) -> bool:
        """
        Remove a node from the tree.

        Args:
            node_id: ID of the node to remove
            recursive: Whether to recursively remove children

        Returns:
            True if node was removed, False if not found
        """
        node = self.nodes.get(node_id)
        if node is None:
            return False

        if node.is_root:
            return False  # Cannot remove root

        # Remove from parent's children
        parent = self.nodes.get(node.parent_id)
        if parent and node_id in parent.children_ids:
            parent.children_ids.remove(node_id)

        # Handle children
        children_to_remove = []
        if recursive:
            children_to_remove = self.get_descendant_ids(node_id)
        elif node.children_ids:
            # Move children to parent
            for child_id in node.children_ids:
                child = self.nodes.get(child_id)
                if child:
                    child.parent_id = node.parent_id
                    if parent:
                        if child_id not in parent.children_ids:
                            parent.children_ids.append(child_id)

        children_to_remove.append(node_id)

        # Remove nodes
        for cid in children_to_remove:
            if cid in self.nodes:
                del self.nodes[cid]

            # Remove from index
            for depth_nodes in self.node_index.values():
                if cid in depth_nodes:
                    depth_nodes.remove(cid)

        return True

    def get_node(self, node_id: str) -> Optional[TreeNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_parent(self, node_id: str) -> Optional[TreeNode]:
        """Get the parent of a node."""
        node = self.nodes.get(node_id)
        if node and node.parent_id:
            return self.nodes.get(node.parent_id)
        return None

    def get_children(self, node_id: str) -> List[TreeNode]:
        """Get all children of a node."""
        node = self.nodes.get(node_id)
        if not node:
            return []
        return [self.nodes[cid] for cid in node.children_ids if cid in self.nodes]

    def get_ancestors(self, node_id: str) -> List[TreeNode]:
        """Get all ancestors of a node from root to parent."""
        ancestors = []
        current = self.nodes.get(node_id)
        while current and current.parent_id:
            parent = self.nodes.get(current.parent_id)
            if parent:
                ancestors.append(parent)
                current = parent
            else:
                break
        return list(reversed(ancestors))

    def get_descendants(self, node_id: str, max_depth: Optional[int] = None) -> List[TreeNode]:
        """
        Get all descendants of a node.

        Args:
            node_id: ID of the node
            max_depth: Maximum depth to traverse (None for unlimited)

        Returns:
            List of descendant nodes
        """
        descendants = []
        stack = [(node_id, 0)]
        visited = set()

        while stack:
            current_id, depth = stack.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)

            if max_depth is not None and depth >= max_depth:
                continue

            node = self.nodes.get(current_id)
            if not node:
                continue

            descendants.append(node)

            for child_id in node.children_ids:
                if child_id not in visited:
                    stack.append((child_id, depth + 1))

        return descendants

    def get_descendant_ids(self, node_id: str) -> List[str]:
        """Get IDs of all descendants of a node."""
        descendants = self.get_descendants(node_id)
        return [d.id for d in descendants]

    def get_all_nodes(self, node_type: Optional[NodeType] = None) -> List[TreeNode]:
        """Get all nodes, optionally filtered by type."""
        if node_type is None:
            return list(self.nodes.values())
        return [n for n in self.nodes.values() if n.node_type == node_type]

    def get_leaves(self, node_id: Optional[str] = None) -> List[TreeNode]:
        """Get all leaf nodes, optionally starting from a specific node."""
        if node_id is None:
            node_id = self.root_id

        root = self.nodes.get(node_id)
        if not root:
            return []

        return [n for n in self.get_descendants(node_id) if n.is_leaf]

    def get_nodes_at_depth(self, depth: int) -> List[TreeNode]:
        """Get all nodes at a specific depth."""
        node_ids = self.node_index.get(depth, [])
        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]

    def get_depth(self, node_id: str) -> int:
        """Get the depth of a node."""
        node = self.nodes.get(node_id)
        return node.depth if node else 0

    def get_height(self) -> int:
        """Get the height of the tree."""
        if not self.node_index:
            return 0
        return max(self.node_index.keys())

    def get_node_count(self) -> int:
        """Get total number of nodes."""
        return len(self.nodes)

    def get_chunk_count(self) -> int:
        """Get total number of chunks across all nodes."""
        return sum(len(node.chunks) for node in self.nodes.values())

    def to_dict(self) -> Dict[str, Any]:
        """Convert tree to dictionary."""
        return {
            "root_id": self.root_id,
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "node_index": dict(self.node_index),
            "content_hash": self.content_hash,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentTree":
        """Create tree from dictionary."""
        nodes = {nid: TreeNode.from_dict(n) for nid, n in data["nodes"].items()}
        tree = cls(
            root_id=data.get("root_id", str(uuid.uuid4())),
            content_hash=data.get("content_hash"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            metadata=data.get("metadata", {}),
        )
        tree.nodes = nodes
        tree.node_index = {int(k): v for k, v in data.get("node_index", {}).items()}
        return tree

    @classmethod
    def from_text(
        cls,
        text: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        preserve_paragraphs: bool = True,
    ) -> "DocumentTree":
        """
        Create a tree from raw text.

        Args:
            text: The text content
            chunk_size: Target size for chunks
            chunk_overlap: Overlap between chunks
            preserve_paragraphs: Whether to preserve paragraph structure

        Returns:
            A new DocumentTree
        """
        tree = cls()
        tree.content_hash = hashlib.md5(text.encode()).hexdigest()

        # Add document root
        doc_node = TreeNode(
            node_type=NodeType.DOCUMENT,
            content=text, 
            title="Document",
            metadata={"full_length": len(text)},
        )
        tree.add_node(doc_node)
        document_id = doc_node.id

        # Split into paragraphs
        if preserve_paragraphs:
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        else:
            # Split by sentences or fixed size
            paragraphs = cls._split_text(text, chunk_size)

        # Create paragraph nodes
        for i, para in enumerate(paragraphs):
            para_node = TreeNode(
                node_type=NodeType.PARAGRAPH,
                content=para,
                title=f"Paragraph {i + 1}",
                metadata={"index": i},
            )
            tree.add_node(para_node, parent_id=document_id)

            # Create chunks for paragraph
            chunks = cls._create_chunks(para, chunk_size, chunk_overlap, i)
            for chunk in chunks:
                tree.add_node(chunk, parent_id=para_node.id)

        return tree

    @staticmethod
    def _split_text(text: str, chunk_size: int) -> List[str]:
        """Split text into chunks."""
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0

        for word in words:
            word_size = len(word) + 1  # +1 for space
            if current_size + word_size > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_size = word_size
            else:
                current_chunk.append(word)
                current_size += word_size

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    @staticmethod
    def _create_chunks(text: str, chunk_size: int, chunk_overlap: int, paragraph_index: int) -> List[TreeNode]:
        """Create chunk nodes from text."""
        if len(text) <= chunk_size:
            return [
                TreeNode(
                    node_type=NodeType.CHUNK,
                    content=text,
                    title=f"Chunk {paragraph_index}-0",
                    metadata={"paragraph_index": paragraph_index, "chunk_index": 0},
                    chunks=[
                        Chunk(
                            id=f"chunk-{paragraph_index}-0",
                            content=text,
                            start_char=0,
                            end_char=len(text),
                            metadata={"paragraph_index": paragraph_index, "chunk_index": 0},
                        )
                    ],
                )
            ]

        chunks = []
        chunk_index = 0
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))

            # Try to end at a sentence boundary
            if end < len(text):
                for punct in [". ", "! ", "? ", "; ", "\n"]:
                    last_punct = text.rfind(punct, start, end)
                    if last_punct > start:
                        end = last_punct + len(punct)
                        break

            chunk_content = text[start:end]
            chunk_id = f"chunk-{paragraph_index}-{chunk_index}"

            chunk_node = TreeNode(
                node_type=NodeType.CHUNK,
                content=chunk_content,
                title=f"Chunk {paragraph_index}-{chunk_index}",
                metadata={"paragraph_index": paragraph_index, "chunk_index": chunk_index},
                chunks=[
                    Chunk(
                        id=chunk_id,
                        content=chunk_content,
                        start_char=start,
                        end_char=end,
                        metadata={"paragraph_index": paragraph_index, "chunk_index": chunk_index},
                    )
                ],
            )
            chunks.append(chunk_node)

            chunk_index += 1
            start = end - chunk_overlap
            if start < 0:
                start = 0

        return chunks

    def find_nodes_by_content(self, query: str, max_results: int = 10) -> List[Tuple[TreeNode, float]]:
        """
        Find nodes containing the query text.

        Args:
            query: The search query
            max_results: Maximum number of results

        Returns:
            List of (node, relevance_score) tuples
        """
        query_lower = query.lower()
        results = []

        for node in self.nodes.values():
            if node.is_root:
                continue

            # Simple content matching
            content_lower = node.content.lower()
            if query_lower in content_lower:
                score = content_lower.count(query_lower) / len(node.content)
                results.append((node, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:max_results]

    def get_subtree(self, node_id: str) -> List[TreeNode]:
        """Get a node and all its descendants."""
        node = self.nodes.get(node_id)
        if not node:
            return []
        return [node] + self.get_descendants(node_id)