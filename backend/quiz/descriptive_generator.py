"""Descriptive Quiz Generator - Adaptive Pattern-Based
Supports: phy_9, cs_9, maths_9, phy_10, cs_10, maths_10
Easy to add new subjects/grades by adding pattern modules.
Quiz NOT stored. Client passes quiz back for evaluation.
Only evaluation results stored in Firestore.
"""

import json
import uuid
import random
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
[ComplexVerify] Verify [PROPERTY] for z₁=[A+Bi] and z₂=[C+Di]
Ex: Verify z₁/z₂ = z̄₁/z̄₂ for z₁=2+3i, z₂=4+2i

[LogCompute] Find value of [EXPRESSION] using logarithm
Ex: 99.87/(18.369×10.785)

[SurdEvaluate] If x=[A±B√C], find x² + 1/x²
Ex: x=3-2√2, find x² + 1/x²

[FactorTheorem] Find factors of [POLYNOMIAL] using factor theorem
Ex: x³+5x²-4x-20

[PerfectSquare] Find p,q for [QUARTIC] to be perfect square
Ex: x⁴+8x³+30x²+px+q

[AbsoluteSolve] Find solution set: |[LINEAR]/[CONST]| ± [N] = [M]
Ex: |(2x+3)/4| + 2 = 7

[QuadraticFormula] Solve by formula: [QUADRATIC] = 0
Ex: 2x²-5x-3=0

[RadicalSolve] Find solution set: √([LINEAR])/[N] = [M]
Ex: √(3y+12)/7 = 3

[ZeroFind] For what k, [N] is zero of P(x)=[CUBIC]
Ex: -2 is zero of P(x)=x³+x²-14x-k

[IdentityEvaluate] Find [EXPRESSION] when [CONDITIONS]
Ex: 125x³+y³ when 5x+y=13, xy=10

[TriangleInequality] Prove: Sum of any two sides > third side

[Concurrency] Prove: [LINE_TYPE] of triangle sides are concurrent
Ex: Right bisectors concurrent

[EqualArea] Prove: Triangles on equal bases and equal altitudes are equal area

[Construct] Construct Δ[ABC] with sides [A],[B],[C], draw [LINE_TYPE]
Ex: ΔPQR: PQ=5.7cm, QR=6.4cm, PR=4cm, draw altitudes from Q,R
"""

_MATHS_9_LONG_PATTERNS = """
[FactorizeSet] Factorize any [N] of: [6_POLYNOMIALS]
Ex: (i) 169x⁴-(3t+4)² (ii) 7x+xz+7z+z² (iii) 8x³+12x²y+6xy²+y³
    (iv) 4x⁴+1 (v) 42x²-8x-2 (vi) a⁶-b⁶

[GraphicalSolve] Solve simultaneous equations graphically (find [N] ordered pairs each)
Ex: 2x=y+5; x=2y+1 (find 4 ordered pairs)

[ASA_Congruence] Prove: If one side and any two angles ≅ corresponding parts, triangles ≅

[Parallelogram_Props] Prove: In parallelogram, opposite sides ≅, opposite angles ≅, diagonals bisect

[Parallelogram_Test] Prove: If opposite sides of quadrilateral are ≅ and parallel, it's parallelogram

[CircleCoords] Find center and radius given diameter endpoints A([x₁],[y₁]), B([x₂],[y₂])
Ex: A(-3,4), B(11,6)

[Collinear_Prove] Prove points P([x₁],[y₁]), Q([x₂],[y₂]), R([x₃],[y₃]) are collinear
Ex: P(-3,-4), Q(2,6), R(0,2)

[Apollonius] Prove: Sum of squares on two sides = 2×(half third side)² + 2×(median)²

[AcuteAngle_Thm] Prove: Square on side opposite acute angle = sum of squares on containing sides minus 2×rectangle×projection

[Isosceles_Thm] Prove: If two angles of triangle are ≅, opposite sides are ≅

[UnequalAngles_Thm] Prove: If two angles unequal, side opposite greater angle is longer

[AngleBisector_Thm] Prove: Any point on angle bisector is equidistant from its arms
"""

_CS_10_SHORT_PATTERNS = """
[WhatIs] What is [CONCEPT]?
Ex: What is an algorithm? / What is a computer program? / What is ITERATION/LOOP?

[DefOnly] Define [CONCEPT].
Ex: Define Reserved words. / Define comment statement. / Define Queue and Stack.

[WhatIs+Importance] What is the importance of [CONCEPT] for [PURPOSE]?
Ex: What is the importance of Flowchart for solving a problem?

[WhatAre] What are [CONCEPT] in [LANGUAGE/CONTEXT]?
Ex: What are Strings in C++?

[WhatIs+WhyUse] What is [CONCEPT]? Why do we use it in our program?
Ex: What is Statement Terminator? Why do we use it in our program?

[Def+Types] Define [CONCEPT] and its types.
Ex: Define comment statement and its types.

[Why] Why do we [ACTION]?
Ex: Why do we make block of statements using braces?

[PurposeOf] What is the purpose of "[KEYWORD]" statement in [LANGUAGE]?
Ex: What is the purpose of "default" statement in C++?

[Diff] Differentiate between [A] and [B].
Ex: Differentiate between Constant and Variable. / Differentiate between constant and variables.

[Diff] What is the difference between [A] and [B]?
Ex: What is the difference between using scratch online and offline?
Ex: What is the difference between Source code and Object code?
Ex: What is the difference between Low-Level language and High-Level language?

[WhatKnow] What do you know about [CONCEPT]?
Ex: What do you know about Script area in a Scratch Editor?

[ListAdvantages] List any [N] advantages of [CONCEPT].
Ex: List of any three advantages of designing flowchart.

[DefRules] Define the rules for [CONCEPT].
Ex: Define the rules for naming variable.

[WritePurpose] Write the purpose of following [CONCEPT_LIST].
Ex: Write the purpose of following escape sequence: (i) \\n (ii) \\t (iii) \\b

[DefFollowing] Define the following: (i) [A] (ii) [B] [OR] (i) [C] (ii) [D]
Ex: Define the following: (i) Syntax error (ii) Logical error OR (i) Compiler (ii) Interpreter

[DefWithExamples] Define [CONCEPT] with examples.
Ex: Define Arithmetic assignment operators with examples.

[DrawFlowchart] Draw a flow chart of [PROCESS].
Ex: Draw a flow chart of finding average of three numbers.

[ExplainType] Explain the following [N] types of [CONCEPT].
Ex: Explain the following two types of low-level language. a) Machine language b) Assembly language.

[DescribeWithExamples] Describe [CONCEPT] with examples.
Ex: Describe OOP language with examples.

[WriteProgramSimple] Write a program to [TASK].
Ex: Write a program to calculate sum and product of 10 and 20.

[SolveOperator] Solving [OPERATOR_TYPE] operator when [VARIABLES], Find value of [EXPRESSION].
Ex: Solving Arithmetic operator when A=24 and B=5, Find value of A%B.

[ExplainStatement] Explain [STATEMENT_TYPE] statement.
Ex: Explain Switch statement.

[WhatIs+HowWorks] What is [CONCEPT]? How it works?
Ex: What is for Loop? How it works?

[WriteNProperties] Write [N] properties of [CONCEPT].
Ex: Write four properties of truth table.

[WhatIs+DiffN] What is [CONCEPT], write [N] difference between [A], [B] and [C].
Ex: What is internet, write one difference between webpage, web browser and web server.
"""

_CS_10_LONG_PATTERNS = """
[ExplainStructure] Explain basic structure of [LANGUAGE].
Ex: Explain basic structure of C++?

[Def+Types+Detail] Define types of [CONCEPT] with its [PROPERTIES] and [DETAIL].
Ex: Define types of Basic Logic Gate with its symbol and Truth Table.

[WhyNeed+DescribeTypes] Why do we need [CONCEPT]? Describe its types.
Ex: Why do we need a language translator? Describe its types.

[Def+Examples] Define [CONCEPT] with examples.
Ex: Define increment and decrement operators with examples.

[DescribeTypes] Describe the types of [CONCEPT].
Ex: Describe the types of Linear Data Structure.

[WritePurposeSyntax] Write down the purpose and syntax of the following:
Ex: Write down the purpose and syntax of the following: (i) FOR (ii) WHILE (iii) DO-WHILE

[ExplainSteps] Explain the steps involved in [PROCESS].
Ex: Explain the steps involved in problem solving.

[DescribeCodes] Give description of the following codes and symbols:
Ex: Give description of the following codes and symbols: i) #include<iostream> ii) using namespace std; iii) Int main()

[DefFollowingDetail] Define the following [CONCEPT_LIST]:
Ex: Define the following logic gates: (i) AND gate (ii) OR gate (iii) NOT gate

[DiffDetail] Differentiate between [A] and [B].
Ex: Differentiate between Algorithm and Flowchart.

[DescribeConcepts] Describe [CONCEPT_A] and [CONCEPT_B].
Ex: Describe Tree and Graph.

[DrawTruthTable] Draw truth table of the following:
Ex: Draw truth table of the following: (i) Y = A. B (ii) Y = A. B. C (iii) Y = AB

[WhatIs+ModulesDetail] What is [CONCEPT]? Write detail of [N] modules of [SYSTEM].
Ex: What is integrated development Environment(IDE) in programming? Write detail of five modules of C programming Environment.

[WriteProgram] Write a Program in [LANGUAGE] to [TASK].
Ex: Write a Program in C to convert Fahrenheit to centigrade temperature.
Ex: Write a program in C to find the factorial of a number."""


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
- Math specific: "Verify that", "Using logarithm", "By using factor theorem", "Find the solution set", "Prove it" — proofs end with "Prove it" not "Prove"; surds written as "sqrt(2)" or "2√3" in plaintext; complex numbers as "z₁ = a + bi"
- Physics specific: "Derive", "State and prove", "Find the", "Calculate the"; formulas with units; standard values in parenthetical
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
    "cs_10": {
        "short": _CS_10_SHORT_PATTERNS,
        "numerical": "", 
        "long": _CS_10_LONG_PATTERNS,
    },
    "maths_9": {
        "short": _MATHS_9_SHORT_PATTERNS,
        "numerical": "",
        "long": _MATHS_9_LONG_PATTERNS,
    },
}


def get_patterns(book_id: str) -> Dict[str, str]:
    """Get patterns for a book_id. Falls back to generic if not found."""
    if book_id in PATTERN_REGISTRY:
        return PATTERN_REGISTRY[book_id]

    for key in PATTERN_REGISTRY:
        if book_id.startswith(key.split("_")[0] + "_"):
            return PATTERN_REGISTRY[key]

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
    duration_minutes: int = 18
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
                "section_b": "SECTION 'B' (Short Answer Questions) Marks: 12\nAnswer ALL FOUR (4) questions. Each carries 3 Marks.",
                "section_c": "SECTION 'C' (Detailed-Answer Question) Marks: 6\nAnswer ALL ONE (1) question. Each carries 6 Marks.",
                "general": "Total Marks: 18. Passing: 40%. Time: 18 minutes. Attempt ALL questions. No choice.",
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
            duration_minutes=data.get("duration_minutes", 18),
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

        if book_id.startswith("maths"):
            section_b_mix = "computation, proof, construction, verification"
            section_c_mix = "factorize set, graphical solve, theorem proof, coordinate geometry"
            type_instruction = "Every question requires working, derivation, or proof. NO theory-only."
            eval_note = "For computation: Working (1) + Method (1) + Answer (1). For proofs: Statement (1) + Steps (2)."
        elif book_id.startswith("phy"):
            section_b_mix = "2 theory + 2 numerical"
            section_c_mix = "derivation, law proof, process explanation"
            type_instruction = "Mix theory definitions/factors/applications with numerical calculations."
            eval_note = "For theory: Definition (1) + Explanation/Example (1) + Application/Factor (1). For numericals: Formula (1) + Substitution (1) + Answer+Unit (1)."
        else:
            section_b_mix = "definition, classification, types, functions, differences, short notes"
            section_c_mix = "detailed explanation with components, types, steps, or process"
            type_instruction = "Theory-only. Definitions, classifications, differences, explanations."
            eval_note = "For definitions: Precise definition (1) + Characteristics (1) + Example (1). For differences: Each valid point (1) × 3."

        return f"""You are a senior Sindh Board examiner creating ORIGINAL descriptive questions for {book_id.upper()}.

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

=== QUIZ STRUCTURE ===
- Section B: EXACTLY 4 short questions (3 marks each) = 12 marks
- Section C: EXACTLY 1 long question (6 marks) = 6 marks
- Total: 18 marks, 18 minutes
- {type_instruction}

=== GENERATION RULES ===
1. DO NOT copy example questions. Use their SENTENCE STRUCTURE only.
2. Every question must trace to SOURCE CONTENT.
3. Section B mix: {section_b_mix}
4. Section C mix: {section_c_mix}
5. Include correct_answer and formula_used for all computational/numerical questions.
6. Each question needs: stem, marks, expected_points, rubric, correct_answer, formula_used, pattern_used
7. Use Sindh Board language and tone from STYLE DNA.
8. Use different patterns for each question.

EVALUATION GUIDANCE:
{eval_note}

Return ONLY JSON:

{{
  "section_b": [
    {{
      "type": "short_answer",
      "stem": "question text",
      "marks": 3,
      "topic": "topic from content",
      "expected_points": ["point 1", "point 2", "point 3"],
      "rubric": "mark distribution",
      "correct_answer": "answer or solution",
      "formula_used": "formula name or expression",
      "pattern_used": "which pattern template"
    }}
  ],
  "section_c": [
    {{
      "type": "long_answer",
      "stem": "question text",
      "marks": 6,
      "topic": "topic from content",
      "expected_points": ["part 1", "part 2", "part 3", "part 4"],
      "rubric": "mark distribution",
      "correct_answer": "full solution",
      "formula_used": "key formulas",
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
            if q.type == "numerical" or (q.formula_used and q.correct_answer):
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

        qa_block = "".join(qa_pairs)

        if book_id.startswith("maths"):
            eval_rules = """1. For computation: Working shown (1) + Correct method (1) + Final answer (1). No working = 0 marks.
2. For proofs: Statement (1) + Construction (1) + Proof steps (2).
3. For factorization: Each correct factor (1.5) × 4 = 6 marks.
4. For graphical: Table of values (2) + Plotting (2) + Solution point (2).
5. If answer correct but no working: deduct 2 marks (award 1 only)."""
        elif book_id.startswith("phy"):
            eval_rules = """1. For theory: Definition (1) + Explanation/Example (1) + Application/Factor (1).
2. For numericals: Formula (1) + Substitution (1) + Answer+Unit (1). No formula = 0 marks.
3. For long: Law statement (2) + Derivation (2) + Application/Example (2).
4. If answer correct but no working shown: deduct 2 marks (award 1 only)."""
        else:
            eval_rules = """1. For definitions: Precise definition (1) + Key characteristics (1) + Example (1).
2. For differences: Each valid difference (1) × 3 = 3 marks.
3. For long: Definition/Concept (2) + Components/Types/Steps (2) + Examples/Applications (2).
4. HTML tags must be in angle brackets < >."""

        return f"""You are a strict Sindh Board examiner marking a {book_id.upper()} chapter quiz.

SUBJECT: {book_id}

{qa_block}

EVALUATION RULES:
{eval_rules}
6. Evaluate ALL answers together for consistency.
7. Be STRICT — no sympathy marks for vague answers.
8. Give specific feedback per question: what was correct, what was missing, how to improve.
9. Calculate total marks, percentage, and pass/fail (40% passing) and return question wise obtain marking.

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
      "calculation_correct": true,
      "weak_area": "concept area student struggles with"
    }}
  ],
  "overall_feedback": "summary of performance — focus on weak areas, never say memorize"
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
        content_nodes = [n for n in nodes if n.content.strip()]

        if not content_nodes:
            yield {"type": "error", "message": "No content available for this chapter"}
            return

        # Extract chapter topics from ALL nodes
        chapter_topics = list(set(
            n.title.split(".")[0].strip()
            for n in content_nodes
            if n.title
        ))[:5]

        content_text = ""
        for i, node in enumerate(content_nodes, 1):
            content_text += f"--- PASSAGE {i}: {node.title or 'Untitled'} ---"
            content_text += f"{node.content}"

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
                    section="B",
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
                    correct_answer=qc.get("correct_answer", ""),
                    formula_used=qc.get("formula_used", ""),
                    pattern_used=qc.get("pattern_used", ""),
                )
                section_c.append(q)

            return DescriptiveQuiz(
                book_id=book_id,
                chapter_id=chapter_id,
                title=title or f"{chapter_id} - Chapter Quiz",
                section_b=section_b,
                section_c=section_c,
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
