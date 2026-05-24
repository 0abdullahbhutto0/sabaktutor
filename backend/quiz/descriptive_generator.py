"""Descriptive Quiz Generator - Adaptive Pattern-Based
Supports: phy_9, cs_9, maths_9, phy_10, cs_10, maths_10, ... 11, 12
Easy to add new subjects/grades by adding pattern modules.
Quiz NOT stored. Client passes quiz back for evaluation.
Only evaluation results stored in Firestore."""


import json
import uuid
from typing import List, Dict, Optional, Any, AsyncGenerator
from dataclasses import dataclass, field

from core.streaming_client import StreamingLLMClient



_PHY_9_SHORT_PATTERNS = """
[Def+Ext] What do you mean by [C]? Also [ACTION] into [PROPERTY].
Ex: What do you mean by resolution of vector? Also split into components.

[Def+Factors] Define [C]. Write [N] factors affecting it.
Ex: Define pressure. Write two factors affecting pressure.

[Def+Formula+Unit] Define [C]. Write formula + SI unit.
Ex: Define density. Write formula and SI unit.

[Concept+Apps] What is [C]? Write [N] applications.
Ex: What is wind energy? Write two applications.

[Diff] Write [N] differences between [A] and [B].
Ex: Scalar vs vector differences.

[Def+Find] Define [C]. Find in: [LIST]
Ex: Define sig figs. Find in 1.33, 0.0012

[Derive] What is [C]? Derive [FORMULA].
Ex: Work. Derive W = Fd cosθ

[Formula+Factors] What is [C]? Write formula, unit, factors (names).
Ex: Moment of force...

[Convert] What is [C]? Convert: A→B, C→D formulas.
Ex: Temperature conversions
"""

_PHY_9_NUMERICAL_PATTERNS = """
[Mom] Gun m1 fires bullet m2 at v → find recoil.
Ex: 6kg gun, 40g bullet, 100m/s

[Gas] P1V1=P2V2 change V or P.
Ex: 120cm³ air, 140kPa → 840kPa

[Work] Power = W/t find result.
Ex: 1800J in 30min

[FreeFall] s=ut+½gt² find time/distance.
Ex: ball 90m

[Heat] Q=mcΔT energy required.
Ex: 50g water 40→70°C

[GravityW] W=mg or scale change on moon.
Ex: 900N on Earth

[Density] m=ρV for solid object.
Ex: iron sphere radius 18cm

[Kinematics] v²=u²+2as braking distance.
Ex: car 30m/s, a=6

[Vector] Fx=Fcosθ Fy=Fsinθ components.
Ex: 80N at 40°

[Spring] F=kx extension force.
Ex: k=15, x=30cm

[Gravity] F=Gm1m2/r² attraction.
Ex: 60kg & 70kg, 50m
"""

_PHY_9_LONG_PATTERNS = """
[Law+Derive] State law. Derive application formula.
Ex: Newton gravitation → Earth mass

[Def+Unit+Proof] Define + SI unit + prove law.
Ex: momentum conservation

[Concept+Derive] Define concept. Derive formula.
Ex: relative motion

[KMT] List variables explain one.
Ex: gas variables

[Types] Explain types + examples + conditions.
Ex: equilibrium

[Defs] Define multiple terms + benefits.
Ex: specific/latent heat

[ProsCons] Advantages + disadvantages + methods.
Ex: friction

[Fluid] Define + derive pressure + factors.
Ex: liquid pressure

[Proof] Define + prove formula.
Ex: satellite velocity

[Law+App] State law + daily life use.
Ex: Boyle's law

[Energy] Define KE & PE derive KE formula.
Ex: ½mv²

[Process] Define + factors affecting.
Ex: evaporation
"""


_CS_9_SHORT_PATTERNS = """
[DefOnly] Define [CONCEPT].
Ex: Define Control Unit. / Define computer hardware. / Define RAM and ROM.

[Def+Describe] Define [CONCEPT]. Also describe its [PROPERTY/TYPE/FUNCTION].
Ex: Define first generation of computer. Describe its characteristics.

[Def+Classify] Define [CONCEPT]. Classify it according to [CRITERION].
Ex: Define computer. Classify computer according to the technology.

[Def+Types] Define [CONCEPT]. Write [N] types of [CONCEPT].
Ex: Define buses. Describe their types. / Define topology and its types.

[Def+Functions] Define [CONCEPT]. Describe [N] functions of [CONCEPT].
Ex: Define Operating System. Describe its functions.

[Def+Features] Define [CONCEPT]. Write [N] features/properties of [CONCEPT].
Ex: Define Microsoft Word. / Define a good communication system. Describe properties.

[WhatIs+Describe] What is [CONCEPT]? Describe [ASPECT].
Ex: What is sorting? / What is computer security? / What is a Word Processor?

[WhatIs+List] What is [CONCEPT]? Write [N] popular names/examples.
Ex: What are Antivirus? Write few popular names of it.

[Diff] Differentiate between [A] and [B]. / Write [N] differences between [A] and [B].
Ex: Differentiate between Compiler and Interpreter.
Ex: Write three differences between physical address and logical address.

[Concept+Precautions] What is [CONCEPT]? Write [N] precautions to avoid [CONCEPT].
Ex: What is meant by Hacking? Write three precautions to avoid malware.

[Explain+List] Explain [CONCEPT]. Write [N] [ASPECTS].
Ex: Explain the importance of MS-Excel.

[HTMLTags] Explain the following tags: [TAG_LIST].
Ex: Explain <head>, <title>, <br>.

[ShortNote] Write a short note on [CONCEPT].
Ex: Write a note on Motherboard. / Write a note on Data Transmission Signals.

[DefOneOf] Define any one of the following: (i) [A] (ii) [B].
Ex: Define any one: (i) Data Communication (ii) Cyber Crime.

[Why+Reasons] Why is [CONCEPT] important? Write any [N] reasons.
Ex: Why is computer security important? Write any two reasons.
"""

_CS_9_LONG_PATTERNS = """
[Def+Components+Explain] Define [CONCEPT]. Explain its components.
Ex: Define Control Unit and Arithmetic Logic Unit (ALU).
Ex: Define software and its types.
Ex: Explain Microprocessor and its components.

[Def+Types+Explain] Define [CONCEPT]. Describe its types.
Ex: Define the types of computer according to technology.
Ex: Describe topology and its types.
Ex: Define the following Networks: (i) LAN (ii) MAN (iii) WAN.

[Functions+Explain] Write the functions of [CONCEPT_LIST].
Ex: Write the functions of: (i) Router (ii) Switch.
Ex: Describe components used in the communication system.

[BasicOps] Describe basic operations of computer.
Ex: Describe basic operations of computer. / What are the basic operations of the computer?

[Types+Examples] Write different types of [CONCEPT].
Ex: Write different types of websites.

[DBMS+Components] Define [CONCEPT]. Describe its components.
Ex: What is DBMS? Define any three components of DBMS.
Ex: Explain the basic components of DBMS.

[Process+Steps] What is [PROCESS]? Explain the steps in detail.
Ex: What is meant by Database Management System? Describe its working.

[Diff+Detail] Differentiate between [A] and [B] in detail.
Ex: Differentiate between Data Rate and Baud Rate.

[Def+Software+Types] What is computer software? Describe its types.
Ex: What is computer software? Describe its types. (System, Application, Utility)

[Concept+Detail] Describe [CONCEPT] in detail.
Ex: Describe Artificial Intelligence (AI).
Ex: Define Hypertext Markup Language (HTML). Explain its structure.
"""

_MATHS_9_SHORT_PATTERNS = """
[Solve] Solve/Evaluate: [PROBLEM]
Ex: Solve: 2x + 5 = 15

[Def+Property] Define [CONCEPT]. Write [N] properties of [CONCEPT].
Ex: Define rational numbers. Write two properties of rational numbers.

[Formula+Apply] Write the formula for [CONCEPT]. Apply it to find [RESULT].
Ex: Write formula for area of triangle. Apply it to find area with base 10cm, height 5cm.

[Simplify] Simplify: [EXPRESSION]
Ex: Simplify: (3x² + 2x - 5) + (2x² - 3x + 7)

[Factorize] Factorize: [EXPRESSION]
Ex: Factorize: x² - 5x + 6
"""

_MATHS_9_LONG_PATTERNS = """
[Theorem+Proof] State and prove [THEOREM].
Ex: State and prove Pythagoras theorem.

[Method+Example] Explain [METHOD]. Solve using [METHOD]: [PROBLEM]
Ex: Explain factorization method. Solve: x² - 5x + 6 = 0

[Concept+Derive] Define [CONCEPT]. Derive [FORMULA/EXPRESSION].
Ex: Define midpoint. Derive midpoint formula.

[Graph+Plot] Plot [EQUATION] on graph paper. Find [PROPERTY].
Ex: Plot y = 2x + 3. Find x-intercept and y-intercept.

[WordProblem] [SCENARIO]. Find [UNKNOWN].
Ex: A train travels 300km in 4 hours. Find average speed.
"""

_GENERIC_SHORT_PATTERNS = """
[Def+Ext] Define [CONCEPT]. Also explain [PROPERTY/ASPECT] of [CONCEPT].
Marks: 1 + 2

[Concept+List] What is [CONCEPT]? Write down [NUMBER] [ASPECTS] of [CONCEPT].
Marks: 1 + 2

[Diff] Write any [NUMBER] differences between [CONCEPT_A] and [CONCEPT_B].
Marks: 3

[ShortExplain] What do you mean by [CONCEPT]? Explain briefly.
Marks: 3
"""

_GENERIC_LONG_PATTERNS = """
[Concept+Detail] What is [CONCEPT]? Explain in detail with examples.
Marks: 2 + 4

[Types+Examples] Explain [NUMBER] types of [CONCEPT] with examples.
Marks: 3 + 3

[Process+Steps] What is [PROCESS]? Explain the steps in detail.
Marks: 2 + 4
"""


_STYLE_DNA = """
SINDH BOARD STYLE DNA:
- Sentence starters: "What do you mean by", "Define", "State and explain", "Write any", "Also write", "Describe"
- Connectors: "Also", "And", "Also write", "Also describe"
- Lists: Roman numerals (i), (ii), (iii) or "any [NUMBER]"
- Numericals: Values embedded in sentence. "Calculate the", "Find the", "Determine the"
- Tone: Direct, imperative. "Write down" not "You are required to write"
- Parenthetical: "(Only name)", "(decelerated a=6 m/s²)", "(G = 6.673 x 10⁻¹¹)"
- Marking implicit: Every question naturally splits into mark-sized parts
- CS specific: HTML tags in angle brackets, network acronyms (LAN/MAN/WAN), device names
"""


PATTERN_REGISTRY: Dict[str, Dict[str, str]] = {
    "phy_9": {
        "short": _PHY_9_SHORT_PATTERNS,
        "numerical": _PHY_9_NUMERICAL_PATTERNS,
        "long": _PHY_9_LONG_PATTERNS,
    },
    "cs_9": {
        "short": _CS_9_SHORT_PATTERNS,
        "numerical": "", 
        "long": _CS_9_LONG_PATTERNS,
    },
    "maths_9": {
        "short": _MATHS_9_SHORT_PATTERNS,
        "numerical": _MATHS_9_SHORT_PATTERNS,  # Maths "numericals" are problem-solving
        "long": _MATHS_9_LONG_PATTERNS,
    },
}


def get_patterns(book_id: str) -> Dict[str, str]:
    """Get patterns for a book_id. Falls back to generic if not found."""
    # Try exact match first
    if book_id in PATTERN_REGISTRY:
        return PATTERN_REGISTRY[book_id]
    
    # Try prefix match (e.g., "phy_10" not in registry, but "phy" patterns work)
    for key in PATTERN_REGISTRY:
        if book_id.startswith(key.split("_")[0] + "_"):
            return PATTERN_REGISTRY[key]
    
    # Fallback to generic
    return {
        "short": _GENERIC_SHORT_PATTERNS,
        "numerical": "",
        "long": _GENERIC_LONG_PATTERNS,
    }


def add_patterns(book_id: str, short: str, long: str, numerical: str = "") -> None:
    """Add new subject/grade patterns easily."""
    PATTERN_REGISTRY[book_id] = {
        "short": short,
        "numerical": numerical,
        "long": long,
    }


@dataclass
class DescriptiveQuestion:
    id: str = ""
    section: str = "B"
    type: str = "short_answer"
    stem: str = ""
    marks: int = 3
    topic: str = ""
    expected_points: List[str] = field(default_factory=list)
    rubric: str = ""
    correct_answer: str = ""
    formula_used: str = ""
    source_node_id: str = ""
    pattern_used: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "section": self.section,
            "type": self.type,
            "stem": self.stem,
            "marks": self.marks,
            "topic": self.topic,
            "expected_points": self.expected_points,
            "rubric": self.rubric,
            "correct_answer": self.correct_answer,
            "formula_used": self.formula_used,
            "source_node_id": self.source_node_id,
            "pattern_used": self.pattern_used,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DescriptiveQuestion":
        return cls(
            id=data.get("id", ""),
            section=data.get("section", "B"),
            type=data.get("type", "short_answer"),
            stem=data.get("stem", ""),
            marks=data.get("marks", 3),
            topic=data.get("topic", ""),
            expected_points=data.get("expected_points", []),
            rubric=data.get("rubric", ""),
            correct_answer=data.get("correct_answer", ""),
            formula_used=data.get("formula_used", ""),
            source_node_id=data.get("source_node_id", ""),
            pattern_used=data.get("pattern_used", ""),
        )


@dataclass
class DescriptiveQuiz:
    id: str = ""
    book_id: str = ""
    chapter_id: Optional[str] = None
    title: str = ""
    section_b: List[DescriptiveQuestion] = field(default_factory=list)
    section_c: List[DescriptiveQuestion] = field(default_factory=list)
    duration_minutes: int = 15
    total_marks: int = 18
    passing_percent: int = 40
    created_at: float = 0.0
    instructions: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:12]
        if not self.created_at:
            import time
            self.created_at = time.time()
        if not self.instructions:
            self.instructions = {
                "section_b": "Answer ALL FOUR (4) questions. Each carries 3 Marks.",
                "section_c": "Answer ALL ONE (1) question. Each carries 6 Marks.",
                "note": "Attempt ALL questions. No choice.",
            }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "book_id": self.book_id,
            "chapter_id": self.chapter_id,
            "title": self.title,
            "instructions": self.instructions,
            "section_b": [q.to_dict() for q in self.section_b],
            "section_c": [q.to_dict() for q in self.section_c],
            "duration_minutes": self.duration_minutes,
            "total_marks": self.total_marks,
            "passing_percent": self.passing_percent,
            "created_at": self.created_at,
            "section_b_count": len(self.section_b),
            "section_c_count": len(self.section_c),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DescriptiveQuiz":
        section_b = [DescriptiveQuestion.from_dict(q) for q in data.get("section_b", [])]
        section_c = [DescriptiveQuestion.from_dict(q) for q in data.get("section_c", [])]
        return cls(
            id=data.get("id", ""),
            book_id=data.get("book_id", ""),
            chapter_id=data.get("chapter_id"),
            title=data.get("title", ""),
            section_b=section_b,
            section_c=section_c,
            duration_minutes=data.get("duration_minutes", 15),
            total_marks=data.get("total_marks", 18),
            passing_percent=data.get("passing_percent", 40),
            created_at=data.get("created_at", 0.0),
            instructions=data.get("instructions", {}),
        )


@dataclass
class SingleEvaluation:
    question_id: str = ""
    marks_obtained: float = 0.0
    max_marks: int = 3
    feedback: str = ""
    missing_points: List[str] = field(default_factory=list)
    correct_points: List[str] = field(default_factory=list)
    suggestions: str = ""
    confidence: float = 0.0
    formula_correct: bool = False
    unit_correct: bool = False
    calculation_correct: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "marks_obtained": self.marks_obtained,
            "max_marks": self.max_marks,
            "feedback": self.feedback,
            "missing_points": self.missing_points,
            "correct_points": self.correct_points,
            "suggestions": self.suggestions,
            "confidence": self.confidence,
            "formula_correct": self.formula_correct,
            "unit_correct": self.unit_correct,
            "calculation_correct": self.calculation_correct,
        }


@dataclass
class BatchEvaluationResult:
    quiz_id: str = ""
    total_marks_obtained: float = 0.0
    total_max_marks: int = 18
    percentage: float = 0.0
    passed: bool = False
    evaluations: List[SingleEvaluation] = field(default_factory=list)
    overall_feedback: str = ""
    time_taken_minutes: Optional[int] = None
    created_at: float = 0.0

    def __post_init__(self):
        if not self.created_at:
            import time
            self.created_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quiz_id": self.quiz_id,
            "total_marks_obtained": self.total_marks_obtained,
            "total_max_marks": self.total_max_marks,
            "percentage": round(self.percentage, 2),
            "passed": self.passed,
            "evaluations": [e.to_dict() for e in self.evaluations],
            "overall_feedback": self.overall_feedback,
            "time_taken_minutes": self.time_taken_minutes,
            "created_at": self.created_at,
        }


# ============================================================================
# PROMPT BUILDER
# ============================================================================

class DescriptivePrompts:

    @staticmethod
    def generate_quiz(
        content_text: str,
        book_id: str,
        chapter_topics: List[str],
    ) -> str:
        patterns = get_patterns(book_id)
        
        short_patterns = patterns.get("short", _GENERIC_SHORT_PATTERNS)
        numerical_patterns = patterns.get("numerical", "")
        long_patterns = patterns.get("long", _GENERIC_LONG_PATTERNS)
        
        numerical_block = f"""
NUMERICAL PATTERNS (3 Marks each):
{numerical_patterns}
""" if numerical_patterns else ""

        return f"""You are a senior Sindh Board examiner creating ORIGINAL descriptive questions for Grade 9-10.

=== LEARN THE PATTERN (Study structures, NEVER copy examples) ===

SHORT ANSWER PATTERNS (3 Marks each):
{short_patterns}
{numerical_block}
LONG ANSWER PATTERNS (6 Marks each):
{long_patterns}

STYLE DNA:
{_STYLE_DNA}

=== SOURCE CONTENT (Generate STRICTLY from this) ===
Book: {book_id}
Chapter Topics: {', '.join(chapter_topics)}

{content_text}

=== GENERATION RULES ===
1. DO NOT copy example questions. Use their SENTENCE STRUCTURE only.
2. Every question must trace to SOURCE CONTENT.
3. Generate EXACTLY:
   - Section B: 4 questions (mix: 2 theory + 2 numerical if numericals available, else 4 theory)
   - Section C: 1 question (derivation, law, detailed explanation, or process)
4. Numericals must have realistic values. Include correct_answer and formula_used.
5. Each question needs: stem, marks, expected_points, rubric, correct_answer (numericals), formula_used (numericals)
6. Use Sindh Board language: "What do you mean by", "Write down", "State and explain", "Also write"
7. Use different patterns for each question

Return ONLY JSON:

{{
  "section_b": [
    {{
      "type": "short_answer|numerical",
      "stem": "question text",
      "marks": 3,
      "topic": "topic from content",
      "expected_points": ["pattern for marks (defination + example + formula ...)"],
      "rubric": "mark distribution",
      "correct_answer": "for numericals only",
      "formula_used": "for numericals only",
      "pattern_used": "which pattern template"
    }}
  ],
  "section_c": [
    {{
      "type": "long_answer|derivation|law_proof",
      "stem": "question text",
      "marks": 6,
      "topic": "topic from content",
      "expected_points": ["pattern of answer (definiation + examples ...)"],
      "rubric": "mark distribution",
      "pattern_used": "which pattern template"
    }}
  ]
}}"""

    @staticmethod
    def evaluate_all_answers(
        questions: List[DescriptiveQuestion],
        answers: List[str],
        book_id: str = "",
    ) -> str:
        qa_pairs = []
        for i, (q, a) in enumerate(zip(questions, answers), 1):
            numerical_extra = ""
            if q.type == "numerical":
                numerical_extra = f"""
    NUMERICAL CHECK for Q{i}:
    - Formula should be: {q.formula_used}
    - Correct answer: {q.correct_answer}
    - Check: Formula written? → Substitution correct? → Final answer + unit correct?"""

            qa_pairs.append(f"""QUESTION {i} (Marks: {q.marks}):
    {q.stem}
    
    MARKING RUBRIC:
    {q.rubric}
    
    EXPECTED POINTS:
    {chr(10).join(f"    - {p}" for p in q.expected_points)}
    {numerical_extra}
    
    STUDENT ANSWER {i}:
    {a}
    """)

        qa_block = "\n\n".join(qa_pairs)

        return f"""You are a strict Sindh Board examiner marking a Grade 9-10 chapter test.

SUBJECT: {book_id}

{qa_block}

EVALUATION RULES:
1. Evaluate ALL 5 answers together for consistency.
2. Be STRICT — no sympathy marks for vague answers.
3. For theory: Check expected points against student answer. 1 mark per valid point.
4. For numericals: Formula (1) + Substitution (1) + Answer+Unit (1). No formula = 0 marks.
5. If answer correct but no working shown: deduct 2 marks (award 1 only for answer).
6. Give specific feedback per question: what was correct, what was missing, how to improve.
7. Calculate total marks, percentage, and pass/fail (40% passing).

Return ONLY JSON:
{{
  "total_marks_obtained": 0.0,
  "total_max_marks": 18,
  "percentage": 0.0,
  "passed": false,
  "evaluations": [
    {{
      "question_id": "q1",
      "marks_obtained": 0.0,
      "max_marks": 3,
      "feedback": "specific feedback",
      "missing_points": ["what was missed"],
      "correct_points": ["what was correct"],
      "suggestions": "how to improve",
      "confidence": 0.95,
      "formula_correct": true,
      "unit_correct": true,
      "calculation_correct": true
    }}
  ],
  "overall_feedback": "summary of performance across all 5 questions"
}}"""


# ============================================================================
# GENERATOR CLASS
# ============================================================================

class DescriptiveQuizGenerator:

    def __init__(
        self,
        api_key: str = "",
        model: str = "openrouter/owl-alpha",
    ):
        self.api_key = api_key
        self.model = model
        self.llm = StreamingLLMClient(api_key, model) if api_key else None
        self.prompts = DescriptivePrompts()

    async def generate_streaming(
        self,
        document_tree,
        chapter_id: str,
        book_id: str = "",
        title: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:

        nodes = self._get_chapter_nodes(document_tree, chapter_id)
        selected_nodes = self._select_nodes(nodes, 8)

        if not selected_nodes:
            yield {"type": "error", "message": "No content available for this chapter"}
            return

        chapter_topics = list(set(
            n.get("node_title", "").split(".")[0].strip()
            for n in selected_nodes
            if n.get("node_title")
        ))[:5]

        content_text = ""
        for i, node in enumerate(selected_nodes, 1):
            content_text += f"\n--- PASSAGE {i} ---\n"
            content_text += f"Title: {node['node_title']}\n"
            content_text += f"Content: {node['content']}\n"

        prompt = self.prompts.generate_quiz(
            content_text=content_text,
            book_id=book_id,
            chapter_topics=chapter_topics,
        )

        if not self.llm:
            yield {"type": "error", "message": "LLM not configured"}
            return

        full_response = []
        async for token in self.llm.stream_complete(prompt, max_tokens=16000, temperature=0.3):
            full_response.append(token)
            yield {"type": "token", "token": token}

        response_text = "".join(full_response)
        quiz = self._parse_response(response_text, book_id, chapter_id, title)

        yield {"type": "done", "quiz": quiz}

    async def evaluate_all_streaming(
        self,
        questions: List[DescriptiveQuestion],
        answers: List[str],
        quiz_id: str,
        book_id: str = "",
        time_taken_minutes: Optional[int] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:

        prompt = self.prompts.evaluate_all_answers(
            questions=questions,
            answers=answers,
            book_id=book_id,
        )

        if not self.llm:
            yield {"type": "error", "message": "LLM not configured"}
            return

        full_response = []
        async for token in self.llm.stream_complete(prompt, max_tokens=12000, temperature=0.2):
            full_response.append(token)
            yield {"type": "token", "token": token}

        response_text = "".join(full_response)
        result = self._parse_batch_evaluation(
            response_text,
            questions,
            quiz_id,
            time_taken_minutes,
        )

        yield {"type": "done", "evaluation": result}

    def _parse_response(self, response: str, book_id: str, chapter_id: str, title: Optional[str]) -> DescriptiveQuiz:
        try:
            text = response.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            data = json.loads(text.strip())

            section_b = []
            section_c = []

            for qa in data.get("section_b", []):
                q = DescriptiveQuestion(
                    section="A",
                    type=qa.get("type", "short_answer"),
                    stem=qa.get("stem", ""),
                    marks=qa.get("marks", 3),
                    topic=qa.get("topic", ""),
                    expected_points=qa.get("expected_points", []),
                    rubric=qa.get("rubric", ""),
                    correct_answer=qa.get("correct_answer", ""),
                    formula_used=qa.get("formula_used", ""),
                    pattern_used=qa.get("pattern_used", ""),
                )
                section_b.append(q)

            for qc in data.get("section_c", []):
                q = DescriptiveQuestion(
                    section="C",
                    type=qc.get("type", "long_answer"),
                    stem=qc.get("stem", ""),
                    marks=qc.get("marks", 6),
                    topic=qc.get("topic", ""),
                    expected_points=qc.get("expected_points", []),
                    rubric=qc.get("rubric", ""),
                    pattern_used=qc.get("pattern_used", ""),
                )
                section_c.append(q)

            total = sum(q.marks for q in section_b + section_c)

            return DescriptiveQuiz(
                book_id=book_id,
                chapter_id=chapter_id,
                title=title or f"{chapter_id} - Chapter Test",
                section_b=section_b,
                section_c=section_c,
                total_marks=total,
                duration_minutes=max(15, total * 2),
            )

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Parse error: {e}")
            return DescriptiveQuiz(
                book_id=book_id,
                chapter_id=chapter_id,
                title=title or f"{chapter_id} - Error",
            )

    def _parse_batch_evaluation(
        self,
        response: str,
        questions: List[DescriptiveQuestion],
        quiz_id: str,
        time_taken_minutes: Optional[int],
    ) -> BatchEvaluationResult:
        try:
            text = response.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            data = json.loads(text.strip())

            evaluations = []
            for i, ev in enumerate(data.get("evaluations", [])):
                q = questions[i] if i < len(questions) else None
                evaluations.append(SingleEvaluation(
                    question_id=ev.get("question_id", q.id if q else ""),
                    marks_obtained=float(ev.get("marks_obtained", 0)),
                    max_marks=ev.get("max_marks", q.marks if q else 3),
                    feedback=ev.get("feedback", ""),
                    missing_points=ev.get("missing_points", []),
                    correct_points=ev.get("correct_points", []),
                    suggestions=ev.get("suggestions", ""),
                    confidence=float(ev.get("confidence", 0.5)),
                    formula_correct=ev.get("formula_correct", False),
                    unit_correct=ev.get("unit_correct", False),
                    calculation_correct=ev.get("calculation_correct", False),
                ))

            total_obtained = float(data.get("total_marks_obtained", 0))
            total_max = int(data.get("total_max_marks", 18))
            percentage = float(data.get("percentage", 0))

            return BatchEvaluationResult(
                quiz_id=quiz_id,
                total_marks_obtained=total_obtained,
                total_max_marks=total_max,
                percentage=percentage,
                passed=data.get("passed", percentage >= 40),
                evaluations=evaluations,
                overall_feedback=data.get("overall_feedback", ""),
                time_taken_minutes=time_taken_minutes,
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Evaluation parse error: {e}")
            return BatchEvaluationResult(
                quiz_id=quiz_id,
                overall_feedback="Error parsing evaluation results",
            )

    def _get_chapter_nodes(self, document_tree, chapter_id: str) -> List[Any]:
        nodes = document_tree.get_chapter_nodes(chapter_id)
        return [n for n in nodes if n.content.strip()]

    def _select_nodes(self, nodes: List[Any], max_nodes: int) -> List[Dict]:
        if not nodes:
            return []

        content_nodes = [n for n in nodes if n.content.strip()]
        if not content_nodes:
            return []

        step = max(1, len(content_nodes) // max_nodes) if len(content_nodes) > max_nodes else 1

        selected = []
        for i in range(0, len(content_nodes), step):
            node = content_nodes[i]
            selected.append({
                "node_id": node.id,
                "content": node.content,
                "node_title": node.title or "",
            })
            if len(selected) >= max_nodes:
                break

        return selected