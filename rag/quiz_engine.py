"""
Quiz Engine Module
==================
Simple adaptive feedback after quiz.
Returns summary + preparation tips. No weak area tracking.
"""

import json
import time
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass, field
import uuid
from quiz_generator import Quiz, MCQQuestion


@dataclass
class QuizAttempt:
    """Quiz attempt record."""
    attempt_id: str = ""
    quiz_id: str = ""
    user_id: str = "default_user"
    started_at: float = 0.0
    completed_at: float = 0.0
    responses: List[Dict[str, Any]] = field(default_factory=list)
    score: int = 0
    total: int = 0
    score_percent: float = 0.0
    passed: bool = False
    topic_mastery: Dict[str, float] = field(default_factory=dict)
    time_per_question: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "quiz_id": self.quiz_id,
            "user_id": self.user_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "responses": self.responses,
            "score": self.score,
            "total": self.total,
            "score_percent": self.score_percent,
            "passed": self.passed,
            "topic_mastery": self.topic_mastery,
            "time_per_question": self.time_per_question,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QuizAttempt":
        return cls(
            attempt_id=data.get("attempt_id", ""),
            quiz_id=data.get("quiz_id", ""),
            user_id=data.get("user_id", "default_user"),
            started_at=data.get("started_at", 0),
            completed_at=data.get("completed_at", 0),
            responses=data.get("responses", []),
            score=data.get("score", 0),
            total=data.get("total", 0),
            score_percent=data.get("score_percent", 0),
            passed=data.get("passed", False),
            topic_mastery=data.get("topic_mastery", {}),
            time_per_question=data.get("time_per_question", []),
        )


@dataclass
class QuizFeedback:
    """Simple feedback after quiz."""
    score_percent: float = 0.0
    passed: bool = False
    summary: str = ""           # How quiz went
    preparation: str = ""         # What to prepare for future

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score_percent": self.score_percent,
            "passed": self.passed,
            "summary": self.summary,
            "preparation": self.preparation,
        }


class QuizEngine:
    """Simple quiz engine. Grades quiz, returns summary + preparation tips."""

    def __init__(self, storage_dir: str = "./quiz_data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)

        self.quizzes_file = self.storage_dir / "quizzes.json"
        self.attempts_file = self.storage_dir / "attempts.json"

        self._quizzes: Dict[str, Quiz] = {}
        self._attempts: List[QuizAttempt] = []

        self._load_all()

    def _load_all(self):
        if self.quizzes_file.exists():
            with open(self.quizzes_file) as f:
                data = json.load(f)
                self._quizzes = {k: Quiz.from_dict(v) for k, v in data.items()}

        if self.attempts_file.exists():
            with open(self.attempts_file) as f:
                data = json.load(f)
                self._attempts = [QuizAttempt.from_dict(a) for a in data]

    def _save_quizzes(self):
        with open(self.quizzes_file, 'w') as f:
            json.dump({k: v.to_dict() for k, v in self._quizzes.items()}, f, indent=2)

    def _save_attempts(self):
        with open(self.attempts_file, 'w') as f:
            json.dump([a.to_dict() for a in self._attempts], f, indent=2)

    # -- Quiz Storage --

    def store_quiz(self, quiz: Quiz) -> str:
        self._quizzes[quiz.id] = quiz
        self._save_quizzes()
        return quiz.id

    def get_quiz(self, quiz_id: str) -> Optional[Quiz]:
        return self._quizzes.get(quiz_id)

    def list_quizzes(self, quiz_type: Optional[str] = None,
                     subject: Optional[str] = None,
                     grade: Optional[str] = None) -> List[Quiz]:
        results = list(self._quizzes.values())
        if quiz_type:
            results = [q for q in results if q.quiz_type == quiz_type]
        if subject:
            results = [q for q in results if q.subject == subject]
        if grade:
            results = [q for q in results if q.grade == grade]
        return results

    def delete_quiz(self, quiz_id: str):
        if quiz_id in self._quizzes:
            del self._quizzes[quiz_id]
            self._save_quizzes()

    # -- Grading --

    def grade_attempt(self, quiz_id: str, responses: List[Dict[str, Any]],
                      user_id: str = "default_user") -> QuizFeedback:
        """
        Grade quiz and return simple feedback.
        Returns QuizFeedback with summary + preparation tips.
        """
        quiz = self.get_quiz(quiz_id)
        if not quiz:
            raise ValueError(f"Quiz {quiz_id} not found")

        correct = 0
        topic_correct: Dict[str, int] = {}
        topic_total: Dict[str, int] = {}
        response_details = []
        time_per_question = []

        for resp in responses:
            q_id = resp.get("question_id")
            selected = resp.get("selected_index", -1)
            time_sec = resp.get("time_seconds", 0)
            time_per_question.append(time_sec)

            question = next((q for q in quiz.questions if q.id == q_id), None)
            if not question:
                continue

            correct_idx = next((i for i, o in enumerate(question.options) if o.is_correct), -1)
            is_correct = (0 <= selected < len(question.options) and selected == correct_idx)

            if is_correct:
                correct += 1
                topic_correct[question.topic] = topic_correct.get(question.topic, 0) + 1

            topic_total[question.topic] = topic_total.get(question.topic, 0) + 1

            response_details.append({
                "question_id": q_id,
                "selected_index": selected,
                "correct_index": correct_idx,
                "is_correct": is_correct,
                "time_seconds": time_sec,
            })

        # Calculate topic mastery
        topic_mastery = {}
        for topic, total_q in topic_total.items():
            c = topic_correct.get(topic, 0)
            topic_mastery[topic] = round((c / total_q) * 100, 1)

        total = len(quiz.questions)
        score_percent = (correct / total * 100) if total > 0 else 0
        passed = score_percent >= quiz.passing_percent

        # Save attempt
        attempt = QuizAttempt(
            attempt_id=str(uuid.uuid4())[:12],
            quiz_id=quiz_id,
            user_id=user_id,
            started_at=responses[0].get("started_at", time.time()) if responses else time.time(),
            completed_at=time.time(),
            responses=response_details,
            score=correct,
            total=total,
            score_percent=round(score_percent, 1),
            passed=passed,
            topic_mastery=topic_mastery,
            time_per_question=time_per_question,
        )

        self._attempts.append(attempt)
        self._save_attempts()

        # Generate simple feedback
        return self._generate_feedback(attempt, topic_mastery)

    def _generate_feedback(self, attempt: QuizAttempt, topic_mastery: Dict[str, float]) -> QuizFeedback:
        """Generate summary + preparation tips."""

        score = attempt.score_percent
        passed = attempt.passed

        # Summary: how quiz went
        if score >= 90:
            summary = f"Outstanding! You scored {score}% -- near perfect! Your understanding is excellent."
        elif score >= 75:
            summary = f"Great job! You scored {score}% and passed comfortably. You are building strong knowledge."
        elif passed:
            summary = f"Good effort! You passed with {score}%. You are on the right track, keep it up!"
        elif score >= 40:
            summary = f"You scored {score}%. Do not worry -- review the material and try again. You will improve!"
        else:
            summary = f"You scored {score}%. This is a learning opportunity! Go back to the chapter and study the basics."

        # Preparation: what to prepare for future
        weak_topics = [t for t, pct in topic_mastery.items() if pct < 60]
        strong_topics = [t for t, pct in topic_mastery.items() if pct >= 80]

        # Clean topic names
        weak_clean = [t.replace("_", " ").title() for t in weak_topics]
        strong_clean = [t.replace("_", " ").title() for t in strong_topics]

        if weak_clean and strong_clean:
            # Mixed performance
            prep = f"Prepare by focusing on {weak_clean[0]}"
            if len(weak_clean) > 1:
                prep += f" and {weak_clean[1]}"
            prep += f". You already have a good grasp of {strong_clean[0]}"
            if len(strong_clean) > 1:
                prep += f" and {strong_clean[1]}"
            prep += ", so build on that strength while filling the gaps."

        elif weak_clean:
            # Only weak areas
            if len(weak_clean) == 1:
                prep = f"Focus on understanding {weak_clean[0]}. Re-read the chapter, watch video tutorials, and practice more questions on this topic before your next quiz."
            elif len(weak_clean) == 2:
                prep = f"Work on {weak_clean[0]} and {weak_clean[1]}. These are your priority areas -- review the relevant chapters and do practice exercises."
            else:
                topics = ", ".join(weak_clean[:3])
                prep = f"You need to strengthen your understanding of {topics}. Go back to the basics, review each chapter carefully, and attempt the chapter exercises before retaking the quiz."

        elif strong_clean:
            # Only strong areas
            prep = f"Excellent work! You have mastered {strong_clean[0]}"
            if len(strong_clean) > 1:
                prep += f" and {strong_clean[1]}"
            prep += ". You are ready to move on to advanced topics or attempt a full mock exam."

        else:
            prep = "Keep practicing consistently. Review the chapter material and try the quiz again to see improvement."

        return QuizFeedback(
            score_percent=score,
            passed=passed,
            summary=summary,
            preparation=prep,
        )

    # -- Simple Stats --

    def get_attempts_for_quiz(self, quiz_id: str) -> List[QuizAttempt]:
        return [a for a in self._attempts if a.quiz_id == quiz_id]

    def get_user_stats(self) -> Dict[str, Any]:
        if not self._attempts:
            return {"total_attempts": 0, "average_score": 0}

        total = len(self._attempts)
        passed = sum(1 for a in self._attempts if a.passed)
        avg = sum(a.score_percent for a in self._attempts) / total

        return {
            "total_attempts": total,
            "passed": passed,
            "failed": total - passed,
            "average_score": round(avg, 1),
        }

    def get_all_questions_pool(self) -> List[MCQQuestion]:
        pool = []
        for quiz in self._quizzes.values():
            pool.extend(quiz.questions)
        return pool

    def clear_all_data(self):
        self._quizzes.clear()
        self._attempts.clear()
        self._save_quizzes()
        self._save_attempts()
