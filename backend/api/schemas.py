"""
Pydantic Schemas for API Request/Response Models
================================================
Streaming-only API. All responses use SSE.
"""

from typing import List, Optional,Dict,Any
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    book_id: str
    query: str
    history: Optional[List[Dict[str, str]]] = None
    previous_summary: Optional[str] = None

class SummarizeRequest(BaseModel):
    history: List[Dict[str, str]]


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

class DescriptiveQuestionData(BaseModel):
    """Single question structure — what generator returns."""
    id: str 
    type: str = "short_answer"  # short_answer | numerical | long_answer | derivation | law_proof
    stem: str
    marks: int
    topic: str = ""
    expected_points: List[str] = Field(default_factory=list)
    rubric: str = ""
    correct_answer: str = ""       # For numericals only
    formula_used: str = ""           # For numericals only
    source_node_id: str = ""
    pattern_used: str = ""


class DescriptiveGenerateRequest(BaseModel):
    """Generate chapter-wise descriptive quiz."""
    book_id: str
    chapter_id: str
    title: Optional[str] = None


class DescriptiveAnswerItem(BaseModel):
    """Single answer from student."""
    question_id: str
    answer_text: str


class DescriptiveQuizData(BaseModel):
    """Quiz data passed back from client for evaluation."""
    quiz_id: str
    book_id: str
    chapter_id: str
    title: str = ""
    section_b: List[DescriptiveQuestionData] = Field(default_factory=list) 
    section_c: List[DescriptiveQuestionData] = Field(default_factory=list)  
    total_marks: int = 15


class DescriptiveEvaluateRequest(BaseModel):
    quiz: DescriptiveQuizData
    answers: List[DescriptiveAnswerItem]
    time_taken_minutes: Optional[int] = None