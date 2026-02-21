"""
IDNA EdTech v8.0 — Instruction Builder

CRITICAL v8.0 RULES:
1. EVERY prompt MUST include: "Respond in {session.preferred_language}."
2. TEACHING prompts MUST include CB material for current teach_material_index
3. WAITING_ANSWER prompts MUST include the question text
4. HINT prompts MUST include the specific hint from CB
5. Language-specific instructions (English = no Hindi, Hindi = no English)

This module builds LLM prompts with guaranteed language injection.
"""

from typing import Optional, Dict, Any, List
from app.models.session import SessionState, TutorState

# Try to load content bank
try:
    from content_bank import get_content_bank
    _content_bank = get_content_bank()
except ImportError:
    _content_bank = None


DIDI_BASE = """You are Didi, a caring Hindi-speaking tutor for Class 8 Math.

PERSONALITY: Warm older sister. Patient. Focused on learning. Use "aap" form always.

FORMAT RULES (STRICT):
- Maximum 2 sentences, 40 words
- ONE idea per turn — never teach AND ask together
- Vary openings — don't always start with "Acha" or "Toh"

SPECIFICITY (CRITICAL):
- ALWAYS reference what the student said: "Aapne X bola..."
- NEVER give generic feedback like "try again" or "sochiye"
- Explain specifically what was right or wrong about their answer

NUMBERS:
- Use digits or English: "5 times 5 = 25", "3 squared = 9"
- NEVER use Hindi number words: teen, chaar, paanch, pachees

MATH ACCURACY:
- Double-check ALL arithmetic before responding
- NEVER state a number is or isn't a perfect square without verifying
"""


def get_language_instruction(preferred_language: str) -> str:
    """
    Get language instruction for LLM prompt.

    EVERY LLM call MUST include this. This is the v8.0 language persistence rule.
    """
    if preferred_language == "english":
        return """

IMPORTANT: Respond in English only. Use only English. No Hindi words at all.
Do not use: "Acha", "Theek hai", "Dekho", "Samajh aaya", "Sochiye"
"""
    elif preferred_language == "hindi":
        return """

IMPORTANT: Respond in Hindi (Devanagari). Use only Hindi. No English words.
Use digits for numbers: "5 × 5 = 25"
"""
    else:
        return """

IMPORTANT: Respond in natural Hinglish mix (Hindi and English mixed naturally).
Use digits for math. Keep it conversational.
"""


def get_cb_material(
    concept_id: str,
    teach_material_index: int,
) -> Dict[str, Any]:
    """
    Get Content Bank material based on teach_material_index.

    Index 0: definition_tts + hook
    Index 1: analogy + examples[0]
    Index 2: examples[1] or vedic_trick + key_insight
    """
    if not _content_bank or not concept_id:
        return {"text": "", "type": "fallback"}

    concept = _content_bank.get_concept(concept_id)
    if not concept:
        return {"text": "", "type": "fallback"}

    methodology = concept.get("teaching_methodology", {})
    examples = concept.get("examples", [])

    if teach_material_index == 0:
        definition = _content_bank.get_definition_tts(concept_id) or ""
        hook = methodology.get("hook", "")
        return {"text": f"{definition} {hook}".strip(), "type": "definition"}

    elif teach_material_index == 1:
        analogy = methodology.get("analogy", "")
        visualization = methodology.get("visualization", "")
        example_text = examples[0].get("solution_tts", "") if examples else ""
        return {"text": f"{analogy} {visualization} {example_text}".strip(), "type": "analogy"}

    elif teach_material_index >= 2:
        vedic_trick = methodology.get("vedic_trick", "")
        key_insight = concept.get("key_insight", "")
        example_text = examples[1].get("solution_tts", "") if len(examples) > 1 else ""
        return {"text": f"{example_text} {vedic_trick} {key_insight}".strip(), "type": "advanced"}

    return {"text": "", "type": "fallback"}


def build_prompt_v8(
    session: SessionState,
    action: str,
    student_text: str = "",
    question_data: Dict[str, Any] = None,
    conversation_history: List[Dict] = None,
) -> List[Dict[str, str]]:
    """
    Build LLM prompt with v8.0 rules.

    GUARANTEED: Every prompt includes language instruction.
    """
    # Start with base system prompt
    system_content = DIDI_BASE

    # ALWAYS add language instruction (v8.0 rule #1)
    system_content += get_language_instruction(session.preferred_language)

    # Add state context
    system_content += f"\n\nCurrent state: {session.current_state.value}"
    system_content += f"\nStudent has heard this concept {session.reteach_count} times."

    # Add student's words for specificity
    if student_text:
        system_content += f'\n\nSTUDENT SAID: "{student_text}"'

    # Build user message based on action
    user_content = _build_user_message(session, action, student_text, question_data)

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]

    # Add conversation history if provided
    if conversation_history:
        history_slice = conversation_history[-6:]
        messages = [messages[0]] + history_slice + [messages[1]]

    return messages


def _build_user_message(
    session: SessionState,
    action: str,
    student_text: str,
    question_data: Dict[str, Any],
) -> str:
    """Build the user message based on action type."""

    # TEACHING actions
    if action in ("teach_concept", "reteach", "start_teaching"):
        cb_material = get_cb_material(
            session.current_concept_id,
            session.teach_material_index,
        )

        if cb_material["text"]:
            return (
                f'Teach this concept naturally using this EXACT material:\n'
                f'"{cb_material["text"]}"\n'
                f'Do NOT generate your own definition. Use the material above.\n'
                f'End with "Samajh aaya?" Wait for response.'
            )
        else:
            return (
                'Teach one concept from this chapter. '
                'Use an Indian example (roti, cricket, laddoo). '
                '2 sentences. End with "Samajh aaya?"'
            )

    # QUESTION actions
    if action in ("ask_question", "read_question", "reread_question"):
        if question_data:
            q_text = question_data.get("question_tts", question_data.get("question_voice", ""))
            return (
                f'Read this question to the student:\n'
                f'"{q_text}"\n'
                f'End with "Batao, kya answer hai?"'
            )
        return 'Read the next question to the student.'

    # HINT actions
    if action in ("give_hint", "give_next_hint"):
        if question_data and _content_bank:
            q_id = question_data.get("question_id", "")
            hints = _content_bank.get_hints(q_id)
            hint_index = session.hints_given
            if hint_index < len(hints):
                hint_text = hints[hint_index]
                return (
                    f'Give this hint to the student:\n'
                    f'"{hint_text}"\n'
                    f'Ask them to try again. 2 sentences.'
                )
        return 'Give a helpful hint about the pattern or approach. 2 sentences.'

    # COMFORT actions
    if action in ("comfort", "comfort_then_teach", "comfort_and_stay"):
        return (
            f'Student said: "{student_text}". They are frustrated.\n'
            'Comfort them warmly. Say "Koi baat nahi" or similar.\n'
            '2 sentences. Do NOT teach yet.'
        )

    # END SESSION
    if action in ("end_session", "farewell"):
        score = session.score
        total = session.total_questions_asked
        return (
            f'Session ending. Score: {score}/{total}.\n'
            'Summarize warmly. Encourage return tomorrow. 3 sentences max.'
        )

    # FALLBACK
    return 'Continue the conversation naturally. 2 sentences.'


def build_greeting_prompt(session: SessionState) -> List[Dict[str, str]]:
    """Build greeting prompt for session start."""
    system_content = DIDI_BASE + get_language_instruction(session.preferred_language)

    user_content = (
        f'Welcome {session.student_name} to the session.\n'
        'Say "Namaste" and announce today\'s topic.\n'
        '2 sentences. Be warm and encouraging.'
    )

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


def build_evaluation_prompt(
    session: SessionState,
    student_answer: str,
    correct: bool,
    correct_answer: str,
    diagnostic: str = "",
) -> List[Dict[str, str]]:
    """Build prompt for answer evaluation feedback."""
    system_content = DIDI_BASE + get_language_instruction(session.preferred_language)

    if correct:
        user_content = (
            f'Student answered: "{student_answer}"\n'
            f'Correct answer: "{correct_answer}"\n'
            'CORRECT! Praise briefly referencing their answer. 1 sentence only.'
        )
    else:
        user_content = (
            f'Student answered: "{student_answer}"\n'
            f'Correct answer: "{correct_answer}"\n'
            f'Diagnostic: "{diagnostic}"\n'
            'INCORRECT. Say "Aapne X bola" and explain what went wrong.\n'
            'Do NOT reveal the answer. 2 sentences.'
        )

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
