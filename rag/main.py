"""
Hybrid Tree Search + Quiz System 
======================================================
Measures:
- Setup time
- Tree load + indexing
- Quiz generation (LLM)
- Quiz taking (grading)
- Total runtime
"""

import json
import uuid
import requests
import time
from typing import List, Dict, Optional

from hybrid_tree_search import (
    HybridSearchEngine,
    SearchOptions,
    DocumentTree,
    TreeNode,
    Chunk,
    NodeType
)
from quiz_generator import QuizGenerator, Quiz
from quiz_engine import QuizEngine



_tree: Optional[DocumentTree] = None
_engine: Optional[HybridSearchEngine] = None
_quiz_gen: Optional[QuizGenerator] = None
_quiz_engine: Optional[QuizEngine] = None

_openrouter_key: Optional[str] = None
_openrouter_model: str = ""

_book_path: str = "cs_9.json"
_subject: str = "Computer Science"
_grade: str = "9"


def _init_search():
    global _tree, _engine
    if _engine is not None:
        return

    _tree = _load_tree(_book_path)

    _engine = HybridSearchEngine()
    _engine.index_tree(_tree)
    


def _init_quiz():
    global _quiz_gen, _quiz_engine
    if _quiz_engine is not None:
        return

    _quiz_gen = QuizGenerator(api_key=_openrouter_key, model=_openrouter_model)
    _quiz_engine = QuizEngine(storage_dir="./quiz_data")



def _load_tree(filepath: str) -> DocumentTree:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    tree = DocumentTree()

    def infer_node_type(title: str) -> NodeType:
        t = (title or "").strip().upper()
        if t in ("COMPUTER SCIENCE", "ROOT", "BOOK"):
            return NodeType.ROOT
        if t[:2].replace('.', '').isdigit():
            return NodeType.CHAPTER
        if t[:3].replace('.', '').isdigit():
            return NodeType.SECTION
        return NodeType.PARAGRAPH

    def process(nodes, parent_id=None):
        for n in nodes:
            node_id = n.get("node_id") or str(uuid.uuid4())[:8]
            content = n.get("text") or n.get("content", "")
            title = n.get("title", "")
            children = n.get("nodes", [])

            if str(node_id) in ("0", "0000"):
                if children:
                    process(children, tree.root_id)
                continue

            node = TreeNode(
                id=node_id,
                node_type=infer_node_type(title),
                content=content,
                title=title,
                metadata={"node_id": node_id}
            )

            if content:
                node.add_chunk(Chunk(content=content))

            tree.add_node(node, parent_id or tree.root_id)

            if children:
                process(children, node.id)

    if isinstance(data, list):
        process(data)
    else:
        process(data.get("nodes", [data]))

    return tree


def _build_context(results: List[Dict]) -> str:
    return "\n\n".join(
        f"Source: {r.get('title', 'Untitled')}\nContent: {r.get('content', '')}"
        for r in results
    )



def _call_openrouter(prompt: str, system: str = "", max_retries: int = 3) -> str:
    if not _openrouter_key:
        return "[No API key]"

    headers = {
        "Authorization": f"Bearer {_openrouter_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost",
        "X-Title": "Quiz System"
    }

    payload = {
        "model": _openrouter_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 4000
    }

    for i in range(max_retries):
        try:
       
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
        

            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

        except Exception as e:
            if i == max_retries - 1:
                return str(e)
            time.sleep(2 ** i)

    return "failed"


def setup(book_path: str, openrouter_key: str, openrouter_model: str,
          subject: str = "Computer Science", grade: str = "9"):


    global _book_path, _openrouter_key, _openrouter_model, _subject, _grade

    _book_path = book_path
    _openrouter_key = openrouter_key
    _openrouter_model = openrouter_model
    _subject = subject
    _grade = grade

    _init_search()
    _init_quiz()



def ask_llm(query: str, max_results: int = 3) -> str:
    _init_search()

    results = _engine.search(query, SearchOptions(max_results=max_results))

    if not results.results:
        return "No data found"

    context = _build_context(results.results)

    system = f"You are a teacher for {_grade} {_subject}"

    prompt = f"""
Context:
{context}

Question: {query}
"""

    answer = _call_openrouter(prompt, system)

    return answer



def do_quiz(action: str, **kwargs):

    _init_quiz()
    _init_search()

    action = action.lower()

    if action == "generate":


        quiz = _quiz_gen.generate_chapter_quiz(
            _tree,
            _subject,
            _grade,
            kwargs.get("chapter_id", ""),
            kwargs.get("chapter_name", "")
        )

       

        _quiz_engine.store_quiz(quiz)
        return quiz

    elif action == "take":


        result = _quiz_engine.grade_attempt(
            kwargs["quiz_id"],
            kwargs["responses"],
            kwargs.get("user_id", "default_user")
        )


        return result

    elif action == "stats":
        return _quiz_engine.get_user_stats()

    else:
        raise ValueError(action)


# ---------------- TEST RUN ---------------- #

if __name__ == "__main__":


    setup(
        book_path="cs_9.json",
        openrouter_key="",
        openrouter_model="inclusionai/ring-2.6-1t:free"
    )

    quiz = do_quiz(
        "generate",
        chapter_id="0057",
        chapter_name="INTRODUCTION TO DATABASE SYSTEM"
    )

    print(f"\nQuiz: {quiz.title}")

    responses = [
        {
            "question_id": q.id,
            "selected_index": 0,
            "time_seconds": 40
        }
        for q in quiz.questions
    ]

    feedback = do_quiz(
        "take",
        quiz_id=quiz.id,
        responses=responses
    )

    print("\n================ RESULT ================\n")
    print(f"Score: {feedback.score_percent}%")
    print(f"Passed: {feedback.passed}")
    print(f"\nSummary:\n{feedback.summary}")
    print(f"\nPrep:\n{feedback.preparation}")