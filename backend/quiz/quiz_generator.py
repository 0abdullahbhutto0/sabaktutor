"""
Quiz Generator Module
=====================
Generates Sindh Board quizzes with:
- Async streaming LLM support - tokens streamed as they arrive
- Mixed quiz generation: board-pattern MCQs + true_false + fill_in_blank + mcq_calculation
- Full chapter content passed to LLM (no node sampling)
- Lesson generation (flashcards)
- No storage dependency
"""

import json
import uuid
import random
from typing import List, Dict, Optional, Any, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from collections import Counter

from core.streaming_client import StreamingLLMClient
from api.prompts import Prompts


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


# =============================================================================
# STANDARD MCQ TYPES (kept for backward compatibility and mixed quiz)
# =============================================================================

@dataclass
class MCQOption:
    text: str
    is_correct: bool = False


@dataclass
class MCQQuestion:
    id: str = ""
    stem: str = ""
    options: List[MCQOption] = field(default_factory=list)
    source_node_id: str = ""
    difficulty: Difficulty = Difficulty.MEDIUM
    topic: str = ""
    marks: int = 1
    time_estimate_seconds: int = 60
    pattern_used: str = ""  

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "stem": self.stem,
            "options": [{"text": o.text, "is_correct": o.is_correct} for o in self.options],
            "correct_index": next((i for i, o in enumerate(self.options) if o.is_correct), 0),
            "source_node_id": self.source_node_id,
            "difficulty": self.difficulty.value,
            "topic": self.topic,
            "marks": self.marks,
            "time_estimate_seconds": self.time_estimate_seconds,
            "pattern_used": self.pattern_used,
            "type": "mcq",
        }


@dataclass
class Quiz:
    id: str = ""
    quiz_type: str = "chapter"
    book_title: str = ""
    title: str = ""
    chapter_ids: List[str] = field(default_factory=list)
    chapter_names: List[str] = field(default_factory=list)
    questions: List[MCQQuestion] = field(default_factory=list)
    duration_minutes: int = 20
    passing_percent: int = 60
    created_at: float = 0.0
    book_id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:12]
        if not self.created_at:
            import time
            self.created_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "quiz_type": self.quiz_type,
            "title": self.title,
            "chapter_ids": self.chapter_ids,
            "chapter_names": self.chapter_names,
            "questions": [q.to_dict() for q in self.questions],
            "duration_minutes": self.duration_minutes,
            "passing_percent": self.passing_percent,
            "created_at": self.created_at,
            "total_marks": sum(q.marks for q in self.questions),
            "question_count": len(self.questions),
            "book_id": self.book_id,
        }


# =============================================================================
# INTERACTIVE / MIXED QUIZ TYPES
# =============================================================================

@dataclass
class TrueFalseItem:
    id: str = ""
    statement: str = ""
    is_true: bool = True
    explanation: str = ""
    type: str = "true_false"
    source_node_id: str = ""
    difficulty: str = "medium"
    marks: int = 1

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "statement": self.statement,
            "is_true": self.is_true,
            "explanation": self.explanation,
            "source_node_id": self.source_node_id,
            "difficulty": self.difficulty,
            "marks": self.marks,
        }


@dataclass
class FillInBlankItem:
    id: str = ""
    sentence_before: str = ""
    blank_answer: str = ""
    sentence_after: str = ""
    type: str = "fill_in_blank"
    source_node_id: str = ""
    difficulty: str = "medium"
    marks: int = 1

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "sentence_before": self.sentence_before,
            "blank_answer": self.blank_answer,
            "sentence_after": self.sentence_after,
            "source_node_id": self.source_node_id,
            "difficulty": self.difficulty,
            "marks": self.marks,
        }


@dataclass
class MCQCalculationItem:
    id: str = ""
    problem: str = ""
    options: List[str] = field(default_factory=list)
    correct_index: int = 0
    explanation: str = ""
    type: str = "mcq_calculation"
    source_node_id: str = ""
    difficulty: str = "medium"
    marks: int = 2

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "problem": self.problem,
            "options": self.options,
            "correct_index": self.correct_index,
            "explanation": self.explanation,
            "source_node_id": self.source_node_id,
            "difficulty": self.difficulty,
            "marks": self.marks,
        }


@dataclass
class InteractiveQuiz:
    """Mixed quiz: board-pattern MCQs + true_false + fill_in_blank + mcq_calculation"""
    id: str = ""
    book_id: str = ""
    title: str = ""
    chapter_ids: List[str] = field(default_factory=list)
    items: List[Any] = field(default_factory=list)
    created_at: float = 0.0
    duration_minutes: int = 20
    passing_percent: int = 60

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:12]
        if not self.created_at:
            import time
            self.created_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        total_marks = sum(
            getattr(item, 'marks', 1) for item in self.items
        )
        return {
            "id": self.id,
            "book_id": self.book_id,
            "title": self.title,
            "chapter_ids": self.chapter_ids,
            "items": [item.to_dict() for item in self.items],
            "created_at": self.created_at,
            "duration_minutes": self.duration_minutes,
            "passing_percent": self.passing_percent,
            "total_marks": total_marks,
            "item_count": len(self.items),
            "breakdown": {
                "mcq": len([i for i in self.items if getattr(i, 'type', '') == "mcq"]),
                "true_false": len([i for i in self.items if getattr(i, 'type', '') == "true_false"]),
                "fill_in_blank": len([i for i in self.items if getattr(i, 'type', '') == "fill_in_blank"]),
                "mcq_calculation": len([i for i in self.items if getattr(i, 'type', '') == "mcq_calculation"]),
            }
        }


# =============================================================================
# LESSON TYPES (Flashcards)
# =============================================================================

@dataclass
class FlashcardItem:
    title: str = ""
    content: str = ""
    type: str = "flashcard"
    source_node_id: str = ""
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "content": self.content,
            "source_node_id": self.source_node_id,
        }


@dataclass
class Lesson:
    book_id: str = ""
    title: str = ""
    chapter_ids: List[str] = field(default_factory=list)
    items: List[FlashcardItem] = field(default_factory=list)
    id: str = ""
    created_at: float = 0.0

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:12]
        if not self.created_at:
            import time
            self.created_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "book_id": self.book_id,
            "title": self.title,
            "chapter_ids": self.chapter_ids,
            "items": [item.to_dict() for item in self.items],
            "created_at": self.created_at,
        }


# =============================================================================
# QUIZ GENERATOR CLASS
# =============================================================================

class QuizGenerator:
    """Generates quizzes with async streaming LLM support."""

    def __init__(
        self,
        api_key: str = "",
        questions_per_node: int = 3,
        model: str = "google/gemini-2.0-flash-001",
    ):
        self.api_key = api_key
        self.model = model
        self.questions_per_node = questions_per_node
        self.llm = StreamingLLMClient(api_key, model) if api_key else None
        self.prompts = Prompts()

    # -------------------------------------------------------------------------
    # MIXED QUIZ GENERATION (NEW - replaces standard quiz streaming)
    # -------------------------------------------------------------------------

    async def generate_mixed_quiz_streaming(
        self,
        document_tree,
        quiz_type: str,
        chapter_id: Optional[str] = None,
        unit_chapters: Optional[List[str]] = None,
        target_count: int = 20,
        duration_minutes: int = 20,
        passing_percent: int = 60,
        book_id: str = "",
        book_title: str = "",
        title: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate mixed quiz (board-pattern MCQs + interactive types) with streaming tokens.
        Uses FULL chapter content — no node sampling.
        """
        if quiz_type == "chapter" and chapter_id:
            nodes = self._get_chapter_nodes(document_tree, chapter_id)
            chapter_ids = [chapter_id]
            default_title = f"{chapter_id} - Mixed Quiz"
        elif quiz_type == "unit" and unit_chapters:
            nodes = []
            chapter_ids = []
            for ch in unit_chapters:
                nodes.extend(self._get_chapter_nodes(document_tree, ch))
                chapter_ids.append(ch)
            default_title = f"Unit Test - Mixed Quiz"
            duration_minutes = 45
            passing_percent = 50
        else:  # full book
            nodes = [n for n in document_tree.get_all_nodes() if not n.is_root and n.content.strip()]
            chapter_ids = []
            default_title = f"{book_id} - Full Book Mixed Quiz"
            duration_minutes = 90
            passing_percent = 50

        # Build content text from ALL nodes — no sampling
        content_nodes = [n for n in nodes if n.content.strip()]
        if not content_nodes:
            yield {"type": "error", "message": "No content available"}
            return

        content_text = self._build_content_text(content_nodes)

        prompt = self.prompts.generate_mixed_quiz(
            content_text=content_text,
            total_items=target_count,
            book_id=book_id,
        )

        if not self.llm:
            yield {"type": "error", "message": "LLM not configured"}
            return

        # Stream tokens as they arrive
        full_response = []
        async for token in self.llm.stream_complete(prompt, max_tokens=12000):
            full_response.append(token)
            yield {"type": "token", "token": token}

        # Parse the complete response
        response_text = "".join(full_response)
        items = self._parse_mixed_quiz_response(response_text, content_nodes)
        items = items[:target_count]

        mixed_quiz = InteractiveQuiz(
            book_id=book_id,
            title=title or default_title,
            chapter_ids=chapter_ids,
            items=items,
            duration_minutes=duration_minutes,
            passing_percent=passing_percent,
        )

        yield {"type": "done", "quiz": mixed_quiz}

    # -------------------------------------------------------------------------
    # LESSON GENERATION (Flashcards)
    # -------------------------------------------------------------------------

    async def generate_lesson_streaming(
        self,
        document_tree,
        chapter_id: str,
        target_count: int = 10,
        book_id: str = "",
        title: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        nodes = self._get_chapter_nodes(document_tree, chapter_id)

        content_nodes = [n for n in nodes if n.content.strip()]
        if not content_nodes:
            yield {"type": "error", "message": "No content available"}
            return

        content_text = self._build_content_text(content_nodes)

        prompt = self.prompts.generate_lesson(
            content_text=content_text,
            total_items=target_count,
            book_id=book_id,
        )

        if not self.llm:
            yield {"type": "error", "message": "LLM not configured"}
            return

        full_response = []
        async for token in self.llm.stream_complete(prompt, max_tokens=12000):
            full_response.append(token)
            yield {"type": "token", "token": token}

        response_text = "".join(full_response)
        items = self._parse_lesson_response(response_text, content_nodes)
        items = items[:target_count]

        lesson = Lesson(
            book_id=book_id,
            title=title or f"{chapter_id} - Lesson",
            chapter_ids=[chapter_id],
            items=items,
        )

        yield {"type": "done", "lesson": lesson}

    # -------------------------------------------------------------------------
    # CONTENT BUILDER — full chapter, no sampling
    # -------------------------------------------------------------------------

    def _build_content_text(self, nodes: List[Any]) -> str:
        """Build content text from ALL nodes. No sampling."""
        content_text = ""
        for i, node in enumerate(nodes, 1):
            content_text += f"--- SECTION {i}: {node.title or 'Untitled'} ---"
            content_text += f"{node.content}"
        return content_text

    # -------------------------------------------------------------------------
    # PARSERS
    # -------------------------------------------------------------------------

    def _parse_mixed_quiz_response(self, response: str, nodes: List[Any]) -> List[Any]:
        """Parse mixed quiz response: mcq, true_false, fill_in_blank, mcq_calculation."""
        try:
            text = response.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            data = json.loads(text.strip())
            if not isinstance(data, list):
                data = [data]

            items = []
            for item in data:
                # Map to a random node from the chapter as source
                source_node = random.choice(nodes) if nodes else None
                source_node_id = source_node.id if source_node else ""

                item_type = item.get("type")

                if item_type == "mcq":
                    opts = [MCQOption(text=o, is_correct=(i == item.get("correct_index", 0)))
                            for i, o in enumerate(item.get("options", []))]
                    if not any(o.is_correct for o in opts):
                        opts[0].is_correct = True

                    items.append(MCQQuestion(
                        stem=item.get("stem", ""),
                        options=opts,
                        source_node_id=source_node_id,
                        difficulty=Difficulty(item.get("difficulty", "medium")),
                        topic=item.get("topic", "general"),
                        marks=item.get("marks", 1),
                        pattern_used=item.get("pattern_used", ""),
                    ))

                elif item_type == "true_false":
                    items.append(TrueFalseItem(
                        statement=item.get("statement", ""),
                        is_true=item.get("is_true", True),
                        explanation=item.get("explanation", ""),
                        source_node_id=source_node_id,
                        difficulty=item.get("difficulty", "medium"),
                        marks=item.get("marks", 1),
                    ))

                elif item_type == "fill_in_blank":
                    items.append(FillInBlankItem(
                        sentence_before=item.get("sentence_before", ""),
                        blank_answer=item.get("blank_answer", ""),
                        sentence_after=item.get("sentence_after", ""),
                        source_node_id=source_node_id,
                        difficulty=item.get("difficulty", "medium"),
                        marks=item.get("marks", 1),
                    ))

                elif item_type == "mcq_calculation":
                    items.append(MCQCalculationItem(
                        problem=item.get("problem", ""),
                        options=item.get("options", []),
                        correct_index=item.get("correct_index", 0),
                        explanation=item.get("explanation", ""),
                        source_node_id=source_node_id,
                        difficulty=item.get("difficulty", "medium"),
                        marks=item.get("marks", 2),
                    ))

            return items
        except (json.JSONDecodeError, KeyError, Exception) as e:
            print(f"Mixed quiz parse error: {e}")
            return []

    def _parse_lesson_response(self, response: str, nodes: List[Any]) -> List[FlashcardItem]:
        try:
            text = response.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            data = json.loads(text.strip())
            if not isinstance(data, list):
                data = [data]

            items = []
            for item in data:
                source_node = random.choice(nodes) if nodes else None
                source_node_id = source_node.id if source_node else ""

                items.append(FlashcardItem(
                    title=item.get("title", ""),
                    content=item.get("content", ""),
                    source_node_id=source_node_id
                ))
            return items
        except (json.JSONDecodeError, KeyError):
            return []

    # -------------------------------------------------------------------------
    # LEGACY PARSERS (kept for backward compatibility)
    # -------------------------------------------------------------------------

    def _parse_batch_response(self, response: str, nodes: List[Any]) -> List[MCQQuestion]:
        """Parse standard MCQ batch response. Legacy — kept for descriptive quiz."""
        try:
            text = response.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            data = json.loads(text.strip())
            if not isinstance(data, list):
                data = [data]

            questions = []
            for qd in data:
                opts = [MCQOption(text=o, is_correct=(i == qd.get("correct_index", 0)))
                        for i, o in enumerate(qd.get("options", []))]

                if not any(o.is_correct for o in opts):
                    opts[0].is_correct = True

                source_node = random.choice(nodes) if nodes else None
                source_node_id = source_node.id if source_node else ""

                questions.append(MCQQuestion(
                    stem=qd["stem"],
                    options=opts,
                    source_node_id=source_node_id,
                    difficulty=Difficulty(qd.get("difficulty", "medium")),
                    topic=qd.get("topic", "general"),
                    marks=qd.get("marks", 1),
                    pattern_used=qd.get("pattern_used", ""),
                ))
            return questions
        except (json.JSONDecodeError, KeyError):
            return []

    def _parse_interactive_response(self, response: str, nodes: List[Any]) -> List[Any]:
        """Legacy interactive parser — delegates to mixed parser."""
        return self._parse_mixed_quiz_response(response, nodes)

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _get_chapter_nodes(self, document_tree, chapter_id: str) -> List[Any]:
        """Get all nodes that belong to a specific chapter."""
        nodes = document_tree.get_chapter_nodes(chapter_id)
        return [n for n in nodes if n.content.strip()]
