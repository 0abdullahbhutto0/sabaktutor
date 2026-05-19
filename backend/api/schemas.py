"""
Pydantic Schemas for API Request/Response Models
================================================
Streaming-only API. All responses use SSE.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    book_id: str
    query: str
    max_results: int = 3


class UnitChapter(BaseModel):
    id: str
    name: str


class QuizGenerateRequest(BaseModel):
    book_id: str
    quiz_type: str = Field(..., pattern="^(chapter|unit|full)$")
    chapter_id: Optional[str] = None
    unit_chapters: Optional[List[UnitChapter]] = None
    subject: Optional[str] = None
    grade: Optional[str] = None
    title: Optional[str] = None
    target_count: int = 20
    duration_minutes: int = 20
    passing_percent: int = 60


class QuizResponseItem(BaseModel):
    question_id: str
    selected_index: int
    time_seconds: int = 0
    started_at: Optional[float] = None


class QuizSubmitRequest(BaseModel):
    responses: List[QuizResponseItem]
    user_id: str = "default"


class QuizSubmitResponse(BaseModel):
    score_percent: float
    passed: bool
    summary: str
    preparation: str


class StreamEvent(BaseModel):
    event: str
    data: Dict[str, Any]
