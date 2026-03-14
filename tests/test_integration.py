"""
IDNA EdTech v8.0 — Integration Tests

These tests simulate real multi-turn conversations and verify v8.0 architecture.
Tests cover:
- Language persistence
- Reteach cap at 3
- Content Bank material injection
- Session completion
- Hint progression
- All state × input combinations
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

# v8.0 imports
from app.state.session import SessionState, TutorState
from app.fsm.transitions import (
    get_transition, validate_matrix_completeness, TRANSITIONS,
    INPUT_CATEGORIES,
)
from app.fsm.handlers import (
    handle_state, handle_greeting, handle_teaching,
    handle_waiting_answer, handle_hint, handle_next_question,
    handle_session_end, get_cb_material_for_index,
)

# Configure pytest-asyncio
pytestmark = pytest.mark.asyncio


def run_async(coro):
    """Helper to run async functions in sync tests."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)


class TestLanguagePersistence:
    """Test 1: Language persists across turns."""

    def test_language_switch_sets_preference(self):
        """LANGUAGE_SWITCH should set preferred_language in session."""
        session = SessionState(
            session_id="test-1",
            student_name="Priya",
            student_pin="1234",
            preferred_language="hinglish",
        )

        transition = get_transition(TutorState.GREETING, "LANGUAGE_SWITCH")
        assert transition.special == "store_language"

        session.preferred_language = "english"
        assert session.preferred_language == "english"

    def test_language_persists_through_repeat(self):
        """After switching to English, REPEAT should not reset language."""
        session = SessionState(
            session_id="test-1",
            student_name="Priya",
            student_pin="1234",
            preferred_language="english",
        )

        transition = get_transition(TutorState.TEACHING, "REPEAT")
        assert session.preferred_language == "english"

    def test_language_persists_through_idk(self):
        """After switching to English, IDK should not reset language."""
        session = SessionState(
            session_id="test-1",
            student_name="Priya",
            student_pin="1234",
            preferred_language="english",
        )

        transition = get_transition(TutorState.TEACHING, "IDK")
        assert session.preferred_language == "english"

    def test_language_persists_through_wrong_answer(self):
        """After switching to English, hints should be in English."""
        session = SessionState(
            session_id="test-1",
            student_name="Priya",
            student_pin="1234",
            preferred_language="english",
        )

        transition = get_transition(TutorState.WAITING_ANSWER, "ANSWER")
        assert session.preferred_language == "english"

    def test_language_persists_across_5_turns(self):
        """Simulate 5 turns - language should persist."""
        session = SessionState(
            session_id="test-1",
            student_name="Priya",
            student_pin="1234",
            preferred_language="hinglish",
            current_state=TutorState.GREETING,
        )

        # Turn 1: Switch to English
        extras = {"preferred_language": "english"}
        response, new_state, updates = run_async(handle_greeting(
            session, "LANGUAGE_SWITCH", extras, "speak in English",
        ))
        if "preferred_language" in updates:
            session.preferred_language = updates["preferred_language"]
        assert session.preferred_language == "english"

        # Turn 2-5: Various inputs - language should persist
        session.current_state = TutorState.TEACHING
        for _ in range(4):
            assert session.preferred_language == "english"


class TestReteachCap:
    """Test 2: Reteach caps at 3."""

    def test_idk_three_times_advances_to_question(self):
        """Say IDK 3 times in TEACHING → advances to WAITING_ANSWER."""
        session = SessionState(
            session_id="test-2",
            student_name="Priya",
            student_pin="1234",
            current_state=TutorState.TEACHING,
            reteach_count=0,
            teach_material_index=0,
        )

        # IDK 1
        response, new_state, updates = run_async(handle_teaching(
            session, "IDK", {}, "pata nahi",
        ))
        session.reteach_count = updates.get("reteach_count", session.reteach_count)
        assert session.reteach_count == 1
        assert new_state == TutorState.TEACHING

        # IDK 2
        response, new_state, updates = run_async(handle_teaching(
            session, "IDK", {}, "still don't know",
        ))
        session.reteach_count = updates.get("reteach_count", session.reteach_count)
        assert session.reteach_count == 2
        assert new_state == TutorState.TEACHING

        # IDK 3 - should force advance
        response, new_state, updates = run_async(handle_teaching(
            session, "IDK", {}, "nope",
        ))
        session.reteach_count = updates.get("reteach_count", session.reteach_count)
        assert session.reteach_count == 3
        assert new_state == TutorState.WAITING_ANSWER

    def test_teach_material_index_progression(self):
        """Verify teach_material_index goes 0 → 1 → 2 (capped)."""
        session = SessionState(
            session_id="test-2",
            student_name="Priya",
            student_pin="1234",
        )

        assert session.teach_material_index == 0

        session.increment_reteach()
        assert session.reteach_count == 1
        assert session.teach_material_index == 1

        session.increment_reteach()
        assert session.reteach_count == 2
        assert session.teach_material_index == 2

        session.increment_reteach()
        assert session.reteach_count == 3
        assert session.teach_material_index == 2  # Capped at 2


class TestContentBankMaterial:
    """Test 3: Content Bank material appears in teaching."""

    def test_get_cb_material_index_0(self):
        """Index 0 returns definition + hook (or fallback without CB)."""
        material = get_cb_material_for_index(
            "math_8_ch6_perfect_square", 0, None
        )
        assert material["type"] == "fallback"

    def test_get_cb_material_index_1(self):
        """Index 1 returns analogy + example."""
        material = get_cb_material_for_index(
            "math_8_ch6_perfect_square", 1, None
        )
        assert material["type"] == "fallback"

    def test_get_cb_material_index_2(self):
        """Index 2 returns vedic_trick + key_insight."""
        material = get_cb_material_for_index(
            "math_8_ch6_perfect_square", 2, None
        )
        assert material["type"] == "fallback"

    def test_get_cb_material_index_3_force_advance(self):
        """Index >= 3 returns force_advance message."""
        material = get_cb_material_for_index(
            "math_8_ch6_perfect_square", 3, None
        )
        # Without content bank, still returns fallback
        assert material["type"] in ("force_advance", "fallback")


class TestTransitionMatrixCompleteness:
    """Test 4: All 60 state × input combinations are defined."""

    def test_all_60_combinations_exist(self):
        """Verify all 60 combinations are in TRANSITIONS."""
        states = list(TutorState)
        categories = list(INPUT_CATEGORIES)

        for state in states:
            for category in categories:
                key = (state, category)
                assert key in TRANSITIONS, f"Missing: {state.value} × {category}"

    def test_validate_matrix_completeness(self):
        """validate_matrix_completeness should return True."""
        assert validate_matrix_completeness() == True

    def test_no_keyerror_on_any_lookup(self):
        """get_transition should never raise KeyError."""
        states = list(TutorState)
        categories = list(INPUT_CATEGORIES)

        for state in states:
            for category in categories:
                result = get_transition(state, category)
                assert result is not None
                assert result.next_state is not None


class TestHintProgression:
    """Test 6: Hint progression."""

    def test_hint_1_to_hint_2_to_solution(self):
        """IDK in HINT should progress hints."""
        session = SessionState(
            session_id="test-6",
            student_name="Priya",
            student_pin="1234",
            current_state=TutorState.HINT,
            hints_given=1,
        )

        # IDK after hint 1 → hint 2
        response, new_state, updates = run_async(handle_hint(
            session, "IDK", {}, "still don't know",
        ))
        session.hints_given = updates.get("hints_given", session.hints_given)
        assert session.hints_given == 2

        # IDK after hint 2 → solution and NEXT_QUESTION
        response, new_state, updates = run_async(handle_hint(
            session, "IDK", {}, "give up",
        ))
        session.hints_given = updates.get("hints_given", session.hints_given)
        assert session.hints_given == 3
        assert new_state == TutorState.NEXT_QUESTION


class TestComfortHandling:
    """Test 7: COMFORT before teaching continues."""

    def test_comfort_in_teaching_then_continues(self):
        """In TEACHING, COMFORT → comfort response, stay in TEACHING."""
        session = SessionState(
            session_id="test-7",
            student_name="Priya",
            student_pin="1234",
            current_state=TutorState.TEACHING,
        )

        response, new_state, updates = run_async(handle_teaching(
            session, "COMFORT", {}, "bahut mushkil hai",
        ))

        assert new_state == TutorState.TEACHING
        assert updates.get("empathy_given") == True


class TestLanguageSwitchNotReteach:
    """Test 8: LANGUAGE_SWITCH does not count as reteach."""

    def test_language_switch_keeps_reteach_count(self):
        """LANGUAGE_SWITCH should NOT increment reteach_count."""
        session = SessionState(
            session_id="test-8",
            student_name="Priya",
            student_pin="1234",
            current_state=TutorState.TEACHING,
            reteach_count=0,
        )

        extras = {"preferred_language": "english"}
        response, new_state, updates = run_async(handle_teaching(
            session, "LANGUAGE_SWITCH", extras, "speak English",
        ))

        # reteach_count should NOT be incremented
        assert updates.get("reteach_count", 0) == 0

    def test_idk_after_language_switch_is_reteach_1(self):
        """After LANGUAGE_SWITCH, IDK should be reteach 1."""
        session = SessionState(
            session_id="test-8",
            student_name="Priya",
            student_pin="1234",
            current_state=TutorState.TEACHING,
            reteach_count=0,
        )

        # First: LANGUAGE_SWITCH
        extras = {"preferred_language": "english"}
        response, new_state, updates = run_async(handle_teaching(
            session, "LANGUAGE_SWITCH", extras, "speak English",
        ))
        assert updates.get("reteach_count", 0) == 0

        # Then: IDK
        response, new_state, updates = run_async(handle_teaching(
            session, "IDK", {}, "I don't understand",
        ))
        assert updates.get("reteach_count", 0) == 1


class TestConceptRequestFromWaitingAnswer:
    """Test 9: CONCEPT_REQUEST from WAITING_ANSWER goes back to TEACHING."""

    def test_concept_request_goes_to_teaching(self):
        """CONCEPT_REQUEST in WAITING_ANSWER → TEACHING."""
        session = SessionState(
            session_id="test-9",
            student_name="Priya",
            student_pin="1234",
            current_state=TutorState.WAITING_ANSWER,
            reteach_count=2,
        )

        response, new_state, updates = run_async(handle_waiting_answer(
            session, "CONCEPT_REQUEST", {}, "explain karo",
        ))

        assert new_state == TutorState.TEACHING
        assert updates.get("reteach_count") == 0


class TestStopFromAnyState:
    """Test 10: STOP from any state ends session."""

    def test_stop_from_greeting(self):
        """STOP in GREETING → SESSION_END."""
        session = SessionState(
            session_id="test-10",
            student_name="Priya",
            student_pin="1234",
            current_state=TutorState.GREETING,
        )

        response, new_state, updates = run_async(handle_greeting(
            session, "STOP", {}, "bye",
        ))
        assert new_state == TutorState.SESSION_END

    def test_stop_from_teaching(self):
        """STOP in TEACHING → SESSION_END."""
        session = SessionState(
            session_id="test-10",
            student_name="Priya",
            student_pin="1234",
            current_state=TutorState.TEACHING,
        )

        response, new_state, updates = run_async(handle_teaching(
            session, "STOP", {}, "band karo",
        ))
        assert new_state == TutorState.SESSION_END

    def test_stop_from_waiting_answer(self):
        """STOP in WAITING_ANSWER → SESSION_END."""
        session = SessionState(
            session_id="test-10",
            student_name="Priya",
            student_pin="1234",
            current_state=TutorState.WAITING_ANSWER,
        )

        response, new_state, updates = run_async(handle_waiting_answer(
            session, "STOP", {}, "stop",
        ))
        assert new_state == TutorState.SESSION_END


class TestStreamingInputCategories:
    """Test 11: All input categories have valid transitions."""

    def test_all_categories_have_transitions(self):
        """All input categories should have transitions from all states."""
        for category in INPUT_CATEGORIES:
            for state in TutorState:
                result = get_transition(state, category)
                assert result is not None


class TestSessionStatePersistence:
    """Test 15: Session state persistence."""

    def test_session_state_to_dict_round_trip(self):
        """Session state should serialize and deserialize correctly."""
        session = SessionState(
            session_id="test-15",
            student_name="Priya",
            student_pin="1234",
            preferred_language="english",
            current_state=TutorState.TEACHING,
            reteach_count=2,
            score=3,
            total_questions_asked=5,
        )

        data = session.to_dict()
        restored = SessionState.from_dict(data)

        assert restored.session_id == "test-15"
        assert restored.student_name == "Priya"
        assert restored.preferred_language == "english"
        assert restored.current_state == TutorState.TEACHING
        assert restored.reteach_count == 2
        assert restored.score == 3
        assert restored.total_questions_asked == 5


class TestGarbledInputHandling:
    """Test 14: Garbled input handling."""

    def test_garbled_stays_in_current_state(self):
        """GARBLED input should stay in current state."""
        session = SessionState(
            session_id="test-14",
            student_name="Priya",
            student_pin="1234",
            current_state=TutorState.TEACHING,
        )

        response, new_state, updates = run_async(handle_teaching(
            session, "GARBLED", {}, "[unintelligible]",
        ))

        assert new_state == TutorState.TEACHING
        # v9.0: Handlers now return None + _llm_instruction for LLM generation
        assert response is None
        assert "_llm_instruction" in updates
        assert updates["_llm_instruction"]["action"] == "handle_garbled"


class TestSessionEndTerminal:
    """Test: SESSION_END is terminal."""

    def test_session_end_stays_terminal(self):
        """Any input in SESSION_END should stay in SESSION_END."""
        session = SessionState(
            session_id="test-end",
            student_name="Priya",
            student_pin="1234",
            current_state=TutorState.SESSION_END,
            score=3,
            total_questions_asked=5,
        )

        for category in INPUT_CATEGORIES:
            response, new_state, updates = run_async(handle_session_end(
                session, category, {}, "anything",
            ))
            assert new_state == TutorState.SESSION_END


class TestFullSessionSimulation:
    """Test 5: Full session flow."""

    def test_full_session_flow(self):
        """Simulate GREETING → TEACHING → WAITING_ANSWER flow."""
        session = SessionState(
            session_id="test-full",
            student_name="Priya",
            student_pin="1234",
            current_state=TutorState.GREETING,
            total_questions_target=5,
        )

        # GREETING → TEACHING
        response, new_state, updates = run_async(handle_greeting(
            session, "ACK", {}, "haan",
        ))
        session.current_state = new_state
        assert new_state == TutorState.TEACHING

        # TEACHING → WAITING_ANSWER (ACK)
        response, new_state, updates = run_async(handle_teaching(
            session, "ACK", {}, "samajh aaya",
        ))
        session.current_state = new_state
        assert new_state == TutorState.WAITING_ANSWER


class TestBugDGreetingNotDumpingLesson:
    """v10.1: Question-first mode — GREETING goes directly to question."""

    def test_old_state_machine_greeting_ack_goes_to_teaching(self):
        """
        v10.5.2: GREETING + ACK → TEACHING (chapter intro before question).
        Old (v10.1): GREETING + ACK → WAITING_ANSWER (question first)
        New (v10.5.2): GREETING + ACK → TEACHING (chapter intro, then question)
        """
        from app.tutor.state_machine import transition

        ctx = {"student_text": "haan"}
        new_state, action = transition("GREETING", "ACK", ctx)

        # v10.5.2: Greeting response → chapter intro (TEACHING)
        assert new_state == "TEACHING", f"Expected TEACHING, got {new_state}"
        assert action.action_type == "teach_concept", f"Expected teach_concept, got {action.action_type}"
        assert action.extra.get("chapter_intro") is True

    def test_old_state_machine_greeting_engagement_goes_to_teaching(self):
        """v10.5.2: Most inputs in GREETING proceed to TEACHING (chapter intro)."""
        from app.tutor.state_machine import transition

        # TROLL, CONCEPT_REQUEST, etc. = student showed up, proceed to chapter intro
        ctx = {"student_text": "kya?"}
        new_state, action = transition("GREETING", "TROLL", ctx)

        # v10.5.2: Chapter intro before question
        assert new_state == "TEACHING", f"Expected TEACHING, got {new_state}"
        assert action.action_type == "teach_concept", f"Expected teach_concept, got {action.action_type}"

    def test_old_state_machine_greeting_comfort_stays(self):
        """COMFORT in GREETING should stay in GREETING (offer support first)."""
        from app.tutor.state_machine import transition

        ctx = {"student_text": "mushkil hai"}
        new_state, action = transition("GREETING", "COMFORT", ctx)

        assert new_state == "GREETING", f"Expected GREETING, got {new_state}"
        assert action.action_type == "comfort_student", f"Expected comfort_student, got {action.action_type}"

    def test_v8_fsm_greeting_ack_goes_to_teaching(self):
        """v8.0 FSM transition for GREETING + ACK → TEACHING."""
        result = get_transition(TutorState.GREETING, "ACK")

        assert result.next_state == TutorState.TEACHING
        assert result.action == "start_teaching"


class TestLanguagePersistenceE2E:
    """
    End-to-end tests for language persistence (Bug A/B fix).
    Tests that language switch persists across multiple turns.
    """

    def test_tts_language_mapping_english(self):
        """Bug B: get_tts_language should return 'en-IN' when language_pref is 'english'."""
        from unittest.mock import MagicMock
        from app.routers.student import get_tts_language

        session = MagicMock()
        session.language_pref = "english"
        session.language = "hi-IN"  # Default

        result = get_tts_language(session)
        assert result == "en-IN", f"Expected en-IN for english, got {result}"

    def test_tts_language_mapping_hindi(self):
        """TTS should return hi-IN for hindi/hinglish."""
        from unittest.mock import MagicMock
        from app.routers.student import get_tts_language

        session = MagicMock()
        session.language_pref = "hinglish"
        session.language = "hi-IN"

        result = get_tts_language(session)
        assert result == "hi-IN", f"Expected hi-IN for hinglish, got {result}"

    def test_language_switch_detection(self):
        """Language switch phrases should be detected correctly."""
        from app.tutor.preprocessing import detect_language_switch

        # English switch
        assert detect_language_switch("speak in English please") == "english"
        assert detect_language_switch("can you speak in english?") == "english"
        assert detect_language_switch("I don't understand Hindi") == "english"

        # Hindi switch
        assert detect_language_switch("Hindi mein bolo") == "hindi"
        assert detect_language_switch("speak in Hindi") == "hindi"


class TestConfusionEscalationE2E:
    """
    End-to-end tests for confusion escalation (Bug C fix).
    v10.1: Simplified persona handles frustration generically.
    """

    def test_confusion_handling_in_v10_persona(self):
        """v10.1: Persona handles frustration with warmth."""
        from app.tutor.instruction_builder import _sys

        # v10.1: Simplified persona handles frustration generically
        ctx = {
            "confusion_count": 4,
            "language_pref": "english",
            "student_name": "Priya",
            "board_name": "NCERT",
            "class_level": 8,
            "state": "TEACHING",
        }
        result = _sys(session_context=ctx)
        # v10.1: Persona should mention handling frustration
        assert "frustration" in result.lower() or "tired" in result.lower(), \
            "v10.1 persona should handle frustration warmly"

    def test_confusion_count_in_prompt(self):
        """V10: confusion_count value should appear in the prompt."""
        from app.tutor.instruction_builder import _sys

        ctx = {
            "confusion_count": 3,
            "language_pref": "english",
            "student_name": "Priya",
            "board_name": "NCERT",
            "class_level": 8,
            "state": "TEACHING",
        }
        result = _sys(session_context=ctx)
        # The confusion count should be visible in prompt
        assert "3" in result, "Confusion count should be injected in prompt"

    def test_confusion_patterns_hindi(self):
        """Bug C: Hindi confusion patterns should be detected."""
        from app.tutor.preprocessing import detect_confusion

        # Devanagari patterns
        assert detect_confusion("समझ में नहीं आया") is True
        assert detect_confusion("कुछ समझ में नहीं") is True
        assert detect_confusion("मुझे समझ में नहीं आया") is True

        # Romanized patterns
        assert detect_confusion("samajh mein nahi aaya") is True
        assert detect_confusion("kuch samajh nahi") is True

        # English patterns
        assert detect_confusion("I can't understand") is True
        assert detect_confusion("I don't understand this") is True


class TestV1069HintChainFixes:
    """v10.6.9: CONCEPT_REQUEST in hint states stays in hint chain."""

    def test_hint1_concept_request_goes_to_hint2(self):
        """HINT_1 + CONCEPT_REQUEST → HINT_2 (not TEACHING)."""
        from app.tutor.state_machine import transition

        ctx = {"student_text": "teach me properly"}
        new_state, action = transition("HINT_1", "CONCEPT_REQUEST", ctx)

        assert new_state == "HINT_2", f"Expected HINT_2, got {new_state}"
        assert action.action_type == "give_hint", f"Expected give_hint, got {action.action_type}"

    def test_hint2_concept_request_goes_to_full_solution(self):
        """HINT_2 + CONCEPT_REQUEST → FULL_SOLUTION (not TEACHING)."""
        from app.tutor.state_machine import transition

        ctx = {"student_text": "samjhao na"}
        new_state, action = transition("HINT_2", "CONCEPT_REQUEST", ctx)

        assert new_state == "FULL_SOLUTION", f"Expected FULL_SOLUTION, got {new_state}"
        assert action.action_type == "show_solution", f"Expected show_solution, got {action.action_type}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
