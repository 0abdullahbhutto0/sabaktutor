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
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from quiz.descriptive_generator import DescriptiveQuiz
from api.schemas import (
    AskRequest,
    SummarizeRequest,
    QuizBackgroundGenerateRequest,
    DescriptiveGenerateRequest,
    DescriptiveEvaluateRequest,
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
        async for token in services.ask_stream(req.query, req.history, req.previous_summary, max_results=5):
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

@app.post("/ask/summarize")
async def ask_summarize(req: SummarizeRequest, services: Services = Depends(get_services)):
    """
    Compress a chat history into a dense summary.
    """
    summary = await services.summarize_history(req.history)
    return {"summary": summary}

async def background_mixed_quiz_generator(req: QuizBackgroundGenerateRequest, services: Services):
    """
    Generate a mixed interactive quiz in background.
    """
    print(f"--- STARTING MIXED QUIZ GEN FOR {req.level_id} ---", flush=True)
    try:
        services.load_book(req.book_id)
        if req.quiz_type == "chapter" and req.chapter_id:
            nodes = services.quiz_generator._get_chapter_nodes(services._active_tree, req.chapter_id)
            chapter_ids = [req.chapter_id]
            default_title = f"{req.chapter_id} - Mixed Quiz"
            duration = 20
            passing = 60
        elif req.quiz_type == "unit" and req.unit_chapters:
            nodes = []
            chapter_ids = []
            for ch in req.unit_chapters:
                nodes.extend(services.quiz_generator._get_chapter_nodes(services._active_tree, ch))
                chapter_ids.append(ch)
            default_title = f"Unit Test - Mixed Quiz"
            duration = 45
            passing = 50
        else:  # full book
            nodes = [n for n in services._active_tree.get_all_nodes() if not n.is_root and n.content.strip()]
            chapter_ids = []
            default_title = f"{req.book_id} - Full Book Mixed Quiz"
            duration = 90
            passing = 50

        content_nodes = [n for n in nodes if n.content.strip()]
        if not content_nodes:
            print("No content available for mixed quiz generation", flush=True)
            return

        content_text = ""
        for i, node in enumerate(content_nodes, 1):
            content_text += f"--- SECTION {i}: {node.title or 'Untitled'} ---"
            content_text += f"{node.content}"

        prompt = services.prompts.generate_mixed_quiz(
            content_text=content_text,
            total_items=req.target_count,
            book_id=req.book_id,
        )

        if not services.quiz_generator.llm:
            print("LLM not configured", flush=True)
            return

        full_response = []
        async for token in services.quiz_generator.llm.stream_complete(prompt, max_tokens=30000):
            full_response.append(token)

        response_text = "".join(full_response)

        items = services.quiz_generator._parse_mixed_quiz_response(response_text, content_nodes)
        items = items[:req.target_count]

        from quiz.quiz_generator import InteractiveQuiz

        mixed_quiz = InteractiveQuiz(
            book_id=req.book_id,
            title=req.title or default_title,
            chapter_ids=chapter_ids,
            items=items,
            duration_minutes=duration,
            passing_percent=passing,
        )

        quiz_data = mixed_quiz.to_dict()
        quiz_id = f"quiz_{req.user_id}_{req.book_id}_{req.level_id}"

        await asyncio.to_thread(
            save_quiz_to_firestore, 
            quiz_id, 
            quiz_data, 
            req.user_id,
        )

        print(f"Mixed quiz generation for {quiz_id} complete. Items: {len(items)}", flush=True)

    except Exception as e:
        print(f"Mixed quiz generation failed: {e}", flush=True)


@app.post("/quiz/generate/interactive/background")
async def generate_mixed_quiz_background(
    req: QuizBackgroundGenerateRequest,
    background_tasks: BackgroundTasks,
    services: Services = Depends(get_services),
):
    """
    Generate a mixed interactive quiz (board-pattern MCQs + true/false + fill-blank + calc)
    in the background and save to Firestore.
    Returns 202 Accepted immediately.
    """
    background_tasks.add_task(background_mixed_quiz_generator, req, services)
    return {"status": "accepted", "message": "Mixed quiz generation started in background"}


async def background_lesson_generator(req: QuizBackgroundGenerateRequest, services: Services):
    print(f"--- STARTING BACKGROUND LESSON GEN FOR {req.level_id} ---", flush=True)
    try:
        services.load_book(req.book_id)
        async for event in services.quiz_generator.generate_lesson_streaming(
            document_tree=services._active_tree,
            chapter_id=req.chapter_id or "",
            target_count=req.target_count,
            book_id=req.book_id,
            title=req.title,
        ):
            if event["type"] == "done":
                lesson = event["lesson"]
                lesson_data = lesson.to_dict()
                lesson_id = f"lesson_{req.user_id}_{req.book_id}_{req.level_id}"
                await asyncio.to_thread(save_quiz_to_firestore, lesson_id, lesson_data, req.user_id, 'lessons')
                print(f"Background lesson generation for {lesson_id} complete.", flush=True)
    except Exception as e:
        print(f"Background lesson generation failed: {e}", flush=True)

@app.post("/quiz/generate/lesson/background")
async def generate_lesson_background(
    req: QuizBackgroundGenerateRequest,
    background_tasks: BackgroundTasks,
    services: Services = Depends(get_services),
):
    """
    Generate a lesson in the background and save to Firestore.
    Returns 202 Accepted immediately.
    """
    background_tasks.add_task(background_lesson_generator, req, services)
    return {"status": "accepted", "message": "Lesson generation started in background"}


@app.post("/descriptive/generate/stream")
async def generate_descriptive_stream(
    req: DescriptiveGenerateRequest,
    services: Services = Depends(get_services),
):
    """
    Generate chapter-wise descriptive quiz.
    Returns: 4 short (Section A, 3 marks each) + 1 long (Section C, 6 marks).
    Total 18 marks.
    """
    try:
        services.load_book(req.book_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Book '{req.book_id}' not found: {str(e)}")

    async def generator() -> AsyncGenerator[str, None]:
        yield sse_stream("status", {
            "message": "Generating chapter descriptive quiz (4 short + 1 long)...",
            "step": 1,
            "pattern_learning": True,
        })

        async for event in services.generate_descriptive_quiz(
            chapter_id=req.chapter_id,
            title = req.book_id + "_" + str(uuid4())
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
                    "chapter_id": quiz.chapter_id,
                    "section_b_count": len(quiz.section_b),
                    "section_c_count": len(quiz.section_c),
                    "total_marks": quiz.total_marks,
                    "duration_minutes": quiz.duration_minutes,
                    "instructions": quiz.instructions,
                    "patterns_used": list(set(
                        q.pattern_used for q in quiz.section_b + quiz.section_c if q.pattern_used
                    )),
                })

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/descriptive/evaluate/stream")
async def evaluate_descriptive_stream(
    req: DescriptiveEvaluateRequest,
    services: Services = Depends(get_services),
):
    """
    Evaluate ALL 5 descriptive answers together (batch evaluation).
    Client passes back the FULL QUIZ (from generate response) + student answers.
    """
    try:
        quiz = DescriptiveQuiz.from_dict(req.quiz)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid quiz data: {str(e)}")

    try:
        services.load_book(quiz.book_id)
    except Exception:
        pass
    
    answer_map = {a.question_id: a.answer_text for a in req.answers}
    all_questions = quiz.section_b + quiz.section_c
    
    ordered_answers = []
    for q in all_questions:
        ordered_answers.append(answer_map.get(q.id, ""))

    async def generator() -> AsyncGenerator[str, None]:
        yield sse_stream("status", {
            "message": "Evaluating all 5 answers...",
            "step": 1,
            "batch_evaluation": True,
        })

        async for event in services.evaluate_descriptive_all(
            quiz=quiz,
            answers=ordered_answers,
            time_taken_minutes=req.time_taken_minutes,
        ):
            if event["type"] == "token":
                yield sse_stream("token", {"token": event["token"]})
            elif event["type"] == "error":
                yield sse_stream("error", {"message": event["message"]})
            elif event["type"] == "done":
                result = event["evaluation"]
                
                result_data = result.to_dict()
                result_data["quiz_id"] = quiz.id
                result_data["book_id"] = quiz.book_id
                result_data["chapter_id"] = quiz.chapter_id
                
                try:
                    # save_quiz_to_firestore(
                    #     doc_id=f"desc_result_{quiz.id}",
                    #     data=result_data,
                    #     collection="descriptive_results"
                    # )
                    pass
                except Exception as e:
                    print(f"Firestore save error: {e}")
                
                yield sse_stream("done", {
                    "evaluation": result.to_dict(),
                    "total_marks_obtained": result.total_marks_obtained,
                    "total_max_marks": result.total_max_marks,
                    "percentage": result.percentage,
                    "passed": result.passed,
                    "overall_feedback": result.overall_feedback,
                    "stored": True,
                })

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "streaming": True}

@app.post("/debug/search")
def debug_search(req: AskRequest, services: Services = Depends(get_services)):
    services.load_book(req.book_id)
    results = services.search(req.query, max_results=5)
    return {
        "query": req.query,
        "results": [
            {
                "node_id": r.get("node_id"),
                "title": r.get("title"),
                "score": r.get("score"),
                "source": r.get("source"),
                "content_preview": r.get("content", ""),
                "start_index": r.get("start_index",0),
                "path": r.get("path"),
            }
            for r in results
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)