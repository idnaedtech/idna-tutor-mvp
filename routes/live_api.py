"""
Gemini Live API Routes
IDNA EdTech - Single Entry Point for Gemini Live Function Calls

This endpoint routes Gemini Live function calls to existing FSM/Evaluator/TutorIntent logic.

Architecture:
- Gemini Live handles: ASR, TTS, barge-in (Ears + Larynx)
- This backend handles: FSM, Evaluator, TutorIntent (Brain)
- Gemini calls tutor_turn() → Backend decides → Gemini speaks response
"""

import logging
import time
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, Optional

from models.live_models import (
    LiveTurnRequest,
    LiveTurnResponse,
    LiveEvent,
    VoicePlan,
    SpeakDirective,
    NextAction,
    Canonical,
    UIDirective,
    Fallback,
)

# Import existing logic from web_server
# These will be imported after we update web_server.py to expose them
# For now, we'll use placeholders and integrate them later

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/live", tags=["Gemini Live"])


def log_live_turn(
    event: str,
    session_id: str,
    latency_ms: float,
    intent: Optional[str] = None,
    is_correct: Optional[bool] = None,
    **kwargs
):
    """Structured logging for Live API turns"""
    log_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "INFO",
        "message": f"Live turn: {event}",
        "event": "live_turn",
        "session_id": session_id,
        "live_event": event,
        "latency_ms": round(latency_ms, 2),
    }

    if intent:
        log_data["tutor_intent"] = intent
    if is_correct is not None:
        log_data["is_correct"] = is_correct

    log_data.update(kwargs)

    logger.info(str(log_data))


@router.post("/tutor_turn", response_model=LiveTurnResponse)
async def live_tutor_turn(request: LiveTurnRequest) -> LiveTurnResponse:
    """
    Single authoritative function for Gemini Live.
    Routes to existing FSM/Evaluator/TutorIntent logic.

    This is the ONLY function Gemini Live calls.
    Backend decides everything: correctness, intent, next steps.
    Gemini only speaks what backend tells it to speak.
    """
    start_time = time.time()

    try:
        # Route based on event type
        if request.event == LiveEvent.START_SESSION:
            response = await handle_start_session(request)

        elif request.event == LiveEvent.REQUEST_CHAPTER:
            response = await handle_select_chapter(request)

        elif request.event == LiveEvent.REQUEST_QUESTION:
            response = await handle_get_question(request)

        elif request.event == LiveEvent.SUBMIT_ANSWER:
            response = await handle_submit_answer(request)

        elif request.event == LiveEvent.INTERRUPT:
            response = await handle_interrupt(request)

        elif request.event == LiveEvent.REPEAT:
            response = await handle_repeat(request)

        elif request.event == LiveEvent.END_SESSION:
            response = await handle_end_session(request)

        else:
            raise HTTPException(400, f"Unknown event: {request.event}")

        # Log the turn
        latency_ms = (time.time() - start_time) * 1000
        log_live_turn(
            event=request.event.value,
            session_id=request.session_id,
            latency_ms=latency_ms,
            intent=response.tutor_intent,
            is_correct=response.is_correct,
            attempt_no=response.attempt_no,
            state=response.state,
        )

        return response

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error(f"Error in live_tutor_turn: {e}", exc_info=True)
        log_live_turn(
            event=request.event.value,
            session_id=request.session_id,
            latency_ms=latency_ms,
            error=str(e),
        )
        raise HTTPException(500, f"Internal error: {str(e)}")


async def handle_start_session(request: LiveTurnRequest) -> LiveTurnResponse:
    """Handle START_SESSION event"""
    # TODO: Integrate with existing session_start logic from web_server.py

    # For now, return a mock response
    return LiveTurnResponse(
        session_id=request.session_id,
        state="IDLE",
        attempt_no=0,
        tutor_intent="SESSION_START",
        language=request.language,
        voice_plan=VoicePlan(
            max_sentences=2,
            required=["greeting", "ready_prompt"],
            forbidden=["lengthy_intro"],
        ),
        speak=SpeakDirective(
            text="Namaste beta! Aaj hum math practice karenge. Ready ho?",
            ssml='<speak>Namaste beta!<break time="300ms"/> Aaj hum math practice karenge.<break time="400ms"/> Ready ho?</speak>',
        ),
        next_action=NextAction(type="WAIT_STUDENT"),
    )


async def handle_select_chapter(request: LiveTurnRequest) -> LiveTurnResponse:
    """Handle REQUEST_CHAPTER event"""
    # TODO: Integrate with existing chapter selection logic

    return LiveTurnResponse(
        session_id=request.session_id,
        state="CHAPTER_SELECTED",
        attempt_no=0,
        tutor_intent="ASK_FRESH",
        language=request.language,
        voice_plan=VoicePlan(
            max_sentences=2,
            required=["chapter_intro"],
            forbidden=["hints", "solution"],
        ),
        speak=SpeakDirective(
            text=f"Great choice! Let's practice {request.chapter_id}. Ready for the first question?",
            ssml=f'<speak>Great choice!<break time="300ms"/> Let\'s practice {request.chapter_id}.<break time="400ms"/> Ready for the first question?</speak>',
        ),
        next_action=NextAction(type="WAIT_STUDENT"),
    )


async def handle_get_question(request: LiveTurnRequest) -> LiveTurnResponse:
    """Handle REQUEST_QUESTION event"""
    # TODO: Integrate with existing question fetching logic

    # Mock question for testing
    return LiveTurnResponse(
        session_id=request.session_id,
        question_id="demo_q1",
        state="IN_QUESTION",
        attempt_no=0,
        tutor_intent="ASK_FRESH",
        language=request.language,
        voice_plan=VoicePlan(
            max_sentences=2,
            required=["question_text"],
            forbidden=["hints", "solution"],
        ),
        canonical=Canonical(
            question_text="What is 2/3 + 1/4?",
            expected_answer="11/12",
            hint_1="Find a common denominator for 3 and 4.",
            hint_2="Convert both fractions to denominator 12.",
            solution_steps=[
                "LCM of 3 and 4 is 12.",
                "2/3 = 8/12 and 1/4 = 3/12.",
                "8/12 + 3/12 = 11/12.",
            ],
        ),
        speak=SpeakDirective(
            text="Achha beta, what is 2/3 plus 1/4? Apna time lo.",
            ssml='<speak>Achha beta,<break time="250ms"/> what is 2/3 plus 1/4?<break time="350ms"/> Apna time lo.</speak>',
        ),
        next_action=NextAction(type="WAIT_STUDENT"),
    )


async def handle_submit_answer(request: LiveTurnRequest) -> LiveTurnResponse:
    """Handle SUBMIT_ANSWER event - core tutoring logic"""
    # TODO: Integrate with existing evaluator and teacher_policy logic

    # Mock response for testing (incorrect answer, first attempt)
    return LiveTurnResponse(
        session_id=request.session_id,
        question_id="demo_q1",
        state="SHOWING_HINT",
        attempt_no=1,
        is_correct=False,
        tutor_intent="GUIDE_THINKING",
        language=request.language,
        voice_plan=VoicePlan(
            max_sentences=2,
            required=["encouragement", "one_guiding_question"],
            forbidden=["say_wrong", "full_solution", "multiple_questions"],
        ),
        canonical=Canonical(
            question_text="What is 2/3 + 1/4?",
            expected_answer="11/12",
            hint_1="Find a common denominator for 3 and 4.",
            hint_2="Convert both fractions to denominator 12.",
            solution_steps=[
                "LCM of 3 and 4 is 12.",
                "2/3 = 8/12 and 1/4 = 3/12.",
                "8/12 + 3/12 = 11/12.",
            ],
        ),
        speak=SpeakDirective(
            text="Hmm beta, close but not quite. Fractions add karne se pehle common denominator chahiye. 3 aur 4 ka common denominator kya hoga?",
            ssml='<speak>Hmm beta,<break time="300ms"/> close but not quite.<break time="200ms"/> Fractions add karne se pehle common denominator chahiye.<break time="450ms"/> 3 aur 4 ka common denominator kya hoga?</speak>',
        ),
        next_action=NextAction(type="WAIT_STUDENT"),
        teacher_move="PROBE",
        error_type="incomplete_answer",
        goal="Diagnose if student knows common denominator concept",
    )


async def handle_interrupt(request: LiveTurnRequest) -> LiveTurnResponse:
    """Handle INTERRUPT event - student cut off tutor"""
    # Log the interrupt for telemetry
    logger.info(f"Student interrupted tutor mid-speech: session={request.session_id}")

    # Return current state without changing anything
    # The frontend will handle stopping audio playback
    return LiveTurnResponse(
        session_id=request.session_id,
        state="IN_QUESTION",  # TODO: Get actual state from session
        attempt_no=0,
        tutor_intent="INTERRUPT_ACKNOWLEDGED",
        language=request.language,
        voice_plan=VoicePlan(max_sentences=0, required=[], forbidden=[]),
        speak=SpeakDirective(text="", ssml=""),
        next_action=NextAction(type="WAIT_STUDENT"),
    )


async def handle_repeat(request: LiveTurnRequest) -> LiveTurnResponse:
    """Handle REPEAT event - student asked to repeat"""
    # TODO: Fetch last spoken message from session

    return LiveTurnResponse(
        session_id=request.session_id,
        state="IN_QUESTION",
        attempt_no=0,
        tutor_intent="REPEAT",
        language=request.language,
        voice_plan=VoicePlan(
            max_sentences=2,
            required=["original_message"],
            forbidden=["additional_hints"],
        ),
        speak=SpeakDirective(
            text="Sure beta. What is 2/3 plus 1/4?",
            ssml='<speak>Sure beta.<break time="200ms"/> What is 2/3 plus 1/4?</speak>',
        ),
        next_action=NextAction(type="WAIT_STUDENT"),
    )


async def handle_end_session(request: LiveTurnRequest) -> LiveTurnResponse:
    """Handle END_SESSION event"""
    # TODO: Integrate with existing session end logic and performance summary

    return LiveTurnResponse(
        session_id=request.session_id,
        state="COMPLETED",
        attempt_no=0,
        tutor_intent="SESSION_END",
        language=request.language,
        voice_plan=VoicePlan(
            max_sentences=2,
            required=["summary_praise"],
            forbidden=["criticism"],
        ),
        speak=SpeakDirective(
            text="Bahut accha kiya aaj beta! You got 3 out of 5 correct. Kal phir milte hain!",
            ssml='<speak>Bahut accha kiya aaj beta!<break time="300ms"/> You got 3 out of 5 correct.<break time="400ms"/> Kal phir milte hain!</speak>',
        ),
        next_action=NextAction(type="END_SESSION"),
    )
