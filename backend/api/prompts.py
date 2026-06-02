"""
Custom Prompts for LLM Interactions
================================================
JSON schema at end for recency bias.
Pattern summaries.
Supports: phy_9, cs_9, maths_9, cs_10 and generic fallback.
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

_MATHS_9_PATTERNS = """
[PATTERN: Inverse operation trap]
Q: "If log_4(x) = 3/2 then x = ___"
A: 8 — tests converting log→exponential form (x = 4^(3/2)), not calculator use; distractors are integers near the log value

[PATTERN: Factor-before-HCF]
Q: "H.C.F. of x² - y² and (x-y)² is ___"
A: (x-y) — requires factoring first (difference of squares), then finding common factor; tests that HCF needs decomposition, not visual matching

[PATTERN: Absolute value dual case]
Q: "Solution set of |(5y)/3| = 5 is ___"
A: {3, -3} — forces splitting into ±cases; single-value answers trap students who ignore the negative branch

[PATTERN: Characteristic vs mantissa]
Q: "Characteristic of log(0.01706) is ___"
A: -2 — tests that characteristic is the exponent in scientific notation (1.706×10⁻²), not the leading digits; common confusion with -4 (digit count)

[PATTERN: Minimal sufficient condition]
Q: "Opposite angles equal, none is right angle → quadrilateral is ___"
A: Parallelogram — rectangle/square are distractors requiring right angles; tests knowing the *minimal* defining property

[PATTERN: Sign-to-quadrant mapping]
Q: "Point (-2, -5) is in ___ quadrant"
A: Third — tests (negative, negative) → Q3 rule; requires coordinate sign analysis, not memorization of random points

[PATTERN: Conjugate sign flip]
Q: "Conjugate of 2 - √3 is ___"
A: 2 + √3 — tests flipping only the surd term's sign; 3-√2 and similar are distractors that rearrange numbers

[PATTERN: Multivariate degree]
Q: "Degree of 4a⁴b² + 6b⁴ - 12 is ___"
A: 6 — requires adding exponents per term (4+2); tests that degree in multivariate polynomials is maximum *sum*, not single exponent

[PATTERN: Perfect square completion]
Q: "If x² - 4x + k is complete square, k = ___"
A: 4 — requires pattern (half of -4, squared); tests structural recognition over formula plugging

[PATTERN: Property naming vs using]
Q: "6(7+8) = 6×7 + 6×8 is ___ property"
A: Distributive — commutative/associative are distractors involving same operations but different structures; tests precise identification

[PATTERN: Terminology absoluteness]
Q: "In right triangle, side opposite right angle is ___"
A: Hypotenuse — base/perpendicular change with reference angle; tests that hypotenuse is *absolute* while others are relative

[PATTERN: Inequality decomposition]
Q: "x ≤ 4 means ___"
A: x < 4 or x = 4 — tests logical meaning of compound symbol; "x < 4" is incomplete, "x = 4" is too narrow

[PATTERN: Expression inverse]
Q: "Multiplicative inverse of x + y is ___"
A: 1/(x+y) — tests inverse of *entire* expression; 1/(x-y) and -x-y are distractors for term-wise or additive confusion

[PATTERN: Scientific notation standard form]
Q: "Scientific notation of 0.0045467 is ___"
A: 4.5467 × 10⁻³ — tests coefficient must be [1,10); 0.45467×10⁻³ violates standard form, 4.5467×10³ is wrong direction

[PATTERN: Logarithm law discrimination]
Q: "log_a(mn) = ___"
A: log_a(m) + log_a(n) — product→sum; distractors are difference rule (quotient) and multiplication of logs (common error)

[PATTERN: Quadratic factorization]
Q: "Solution set of x² + 10x + 24 = 0 is ___"
A: {-6, -4} — requires middle-term splitting; {-6, 4} and {6, -4} are sign-error distractors

[PATTERN: Equation family by structure]
Q: "3^x + 3^(2x) = 1 is ___ equation"
A: Exponential (reducible to quadratic in 3^x) — tests classification by variable position, not polynomial degree

[PATTERN: HCF via factor hierarchy]
Q: "HCF of a³ - b³ and a⁶ - b⁶ is ___"
A: a³ - b³ — requires recognizing a⁶-b⁶ = (a³)²-(b³)² = (a³+b³)(a³-b³); tests factorization depth

[PATTERN: Parallelogram angle chain]
Q: "If ∠A + ∠C = 130° in parallelogram ABCD, then m∠B = ___"
A: 115° — requires 3-step chain: opposite angles equal → ∠A=65° → consecutive angles supplementary; tests property chaining

[PATTERN: Polygon angle formula]
Q: "Sum of angles in quadrilateral is ___"
A: 360° — tests (n-2)×180°; 180° (triangle) is common distractor from overgeneralization
"""

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

_CS_10_PATTERNS = """[PATTERN: Continue vs Break target]
Q: "Continue statement controls to: ___"
A: The top of loop — continue restarts iteration; break exits. Distractors swap targets or add function scope.

[PATTERN: Universal gate = NOR/NAND]
Q: "The universal gate is: ___"
A: NOR — any logic implementable. NOT/OR incomplete; "None" overthink trap.

[PATTERN: Truth table row count = 2^n]
Q: "With combination of three variables, outputs expected: ___"
A: Eight — 2^n rule. Distractors: nearby evens (4,6,10) for pattern-guessers.

[PATTERN: Stack push = insert, pop = delete]
Q: "When data is pushed in stack, data is: ___"
A: inserted — LIFO vocab. deleted/pop = opposite; sorted/edited = unrelated traps.

[PATTERN: Operator family classification]
Q: "!= belongs to: ___" / "&& is: ___" / ">> is: ___"
A: Relational / Logical / Input stream — test symbol→family mapping. Distractors swap families (arithmetic, bitwise & vs &&).

[PATTERN: Assignment (=) vs Equality (==)]
Q: "To compare two values, correct operator is: ___"
A: == — = assigns; <= is relational but not equality; * is arithmetic trap.

[PATTERN: Nested loop = loop-in-loop]
Q: "Loop within loop is called: ___"
A: Nested loop — inner/outer describe position, not the structure name.

[PATTERN: Break canonical use = switch]
Q: "break statement is used with: ___"
A: switch — canonical case-termination. if/for/while can use it but switch is primary.

[PATTERN: Binary = max 2 children]
Q: "In binary tree, each child can have maximum: ___"
A: two nodes — "bi" = two. One/three/four = number-pattern guessing.

[PATTERN: HLL readable by humans, LLL by machines]
Q: "Syntax of High Level Language is easily readable for: ___"
A: humans — "both" ignores compilation; machines read bytecode/binary.

[PATTERN: Algorithm = textual, Flowchart = graphical]
Q: "Logic of program is graphically called: ___" / "Step by step solution in simple language is: ___"
A: Flowchart / Algorithm — test medium→representation mapping. Swapping = common error.

[PATTERN: Error taxonomy by detector]
Q: "All errors detected by user are called: ___"
A: Logical error — syntax/runtime/semantic = compiler/interpreter detected.

[PATTERN: Bool domain = {True, False} only]
Q: "A Bool data can store: ___"
A: True or False — number/string/fractional = type-confusion distractors.

[PATTERN: Flowchart symbol shapes]
Q: "Symbol for input/output in flowchart: ___"
A: Parallelogram — triangle/square/rectangle = other symbol purposes.

[PATTERN: Variable scope by declaration location]
Q: "Variables declared in function definition are: ___"
A: Local variables — instance (OOP), global (file), static (storage class) = scope-family distractors."""


# =============================================================================
# PROMPT BUILDER
# =============================================================================

# Dynamic ratio configuration per subject
# Format: (mcq_pct, true_false_pct, fill_in_blank_pct, mcq_calculation_pct, step_builder_pct)
_QUIZ_RATIOS = {
    "cs_9":    (60, 15, 20, 5, 0),    
    "cs_10":   (60, 15, 20, 5, 0),   
    "maths_9": (30, 10, 10, 25, 25),  
    "maths_10":(30, 10, 10, 25, 25),   
    "phy_9":   (40, 15, 15, 30, 0),   
    "phy_10":  (40, 15, 15, 30, 0),   
}

def _get_quiz_ratio(book_id: str) -> tuple:
    """Return (mcq%, true_false%, fill_blank%, calc%, step_builder%) for a given book_id."""
    for key in _QUIZ_RATIOS:
        if key in book_id:
            return _QUIZ_RATIOS[key]
    return (40, 20, 15, 15, 10)


def _get_patterns_for_book(book_id: str) -> str:
    """Return the appropriate pattern set for a book_id."""
    if "phy_9" in book_id:
        return _PHY_9_PATTERNS
    elif "cs_9" in book_id:
        return _CS_9_PATTERNS
    elif "maths_9" in book_id:
        return _MATHS_9_PATTERNS
    elif "cs_10" in book_id:
        return _CS_10_PATTERNS
    else:
        return "Generate questions that test understanding, not memorization. Use plausible distractors."

# =============================================================================
# PROMPTS CLASS
# =============================================================================
class Prompts:
    """Optimized prompt templates for LLM interactions."""

    @staticmethod
    def ask_stream(query: str, context: str, book_title: str) -> str:
        """Streaming Q&A prompt."""
        return f"""
RELEVANT CONTENT:
{context}

STUDENT QUESTION:
{query}

Answer:
"""

    @staticmethod
    def teacher_system(book_title: str = "") -> str:
      return f"""You are an expert educational tutor for the Sindh Board curriculum.
{('Book: ' + book_title) if book_title else ''}
Instructions:
- You are sabakTutor chat buddy trained for helping students of Sindh board 9/10th in studies
- Answer ONLY from the provided content if cant do from provided content state this topic is not in book and tell what user should ask according to provided book but never mention what content provided say for exam lets learn about this instead.
- if query is for solving numericals, examples and content is not provided according to it then solve it provide step by step reasoning + used formula
- Use simple and clear language suitable for Sindh Board students.
- If formulas, tables, OCR text, or parsed content look incomplete or broken, intelligently reconstruct them from the surrounding provided content only.
- Do NOT mention missing context, parsing issues, excerpts, or limitations unless absolutely necessary.
- Include definitions, examples, formulas, or explanations if present in the content.
- Mention page numbers if available in the content.
- Never explain your reasoning process.
- if content is from physics provide formula or definition if required if its maths provide formulas and if its of computer science provide code blocks if necessary
"""

    @staticmethod
    def generate_mixed_quiz(content_text: str, total_items: int, book_id: str) -> str:
        """
        Generate a mixed interactive quiz with subject-specific ratios.
        Ratios adapt per book: CS=theory-heavy, Maths=calc-heavy, Physics=balanced.
        """
        patterns = _get_patterns_for_book(book_id)
        mcq_pct, tf_pct, fb_pct, calc_pct, step_builder_pct = _get_quiz_ratio(book_id)

        return f"""You are a Sindh Board examiner creating a mixed-format quiz for Grade 9/10.

SOURCE CONTENT (derive ALL questions strictly from this):
Book: {book_id}

{content_text}

BOARD EXAM PATTERNS (learn the style, never copy these exact questions):
{patterns}

RULES:
1. Generate exactly {total_items} items total.
2. Mix these types in this ratio (STRICT — follow percentages):
   - {mcq_pct}% Standard MCQ (board pattern): definition traps, formula application, concept comparison, real-life mapping
   - {tf_pct}% True/False: test common misconceptions
   - {fb_pct}% Fill-in-Blank: key terms, formulas, definitions
   - {calc_pct}% MCQ Calculation: step-by-step numerical problems
   - {step_builder_pct}% Step Builder: interactive step-by-step math problem solving
3. Every question must trace directly to SOURCE CONTENT. No external knowledge.
4. For MCQs: use plausible distractors from the same concept family. Test understanding, not memorization.
5. For True/False: statements should be tricky — common student misconceptions.
6. For Fill-in-Blank: one precise answer. No ambiguity.
7. For MCQ Calculation: show step-by-step solution in explanation.
8. Vary difficulty: 40% easy, 40% medium, 20% hard.
9. Board pattern MCQs must follow the cognitive traps shown in patterns above.

Return ONLY a JSON array with polymorphic objects:

For Standard MCQ (board pattern):
{{
  "type": "mcq",
  "stem": "question text",
  "options": ["A", "B", "C", "D"],
  "correct_index": 0,
  "topic": "topic from content",
  "difficulty": "easy|medium|hard",
  "marks": 1,
  "pattern_used": "name of pattern from patterns above"
}}

For True/False:
{{
  "type": "true_false",
  "statement": "The statement to evaluate",
  "is_true": true,
  "explanation": "Why it is true or false",
  "difficulty": "easy|medium|hard",
  "marks": 1
}}

For Fill in the Blank:
{{
  "type": "fill_in_blank",
  "sentence_before": "The beginning of the sentence ",
  "blank_answer": "the missing word",
  "sentence_after": " the rest of the sentence.",
  "difficulty": "easy|medium|hard",
  "marks": 1
}}

For MCQ Calculation:
{{
  "type": "mcq_calculation",
  "problem": "The calculation question",
  "options": ["A", "B", "C", "D"],
  "correct_index": 0,
  "explanation": "Step by step solution",
  "difficulty": "easy|medium|hard",
  "marks": 2
}}

For Step Builder:
{{
  "type": "step_builder",
  "problem": "Solve for x: 3x - 5 = 10",
  "steps": [
    {{
      "correct": "3x = 15",
      "distractors": ["3x = 5", "x - 5 = 3"]
    }}
  ],
  "difficulty": "easy|medium|hard",
  "marks": 2
}}

Generate the JSON array now."""

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
