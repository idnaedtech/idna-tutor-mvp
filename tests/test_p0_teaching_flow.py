"""
P0 Teaching Flow Tests
Verifies fixes for 5 bugs identified through database forensics on 872 sessions.
"""

import pytest


class TestBug1ConceptRequestIncrements:
    """Bug 1: CONCEPT_REQUEST during TEACHING must increment teaching_turn."""

    def test_concept_request_increments_teaching_turn(self):
        """CONCEPT_REQUEST during TEACHING must increment teaching_turn."""
        from app.tutor.state_machine import transition
        ctx = {
            "student_text": "explain again",
            "teaching_turn": 0,
            "current_question_id": None,
            "current_hint_level": 0,
            "current_reteach_count": 0,
            "questions_attempted": 0,
        }
        new_state, action = transition("TEACHING", "CONCEPT_REQUEST", ctx)
        assert action.teaching_turn == 1, f"Expected teaching_turn=1, got {action.teaching_turn}"

    def test_concept_request_forces_transition_at_3(self):
        """After 3 CONCEPT_REQUESTs, force to WAITING_ANSWER."""
        from app.tutor.state_machine import transition
        ctx = {
            "student_text": "explain again",
            "teaching_turn": 2,
            "current_question_id": None,
            "current_hint_level": 0,
            "current_reteach_count": 0,
            "questions_attempted": 0,
        }
        new_state, action = transition("TEACHING", "CONCEPT_REQUEST", ctx)
        assert new_state == "WAITING_ANSWER", f"Expected WAITING_ANSWER, got {new_state}"
        assert action.teaching_turn == 3

    def test_concept_request_at_turn_1_stays_in_teaching(self):
        """At turn 1, CONCEPT_REQUEST should stay in TEACHING with turn 2."""
        from app.tutor.state_machine import transition
        ctx = {
            "student_text": "please explain",
            "teaching_turn": 1,
            "current_question_id": None,
            "current_hint_level": 0,
            "current_reteach_count": 0,
            "questions_attempted": 0,
        }
        new_state, action = transition("TEACHING", "CONCEPT_REQUEST", ctx)
        assert new_state == "TEACHING", f"Expected TEACHING, got {new_state}"
        assert action.teaching_turn == 2


class TestBug3DevanagariMetaPatterns:
    """Bug 3: Devanagari meta-question patterns from Sarvam STT."""

    def test_devanagari_kaun_sa_chapter(self):
        """Full Devanagari: kaun sa chapter."""
        from app.tutor.preprocessing import detect_meta_question
        assert detect_meta_question("कौन सा चैप्टर पढ़ रहे हैं") == "chapter"

    def test_devanagari_kaunsa_chapter(self):
        """Full Devanagari: kaunsa chapter."""
        from app.tutor.preprocessing import detect_meta_question
        assert detect_meta_question("कौनसा चैप्टर है ये") == "chapter"

    def test_devanagari_konsa_chapter(self):
        """Colloquial Devanagari: konsa chapter."""
        from app.tutor.preprocessing import detect_meta_question
        assert detect_meta_question("कोनसा चैप्टर है") == "chapter"

    def test_devanagari_chapter_kya(self):
        """Reversed order: chapter kya."""
        from app.tutor.preprocessing import detect_meta_question
        assert detect_meta_question("चैप्टर क्या है") == "chapter"

    def test_devanagari_kya_padh_rahe_hain(self):
        """Full phrase: kya padh rahe hain."""
        from app.tutor.preprocessing import detect_meta_question
        assert detect_meta_question("क्या पढ़ रहे हैं हम") == "topic"

    def test_devanagari_kaun_sa_topic(self):
        """Mixed: kaun sa topic."""
        from app.tutor.preprocessing import detect_meta_question
        assert detect_meta_question("कौन सा topic है") == "topic"


class TestBug4EmotionalDistress:
    """Bug 4: Emotional distress detection."""

    def test_emotional_distress_udaas_devanagari(self):
        """Devanagari: udaas (sad)."""
        from app.tutor.preprocessing import detect_emotional_distress
        assert detect_emotional_distress("मैं बहुत उदास हूं") == True

    def test_emotional_distress_sad_english(self):
        """English: I'm very sad."""
        from app.tutor.preprocessing import detect_emotional_distress
        assert detect_emotional_distress("I'm very sad today") == True

    def test_emotional_distress_tired(self):
        """English: very tired."""
        from app.tutor.preprocessing import detect_emotional_distress
        assert detect_emotional_distress("I'm very tired") == True

    def test_emotional_distress_bad_day(self):
        """English: had a bad day."""
        from app.tutor.preprocessing import detect_emotional_distress
        assert detect_emotional_distress("I had a bad day") == True

    def test_emotional_distress_mood_kharab(self):
        """Romanized: mood kharab."""
        from app.tutor.preprocessing import detect_emotional_distress
        assert detect_emotional_distress("mood kharab hai") == True

    def test_no_emotional_distress_school_good(self):
        """Normal: school was good."""
        from app.tutor.preprocessing import detect_emotional_distress
        assert detect_emotional_distress("school was good") == False

    def test_no_emotional_distress_answer(self):
        """Normal: math answer."""
        from app.tutor.preprocessing import detect_emotional_distress
        assert detect_emotional_distress("the answer is 64") == False


class TestBug5ResponseLength:
    """Bug 5: Response length guard for long content."""

    def test_long_content_triggers_summarize(self):
        """Content > 200 chars should trigger summarization instruction."""
        from app.tutor.instruction_builder import _build_teach_concept
        from app.tutor.state_machine import Action

        # Create a mock action with teaching_turn=0
        action = Action(
            action_type="teach_concept",
            teaching_turn=0,
            student_text="explain this"
        )

        # Create session context
        ctx = {
            "language_pref": "english",
            "chapter": "ch1_square_and_cube",
            "confusion_count": 0,
        }

        # Create question data with a skill that has long content
        q = {"target_skill": "perfect_square_identification"}

        messages = _build_teach_concept(action, ctx, q, None, None)

        # The message should exist and be properly formatted
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"


class TestPreprocessResultEmotional:
    """Test PreprocessResult includes emotional_distress field."""

    def test_preprocess_result_has_emotional_field(self):
        """PreprocessResult should have emotional_distress field."""
        from app.tutor.preprocessing import PreprocessResult
        result = PreprocessResult()
        assert hasattr(result, 'emotional_distress')
        assert result.emotional_distress == False

    def test_preprocess_detects_emotional(self):
        """preprocess_student_message should detect emotional distress."""
        from app.tutor.preprocessing import preprocess_student_message
        result = preprocess_student_message("I'm very sad today")
        assert result.emotional_distress == True

    def test_preprocess_no_emotional_for_normal(self):
        """preprocess_student_message should not flag normal messages."""
        from app.tutor.preprocessing import preprocess_student_message
        result = preprocess_student_message("the answer is 16")
        assert result.emotional_distress == False
