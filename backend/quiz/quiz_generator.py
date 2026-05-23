"""
Quiz Generator Module
=====================
Generates Sindh Board MCQs with:
- Async streaming LLM support - tokens streamed as they arrive
- Balanced correct answer distribution (A, B, C, D)
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

@dataclass
class TrueFalseItem:
    statement: str = ""
    is_true: bool = True
    explanation: str = ""
    type: str = "true_false"
    source_node_id: str = ""
    id: str = ""

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
        }

@dataclass
class FillInBlankItem:
    sentence_before: str = ""
    blank_answer: str = ""
    sentence_after: str = ""
    type: str = "fill_in_blank"
    source_node_id: str = ""
    id: str = ""

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
        }

@dataclass
class MCQCalculationItem:
    problem: str = ""
    options: List[str] = field(default_factory=list)
    correct_index: int = 0
    explanation: str = ""
    type: str = "mcq_calculation"
    source_node_id: str = ""
    id: str = ""

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
        }

@dataclass
class InteractiveQuiz:
    book_id: str = ""
    title: str = ""
    chapter_ids: List[str] = field(default_factory=list)
    items: List[Any] = field(default_factory=list)
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


class QuizGenerator:
    """Generates MCQs with async streaming LLM support and balanced correct answers."""

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

    async def generate_quiz_streaming(
        self,
        document_tree,
        quiz_type: str,
        chapter_id: Optional[str] = None,
        unit_chapters: Optional[List[Dict[str, str]]] = None,
        target_count: int = 10,
        duration_minutes: int = 20,
        passing_percent: int = 60,
        book_id: str = "",
        book_title: str = "",
        title: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate quiz with streaming tokens as they arrive.
        NO subject/grade - uses book_title instead.
        """
        if quiz_type == "chapter" and chapter_id:
            nodes = self._get_chapter_nodes(document_tree, chapter_id)
            chapter_ids = [chapter_id]
            chapter_names = [chapter_id]
            default_title = f"{chapter_id} - Chapter Quiz"
        elif quiz_type == "unit" and unit_chapters:
            nodes = []
            chapter_ids = []
            chapter_names = []
            for ch in unit_chapters:
                nodes.extend(self._get_chapter_nodes(document_tree, ch["id"]))
                chapter_ids.append(ch["id"])
                chapter_names.append(ch.get("name", ch["id"]))
            default_title = f"Unit Test - {len(unit_chapters)} Chapters"
            duration_minutes = 45
            passing_percent = 50
        else:  # full book
            nodes = [n for n in document_tree.get_all_nodes() if not n.is_root and n.content.strip()]
            chapter_ids = []
            chapter_names = []
            default_title = f"{book_id} - Full Book Mock"
            duration_minutes = 90
            passing_percent = 50


        selected_nodes = self._select_nodes(nodes, target_count)
        if not selected_nodes:
            yield {"type": "error", "message": "No content available"}
            return

        content_text = ""
        for i, node in enumerate(selected_nodes, 1):
            content_text += f"\n--- CONTENT {i} ---\n"
            content_text += f"Title: {node['node_title']}\n"
            content_text += f"Content: {node['content']}\n"

        prompt = self.prompts.quiz_batch(
            content_text=content_text,
            total_questions=target_count,
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
        questions = self._parse_batch_response(response_text, selected_nodes)
        questions = questions[:target_count]
        quiz = Quiz(
            quiz_type=quiz_type,
            book_title=book_id,
            title=title or default_title,
            chapter_ids=chapter_ids,
            chapter_names=chapter_names,
            questions=questions,
            duration_minutes=duration_minutes,
            passing_percent=passing_percent,
            book_id=book_id,
        )

        yield {"type": "done", "quiz": quiz}

    async def generate_lesson_streaming(
        self,
        document_tree,
        chapter_id: str,
        target_count: int = 10,
        book_id: str = "",
        title: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        nodes = self._get_chapter_nodes(document_tree, chapter_id)
        selected_nodes = self._select_nodes(nodes, target_count)
        if not selected_nodes:
            yield {"type": "error", "message": "No content available"}
            return

        content_text = ""
        for i, node in enumerate(selected_nodes, 1):
            content_text += f"\n--- CONTENT {i} ---\n"
            content_text += f"Title: {node['node_title']}\n"
            content_text += f"Content: {node['content']}\n"

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
        items = self._parse_lesson_response(response_text, selected_nodes)
        items = items[:target_count]
        
        lesson = Lesson(
            book_id=book_id,
            title=title or f"{chapter_id} - Lesson",
            chapter_ids=[chapter_id],
            items=items,
        )

        yield {"type": "done", "lesson": lesson}

    async def generate_interactive_streaming(
        self,
        document_tree,
        chapter_id: str,
        target_count: int = 10,
        book_id: str = "",
        title: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        nodes = self._get_chapter_nodes(document_tree, chapter_id)
        selected_nodes = self._select_nodes(nodes, target_count)
        if not selected_nodes:
            yield {"type": "error", "message": "No content available"}
            return

        content_text = ""
        for i, node in enumerate(selected_nodes, 1):
            content_text += f"\n--- CONTENT {i} ---\n"
            content_text += f"Title: {node['node_title']}\n"
            content_text += f"Content: {node['content']}\n"

        prompt = self.prompts.generate_interactive_quiz(
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
        items = self._parse_interactive_response(response_text, selected_nodes)
        items = items[:target_count]
        
        interactive_quiz = InteractiveQuiz(
            book_id=book_id,
            title=title or f"{chapter_id} - Interactive Quiz",
            chapter_ids=[chapter_id],
            items=items,
        )

        yield {"type": "done", "interactive_quiz": interactive_quiz}

    def _parse_lesson_response(self, response: str, nodes: List[Dict]) -> List[FlashcardItem]:
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
                chunk_ref = item.get("chunk_ref", 1)
                chunk_idx = min(chunk_ref - 1, len(nodes) - 1) if chunk_ref > 0 else 0
                source_node_id = nodes[chunk_idx]["node_id"] if nodes else ""

                items.append(FlashcardItem(
                    title=item.get("title", ""),
                    content=item.get("content", ""),
                    source_node_id=source_node_id
                ))
            return items
        except (json.JSONDecodeError, KeyError):
            return []

    def _parse_interactive_response(self, response: str, nodes: List[Dict]) -> List[Any]:
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
                chunk_ref = item.get("chunk_ref", 1)
                chunk_idx = min(chunk_ref - 1, len(nodes) - 1) if chunk_ref > 0 else 0
                source_node_id = nodes[chunk_idx]["node_id"] if nodes else ""
                
                item_type = item.get("type")
                if item_type == "true_false":
                    items.append(TrueFalseItem(
                        statement=item.get("statement", ""),
                        is_true=item.get("is_true", True),
                        explanation=item.get("explanation", ""),
                        source_node_id=source_node_id
                    ))
                elif item_type == "fill_in_blank":
                    items.append(FillInBlankItem(
                        sentence_before=item.get("sentence_before", ""),
                        blank_answer=item.get("blank_answer", ""),
                        sentence_after=item.get("sentence_after", ""),
                        source_node_id=source_node_id
                    ))
                elif item_type == "mcq_calculation":
                    items.append(MCQCalculationItem(
                        problem=item.get("problem", ""),
                        options=item.get("options", []),
                        correct_index=item.get("correct_index", 0),
                        explanation=item.get("explanation", ""),
                        source_node_id=source_node_id
                    ))
                elif item_type == "mcq":
                    items.append(MCQQuestion(
                        stem=item.get("stem", ""),
                        options=[MCQOption(text=o, is_correct=(i == item.get("correct_index", 0))) 
                                 for i, o in enumerate(item.get("options", []))],
                        source_node_id=source_node_id,
                        difficulty=Difficulty(item.get("difficulty", "medium")),
                        topic=item.get("topic", "general")
                    ))
            return items
        except (json.JSONDecodeError, KeyError):
            return []

    def _get_chapter_nodes(self, document_tree, chapter_id: str) -> List[Any]:
        """Get all nodes that belong to a specific chapter."""
        nodes = document_tree.get_chapter_nodes(chapter_id)
        # NO chunking - return nodes with content directly
        return [n for n in nodes if n.content.strip()]

    def _select_nodes(self, nodes: List[Any], target_count: int) -> List[Dict]:
        """
        Select representative nodes from the tree for quiz generation.
        NO chunking - uses node content directly.
        """
        if not nodes:
            return []
        
        content_nodes = [n for n in nodes if n.content.strip()]

        if not content_nodes:
            return []

        max_nodes = min(len(content_nodes), max(target_count // 2, 5))
        step = max(1, len(content_nodes) // max_nodes) if len(content_nodes) > max_nodes else 1

        selected = []
        for i in range(0, len(content_nodes), step):
            node = content_nodes[i]
            selected.append({
                "node_id": node.id,
                "content": node.content,
                "node_title": node.title or "",
            })
            if len(selected) >= max_nodes:
                break

        return selected

    def _parse_batch_response(self, response: str, nodes: List[Dict]) -> List[MCQQuestion]:
        """Parse all questions from a single batch response."""
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

                chunk_ref = qd.get("chunk_ref", 1)
                chunk_idx = min(chunk_ref - 1, len(nodes) - 1) if chunk_ref > 0 else 0
                source_node_id = nodes[chunk_idx]["node_id"] if nodes else ""

                questions.append(MCQQuestion(
                    stem=qd["stem"],
                    options=opts,
                    source_node_id=source_node_id,
                    difficulty=Difficulty(qd.get("difficulty", "medium")),
                    topic=qd.get("topic", "general"),
                ))
            return questions
        except (json.JSONDecodeError, KeyError):
            return []
