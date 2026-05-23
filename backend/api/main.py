"""
FastAPI Application for Hybrid Tree Search + Quiz System
=========================================================
Books auto-discovered from project directory (*.json files).
Every request includes book_id — loaded on-demand per request.
API:
- Querying books via LLM (streaming SSE)
- Quiz generation (chapter, unit, full book) - streaming SSE
"""

from typing import AsyncGenerator, List
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import (
    AskRequest,
    QuizGenerateRequest,
    QuizBackgroundGenerateRequest,
)
from api.dependencies import get_services, Services
from api.streaming import sse_stream
from core.firebase import save_quiz_to_firestore
import asyncio

DATA_DIR = "."


def _discover_books() -> List[dict]:
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
                file_path=book["file_path"],
            )
        except Exception as e:
            print(f"Warning: Failed to register book {book['book_id']}: {e}")
    yield
    await services.close()


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
        async for token in services.ask_stream(req.query, max_results=10):
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
        yield sse_stream("status", {"message": "Starting quiz generation...", "step": 1})

        async for event in services.quiz_generator.generate_quiz_streaming(
            document_tree=services._active_tree,
            quiz_type=req.quiz_type,
            chapter_id=req.chapter_id,
            unit_chapters=[{"id": c} for c in (req.unit_chapters or [])],
            target_count=req.target_count,
            duration_minutes=req.duration_minutes,
            passing_percent=req.passing_percent,
            book_id=req.book_id,
            title=req.title,
        ):
            if event["type"] == "token":
                yield sse_stream("token", {"token": event["token"]})
            elif event["type"] == "error":
                yield sse_stream("error", {"message": event["message"]})
            elif event["type"] == "done":
                quiz = event["quiz"]
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

async def background_quiz_generator(req: QuizBackgroundGenerateRequest, services: Services):
    print(f"--- STARTING BACKGROUND GEN FOR {req.level_id} ---", flush=True)
    try:
        services.load_book(req.book_id)
        print(f"--- BOOK LOADED FOR {req.level_id} ---", flush=True)
        async for event in services.quiz_generator.generate_quiz_streaming(
            document_tree=services._active_tree,
            quiz_type=req.quiz_type,
            chapter_id=req.chapter_id,
            unit_chapters=[{"id": c.id, "name": c.name} for c in (req.unit_chapters or [])],
            target_count=req.target_count,
            duration_minutes=req.duration_minutes,
            passing_percent=req.passing_percent,
            book_id=req.book_id,
            title=req.title,
        ):
            print(f"--- EVENT {event['type']} for {req.level_id} ---", flush=True)
            if event["type"] == "done":
                quiz = event["quiz"]
                quiz_data = quiz.to_dict()
                quiz_id = f"quiz_{req.user_id}_{req.level_id}"
                await asyncio.to_thread(save_quiz_to_firestore, quiz_id, quiz_data, req.user_id)
                print(f"Background quiz generation for {quiz_id} complete.", flush=True)
    except Exception as e:
        print(f"Background quiz generation failed: {e}", flush=True)

@app.post("/quiz/generate/background")
async def generate_quiz_background(
    req: QuizBackgroundGenerateRequest,
    background_tasks: BackgroundTasks,
    services: Services = Depends(get_services),
):
    """
    Generate a quiz in the background and save to Firestore.
    Returns 202 Accepted immediately.
    """
    background_tasks.add_task(background_quiz_generator, req, services)
    return {"status": "accepted", "message": "Quiz generation started in background"}


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "streaming": True}

@app.post("/debug/search")
def debug_search(req: AskRequest, services: Services = Depends(get_services)):
    services.load_book(req.book_id)
    results = services.search(req.query, max_results=10)
    return {
        "query": req.query,
        "results": [
            {
                "node_id": r.get("node_id"),
                "title": r.get("title"),
                "score": r.get("score"),
                "source": r.get("source"),
                "content_preview": r.get("content", "")[:200],
                "path": r.get("path"),
            }
            for r in results
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)