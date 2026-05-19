"""
Quiz Generator Module (Updated with Streaming + Balanced Correct Answers)
==========================================================================
Generates Sindh Board MCQs with:
- Streaming LLM support
- Balanced correct answer distribution (A, B, C, D)
- No storage dependency
"""

import json
import uuid
import random
from typing import List, Dict, Optional, Any, Iterator
from dataclasses import dataclass, field
from enum import Enum

from core.streaming_client import StreamingLLMClient


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
    source_chunk_id: str = ""
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
            "source_chunk_id": self.source_chunk_id,
            "difficulty": self.difficulty.value,
            "topic": self.topic,
            "marks": self.marks,
            "time_estimate_seconds": self.time_estimate_seconds,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCQQuestion":
        options = [MCQOption(text=o["text"], is_correct=o.get("is_correct", False))
                   for o in data.get("options", [])]
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            stem=data["stem"],
            options=options,
            source_chunk_id=data.get("source_chunk_id", ""),
            difficulty=Difficulty(data.get("difficulty", "medium")),
            topic=data.get("topic", ""),
            marks=data.get("marks", 1),
            time_estimate_seconds=data.get("time_estimate_seconds", 60),
        )


@dataclass
class Quiz:
    id: str = ""
    quiz_type: str = "chapter"
    subject: str = ""
    grade: str = ""
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
            "subject": self.subject,
            "grade": self.grade,
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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Quiz":
        questions = [MCQQuestion.from_dict(q) for q in data.get("questions", [])]
        return cls(
            id=data.get("id", ""),
            quiz_type=data.get("quiz_type", "chapter"),
            subject=data.get("subject", ""),
            grade=data.get("grade", ""),
            title=data.get("title", ""),
            chapter_ids=data.get("chapter_ids", []),
            chapter_names=data.get("chapter_names", []),
            questions=questions,
            duration_minutes=data.get("duration_minutes", 20),
            passing_percent=data.get("passing_percent", 60),
            created_at=data.get("created_at", 0),
            book_id=data.get("book_id", ""),
        )


class QuizGenerator:
    """
    Generates MCQs with streaming LLM support and balanced correct answers.
    No storage dependency — quizzes returned directly.
    """

    def __init__(
        self,
        api_key: str = "",
        questions_per_chunk: int = 2,
        model: str = "google/gemini-2.0-flash-001",
        use_streaming: bool = True,
    ):
        self.api_key = api_key
        self.model = model
        self.questions_per_chunk = questions_per_chunk
        self.use_streaming = use_streaming

        self.llm = StreamingLLMClient(api_key, model) if api_key else None

    def set_key(self, api_key: str):
        """Update OpenRouter API key."""
        self.api_key = api_key
        self.llm = StreamingLLMClient(api_key, self.model) if api_key else None

    def set_model(self, model: str):
        """Update OpenRouter model."""
        self.model = model
        if self.llm:
            self.llm.model = model

    def generate_chapter_quiz(
        self,
        document_tree,
        subject: str,
        grade: str,
        chapter_id: str,
        chapter_name: str,
        book_id: str = "",
        stream_callback: Optional[Any] = None,
    ) -> Quiz:
        """Generate chapter-level quiz with optional streaming."""
        chapter_nodes = self._get_chapter_nodes(document_tree, chapter_id)

        if self.use_streaming and stream_callback:
            questions = self._generate_streaming(
                chapter_nodes, target_count=20, callback=stream_callback
            )
        else:
            questions = self._generate_all_in_one_call(chapter_nodes, target_count=20)

        quiz = Quiz(
            quiz_type="chapter",
            subject=subject,
            grade=grade,
            title=f"{chapter_name} - Chapter Quiz",
            chapter_ids=[chapter_id],
            chapter_names=[chapter_name],
            questions=questions,
            duration_minutes=20,
            passing_percent=60,
            book_id=book_id,
        )

        return quiz

    def generate_unit_quiz(
        self,
        document_tree,
        subject: str,
        grade: str,
        unit_chapters: List[Dict[str, str]],
        book_id: str = "",
    ) -> Quiz:
        """Generate unit quiz from multiple chapters."""
        all_nodes = []
        for ch in unit_chapters:
            all_nodes.extend(self._get_chapter_nodes(document_tree, ch["id"]))

        questions = self._generate_all_in_one_call(all_nodes, target_count=40)

        quiz = Quiz(
            quiz_type="unit",
            subject=subject,
            grade=grade,
            title=f"Unit Test - {len(unit_chapters)} Chapters",
            chapter_ids=[c["id"] for c in unit_chapters],
            chapter_names=[c["name"] for c in unit_chapters],
            questions=questions,
            duration_minutes=45,
            passing_percent=50,
            book_id=book_id,
        )
        return quiz

    def generate_full_book_quiz(
        self,
        document_tree,
        subject: str,
        grade: str,
        all_chapters: List[Dict[str, str]],
        book_id: str = "",
    ) -> Quiz:
        """Generate full book mock exam."""
        all_nodes = [n for n in document_tree.get_all_nodes() if not n.is_root and n.chunks]
        questions = self._generate_all_in_one_call(all_nodes, target_count=60)

        quiz = Quiz(
            quiz_type="full",
            subject=subject,
            grade=grade,
            title=f"{subject} Grade {grade} - Full Book Mock",
            chapter_ids=[c["id"] for c in all_chapters],
            chapter_names=[c["name"] for c in all_chapters],
            questions=questions,
            duration_minutes=90,
            passing_percent=50,
            book_id=book_id,
        )
        return quiz

    def _get_chapter_nodes(self, document_tree, chapter_id: str) -> List[Any]:
        """Get all nodes that belong to a specific chapter."""
        nodes = document_tree.get_chapter_nodes(chapter_id)
        return [n for n in nodes if n.chunks]

    def _generate_all_in_one_call(self, nodes: List[Any], target_count: int) -> List[MCQQuestion]:
        """Generate ALL questions from ALL chunks in a SINGLE API call."""
        if not self.llm:
            return []

        all_chunks = []
        for node in nodes:
            for chunk in node.chunks:
                if chunk.content.strip():
                    all_chunks.append({
                        "chunk_id": chunk.id,
                        "content": chunk.content,
                        "node_title": node.title or "",
                    })

        if not all_chunks:
            return []

        max_chunks = min(len(all_chunks), max(target_count // 2, 5))
        step = max(1, len(all_chunks) // max_chunks) if len(all_chunks) > max_chunks else 1
        selected_chunks = [all_chunks[i] for i in range(0, len(all_chunks), step)][:max_chunks]

        prompt = self._build_batch_prompt(selected_chunks, target_count)

        response = self.llm.complete(prompt, max_tokens=8000)

        questions = self._parse_batch_response(response, selected_chunks)
        questions = questions[:target_count]
        questions = self._balance_difficulty(questions)
        questions = self._balance_correct_index(questions)

        return questions

    def _generate_streaming(
        self,
        nodes: List[Any],
        target_count: int,
        callback: Any,
    ) -> List[MCQQuestion]:
        """Generate questions with streaming output."""
        if not self.llm:
            return []

        all_chunks = []
        for node in nodes:
            for chunk in node.chunks:
                if chunk.content.strip():
                    all_chunks.append({
                        "chunk_id": chunk.id,
                        "content": chunk.content,
                        "node_title": node.title or "",
                    })

        max_chunks = min(len(all_chunks), max(target_count // 2, 5))
        step = max(1, len(all_chunks) // max_chunks) if len(all_chunks) > max_chunks else 1
        selected_chunks = [all_chunks[i] for i in range(0, len(all_chunks), step)][:max_chunks]

        prompt = self._build_batch_prompt(selected_chunks, target_count)

        full_response = []
        token_count = 0

        for token in self.llm.stream_complete(prompt, max_tokens=8000, on_token=callback):
            full_response.append(token)
            token_count += 1

        response_text = "".join(full_response)
        questions = self._parse_batch_response(response_text, selected_chunks)
        questions = questions[:target_count]
        questions = self._balance_difficulty(questions)
        questions = self._balance_correct_index(questions)

        return questions

    def _build_batch_prompt(self, chunks: List[Dict], total_questions: int) -> str:
        """Build a SINGLE prompt containing ALL chunks."""
        chunks_text = ""
        for i, chunk in enumerate(chunks, 1):
            chunks_text += f"\n--- CHUNK {i} ---\n"
            chunks_text += f"Title: {chunk['node_title']}\n"
            chunks_text += f"Content: {chunk['content'][:800]}\n"

        easy_count = max(1, total_questions // 4)
        medium_count = total_questions // 2
        hard_count = total_questions // 4

        return f"""You are generating Sindh Board (Pakistan) high school MCQs.

INSTRUCTIONS:
Generate exactly {total_questions} multiple choice questions from ALL the content chunks below.
Distribute questions across ALL chunks provided.

CONTENT CHUNKS:{chunks_text}

RULES:
- Each question must have exactly 4 options (A, B, C, D)
- Only ONE option is correct
- Options should be plausible distractors based on common student misconceptions
- Include numerical/computational questions where content supports it
- Questions should test understanding, not just memorization
- The correct answer index MUST be fairly distributed across A(0), B(1), C(2), D(3) — do NOT make only B and C correct
- Each question MUST reference which chunk it came from (use chunk number)

DIFFICULTY DISTRIBUTION:
- {easy_count} easy: Direct fact recall, single-step computation
- {medium_count} medium: Application, two-step reasoning  
- {hard_count} hard: Analysis, multi-step, edge cases

OUTPUT FORMAT (strict JSON array):
[
  {{
    "stem": "Question text here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_index": 0,
    "difficulty": "medium",
    "topic": "sub_topic_tag",
    "chunk_ref": 1
  }},
  ...
]

Respond with ONLY the JSON array. No markdown, no explanations, no code blocks."""

    def _parse_batch_response(self, response: str, chunks: List[Dict]) -> List[MCQQuestion]:
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

                if not any(o.is_correct for o in opts) and opts:
                    opts[0].is_correct = True

                chunk_ref = qd.get("chunk_ref", 1)
                chunk_idx = min(chunk_ref - 1, len(chunks) - 1) if chunk_ref > 0 else 0
                source_chunk_id = chunks[chunk_idx]["chunk_id"] if chunks else ""

                questions.append(MCQQuestion(
                    stem=qd["stem"],
                    options=opts,
                    source_chunk_id=source_chunk_id,
                    difficulty=Difficulty(qd.get("difficulty", "medium")),
                    topic=qd.get("topic", "general"),
                ))
            return questions
        except (json.JSONDecodeError, KeyError) as e:
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
        """
        Ensure correct answers are fairly distributed across A(0), B(1), C(2), D(3).
        Not only B & C should be correct.
        """
        if not questions:
            return questions

        counts = {0: 0, 1: 0, 2: 0, 3: 0}
        for q in questions:
            correct_idx = next((i for i, o in enumerate(q.options) if o.is_correct), 0)
            counts[correct_idx] = counts.get(correct_idx, 0) + 1

        total = len(questions)
        target_per_option = total // 4
        remainder = total % 4

        targets = {}
        for i in range(4):
            targets[i] = target_per_option + (1 if i < remainder else 0)

        questions_by_correct = {0: [], 1: [], 2: [], 3: []}
        for q in questions:
            correct_idx = next((i for i, o in enumerate(q.options) if o.is_correct), 0)
            questions_by_correct[correct_idx].append(q)

        balanced_questions = []
        excess = {i: max(0, len(questions_by_correct[i]) - targets[i]) for i in range(4)}
        deficit = {i: max(0, targets[i] - len(questions_by_correct[i])) for i in range(4)}

        for i in range(4):
            to_add = min(len(questions_by_correct[i]), targets[i])
            balanced_questions.extend(questions_by_correct[i][:to_add])
            questions_by_correct[i] = questions_by_correct[i][to_add:]

        for deficit_idx in range(4):
            while deficit[deficit_idx] > 0:
                for excess_idx in range(4):
                    if excess[excess_idx] > 0 and questions_by_correct[excess_idx]:
                        q = questions_by_correct[excess_idx].pop(0)
                        for opt in q.options:
                            opt.is_correct = False
                        q.options[deficit_idx].is_correct = True
                        balanced_questions.append(q)
                        excess[excess_idx] -= 1
                        deficit[deficit_idx] -= 1
                        break

        for i in range(4):
            balanced_questions.extend(questions_by_correct[i])

        random.shuffle(balanced_questions)
        return balanced_questions
