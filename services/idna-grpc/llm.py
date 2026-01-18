# services/idna-grpc/llm.py
"""
LLM wrapper for generating tutor text using OpenAI GPT-4o-mini.
Provides fallback responses if API is unavailable or key is missing.
"""
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import OpenAI client
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not installed, using fallback mode")


# System prompt for the tutor
SYSTEM_PROMPT = """You are a friendly Indian K-10 math tutor helping young students learn addition.

IMPORTANT RULES:
1. Use simple English that a child can understand
2. Be encouraging and patient
3. Keep responses SHORT (1-2 sentences maximum)
4. NEVER compute or reveal the answer - that's the student's job
5. Questions are about addition with numbers up to 20
6. Use Indian context when helpful (like mangoes, chapatis, rupees)
7. If giving a hint, guide the thinking process without solving

You generate ONLY the tutor's spoken response. No explanations, no markdown, just the text to speak."""


# Fallback responses for each scenario
FALLBACK_RESPONSES = {
    "explain": "Let's learn addition! When we add numbers, we put them together. Ready to try a question?",
    "quiz": "Here's your question: What is {a} + {b}?",
    "correct": "Excellent! That's correct! Let's try another one.",
    "hint1": "Not quite. Try counting on your fingers - start with {a} and count {b} more.",
    "hint2": "Here's another way: imagine you have {a} mangoes and get {b} more. How many total?",
    "reveal": "The answer is {expected}. Let's practice with the next question!",
    "empty_input": "I didn't catch that. Can you say your answer again?",
    "complete": "Great job! You finished all the questions! Keep practicing!",
    "error": "Let's try again. What is {a} + {b}?",
}


def _get_client():
    """Get OpenAI client if API key is available."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not OPENAI_AVAILABLE:
        return None
    return OpenAI(api_key=api_key)


def _build_user_prompt(state: str, question: dict, attempt_no: int, user_text: str,
                       is_correct: bool, expected_answer: int) -> str:
    """Build the user prompt for the LLM based on current state."""
    a = question.get("a", 0)
    b = question.get("b", 0)

    if state == "EXPLAIN":
        return "Introduce addition to a young student in 1-2 sentences. Be warm and encouraging."

    if state == "QUIZ":
        return f"Ask the student: What is {a} + {b}? Make it fun and simple."

    if is_correct:
        return f"The student correctly answered {a} + {b} = {expected_answer}. Praise them briefly (1 sentence) and encourage them."

    # Wrong answer scenarios
    if attempt_no == 1:
        return f"Student answered '{user_text}' for {a} + {b}, which is wrong. Give a gentle hint without revealing {expected_answer}. Be encouraging."

    if attempt_no == 2:
        return f"Student still got {a} + {b} wrong (they said '{user_text}'). Give a different hint, maybe using counting or objects. Don't reveal {expected_answer}."

    # attempt_no >= 3 - reveal
    return f"Student couldn't get {a} + {b} after 3 tries. Now reveal that the answer is {expected_answer} kindly, and encourage them to try the next question."


def _get_fallback(state: str, question: dict, attempt_no: int, is_correct: bool,
                  expected_answer: int) -> str:
    """Get fallback response when LLM is unavailable."""
    a = question.get("a", 0)
    b = question.get("b", 0)

    if state == "EXPLAIN":
        return FALLBACK_RESPONSES["explain"]

    if state == "QUIZ":
        return FALLBACK_RESPONSES["quiz"].format(a=a, b=b)

    if is_correct:
        return FALLBACK_RESPONSES["correct"]

    # Wrong answer
    if attempt_no == 1:
        return FALLBACK_RESPONSES["hint1"].format(a=a, b=b)
    if attempt_no == 2:
        return FALLBACK_RESPONSES["hint2"].format(a=a, b=b)

    # Reveal
    return FALLBACK_RESPONSES["reveal"].format(expected=expected_answer, a=a, b=b)


def generate_tutor_text(
    state: str,
    question: dict,
    attempt_no: int,
    user_text: str,
    is_correct: bool,
    expected_answer: int
) -> str:
    """
    Generate tutor response text using GPT-4o-mini.

    Args:
        state: Current FSM state (EXPLAIN, QUIZ, HINT, REVEAL, etc.)
        question: Dict with keys: a, b, answer, prompt, hint1, hint2, reveal
        attempt_no: Number of attempts on current question (0-3)
        user_text: What the student said/typed
        is_correct: Whether the student's answer was correct
        expected_answer: The correct answer

    Returns:
        Tutor text to speak/display
    """
    logger.info(f"LLM_CALL state={state} attempt={attempt_no} is_correct={is_correct}")

    client = _get_client()
    if client is None:
        logger.info("LLM_CALL using fallback (no API key or OpenAI not available)")
        return _get_fallback(state, question, attempt_no, is_correct, expected_answer)

    try:
        user_prompt = _build_user_prompt(state, question, attempt_no, user_text,
                                         is_correct, expected_answer)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=100,
            temperature=0.7,
        )

        tutor_text = response.choices[0].message.content.strip()
        logger.info(f"LLM_OK response_length={len(tutor_text)}")
        return tutor_text

    except Exception as e:
        logger.error(f"LLM_FAIL error={type(e).__name__}: {e}")
        return _get_fallback(state, question, attempt_no, is_correct, expected_answer)


def get_empty_input_response() -> str:
    """Return response for empty/gibberish input."""
    return FALLBACK_RESPONSES["empty_input"]


def get_complete_response() -> str:
    """Return response for session completion."""
    return FALLBACK_RESPONSES["complete"]
