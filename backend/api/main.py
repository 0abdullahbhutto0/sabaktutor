"""
FastAPI Application for Hybrid Tree Search + Quiz System
=========================================================
Books auto-discovered from project directory (*.json files).
Every request includes book_id — loaded on-demand per request.
API:
- Querying books via LLM (streaming SSE)
- Quiz generation (chapter, unit, full book) - streaming SSE
- Quiz submission and grading
"""

import os
from typing import AsyncGenerator, List, Dict
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.schemas import (
    AskRequest,
    QuizGenerateRequest,
    QuizSubmitRequest,
    QuizSubmitResponse,
)
from api.dependencies import get_services, Services
from api.streaming import sse_stream
from api.prompts import Prompts

# ─── Environment ───
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

BOOK_CACHE_DIR = "./book_cache"
VECTOR_INDEX_DIR = "./vector_index"
DATA_DIR = "."

DEFAULT_SUBJECT = "Computer Science"
DEFAULT_GRADE = "9"


def _discover_books() -> List[Dict[str, str]]:
    """Auto-discover JSON book files in project directory."""
    books = []
    data_dir = Path(DATA_DIR)
    for f in data_dir.glob("*.json"):
        if f.name in ("books_metadata.json", "config.json"):
            continue
        book_id = f.stem
        books.append({
            "book_id": book_id,
            "title": book_id.replace("_", " ").title(),
            "subject": DEFAULT_SUBJECT,
            "grade": DEFAULT_GRADE,
            "file_path": str(f),
        })
    return books


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: auto-discover and register all JSON books in project dir."""
    services = get_services()
    books = _discover_books()
    for book in books:
        try:
            services.book_manager.register_book(
                book_id=book["book_id"],
                title=book["title"],
                subject=book["subject"],
                grade=book["grade"],
                file_path=book["file_path"],
            )
        except Exception as e:
            print(f"⚠️ Failed to register book {book['book_id']}: {e}")
    yield
    services.close()


app = FastAPI(
    title="Hybrid Tree Search + Quiz API",
    description="LLM Q&A and Quiz Generation API. Books auto-loaded from project directory. Pass book_id in every request.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/books")
async def list_books(services: Services = Depends(get_services)):
    """List all auto-discovered books."""
    books = services.book_manager.list_books()
    return {
        "books": [
            {
                "book_id": b.book_id,
                "title": b.title,
                "subject": b.subject,
                "grade": b.grade,
                "is_indexed": b.is_indexed,
            }
            for b in books
        ]
    }

@app.post("/ask/stream")
async def ask_stream(req: AskRequest, services: Services = Depends(get_services)):
    """
    Ask a question about a specific book.
    Pass book_id in request — book loaded on-demand.
    Returns SSE stream with LLM tokens.
    """
    try:
        services.load_book(req.book_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Book '{req.book_id}' not found: {str(e)}")

    async def token_generator() -> AsyncGenerator[str, None]:
        for token in services.ask_stream(req.query, max_results=3):
            yield sse_stream("token", {"token": token})
        yield sse_stream("done", {"status": "complete"})

    return StreamingResponse(
        token_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@app.post("/quiz/generate/stream")
async def generate_quiz_stream(
    req: QuizGenerateRequest,
    services: Services = Depends(get_services),
):
    """
    Generate a quiz (chapter, unit, or full book).
    Pass book_id in request — book loaded on-demand.
    Returns SSE stream with progress + final quiz JSON.
    """
    try:
        services.load_book(req.book_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Book '{req.book_id}' not found: {str(e)}")

    async def quiz_generator() -> AsyncGenerator[str, None]:
        yield sse_stream("status", {"message": "Starting quiz generation...", "step": 1, "total": 3})
        yield sse_stream("status", {"message": "Collecting content...", "step": 2, "total": 3})

        if req.quiz_type == "chapter":
            nodes = services._get_chapter_nodes(req.chapter_id)
        elif req.quiz_type == "unit":
            nodes = []
            for ch in req.unit_chapters or []:
                nodes.extend(services._get_chapter_nodes(ch["id"]))
        else:  
            nodes = [n for n in services._active_tree.get_all_nodes() if not n.is_root and n.chunks]

        yield sse_stream("status", {"message": f"Generating {req.target_count} questions via LLM...", "step": 3, "total": 3})

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
            yield sse_stream("error", {"message": "No content found for quiz generation"})
            return

        max_chunks = min(len(all_chunks), max(req.target_count // 2, 5))
        step = max(1, len(all_chunks) // max_chunks) if len(all_chunks) > max_chunks else 1
        selected_chunks = [all_chunks[i] for i in range(0, len(all_chunks), step)][:max_chunks]

        chunks_text = ""
        for i, chunk in enumerate(selected_chunks, 1):
            chunks_text += f"""
--- CHUNK {i} ---"""
            chunks_text += f"Title: {chunk['node_title']}"
            chunks_text += f"Content: {chunk['content']}"

        prompt = services.prompts.quiz_batch(
            chunks_text=chunks_text,
            total_questions=req.target_count,
            subject=req.subject or DEFAULT_SUBJECT,
            grade=req.grade or DEFAULT_GRADE,
        )

        full_response = []
        for token in services.llm.stream_complete(
            prompt,
            system=services.prompts.quiz_system(req.subject or DEFAULT_SUBJECT, req.grade or DEFAULT_GRADE),
            max_tokens=12000,
        ):
            full_response.append(token)
            yield sse_stream("token", {"token": token})

        response_text = "".join(full_response)
        questions = services.quiz_generator._parse_batch_response(response_text, selected_chunks)
        questions = questions[:req.target_count]
        questions = services.quiz_generator._balance_difficulty(questions)
        questions = services.quiz_generator._balance_correct_index(questions)

        from quiz.quiz_generator import Quiz
        quiz = Quiz(
            quiz_type=req.quiz_type,
            subject=req.subject or DEFAULT_SUBJECT,
            grade=req.grade or DEFAULT_GRADE,
            title=req.title or f"{req.quiz_type.title()} Quiz",
            chapter_ids=[req.chapter_id] if req.quiz_type == "chapter" else [c["id"] for c in (req.unit_chapters or [])],
            chapter_names=[req.chapter_id] if req.quiz_type == "chapter" else [c["name"] for c in (req.unit_chapters or [])],
            questions=questions,
            duration_minutes=req.duration_minutes,
            passing_percent=req.passing_percent,
            book_id=services._active_book_id or "",
        )

        yield sse_stream("done", {
            "quiz": quiz.to_dict(),
            "title": quiz.title,
            "question_count": len(quiz.questions),
            "duration_minutes": quiz.duration_minutes,
            "passing_percent": quiz.passing_percent,
        })

    return StreamingResponse(
        quiz_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/quiz/grade", response_model=QuizSubmitResponse)
async def grade_quiz(
    req: QuizSubmitRequest, 
    services: Services = Depends(get_services),
):
    """
    Grade quiz answers and get feedback.
    Client sends full quiz object + responses.
    """
    from quiz.quiz_generator import Quiz, MCQQuestion, MCQOption

    quiz_data = req.quiz
    questions = []
    for q_data in quiz_data.get("questions", []):
        options = [MCQOption(text=o["text"], is_correct=o.get("is_correct", False)) 
                   for o in q_data.get("options", [])]
        questions.append(MCQQuestion(
            id=q_data.get("id", ""),
            stem=q_data.get("stem", ""),
            options=options,
            difficulty=q_data.get("difficulty", "medium"),
            topic=q_data.get("topic", "general"),
            marks=q_data.get("marks", 1),
        ))

    quiz = Quiz(
        id=quiz_data.get("id", "temp"),
        quiz_type=quiz_data.get("quiz_type", "chapter"),
        subject=quiz_data.get("subject", ""),
        grade=quiz_data.get("grade", ""),
        title=quiz_data.get("title", ""),
        questions=questions,
        duration_minutes=quiz_data.get("duration_minutes", 20),
        passing_percent=quiz_data.get("passing_percent", 60),
    )

    feedback = services.quiz_engine.grade_attempt_in_memory(quiz, req.responses, req.user_id)

    return QuizSubmitResponse(
        score_percent=feedback.score_percent,
        passed=feedback.passed,
        summary=feedback.summary,
        preparation=feedback.preparation,
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "streaming_only": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
