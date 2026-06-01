"""
Pydantic Schemas for API Request/Response Models
================================================
Streaming-only API. All responses use SSE.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class AskRequest(BaseModel):
    book_id: str
    query: str
    history: List[ChatMessage] = Field(default_factory=list)
    previous_summary: Optional[str] = None

class SummarizeRequest(BaseModel):
    history: List[ChatMessage]


# =============================================================================
# QUIZ GENERATION SCHEMAS (MERGED - single background endpoint)
# =============================================================================

class QuizBackgroundGenerateRequest(BaseModel):
    """Request for mixed quiz generation (background task).

    Generates: 60% board-pattern MCQ + 20% true_false + 10% fill_in_blank + 10% mcq_calculation
    """
    user_id: str
    book_id: str
    level_id: str
    quiz_type: str = "chapter"  # "chapter" | "unit" | "full_book"
    chapter_id: Optional[str] = None
    unit_chapters: Optional[List[str]] = None
    target_count: int = 20
    title: Optional[str] = None


# =============================================================================
# DESCRIPTIVE QUIZ SCHEMAS
# =============================================================================

class DescriptiveGenerateRequest(BaseModel):
    book_id: str
    chapter_id: str


class StudentAnswer(BaseModel):
    question_id: str
    answer_text: str


class DescriptiveEvaluateRequest(BaseModel):
    quiz: Dict[str, Any]  # Full quiz object from generate response
    answers: List[StudentAnswer]
    time_taken_minutes: int


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class HealthResponse(BaseModel):
    status: str
    version: str
    streaming: bool
