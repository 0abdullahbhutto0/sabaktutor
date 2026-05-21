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
            "book_title": self.book_title,
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
        target_count: int = 20,
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
            default_title = f"{book_title} - Full Book Mock"
            duration_minutes = 90
            passing_percent = 50

        # Select nodes for quiz - NO chunking
        selected_nodes = self._select_nodes(nodes, target_count)
        if not selected_nodes:
            yield {"type": "error", "message": "No content available"}
            return

        content_text = ""
        for i, node in enumerate(selected_nodes, 1):
            content_text += f"\n--- CONTENT {i} ---\n"
            content_text += f"Title: {node['node_title']}\n"
            content_text += f"Content: {node['content'][:800]}\n"

        prompt = self.prompts.quiz_batch(
            content_text=content_text,
            total_questions=target_count,
            book_title=book_title,
        )

        if not self.llm:
            yield {"type": "error", "message": "LLM not configured"}
            return

        # Stream tokens as they arrive
        full_response = []
        async for token in self.llm.stream_complete(prompt, max_tokens=8000):
            full_response.append(token)
            yield {"type": "token", "token": token}

        # Parse the complete response
        response_text = "".join(full_response)
        questions = self._parse_batch_response(response_text, selected_nodes)
        questions = questions[:target_count]
        questions = self._balance_difficulty(questions)
        questions = self._balance_correct_index(questions)

        # Create and yield the quiz
        quiz = Quiz(
            quiz_type=quiz_type,
            book_title=book_title,
            title=title or default_title,
            chapter_ids=chapter_ids,
            chapter_names=chapter_names,
            questions=questions,
            duration_minutes=duration_minutes,
            passing_percent=passing_percent,
            book_id=book_id,
        )

        yield {"type": "done", "quiz": quiz}

    def generate_quiz(
        self,
        document_tree,
        quiz_type: str,
        chapter_id: Optional[str] = None,
        unit_chapters: Optional[List[Dict[str, str]]] = None,
        target_count: int = 20,
        duration_minutes: int = 20,
        passing_percent: int = 60,
        book_id: str = "",
        book_title: str = "",
        title: Optional[str] = None,
    ) -> Quiz:
        """Synchronous generate quiz - collects all tokens first."""
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
        else:
            nodes = [n for n in document_tree.get_all_nodes() if not n.is_root and n.content.strip()]
            chapter_ids = []
            chapter_names = []
            default_title = f"{book_title} - Full Book Mock"
            duration_minutes = 90
            passing_percent = 50

        selected_nodes = self._select_nodes(nodes, target_count)
        if not selected_nodes or not self.llm:
            return Quiz(quiz_type=quiz_type, book_title=book_title, title=title or default_title)

        # Build content_text - NO chunking
        content_text = ""
        for i, node in enumerate(selected_nodes, 1):
            content_text += f"\n--- CONTENT {i} ---\n"
            content_text += f"Title: {node['node_title']}\n"
            content_text += f"Content: {node['content'][:800]}\n"

        prompt = self.prompts.quiz_batch(
            content_text=content_text,
            total_questions=target_count,
            book_title=book_title,
        )

        full_response = []
        for token in self.llm.stream_complete(prompt, max_tokens=8000):
            full_response.append(token)

        response_text = "".join(full_response)
        questions = self._parse_batch_response(response_text, selected_nodes)
        questions = questions[:target_count]
        questions = self._balance_difficulty(questions)
        questions = self._balance_correct_index(questions)

        return Quiz(
            quiz_type=quiz_type,
            book_title=book_title,
            title=title or default_title,
            chapter_ids=chapter_ids,
            chapter_names=chapter_names,
            questions=questions,
            duration_minutes=duration_minutes,
            passing_percent=passing_percent,
            book_id=book_id,
        )

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

    def _balance_difficulty(self, questions: List[MCQQuestion]) -> List[MCQQuestion]:
        """Ensure 25% easy, 50% medium, 25% hard."""
        by_diff = {"easy": [], "medium": [], "hard": []}
        for q in questions:
            by_diff[q.difficulty.value].append(q)

        total = len(questions)
        targets = {"easy": max(1, total // 4), "medium": total // 2, "hard": total // 4}

        balanced = []
        for diff, target in targets.items():
            balanced.extend(by_diff.get(diff, [])[:target])

        remaining = [q for q in questions if q not in balanced]
        while len(balanced) < total and remaining:
            balanced.append(remaining.pop(0))

        random.shuffle(balanced)
        return balanced

    def _balance_correct_index(self, questions: List[MCQQuestion]) -> List[MCQQuestion]:
        """Ensure correct answers are fairly distributed across A(0), B(1), C(2), D(3)."""
        if not questions:
            return questions

        correct_indices = [
            next((i for i, o in enumerate(q.options) if o.is_correct), 0)
            for q in questions
        ]
        counts = Counter(correct_indices)

        total = len(questions)
        targets = {i: total // 4 + (1 if i < total % 4 else 0) for i in range(4)}

        excess = []
        deficit = []
        for i in range(4):
            diff = counts[i] - targets[i]
            if diff > 0:
                excess.extend([i] * diff)
            elif diff < 0:
                deficit.extend([i] * (-diff))

        changes = dict(zip(excess, deficit))
        for q in questions:
            correct_idx = next((i for i, o in enumerate(q.options) if o.is_correct), 0)
            if correct_idx in changes:
                for opt in q.options:
                    opt.is_correct = False
                q.options[changes[correct_idx]].is_correct = True
                del changes[correct_idx]

        random.shuffle(questions)
        return questions