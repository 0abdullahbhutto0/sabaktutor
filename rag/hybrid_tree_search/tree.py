"""
Document Tree Structure Module
================================
Implements the hierarchical tree structure for documents with support for
chunks and node metadata.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid


class NodeType(str, Enum):
    """Types of nodes in the document tree."""
    ROOT = "root"
    DOCUMENT = "document"
    CHAPTER = "chapter"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    CHUNK = "chunk"


@dataclass
class Chunk:
    """Represents a text chunk with optional embedding."""
    id: str = ""
    content: str = ""
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())

  
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            content=data["content"],
            embedding=data.get("embedding"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TreeNode:
    """Represents a node in the document tree."""
    id: str = ""
    node_type: NodeType = NodeType.PARAGRAPH
    content: str = ""
    title: Optional[str] = None
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    chunks: List[Chunk] = field(default_factory=list)
    depth: int = 0
    path: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_index: int = 0
    end_index: int = 0

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())

    @property
    def is_root(self) -> bool:
        return self.node_type == NodeType.ROOT

    @property
    def num_chunks(self) -> int:
        return len(self.chunks)

    def add_chunk(self, chunk: Chunk) -> None:
        """Add a chunk to this node if not already present."""
        if not any(c.id == chunk.id for c in self.chunks):
            self.chunks.append(chunk)

    def to_dict(self) -> Dict[str, Any]:
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
            "start_index": self.start_index,
            "end_index": self.end_index,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TreeNode":
        chunks = [Chunk.from_dict(c) for c in data.get("chunks", [])]
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            node_type=NodeType(data.get("node_type", "paragraph")),
            content=data.get("content", ""),
            title=data.get("title"),
            parent_id=data.get("parent_id"),
            children_ids=data.get("children_ids", []),
            chunks=chunks,
            depth=data.get("depth", 0),
            path=data.get("path", ""),
            metadata=data.get("metadata", {}),
            start_index=data.get("start_index", 0),
            end_index=data.get("end_index", 0),
        )


@dataclass
class DocumentTree:
    """Hierarchical tree structure for documents."""
    root_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nodes: Dict[str, TreeNode] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
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

    def add_node(
        self,
        node: TreeNode,
        parent_id: Optional[str] = None,
    ) -> TreeNode:
        """Add a node to the tree under the specified parent."""
        if parent_id is None:
            parent_id = self.root_id

        parent = self.nodes.get(parent_id)
        if parent is None:
            raise ValueError("Parent node not found")

        node.parent_id = parent_id
        node.depth = parent.depth + 1
        node.path = "/" + node.id if parent.path == "/" else parent.path + "/" + node.id

        if node.id not in parent.children_ids:
            parent.children_ids.append(node.id)

        self.nodes[node.id] = node
        return node

    def get_node(self, node_id: str) -> Optional[TreeNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)
    
    def print_tree(self, max_content_length: int = 80) -> str:
        """
        Print the tree structure as a formatted string.
        Shows hierarchy, node IDs, titles, and content previews.

        Args:
            max_content_length: Truncate content previews to this length

        Returns:
            Formatted string representation of the tree
        """
        lines = []
        lines.append("=" * 60)
        lines.append("DOCUMENT TREE STRUCTURE")
        lines.append("=" * 60)

        root = self.nodes.get(self.root_id)
        if not root:
            return "Empty tree"

        def format_node(node: TreeNode, depth: int, prefix: str = ""):
            indent = "  " * depth
            node_id = node.metadata.get("node_id", node.id)

            # Build info line
            title = node.title or "Untitled"
            chunk_count = len(node.chunks)
            content_preview = ""
            if node.content:
                preview = node.content[:max_content_length].replace("\n", " ")
                if len(node.content) > max_content_length:
                    preview += "..."
                content_preview = f" | {preview}"

            lines.append(f"{indent}{prefix}[{node_id}] {title} ({chunk_count} chunks){content_preview}")

            # Recurse to children
            for i, child_id in enumerate(node.children_ids):
                child = self.nodes.get(child_id)
                if child:
                    is_last = (i == len(node.children_ids) - 1)
                    child_prefix = "└── " if is_last else "├── "
                    format_node(child, depth + 1, child_prefix)

        # Start from root's children (chapters)
        for i, child_id in enumerate(root.children_ids):
            child = self.nodes.get(child_id)
            if child:
                is_last = (i == len(root.children_ids) - 1)
                prefix = "└── " if is_last else "├── "
                format_node(child, 0, prefix)

        lines.append("=" * 60)
        lines.append(f"Total nodes: {self.get_node_count()}")
        lines.append(f"Root ID: {self.root_id}")
        lines.append("=" * 60)

        return "\n".join(lines)

    def get_node_path(self, node_id: str) -> List[str]:
        """
        Get the path from root to a specific node.

        Args:
            node_id: Target node ID

        Returns:
            List of node titles from root to target
        """
        path = []
        current = self.nodes.get(node_id)
        while current:
            path.append(current.title or current.id)
            current = self.nodes.get(current.parent_id) if current.parent_id else None
        return list(reversed(path))


    def get_all_nodes(self, node_type: Optional[NodeType] = None) -> List[TreeNode]:
        """Get all nodes, optionally filtered by type."""
        if node_type is None:
            return list(self.nodes.values())
        return [n for n in self.nodes.values() if n.node_type == node_type]

    def get_chapter_nodes(self, chapter_node_id: str) -> List["TreeNode"]:
        """
        Get all nodes belonging to a specific chapter.
        Includes the chapter node itself + all descendants.

        Args:
            chapter_node_id: ID of the chapter node (top-level node under root)

        Returns:
            List of TreeNode objects in this chapter
        """
        chapter_nodes = []

        # Verify the node exists and is a direct child of root (i.e., a chapter)
        chapter_node = self.nodes.get(chapter_node_id)
        if not chapter_node:
            return []

        # Collect chapter + all descendants recursively
        def collect_descendants(node_id: str):
            node = self.nodes.get(node_id)
            if not node:
                return
            chapter_nodes.append(node)
            for child_id in node.children_ids:
                collect_descendants(child_id)

        collect_descendants(chapter_node_id)
        return chapter_nodes

    def get_chapters(self) -> List["TreeNode"]:
        """
        Get all top-level chapters (direct children of root).

        Returns:
            List of chapter TreeNode objects
        """
        root = self.nodes.get(self.root_id)
        if not root:
            return []

        chapters = []
        for child_id in root.children_ids:
            node = self.nodes.get(child_id)
            if node:
                chapters.append(node)
        return chapters

    def get_node_count(self) -> int:
        """Get total number of nodes."""
        return len(self.nodes)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_id": self.root_id,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentTree":
        tree = cls(
            root_id=data.get("root_id", str(uuid.uuid4())),
            metadata=data.get("metadata", {}),
        )
        tree.nodes = {k: TreeNode.from_dict(v) for k, v in data["nodes"].items()}
        return tree
