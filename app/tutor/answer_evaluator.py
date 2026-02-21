"""
IDNA EdTech v7.5.0 — LLM-Based Answer Evaluator

Replaces regex + enforcer dance with GPT-4o evaluation.
Content Bank provides ground truth context. Enforcer validates JSON shape only.
"""

import json
import logging
from typing import Optional, Dict, Any, List, Callable, Awaitable

logger = logging.getLogger("idna.answer_evaluator")

ANSWER_EVAL_SYSTEM_PROMPT = """You are an answer evaluator for a Class 8 math tutor.

You receive:
- The question that was asked
- The expected correct answer
- Acceptable alternate forms of the answer
- Known misconceptions for this concept
- The student's response (may be in Hindi, English, Hinglish, or Devanagari)

Your job: determine if the student's answer is correct, incorrect, or partially correct.

IMPORTANT RULES:
1. The student may embed the answer in a full sentence.
   "Yes, 49 is a square of 7" contains the correct answer.
2. Numbers may be written as words in any language:
   "eight" = "aath" = "आठ" = "8"
3. Hindi math terms: "bata" = "बटा" = "/" (division)
4. If the student says the correct number anywhere in their response,
   and the context makes clear they mean it as their answer, it IS correct.
5. "I don't know" or "pata nahi" is NOT an answer — classify as "idk".
6. Be lenient with spelling variations in Hindi/Hinglish.

Respond with ONLY this JSON (no markdown, no explanation):
{
    "verdict": "correct" | "incorrect" | "partial" | "idk",
    "student_answer_extracted": "<the number/value you extracted from their response>",
    "feedback_hi": "<1 sentence feedback in Hinglish for TTS>",
    "feedback_en": "<1 sentence feedback in English for TTS>",
    "misconception_id": "<id from misconceptions list if matched, else null>"
}
"""


def build_eval_prompt(
    question_text: str,
    expected_answer: str,
    acceptable_alternates: List[str],
    misconceptions: List[Dict],
    student_response: str,
) -> List[Dict[str, str]]:
    """Build the evaluation prompt with Content Bank context."""

    context = f"""QUESTION ASKED: {question_text}

EXPECTED ANSWER: {expected_answer}

ACCEPTABLE ALTERNATES: {json.dumps(acceptable_alternates)}

KNOWN MISCONCEPTIONS:
{json.dumps(misconceptions, indent=2, ensure_ascii=False)}

STUDENT'S RESPONSE: "{student_response}"

Evaluate and respond with JSON only."""

    return [
        {"role": "system", "content": ANSWER_EVAL_SYSTEM_PROMPT},
        {"role": "user", "content": context},
    ]


def parse_eval_response(llm_response: str) -> Dict[str, Any]:
    """
    Parse the LLM's evaluation JSON.
    This is what the enforcer validates — JSON shape only.
    """
    # Strip markdown fences if present
    text = llm_response.strip()
    if text.startswith("```"):
        # Remove ```json or ``` at start
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Answer eval JSON parse failed: {text[:200]}... Error: {e}")
        return {
            "verdict": "unclear",
            "student_answer_extracted": "",
            "feedback_hi": "Ek baar phir se boliye?",
            "feedback_en": "Could you say that again?",
            "misconception_id": None,
        }

    # Validate required fields
    required = ["verdict", "student_answer_extracted", "feedback_hi", "feedback_en"]
    for field in required:
        if field not in result:
            result[field] = "" if field != "verdict" else "unclear"

    # Validate verdict is one of allowed values
    if result["verdict"] not in ("correct", "incorrect", "partial", "idk"):
        logger.warning(f"Invalid verdict '{result['verdict']}', defaulting to 'unclear'")
        result["verdict"] = "unclear"

    # Ensure misconception_id is present
    if "misconception_id" not in result:
        result["misconception_id"] = None

    return result


async def evaluate_answer(
    question_text: str,
    expected_answer: str,
    acceptable_alternates: List[str],
    misconceptions: List[Dict],
    student_response: str,
    llm_call_func: Callable[[List[Dict], int], Awaitable[str]],
) -> Dict[str, Any]:
    """
    Full answer evaluation pipeline.

    Args:
        question_text: The question that was asked
        expected_answer: The expected correct answer
        acceptable_alternates: List of acceptable alternate answers
        misconceptions: List of known misconceptions for this concept
        student_response: What the student said
        llm_call_func: Async function to call LLM with (messages, max_tokens) -> response

    Returns:
        Dict with verdict, extracted answer, feedback, misconception.
    """
    messages = build_eval_prompt(
        question_text, expected_answer, acceptable_alternates,
        misconceptions, student_response,
    )

    # Use GPT-4o for evaluation
    raw_response = await llm_call_func(messages, 150)
    result = parse_eval_response(raw_response)

    logger.info(
        f"Answer eval: '{student_response[:40]}...' -> {result['verdict']} "
        f"(extracted: {result['student_answer_extracted']})"
    )

    return result


def enforce_answer_eval(raw_response: str) -> tuple[bool, str]:
    """
    Enforcer for answer evaluation — validates JSON shape only.
    Does NOT validate whether the math is correct — that's the LLM's job.
    """
    try:
        # Strip markdown fences
        text = raw_response.strip()
        if text.startswith("```"):
            first_newline = text.find("\n")
            if first_newline != -1:
                text = text[first_newline + 1:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        result = json.loads(text)
        required = ["verdict", "student_answer_extracted", "feedback_hi"]
        if all(k in result for k in required):
            if result["verdict"] in ("correct", "incorrect", "partial", "idk", "unclear"):
                return True, raw_response
        return False, "Missing required fields in eval JSON"
    except json.JSONDecodeError:
        return False, "Invalid JSON from answer evaluator"
