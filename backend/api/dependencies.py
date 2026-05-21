"""
Dependency Injection for FastAPI
Wraps the existing Services class from the core system.
Loads config from .env file.
"""

import os
from typing import Optional, AsyncGenerator
from dotenv import load_dotenv

from core.book_manager import BookManager
from quiz.quiz_generator import QuizGenerator
from core.streaming_client import StreamingLLMClient
from core.embeddings import EmbeddingManager
from api.prompts import Prompts
from core.hybrid_search import SearchOptions

load_dotenv()

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/owl-alpha")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nvidia/llama-nemotron-embed-vl-1b-v2:free")

VECTOR_INDEX_DIR = os.getenv("VECTOR_INDEX_DIR", "./vector_index")


class Services:
    """Lazy-initialized services - singleton per process."""

    def __init__(self):
        self._book_manager = None
        self._quiz_generator = None
        self._llm = None
        self._embedding_manager = None
        self._active_book_id = None
        self._active_engine = None
        self._active_tree = None
        self._active_book_title = None
        self._prompts = Prompts()

    @property
    def embedding_manager(self):
        if self._embedding_manager is None:
            self._embedding_manager = EmbeddingManager(
                api_key=OPENROUTER_KEY,
                model_name=EMBEDDING_MODEL,
                embedding_dim=2048,
            )
        return self._embedding_manager

    @property
    def book_manager(self):
        if self._book_manager is None:
            self._book_manager = BookManager(
                vector_index_dir=VECTOR_INDEX_DIR,
                embedding_manager=self.embedding_manager,
            )
        return self._book_manager

    @property
    def quiz_generator(self):
        if self._quiz_generator is None:
            self._quiz_generator = QuizGenerator(
                api_key=OPENROUTER_KEY,
                model=OPENROUTER_MODEL,
            )
        return self._quiz_generator

    @property
    def llm(self):
        if self._llm is None and OPENROUTER_KEY:
            self._llm = StreamingLLMClient(
                api_key=OPENROUTER_KEY,
                model=OPENROUTER_MODEL,
            )
        return self._llm

    @property
    def prompts(self):
        return self._prompts

    def load_book(self, book_id: str):
        if self._active_book_id == book_id and self._active_engine is not None:
            return
        book_data = self.book_manager.load_book(book_id)
        self._active_book_id = book_id
        self._active_engine = book_data["engine"]
        self._active_tree = book_data["tree"]
        self._active_book_title = book_data["metadata"].title

    def search(self, query: str, max_results: int = 5):
        if self._active_engine is None:
            raise RuntimeError("No book loaded")
        options = SearchOptions(max_results=max_results)
        response = self._active_engine.search(query, options)
        return response.results

    async def ask_stream(self, query: str, max_results: int = 3) -> AsyncGenerator[str, None]:
        """Async streaming ask with custom prompts."""
        results = self.search(query, max_results)
        if not results:
            yield "No relevant content found."
            return

        context = "\n\n".join(
            f"Source: {r.get('title', 'Untitled')}\n{r.get('content', '')}"
            for r in results
        )
        book_title = self._active_book_title or ""

        prompt = self._prompts.ask_stream(
            query=query,
            context=context,
            book_title=book_title,
        )

        if self.llm is None:
            yield "[LLM not configured]"
            return

        system_msg = self._prompts.teacher_system(book_title)
        async for token in self.llm.stream_complete(prompt, system=system_msg):
            yield token

    def generate_quiz(self, chapter_id: str):
        if self._active_tree is None:
            raise RuntimeError("No book loaded.")
        return self.quiz_generator.generate_quiz(
            self._active_tree,
            "chapter",
            chapter_id=chapter_id,
            book_id=self._active_book_id or "",
            book_title=self._active_book_title or "",
        )

    def _get_chapter_nodes(self, chapter_id: str):
        return self.quiz_generator._get_chapter_nodes(self._active_tree, chapter_id)

    async def close(self):
        if self._llm:
            await self.llm.close()
        if self._embedding_manager:
            self._embedding_manager.close()


_services_instance: Optional[Services] = None


def get_services() -> Services:
    global _services_instance
    if _services_instance is None:
        _services_instance = Services()
    return _services_instance