"""
Pydantic Schemas for API Request/Response Models
================================================
Streaming-only API. All responses use SSE.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    book_id: str
    query: str


class UnitChapter(BaseModel):
    id: str
    name: str


class QuizGenerateRequest(BaseModel):
    book_id: str
    book_title: str = ""
    quiz_type: str = Field(..., pattern="^(chapter|unit|full)$")
    chapter_id: Optional[str] = None
    unit_chapters: Optional[List[UnitChapter]] = None
    title: Optional[str] = None
    target_count: int = 10
    duration_minutes: int = 20
    passing_percent: int = 60


class StreamEvent(BaseModel):
    event: str
    data: dict


class QuizBackgroundGenerateRequest(QuizGenerateRequest):
    user_id: str
    level_id: str