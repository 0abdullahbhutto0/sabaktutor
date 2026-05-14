"""
Quiz Generator Module (Optimized)
====================================
Generates Sindh Board MCQs from indexed document chunks using OpenRouter.
**OPTIMIZED**: Sends all chunks in a SINGLE API call to avoid rate limits.
"""

import json
import uuid
import random
import requests
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


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
        )


class OpenRouterLLMClient:
    """Wrapper for OpenRouter API - supports multiple LLM providers."""

    def __init__(self, api_key: str, model: str = "google/gemini-2.0-flash-001"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"

    def complete(self, prompt: str, max_retries: int = 3) -> str:
        """Send prompt and return text response via OpenRouter with retry logic."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://localhost",
            "X-Title": "Sindh Board Quiz Generator"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an expert educational content creator for Sindh Board Pakistan. Generate high-quality multiple choice questions."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 8000  # Increased for batch generation
        }

        import time
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    print(f"Rate limited. Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                raise RuntimeError(f"OpenRouter API error: {e}")
            except requests.exceptions.RequestException as e:
                raise RuntimeError(f"OpenRouter API error: {e}")
            except (KeyError, IndexError) as e:
                raise RuntimeError(f"Invalid response format from OpenRouter: {e}")

        raise RuntimeError("Max retries exceeded due to rate limiting.")


class QuizGenerator:
    """Generates MCQs from document tree using OpenRouter LLM. SINGLE API CALL per quiz."""

    def __init__(self, api_key: str = "", questions_per_chunk: int = 2, model: str = "google/gemini-2.0-flash-001"):
        self.api_key = api_key
        self.model = model
        self.llm = OpenRouterLLMClient(api_key, model) if api_key else None
        self.questions_per_chunk = questions_per_chunk

    def set_key(self, api_key: str):
        """Update OpenRouter API key."""
        self.api_key = api_key
        self.llm = OpenRouterLLMClient(api_key, self.model) if api_key else None

    def set_model(self, model: str):
        """Update OpenRouter model."""
        self.model = model
        if self.llm:
            self.llm.model = model

    def generate_chapter_quiz(self, document_tree, subject: str, grade: str,
                              chapter_id: str, chapter_name: str) -> Quiz:
        """Generate chapter-level quiz (20 MCQs) from SPECIFIC chapter only. SINGLE API CALL."""
        chapter_nodes = self._get_chapter_nodes(document_tree, chapter_id)
        questions = self._generate_all_in_one_call(chapter_nodes, target_count=20)

        return Quiz(
            quiz_type="chapter",
            subject=subject,
            grade=grade,
            title=f"{chapter_name} - Chapter Quiz",
            chapter_ids=[chapter_id],
            chapter_names=[chapter_name],
            questions=questions,
            duration_minutes=20,
            passing_percent=60,
        )

    def generate_unit_quiz(self, document_tree, subject: str, grade: str,
                           unit_chapters: List[Dict[str, str]]) -> Quiz:
        """Generate unit quiz from multiple chapters (40 MCQs). SINGLE API CALL."""
        all_nodes = []
        for ch in unit_chapters:
            all_nodes.extend(self._get_chapter_nodes(document_tree, ch["id"]))

        questions = self._generate_all_in_one_call(all_nodes, target_count=40)

        return Quiz(
            quiz_type="unit",
            subject=subject,
            grade=grade,
            title=f"Unit Test - {len(unit_chapters)} Chapters",
            chapter_ids=[c["id"] for c in unit_chapters],
            chapter_names=[c["name"] for c in unit_chapters],
            questions=questions,
            duration_minutes=45,
            passing_percent=50,
        )

    def generate_full_book_quiz(self, document_tree, subject: str, grade: str,
                                all_chapters: List[Dict[str, str]]) -> Quiz:
        """Generate full book mock exam (60 MCQs). SINGLE API CALL."""
        all_nodes = [n for n in document_tree.get_all_nodes() if not n.is_root and n.chunks]
        questions = self._generate_all_in_one_call(all_nodes, target_count=60)

        return Quiz(
            quiz_type="full",
            subject=subject,
            grade=grade,
            title=f"{subject} Grade {grade} - Full Book Mock",
            chapter_ids=[c["id"] for c in all_chapters],
            chapter_names=[c["name"] for c in all_chapters],
            questions=questions,
            duration_minutes=90,
            passing_percent=50,
        )

    def generate_weak_areas_quiz(self, questions_pool: List[MCQQuestion],
                                  weak_topics: List[str], subject: str, grade: str) -> Optional[Quiz]:
        """Generate retry quiz from weak topics only (5-10 MCQs)."""
        weak_questions = [q for q in questions_pool if q.topic in weak_topics]
        if len(weak_questions) < 3:
            return None

        selected = random.sample(weak_questions, min(10, len(weak_questions)))
        for q in selected:
            random.shuffle(q.options)

        return Quiz(
            quiz_type="weak",
            subject=subject,
            grade=grade,
            title=f"Weak Areas Retry - {', '.join(weak_topics[:2])}",
            questions=selected,
            duration_minutes=10,
            passing_percent=80,
        )

    def _get_chapter_nodes(self, document_tree, chapter_id: str) -> List[Any]:
        """Get all nodes that belong to a specific chapter."""
        nodes = document_tree.get_chapter_nodes(chapter_id)
        return [n for n in nodes if n.chunks]

    def _generate_all_in_one_call(self, nodes: List[Any], target_count: int) -> List[MCQQuestion]:
        """Generate ALL questions from ALL chunks in a SINGLE API call."""
        if not self.llm:
            return []

        # Collect all chunks with content
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

        # Select diverse chunks (but keep it reasonable for token limits)
        # For most models, ~4000-8000 tokens context is safe
        max_chunks = min(len(all_chunks), max(target_count // 2, 5))
        step = max(1, len(all_chunks) // max_chunks) if len(all_chunks) > max_chunks else 1
        selected_chunks = [all_chunks[i] for i in range(0, len(all_chunks), step)][:max_chunks]

        # Build ONE prompt with ALL chunks
        prompt = self._build_batch_prompt(selected_chunks, target_count)

        # SINGLE API CALL
        print(f"Generating {target_count} questions from {len(selected_chunks)} chunks in 1 API call...")
        response = self.llm.complete(prompt)

        # Parse all questions from single response
        questions = self._parse_batch_response(response, selected_chunks)

        # Ensure we have exactly target_count
        questions = questions[:target_count]
        return self._balance_difficulty(questions)

    def _build_batch_prompt(self, chunks: List[Dict], total_questions: int) -> str:
        """Build a SINGLE prompt containing ALL chunks to generate ALL questions at once."""

        # Build chunks section
        chunks_text = ""
        for i, chunk in enumerate(chunks, 1):
            chunks_text += f"\n--- CHUNK {i} ---\n"
            chunks_text += f"Title: {chunk['node_title']}\n"
            chunks_text += f"Content: {chunk['content'][:800]}\n"  # Truncate to save tokens

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

            # Extract JSON from markdown code blocks if present
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

                # Map chunk_ref to actual chunk_id
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
            print(f"Failed to parse batch response: {e}")
            print(f"Response preview: {response[:500]}...")
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
