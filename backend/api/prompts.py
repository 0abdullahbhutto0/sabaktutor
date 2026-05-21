"""
Custom Prompts for LLM Interactions
==================================
All prompts centralized for easy customization.
"""


class Prompts:
    """Prompt templates for LLM interactions."""

    @staticmethod
    def ask_stream(
        query: str,
        context: str,
        book_title: str,
    ) -> str:
        """
        Generate prompt for streaming Q&A about book content.

        Args:
            query: The user's question
            context: Retrieved relevant content from the book tree
            book_title: The book title
        """
        return f"""You are a helpful tutor for the Sindh Board curriculum. Answer the student's question based on the provided textbook content.

Book: {book_title}

RELEVANT CONTENT:
{context}

STUDENT QUESTION:
{query}

INSTRUCTIONS:
- Answer based ONLY on the provided textbook content
- If the content doesn't contain the answer, say so clearly
- Be concise but thorough
- Use simple language suitable for the student's level
- Include examples from the text when relevant
- give citation at end include page number

Answer:"""

    @staticmethod
    def teacher_system(book_title: str = "") -> str:
        """System message for the tutor."""
        return f"""You are an expert educational tutor for the Sindh Board curriculum.
{('Book: ' + book_title) if book_title else ''}
You help students understand concepts from their textbooks clearly and accurately.
Always base your answers on the provided content."""

    @staticmethod
    def quiz_batch(
        content_text: str,
        total_questions: int,
        book_title: str,
    ) -> str:
        """
        Generate prompt for batch MCQ quiz generation.

        Args:
            content_text: The textbook content to generate questions from
            total_questions: Total number of questions to generate
            book_title: The book title (e.g., "Physics Grade 9")
        """
        return f"""You are an expert educational content creator for the Sindh Board curriculum.

Generate {total_questions} high-quality multiple-choice questions (MCQs) based on the following textbook content.

Book: {book_title}

CONTENT:
{content_text}

REQUIREMENTS:
1. Generate exactly {total_questions} MCQs covering the key concepts in the content
2. Each question should have:
   - A clear, grammatically correct stem (question)
   - 4 distinct options (A, B, C, D)
   - Only ONE correct answer
   - A difficulty level: "easy", "medium", or "hard"
   - A topic label (e.g., "measurement", "kinematics", "forces")
3. Mix of difficulties: ~25% easy, ~50% medium, ~25% hard
4. Questions should test understanding, not just recall
5. Do not include the correct answer in the stem
6. Options should be plausible but clearly distinguishable

OUTPUT FORMAT:
Return a JSON array with {total_questions} objects. Each object must have:
- "stem": The question text
- "options": Array of 4 option strings
- "correct_index": 0-3 indicating the correct option
- "difficulty": "easy", "medium", or "hard"
- "topic": Brief topic label
- "chunk_ref": Reference to which content section (1, 2, 3...) the question relates to

Example:
[
  {{
    "stem": "What is the SI unit of force?",
    "options": ["Newton", "Joule", "Watt", "Pascal"],
    "correct_index": 0,
    "difficulty": "easy",
    "topic": "measurement",
    "chunk_ref": 1
  }}
]

Generate the questions now:"""

    @staticmethod
    def quiz_single(
        content: str,
        difficulty: str = "medium",
        topic: str = "general",
        book_title: str = "",
    ) -> str:
        """Generate prompt for a single MCQ."""
        return f"""Generate one MCQ based on this content:

Book: {book_title}

Content:
{content}

Requirements:
- Difficulty: {difficulty}
- Topic: {topic}
- Return as JSON with: stem, options (array of 4), correct_index (0-3), difficulty, topic

JSON:"""

    @staticmethod
    def explain_answer(
        question: str,
        correct_answer: str,
        options: list,
        book_title: str = "",
    ) -> str:
        """Generate prompt for explaining why an answer is correct."""
        return f"""Explain why the following answer is correct for this question:

Book: {book_title}

Question: {question}
Correct Answer: {correct_answer}
All Options: {options}

Provide a brief, educational explanation (2-3 sentences) of why the correct answer is right.
Keep the explanation concise and suitable for a student. Focus on the key concept being tested."""

    @staticmethod
    def generate_summary(content: str, max_sentences: int = 5) -> str:
        """Generate a summary of content."""
        return f"""Summarize the following content in exactly {max_sentences} sentences:

{content}

Keep the summary clear, accurate, and focused on key points."""
