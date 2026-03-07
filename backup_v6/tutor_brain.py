"""
IDNA Tutor Brain v1.0 — The Teacher's Mind
=============================================
This is what separates a chatbot from a teacher.

The state machine (tutor_states.py) handles FLOW:
  "Student said yeah → move to next question"

The brain handles PEDAGOGY:
  "This student has failed 3 fraction questions. They don't understand
   what a fraction IS. I need to teach the concept before asking
   another question. And they learn better with concrete examples,
   not abstract rules."

HOW IT WORKS:
  1. Before each question: brain builds a TEACHING PLAN
  2. Before each response: brain builds a CONTEXT PACKET
  3. After each interaction: brain updates STUDENT MODEL
  4. At session end: brain generates SESSION SUMMARY

The brain DOES NOT generate speech. It generates INSTRUCTIONS
that didi_voice.py turns into speech.

The brain DOES NOT control flow. tutor_states.py still handles
state transitions. But the brain ENRICHES what happens at each state.

INTEGRATION:
  agentic_tutor.py calls brain methods at key points.
  Brain returns enriched instructions that replace the basic ones.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Optional


# ============================================================
# STUDENT MODEL — what the brain knows about this student
# ============================================================

@dataclass
class StudentModel:
    """
    Live model of the student, updated every interaction.
    This is SHORT-TERM memory (session only) for MVP.
    Phase 2 adds persistence via SQLite.
    """
    name: str
    # Skill tracking
    concepts_understood: list = field(default_factory=list)   # ["same_denom_addition"]
    concepts_struggling: list = field(default_factory=list)   # ["sign_rules", "fraction_basics"]
    error_patterns: list = field(default_factory=list)        # ["forgets_negative_sign", "adds_denominators"]

    # Learning style (detected during session)
    needs_concrete_examples: bool = False     # Asked for examples? Visual learner?
    needs_concept_teaching: bool = False      # Doesn't know basics? Needs pre-teaching?
    responds_to_encouragement: bool = True    # Does praise help or feel fake?
    preferred_hint_style: str = "break_down"  # "break_down", "analogy", "first_step"

    # Engagement
    confidence_level: str = "medium"          # "low", "medium", "high"
    frustration_signals: int = 0              # count of "I don't understand" type messages
    consecutive_correct: int = 0
    consecutive_wrong: int = 0

    # Session stats
    questions_seen: int = 0
    questions_correct: int = 0
    total_hints_needed: int = 0
    total_explanations_needed: int = 0
    topics_covered: list = field(default_factory=list)


# ============================================================
# TEACHING PLAN — what to do for the current question
# ============================================================

@dataclass
class TeachingPlan:
    """
    Brain's plan for the current question.
    Generated BEFORE the question is asked.
    """
    should_pre_teach: bool = False            # Teach the concept before asking?
    pre_teach_concept: str = ""               # What to teach first
    pre_teach_instruction: str = ""           # Instruction for voice generator

    question_framing: str = "direct"          # "direct", "scaffolded", "with_example"
    intro_instruction: str = ""               # How to introduce this question

    hint_strategy: str = "standard"           # "standard", "concrete_example", "analogy", "visual"
    custom_hint_1: str = ""                   # Override default hint if brain has better one
    custom_hint_2: str = ""

    max_attempts_before_explain: int = 3      # Can be lowered for struggling students

    expected_difficulty: str = "normal"       # "easy", "normal", "hard" for this student
    encouragement_level: str = "normal"       # "high" for low-confidence students


# ============================================================
# CONTEXT PACKET — what the LLM sees for each response
# ============================================================

def build_context_packet(student: StudentModel, plan: TeachingPlan) -> str:
    """
    Builds a compact string that gets injected into every LLM call.
    This is the brain's voice — it tells the LLM WHO this student is
    and HOW to teach them.
    """
    lines = []

    # Student profile (what the LLM needs to know)
    if student.concepts_struggling:
        lines.append(f"STUDENT STRUGGLES WITH: {', '.join(student.concepts_struggling[-3:])}")

    if student.error_patterns:
        lines.append(f"COMMON ERRORS: {', '.join(student.error_patterns[-3:])}")

    if student.needs_concept_teaching:
        lines.append("⚠️ THIS STUDENT NEEDS CONCEPT EXPLANATION BEFORE QUESTIONS. "
                      "They don't understand the basics yet. Teach first, then ask.")

    if student.needs_concrete_examples:
        lines.append("📌 USE CONCRETE EXAMPLES. This student learns from real-world "
                      "comparisons (apples, money, sharing), not abstract math language.")

    if student.confidence_level == "low":
        lines.append("🔻 LOW CONFIDENCE. Be extra gentle. Start with something easy. "
                      "Celebrate small wins. Don't say 'that's easy' or 'you should know this.'")

    if student.frustration_signals >= 3:
        lines.append("😤 STUDENT IS FRUSTRATED. They've asked for help multiple times. "
                      "Don't push micro-questions. Give a clear, simple explanation.")

    if student.consecutive_correct >= 3:
        lines.append("🔥 ON A STREAK! Student got 3+ right. Keep the energy up. "
                      "Can increase difficulty slightly.")

    # Teaching plan for this question
    if plan.should_pre_teach:
        lines.append(f"📚 PRE-TEACH FIRST: {plan.pre_teach_concept}")
        lines.append(f"   Instruction: {plan.pre_teach_instruction}")

    if plan.hint_strategy != "standard":
        lines.append(f"HINT STRATEGY: Use {plan.hint_strategy} approach")

    if plan.question_framing == "with_example":
        lines.append("FRAMING: Give a solved example first, then ask the question")
    elif plan.question_framing == "scaffolded":
        lines.append("FRAMING: Break into smaller steps before asking full question")

    return "\n".join(lines) if lines else ""


# ============================================================
# THE BRAIN — main class
# ============================================================

class TutorBrain:
    """
    The teacher's mind. Observes, reasons, plans.

    Usage:
        brain = TutorBrain("Hemant")

        # Before asking a question:
        plan = brain.plan_for_question(question, session)
        context = brain.get_context_packet()

        # After student responds:
        brain.observe_interaction(student_input, category, action, question)

        # At session end:
        summary = brain.get_session_summary()
    """

    def __init__(self, student_name: str):
        self.student = StudentModel(name=student_name)
        self.current_plan = TeachingPlan()
        self.session_start = time.time()
        self.interaction_log = []  # [{input, category, action, question_id, timestamp}]

    # ============================================================
    # PLAN — called before each question
    # ============================================================

    def plan_for_question(self, question: dict, session: dict) -> TeachingPlan:
        """
        Build a teaching plan for the upcoming question.
        Called BEFORE the question is read to the student.
        """
        plan = TeachingPlan()
        topic = question.get("subtopic", question.get("topic", ""))
        difficulty = question.get("difficulty", 1)

        # --- DECISION 1: Should we pre-teach? ---
        # If student has asked "what is X?" or shown they lack basics
        if self.student.needs_concept_teaching:
            if topic in self.student.concepts_struggling or self.student.frustration_signals >= 2:
                plan.should_pre_teach = True
                plan.pre_teach_concept = topic
                plan.pre_teach_instruction = (
                    f"Before asking the question, teach the concept of {topic} simply. "
                    f"Use a concrete everyday example. Then say 'Now let's try one together' "
                    f"and read the question."
                )

        # --- DECISION 2: How to frame the question ---
        if self.student.consecutive_wrong >= 2 or self.student.confidence_level == "low":
            if difficulty > 1:
                plan.question_framing = "scaffolded"
                plan.intro_instruction = (
                    "Break this into smaller steps. Don't read the full question at once. "
                    "Start with the easier part."
                )
            else:
                plan.question_framing = "with_example"
                plan.intro_instruction = (
                    "Give a quick solved example of the same type first, "
                    "then ask the student to try one."
                )

        # --- DECISION 3: Hint strategy ---
        if self.student.needs_concrete_examples:
            plan.hint_strategy = "concrete_example"
            plan.custom_hint_1 = (
                "Use a real-world example: sharing chocolates, "
                "owing money, temperature below zero."
            )
        elif "sign_rules" in self.student.error_patterns:
            plan.hint_strategy = "visual"
            plan.custom_hint_1 = (
                "Use a number line. Ask them to start at the first number "
                "and move right or left."
            )

        # --- DECISION 4: Patience level ---
        if self.student.confidence_level == "low" or self.student.frustration_signals >= 2:
            plan.max_attempts_before_explain = 2  # Explain sooner
            plan.encouragement_level = "high"
        elif self.student.consecutive_correct >= 3:
            plan.max_attempts_before_explain = 4  # Let them struggle more

        # --- DECISION 5: Expected difficulty ---
        if topic in self.student.concepts_understood:
            plan.expected_difficulty = "easy"
        elif topic in self.student.concepts_struggling:
            plan.expected_difficulty = "hard"

        self.current_plan = plan
        return plan

    # ============================================================
    # OBSERVE — called after every student interaction
    # ============================================================

    def observe_interaction(self, student_input: str, category: str,
                            action: str, question: dict):
        """
        Update the student model based on what just happened.
        This is how the brain LEARNS about the student during the session.
        """
        topic = question.get("subtopic", question.get("topic", ""))

        # Log it
        self.interaction_log.append({
            "input": student_input,
            "category": category,
            "action": action,
            "topic": topic,
            "timestamp": time.time()
        })

        # --- UPDATE: Concept understanding ---
        if action == "praise_and_continue":
            self.student.consecutive_correct += 1
            self.student.consecutive_wrong = 0
            if topic and topic not in self.student.concepts_understood:
                self.student.concepts_understood.append(topic)
            if topic in self.student.concepts_struggling:
                self.student.concepts_struggling.remove(topic)
            self.student.questions_correct += 1

            # Recovery detection
            if self.student.consecutive_correct >= 3:
                self.student.frustration_signals = max(0, self.student.frustration_signals - 2)
                self.student.needs_concept_teaching = False

        # --- UPDATE: Error patterns ---
        if action in ("give_hint", "explain_solution"):
            self.student.consecutive_wrong += 1
            self.student.consecutive_correct = 0
            if topic and topic not in self.student.concepts_struggling:
                self.student.concepts_struggling.append(topic)
            self.student.total_hints_needed += 1

            # Detect specific error patterns from input
            input_lower = student_input.lower()
            if _has_sign_error(input_lower, question):
                _add_pattern(self.student, "forgets_negative_sign")
            if _has_denominator_error(input_lower, question):
                _add_pattern(self.student, "adds_denominators_instead_of_numerators")

        if action == "explain_solution":
            self.student.total_explanations_needed += 1

        # --- UPDATE: Learning style detection ---
        if category == "IDK":
            self.student.frustration_signals += 1

            input_lower = student_input.lower()
            # "Can you give me examples?" → needs concrete examples
            if any(p in input_lower for p in ["example", "show me", "like what",
                                                "real life", "day to day",
                                                "daily life", "how can i use",
                                                "how to use in life",
                                                "where do we use"]):
                self.student.needs_concrete_examples = True

            # "What is fraction? Explain" → needs concept teaching
            if any(p in input_lower for p in ["what is", "what are", "explain the chapter",
                                                "teach me", "i don't understand",
                                                "i dont understand", "can you explain"]):
                self.student.needs_concept_teaching = True

        # --- UPDATE: Confidence level ---
        if self.student.consecutive_correct >= 3:
            self.student.confidence_level = "high"
        elif self.student.consecutive_wrong >= 3 or self.student.frustration_signals >= 3:
            self.student.confidence_level = "low"
        else:
            self.student.confidence_level = "medium"

        # --- UPDATE: Question stats ---
        if action in ("praise_and_continue", "explain_solution", "move_to_next"):
            self.student.questions_seen += 1
            if topic and topic not in self.student.topics_covered:
                self.student.topics_covered.append(topic)

    # ============================================================
    # CONTEXT — called before every LLM speech generation
    # ============================================================

    def get_context_packet(self) -> str:
        """
        Returns the brain's instructions for the LLM.
        This gets injected into every speech generation call.
        """
        return build_context_packet(self.student, self.current_plan)

    def get_pre_teach_instruction(self) -> Optional[str]:
        """
        If brain decided to pre-teach, return the instruction.
        Called by agentic_tutor before reading a new question.
        """
        if self.current_plan.should_pre_teach:
            return self.current_plan.pre_teach_instruction
        return None

    def get_enhanced_hint(self, hint_level: int) -> Optional[str]:
        """
        If brain has a better hint strategy, return custom hint instruction.
        """
        if hint_level == 1 and self.current_plan.custom_hint_1:
            return self.current_plan.custom_hint_1
        if hint_level == 2 and self.current_plan.custom_hint_2:
            return self.current_plan.custom_hint_2
        return None

    def should_explain_early(self) -> bool:
        """
        Should we explain sooner than the default threshold?
        """
        return self.current_plan.max_attempts_before_explain < 3

    def get_encouragement_instruction(self) -> str:
        """
        How to encourage this specific student.
        """
        if self.student.confidence_level == "low":
            return (
                "Be extra gentle. Start with what they DO know. "
                "Say something like 'No worries, let me help you with this.'"
            )
        elif self.student.needs_concrete_examples:
            return (
                "Give them a concrete example to anchor on. "
                "Use everyday objects — chocolates, rupees, cricket scores."
            )
        return "Encourage them to try. Break the problem into a smaller piece."

    # ============================================================
    # SESSION SUMMARY — called at session end
    # ============================================================

    def get_session_summary(self) -> dict:
        """
        Summary of what the brain learned about this student.
        Used for:
        1. Parent reports (Phase 4)
        2. Next session pre-loading (Phase 2 with persistence)
        3. Debugging/improvement
        """
        duration = int((time.time() - self.session_start) / 60)

        return {
            "student_name": self.student.name,
            "duration_minutes": duration,
            "questions_seen": self.student.questions_seen,
            "questions_correct": self.student.questions_correct,
            "accuracy": (self.student.questions_correct / max(self.student.questions_seen, 1)) * 100,
            "concepts_understood": self.student.concepts_understood,
            "concepts_struggling": self.student.concepts_struggling,
            "error_patterns": self.student.error_patterns,
            "learning_style": {
                "needs_concrete_examples": self.student.needs_concrete_examples,
                "needs_concept_teaching": self.student.needs_concept_teaching,
                "preferred_hint_style": self.student.preferred_hint_style,
                "confidence_at_end": self.student.confidence_level,
            },
            "hints_needed": self.student.total_hints_needed,
            "explanations_needed": self.student.total_explanations_needed,
            "topics_covered": self.student.topics_covered,
            "frustration_signals": self.student.frustration_signals,
        }


# ============================================================
# PATTERN DETECTION HELPERS
# ============================================================

def _add_pattern(student: StudentModel, pattern: str):
    """Add error pattern if not already tracked."""
    if pattern not in student.error_patterns:
        student.error_patterns.append(pattern)


def _has_sign_error(input_lower: str, question: dict) -> bool:
    """Detect if student forgot the negative sign."""
    answer = str(question.get("answer", ""))
    if "-" in answer or "negative" in answer.lower() or "minus" in answer.lower():
        # Answer should be negative but student gave positive
        if not any(neg in input_lower for neg in ["-", "minus", "negative"]):
            # Student said a number without negative sign
            if any(c.isdigit() for c in input_lower):
                return True
    return False


def _has_denominator_error(input_lower: str, question: dict) -> bool:
    """Detect if student added denominators (common fraction mistake)."""
    # If question involves same-denominator fractions
    text = question.get("text", question.get("question_text", "")).lower()
    if "/" in text:
        # Very basic: if student answer has a different denominator
        # This is a heuristic, not perfect
        common_mistakes = question.get("common_mistakes", [])
        for m in common_mistakes:
            if "denominator" in m.get("diagnosis", "").lower():
                if m.get("wrong_answer", "").lower() in input_lower:
                    return True
    return False
