"""
Dependency Injection for FastAPI
Wraps the existing Services class from the core system.
Loads config from .env file.
"""

import os
from typing import Optional
from dotenv import load_dotenv

from core.book_manager import BookManager
from core.hybrid_search import HybridSearchEngine, SearchOptions
from quiz.quiz_generator import QuizGenerator
from quiz.quiz_engine import QuizEngine
from core.streaming_client import StreamingLLMClient
from api.prompts import Prompts

load_dotenv()

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/owl-alpha")

BOOK_CACHE_DIR = os.getenv("BOOK_CACHE_DIR", "./book_cache")
VECTOR_INDEX_DIR = os.getenv("VECTOR_INDEX_DIR", "./vector_index")
QUIZ_STORAGE_DIR = os.getenv("QUIZ_STORAGE_DIR", "./quiz_data")

DEFAULT_SUBJECT = os.getenv("DEFAULT_SUBJECT", "Computer Science")
DEFAULT_GRADE = os.getenv("DEFAULT_GRADE", "9")


class Services:
    """Lazy-initialized services — singleton per process."""

    def __init__(self):
        self._book_manager = None
        self._quiz_generator = None
        self._quiz_engine = None
        self._llm = None
        self._active_book_id = None
        self._active_engine = None
        self._active_tree = None
        self._prompts = Prompts()

    @property
    def book_manager(self):
        if self._book_manager is None:
            self._book_manager = BookManager(
                local_cache_dir=BOOK_CACHE_DIR,
                vector_index_dir=VECTOR_INDEX_DIR,
            )
        return self._book_manager

    @property
    def quiz_generator(self):
        if self._quiz_generator is None:
            self._quiz_generator = QuizGenerator(
                api_key=OPENROUTER_KEY,
                model=OPENROUTER_MODEL,
                use_streaming=True,
            )
        return self._quiz_generator

    @property
    def quiz_engine(self):
        if self._quiz_engine is None:
            self._quiz_engine = QuizEngine(storage_dir=QUIZ_STORAGE_DIR)
        return self._quiz_engine

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

    def search(self, query: str, max_results: int = 5):
        if self._active_engine is None:
            raise RuntimeError("No book loaded")
        options = SearchOptions(max_results=max_results)
        response = self._active_engine.search(query, options)
        return response.results

    def ask_stream(self, query: str, max_results: int = 3):
        """Streaming ask with custom prompts."""
        results = self.search(query, max_results)
        if not results:
            yield "No relevant content found."
            return

        context = "\n\n".join(
            f"Source: {r.get('title', 'Untitled')}\n{r.get('content', '')}"
            for r in results
        )

        prompt = self._prompts.ask_stream(
            context=context,
            query=query,
            subject=DEFAULT_SUBJECT,
            grade=DEFAULT_GRADE,
        )

        if self.llm is None:
            yield "[LLM not configured]"
            return

        yield from self.llm.stream_complete(
            prompt,
            system=self._prompts.teacher_system(DEFAULT_SUBJECT, DEFAULT_GRADE),
        )

    def generate_quiz(self, chapter_id: str, chapter_name: str):
        if self._active_tree is None:
            raise RuntimeError("No book loaded.")
        quiz = self.quiz_generator.generate_chapter_quiz(
            self._active_tree,
            DEFAULT_SUBJECT,
            DEFAULT_GRADE,
            chapter_id,
            chapter_name,
            book_id=self._active_book_id or "",
        )
        return quiz

    def grade_quiz(self, quiz_id: str, responses: list, user_id: str = "default"):
        return self.quiz_engine.grade_attempt(quiz_id, responses, user_id)

    def _get_chapter_nodes(self, chapter_id: str):
        return self.quiz_generator._get_chapter_nodes(self._active_tree, chapter_id)

    def close(self):
        if self._llm:
            self._llm.close()


_services_instance: Optional[Services] = None


def get_services() -> Services:
    global _services_instance
    if _services_instance is None:
        _services_instance = Services()
    return _services_instance
