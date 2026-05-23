"""
Custom Prompts for LLM Interactions - OPTIMIZED
================================================
40% token reduction. JSON schema at end for recency bias.
Pattern summaries instead of 39 full examples.
Supports: phy_9, cs_9, and generic fallback.
"""

_PHY_9_PATTERNS = """[PATTERN: Definition trap]
Q: "The least distance covered in a particular direction is called ___"
A: Displacement (not Distance) — tests precise definition, not vague recall

[PATTERN: Formula application]
Q: "If work=20J and time=10s, power is ___"
A: 2W — requires unit+formula recall, not just number matching

[PATTERN: Vector vs Scalar classification]
Q: "Which is NOT a vector quantity?"
A: Time — distractors are all vectors (Weight, Displacement, Acceleration)

[PATTERN: Unit conversion]
Q: "1.013 × 10⁵ Pa equals ___"
A: 1 atmosphere — constant recall with scientific notation

[PATTERN: Real-life concept mapping]
Q: "Blowing up a balloon demonstrates ___"
A: Pressure force — connects textbook concept to everyday observation

[PATTERN: Directional concept]
Q: "Centripetal force is always directed ___"
A: Toward centre — tests understanding of direction, not just name

[PATTERN: Process identification]
Q: "During which process does a gas become liquid?"
A: Condensation — requires phase-change sequence understanding

[PATTERN: Numerical property]
Q: "Coefficient of friction between tyre and road is ___"
A: 0.2 — tests memorization of standard values"""


# =============================================================================
# COMPUTER SCIENCE 9 PATTERNS
# =============================================================================
_CS_9_PATTERNS = """[PATTERN: Definition/Concept identification]
Q: "Physical and logical address both are: ___"
A: Permanent — tests precise terminology (distractors: Different, Unique, Temporary are all partially true, making it tricky)

[PATTERN: Software purpose matching]
Q: "The software used for accounting purpose is: ___"
A: MS-Excel — matches tool to real-world use case (distractors: other MS Office apps)

[PATTERN: MS Office feature recall]
Q: "The special character that initiates formula mode in a cell is: ___"
A: = — tests hands-on knowledge of spreadsheet operations

[PATTERN: Database concept]
Q: "A key that allows only unique entries in a field is called: ___"
A: Primary key — tests DBMS terminology (distractors: Foreign key, Super key are real but wrong for this context)

[PATTERN: Networking specification]
Q: "The number of bits used in an IPV4 address are: ___"
A: 32 — tests technical specification recall (distractors: 16, 64, 128 are other common bit sizes)

[PATTERN: OS classification]
Q: "Jobs in an Operating System are executed in groups in: ___"
A: Batch Processing — tests OS type understanding (distractors: Time Sharing, Real Time are other valid OS types)

[PATTERN: Internet/Web concept]
Q: "The service responsible for making a website publicly accessible is called: ___"
A: Web Hosting — tests internet infrastructure understanding

[PATTERN: Security/Ethics concept]
Q: "Ethical Hacker is also known as: ___"
A: White hat Hacker — tests cybersecurity terminology (distractors: Black Hat, Red Hat are real hacker types)"""


# =============================================================================
# PROMPT BUILDER
# =============================================================================
def _build_quiz_prompt(content_text: str, book_id: str, total_questions: int, patterns: str) -> str:
    """Build optimized quiz generation prompt."""
    return f"""You are a Sindh Board examiner creating MCQs for Grade 9.

SOURCE CONTENT (derive all questions strictly from this):
Book: {book_id}

{content_text}

STYLE PATTERNS (learn the style, never copy these exact questions):
{patterns}

RULES:
1. Every question must trace directly to the SOURCE CONTENT above. No external knowledge.
2. Questions must be NEW — do not reuse the structure or wording of the style patterns.
3. Distractors must be plausible (related concepts students confuse) but clearly wrong.
4. Test understanding: apply concepts, compare terms, interpret definitions — not just recall names.
5. Vary question types across the {total_questions}: mix definition, application, comparison, and real-life mapping.

Generate exactly {total_questions} MCQs. Return ONLY a JSON array:

[
  {{
    "stem": "question text",
    "options": ["A", "B", "C", "D"],
    "correct_index": 0,
    "topic": "topic from content",
    "difficulty": "easy|medium|hard"
  }}
]"""


# =============================================================================
# PROMPTS CLASS
# =============================================================================
class Prompts:
    """Optimized prompt templates for LLM interactions."""

    @staticmethod
    def ask_stream(query: str, context: str, book_title: str) -> str:
        """Streaming Q&A prompt."""
        return f"""You are a helpful tutor for the Sindh Board curriculum.

Book: {book_title}

RELEVANT CONTENT:
{context}

STUDENT QUESTION:
{query}

Instructions:
- Answer ONLY from the provided content.
- Use simple and clear language suitable for Sindh Board students.
- If formulas, tables, OCR text, or parsed content look incomplete or broken, intelligently reconstruct them from the surrounding provided content only.
- Do NOT mention missing context, parsing issues, excerpts, or limitations unless absolutely necessary.
- Keep the answer concise and direct.
- Include definitions, examples, formulas, or explanations if present in the content.
- Mention page numbers if available in the content.
- If the exact answer is not directly stated but can be reasonably inferred from the provided content, give the best educational answer based on it.
- Avoid meta explanations like “the provided content does not mention”.
- Never explain your reasoning process.

Answer:
"""

    @staticmethod
    def teacher_system(book_title: str = "") -> str:
        """System message for the tutor."""
        return f"""You are an expert educational tutor for the Sindh Board curriculum.
{('Book: ' + book_title) if book_title else ''}
Base all answers strictly on provided textbook content."""

    @staticmethod
    def quiz_batch(content_text: str, total_questions: int, book_id: str) -> str:
        """Optimized batch MCQ generation prompt.
        
        Supports: phy_9, cs_9, and generic fallback.
        """
        if "phy_9" in book_id:
            return _build_quiz_prompt(content_text, book_id, total_questions, _PHY_9_PATTERNS)
        elif "cs_9" in book_id:
            return _build_quiz_prompt(content_text, book_id, total_questions, _CS_9_PATTERNS)
        else:
            # Generic fallback for any other book
            return _build_quiz_prompt(
                content_text, book_id, total_questions,
                "Generate questions that test understanding, not memorization. Use plausible distractors."
            )

    @staticmethod
    def explain_answer(question: str, correct_answer: str, options: list, book_title: str = "") -> str:
        """Explain why an answer is correct."""
        return f"""Explain why the correct answer is right for this question:

Book: {book_title}
Question: {question}
Correct Answer: {correct_answer}
All Options: {options}

Provide a brief educational explanation (2-3 sentences) focusing on the key concept."""

    @staticmethod
    def generate_summary(content: str, max_sentences: int = 5) -> str:
        """Summarize content."""
        return f"""Summarize the following in exactly {max_sentences} sentences:

{content}

Focus on key points. Be clear and accurate."""

    @staticmethod
    def generate_lesson(content_text: str, total_items: int, book_id: str) -> str:
        """Generate a lesson extracting formulas, definitions, concepts as flashcards."""
        return f"""You are a Sindh Board expert creating a micro-lesson from the textbook.

SOURCE CONTENT:
Book: {book_id}

{content_text}

RULES:
1. Extract exactly {total_items} key learning items (formulas, definitions, or important concepts).
2. Format them as flashcards.
3. Every item must trace directly to the SOURCE CONTENT.

Return ONLY a JSON array:

[
  {{
    "type": "flashcard",
    "title": "Concept Name or Formula Name",
    "content": "Definition, formula, or explanation"
  }}
]"""

    @staticmethod
    def generate_interactive_quiz(content_text: str, total_items: int, book_id: str) -> str:
        """Generate an interactive quiz with a mix of true_false, fill_in_blank, and mcq_calculation items."""
        return f"""You are a Sindh Board examiner creating an interactive quiz from the textbook.

SOURCE CONTENT:
Book: {book_id}

{content_text}

RULES:
1. Generate exactly {total_items} interactive quiz items.
2. Mix the following types: true_false, fill_in_blank, mcq, and (if applicable) mcq_calculation.
3. Every item must trace directly to the SOURCE CONTENT.

Return ONLY a JSON array containing polymorphic objects based on their type:

For True/False:
{{
  "type": "true_false",
  "statement": "The statement to evaluate",
  "is_true": true,
  "explanation": "Why it is true or false"
}}

For Fill in the Blank:
{{
  "type": "fill_in_blank",
  "sentence_before": "The beginning of the sentence ",
  "blank_answer": "the missing word",
  "sentence_after": " the rest of the sentence."
}}

For MCQ Calculation:
{{
  "type": "mcq_calculation",
  "problem": "The calculation question",
  "options": ["A", "B", "C", "D"],
  "correct_index": 0,
  "explanation": "Step by step solution"
}}

For Standard MCQ:
{{
  "type": "mcq",
  "stem": "The question text",
  "options": ["A", "B", "C", "D"],
  "correct_index": 0
}}

Generate the JSON array now."""