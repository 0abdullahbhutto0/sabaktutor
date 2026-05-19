"""
Book Manager Module (Simplified - No Metadata Files)
=====================================================
Books loaded directly from JSON files in root directory.
No metadata persistence needed.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from core.tree import DocumentTree, TreeNode, Chunk, NodeType
from core.hybrid_search import HybridSearchEngine
import uuid


@dataclass
class BookMetadata:
    """Simple metadata for a stored book (in-memory only)."""
    book_id: str
    title: str
    subject: str
    grade: str
    file_path: str
    is_indexed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "book_id": self.book_id,
            "title": self.title,
            "subject": self.subject,
            "grade": self.grade,
            "file_path": self.file_path,
            "is_indexed": self.is_indexed,
        }


class BookManager:
    """
    Manages books loaded directly from JSON files.
    """

    def __init__(
        self,
        local_cache_dir: str = "./book_cache",
        vector_index_dir: str = "./vector_index",
    ):
        self.local_cache_dir = Path(local_cache_dir)
        self.vector_index_dir = Path(vector_index_dir)
        self.local_cache_dir.mkdir(parents=True, exist_ok=True)
        self.vector_index_dir.mkdir(parents=True, exist_ok=True)

        self._active_books: Dict[str, Any] = {}
        self._metadata_cache: Dict[str, BookMetadata] = {}

    def register_book(
        self,
        book_id: str,
        title: str,
        subject: str,
        grade: str,
        file_path: str,
    ) -> BookMetadata:
        """Register a new book in memory."""
        metadata = BookMetadata(
            book_id=book_id,
            title=title,
            subject=subject,
            grade=grade,
            file_path=file_path,
        )
        self._metadata_cache[book_id] = metadata
        return metadata

    def load_book(self, book_id: str, force_reload: bool = False) -> Dict[str, Any]:
        """Load a book's tree and search engine."""
        if not force_reload and book_id in self._active_books:
            return self._active_books[book_id]

        metadata = self._get_metadata(book_id)
        if metadata and Path(metadata.file_path).exists():
            book_data = self._load_from_file(metadata)
            self._active_books[book_id] = book_data
            return book_data

        raise ValueError(f"Book {book_id} not found or file missing: {metadata.file_path if metadata else 'N/A'}")

    def get_book(self, book_id: str) -> Optional[BookMetadata]:
        """Get book metadata."""
        return self._metadata_cache.get(book_id)

    def list_books(
        self,
        subject: Optional[str] = None,
        grade: Optional[str] = None,
    ) -> List[BookMetadata]:
        """List all registered books."""
        books = list(self._metadata_cache.values())

        if subject:
            books = [b for b in books if b.subject == subject]
        if grade:
            books = [b for b in books if b.grade == grade]

        return sorted(books, key=lambda b: (b.subject, b.grade, b.title))

    def delete_book(self, book_id: str) -> bool:
        """Delete a book from memory."""
        if book_id in self._active_books:
            del self._active_books[book_id]
        if book_id in self._metadata_cache:
            del self._metadata_cache[book_id]
        return True

    def _get_metadata(self, book_id: str) -> Optional[BookMetadata]:
        """Get metadata from cache."""
        return self._metadata_cache.get(book_id)

    def _load_from_file(self, metadata: BookMetadata) -> Dict[str, Any]:
        """Load book from JSON file."""
        with open(metadata.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        tree = DocumentTree()

        def infer_node_type(title: str) -> NodeType:
            t = (title or "").strip().upper()
            if t in ("COMPUTER SCIENCE", "ROOT", "BOOK"):
                return NodeType.ROOT
            if t[:2].replace(".", "").isdigit():
                return NodeType.CHAPTER
            if t[:3].replace(".", "").isdigit():
                return NodeType.SECTION
            return NodeType.PARAGRAPH

        def process(nodes, parent_id=None):
            for n in nodes:
                node_id = n.get("node_id") or str(uuid.uuid4())[:8]
                content = n.get("text") or n.get("content", "")
                title = n.get("title", "")
                children = n.get("nodes", [])

                if str(node_id) in ("0", "0000"):
                    if children:
                        process(children, tree.root_id)
                    continue

                node = TreeNode(
                    id=node_id,
                    node_type=infer_node_type(title),
                    content=content,
                    title=title,
                )

                if content:
                    node.add_chunk(Chunk(content=content))

                tree.add_node(node, parent_id or tree.root_id)

                if children:
                    process(children, node.id)

        if isinstance(data, list):
            process(data)
        else:
            process(data.get("nodes", [data]))

        vector_path = str(self.vector_index_dir / metadata.book_id)
        engine = HybridSearchEngine(
            vector_store_path=vector_path,
            book_id=metadata.book_id,
        )

        engine.index_tree(tree)
        metadata.is_indexed = True

        return {
            "tree": tree,
            "engine": engine,
            "metadata": metadata,
        }
