# Hybrid Tree Search + Quiz API

A FastAPI-based intelligent system for querying educational content and generating MCQ quizzes with real-time streaming support.

## Features

- **Book Auto-Discovery**: Automatically loads JSON book files from the project directory
- **Hybrid Tree Search**: Combines keyword and semantic search for accurate content retrieval
- **Streaming Q&A**: Get answers to questions with token-by-token streaming response
- **Streaming Quiz Generation**: Generate MCQ quizzes with real-time streaming (3-5 second latency)
- **Multiple Quiz Types**: Support for chapter, unit, and full-book quizzes
- **Balanced Distribution**: Even distribution of correct answers (A, B, C, D) and difficulty levels

## Tech Stack

- **FastAPI**: Modern async web framework
- **OpenAI SDK**: Compatible with OpenRouter API
- **SSE (Server-Sent Events)**: Real-time streaming responses
- **Pydantic**: Request/response validation

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env .env.example
```

## Configuration

Create a `.env` file in the project root:

```env
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=openrouter/owl-alpha
EMBEDDING_MODEL=nvidia/llama-nemotron-embed-vl-1b-v2:free
VECTOR_INDEX_DIR=./vector_index
DEFAULT_SUBJECT=Computer Science
DEFAULT_GRADE=9
```

## API Endpoints

### List Books
```
GET /books
```
Returns all auto-discovered books.

### Health Check
```
GET /health
```
Returns API status and version.

### Ask Question (Streaming)
```
POST /ask/stream
Content-Type: application/json

{
  "book_id": "cs_9",
  "query": "What is an algorithm?"
}
```
Streams LLM-generated answer with token-by-token response.

### Generate Quiz (Streaming)
```
POST /quiz/generate/stream
Content-Type: application/json

{
  "book_id": "cs_9",
  "quiz_type": "chapter",
  "chapter_id": "00057",
  "target_count": 20,
  "duration_minutes": 20,
  "passing_percent": 60
}
```
Streams quiz generation progress and final quiz JSON.

## Quiz Types

| Type | Description | Duration | Passing % |
|------|-------------|----------|-----------|
| `chapter` | Single chapter quiz | 20 min | 60% |
| `unit` | Multiple chapters (unit test) | 45 min | 50% |
| `full_book` | Entire book (mock exam) | 90 min | 50% |

## Running the Server

```bash
# Development mode with auto-reload
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## SSE Response Format

All streaming endpoints use Server-Sent Events:

```text
event: token
data: {"token": "This"}

event: token
data: {"token": " is"}

event: done
data: {"status": "complete"}
```

## Project Structure

```
.
├── api/
│   ├── main.py          # FastAPI application
│   ├── dependencies.py  # Dependency injection
│   ├── schemas.py       # Pydantic models
│   ├── prompts.py       # LLM prompts
│   └── streaming.py     # SSE helpers
├── core/
│   ├── streaming_client.py  # OpenAI SDK client
│   ├── book_manager.py      # Book management
│   ├── hybrid_search.py     # Search engine
│   └── embeddings.py        # Embedding manager
├── quiz/
│   └── quiz_generator.py    # Quiz generation
├── data/
│   └── *.json          # Book data files
└── vector_index/        # Cached vector indices
```

## Streaming Behavior

### Query Streaming
- First token arrives in 3-5 seconds
- Tokens stream as they arrive from LLM
- Final `done` event marks completion

### Quiz Streaming
- Status events show generation progress
- Tokens stream as LLM generates questions
- Final `done` event contains complete quiz JSON

## License

MIT