"""
IDNA EdTech v8.1.0 — Tests for Preprocessing Module

Tests for the three detectors:
1. Language switch detector
2. Confusion detector
3. Meta-question detector

Also tests processing order and integration.
"""

import pytest
from app.tutor.preprocessing import (
    detect_language_switch,
    detect_confusion,
    detect_meta_question,
    build_meta_response,
    preprocess_student_message,
    PreprocessResult,
)


class TestLanguageSwitchDetector:
    """Test language switch detection patterns."""

    def test_speak_in_english(self):
        assert detect_language_switch("speak in english") == "english"

    def test_please_talk_in_english(self):
        assert detect_language_switch("please talk in english") == "english"

    def test_english_please(self):
        assert detect_language_switch("English please") == "english"

    def test_i_dont_understand_hindi(self):
        assert detect_language_switch("I don't understand hindi") == "english"

    def test_switch_to_english(self):
        assert detect_language_switch("switch to english") == "english"

    def test_can_you_speak_in_english(self):
        assert detect_language_switch("can you speak in english?") == "english"

    def test_hindi_mein_bolo(self):
        assert detect_language_switch("hindi mein bolo") == "hindi"

    def test_speak_in_hindi(self):
        assert detect_language_switch("speak in hindi") == "hindi"

    def test_no_switch_normal_answer(self):
        assert detect_language_switch("49") is None

    def test_no_switch_math_answer(self):
        assert detect_language_switch("7 times 7 is 49") is None

    def test_no_switch_yes(self):
        assert detect_language_switch("yes, samajh aaya") is None

    def test_case_insensitive(self):
        assert detect_language_switch("SPEAK IN ENGLISH") == "english"
        assert detect_language_switch("English Please") == "english"


class TestConfusionDetector:
    """Test confusion detection patterns."""

    def test_i_dont_understand(self):
        assert detect_confusion("I don't understand") is True

    def test_samajh_nahi(self):
        assert detect_confusion("samajh nahi aaya") is True

    def test_nahi_samjha(self):
        assert detect_confusion("nahi samjha") is True

    def test_not_understanding(self):
        assert detect_confusion("not understanding") is True

    def test_nahi_aaya(self):
        assert detect_confusion("nahi aaya") is True

    def test_can_you_explain_again(self):
        assert detect_confusion("can you explain again") is True

    def test_what_do_you_mean(self):
        assert detect_confusion("what do you mean?") is True

    def test_huh(self):
        assert detect_confusion("huh?") is True

    def test_confusing(self):
        assert detect_confusion("this is confusing") is True

    def test_phir_se_bolo(self):
        assert detect_confusion("phir se bolo") is True

    def test_no_confusion_yes(self):
        assert detect_confusion("yes") is False

    def test_no_confusion_ok(self):
        assert detect_confusion("ok, samajh aaya") is False

    def test_no_confusion_answer(self):
        assert detect_confusion("49") is False

    def test_no_confusion_normal_sentence(self):
        assert detect_confusion("I think the answer is 49") is False


class TestMetaQuestionDetector:
    """Test meta-question detection patterns."""

    def test_what_chapter(self):
        assert detect_meta_question("what chapter are we learning?") == "chapter"

    def test_which_chapter(self):
        assert detect_meta_question("which chapter is this?") == "chapter"

    def test_kaunsa_chapter(self):
        assert detect_meta_question("kaunsa chapter hai") == "chapter"

    def test_what_topic(self):
        assert detect_meta_question("what topic are we on?") == "topic"

    def test_what_are_we_learning(self):
        assert detect_meta_question("what are we learning?") == "topic"

    def test_what_are_we_studying(self):
        assert detect_meta_question("what are we studying?") == "topic"

    def test_kya_padh_rahe(self):
        assert detect_meta_question("kya padh rahe hain?") == "topic"

    def test_what_subject(self):
        assert detect_meta_question("what subject is this?") == "subject"

    def test_how_long(self):
        assert detect_meta_question("how long have we been studying?") == "progress"

    def test_what_did_we_cover(self):
        assert detect_meta_question("what did we cover today?") == "progress"

    def test_no_meta_normal_answer(self):
        assert detect_meta_question("49") is None

    def test_no_meta_confusion(self):
        assert detect_meta_question("I don't understand") is None


class TestBuildMetaResponse:
    """Test building meta-question responses."""

    def test_chapter_english(self):
        response = build_meta_response(
            meta_type="chapter",
            chapter="ch1_square_and_cube",
            chapter_name="Chapter 6 - Squares and Square Roots",
            subject="math",
            current_skill="perfect_square_concept",
            language_pref="english",
        )
        assert "Chapter 6 - Squares and Square Roots" in response
        assert "learning" in response.lower()

    def test_chapter_hindi(self):
        response = build_meta_response(
            meta_type="chapter",
            chapter="ch1_square_and_cube",
            chapter_name="Chapter 6 - Squares and Square Roots",
            subject="math",
            current_skill="perfect_square_concept",
            language_pref="hinglish",
        )
        assert "Chapter 6 - Squares and Square Roots" in response
        assert "padh rahe hain" in response

    def test_topic_with_skill_english(self):
        response = build_meta_response(
            meta_type="topic",
            chapter="ch1_square_and_cube",
            chapter_name="Chapter 6 - Squares and Square Roots",
            subject="math",
            current_skill="perfect_square_concept",
            language_pref="english",
        )
        assert "Perfect Square Concept" in response

    def test_subject_english(self):
        response = build_meta_response(
            meta_type="subject",
            chapter="",
            chapter_name="",
            subject="math",
            current_skill="",
            language_pref="english",
        )
        assert "Math" in response


class TestPreprocessStudentMessage:
    """Test the main preprocessing function."""

    def test_meta_question_bypasses_llm(self):
        result = preprocess_student_message(
            text="what chapter are we learning?",
            chapter="ch1_square_and_cube",
            chapter_name="Chapter 6 - Squares and Square Roots",
            subject="math",
            language_pref="english",
        )
        assert result.bypass_llm is True
        assert result.meta_question_type == "chapter"
        assert "Chapter 6" in result.template_response

    def test_language_switch_detected(self):
        result = preprocess_student_message(
            text="speak in english please",
            chapter="ch1_square_and_cube",
            chapter_name="Chapter 6",
            subject="math",
            language_pref="hinglish",
        )
        assert result.bypass_llm is False
        assert result.language_switched is True
        assert result.new_language == "english"

    def test_confusion_detected(self):
        result = preprocess_student_message(
            text="I don't understand",
            chapter="ch1_square_and_cube",
            chapter_name="Chapter 6",
            subject="math",
            language_pref="english",
        )
        assert result.bypass_llm is False
        assert result.confusion_detected is True

    def test_meta_question_takes_priority(self):
        """Meta-question should bypass LLM even if other patterns present."""
        result = preprocess_student_message(
            text="what chapter? I don't understand",
            chapter="ch1_square_and_cube",
            chapter_name="Chapter 6",
            subject="math",
            language_pref="english",
        )
        # Meta-question should cause bypass, ignoring confusion
        assert result.bypass_llm is True
        assert result.meta_question_type == "chapter"

    def test_both_language_and_confusion(self):
        """Language switch and confusion can both be detected."""
        result = preprocess_student_message(
            text="speak in english, I don't understand hindi",
            chapter="ch1_square_and_cube",
            chapter_name="Chapter 6",
            subject="math",
            language_pref="hinglish",
        )
        assert result.bypass_llm is False
        assert result.language_switched is True
        assert result.new_language == "english"
        # Note: "I don't understand hindi" matches language switch, not confusion

    def test_normal_answer_no_detection(self):
        """Normal answers should not trigger any detector."""
        result = preprocess_student_message(
            text="49",
            chapter="ch1_square_and_cube",
            chapter_name="Chapter 6",
            subject="math",
            language_pref="english",
        )
        assert result.bypass_llm is False
        assert result.language_switched is False
        assert result.confusion_detected is False
        assert result.meta_question_type is None


class TestProcessingOrder:
    """Test that processing order is correct: meta → language → confusion."""

    def test_order_meta_first(self):
        """Meta-questions should be checked first and bypass LLM."""
        result = preprocess_student_message(
            text="what chapter are we on?",
            chapter="ch1_square_and_cube",
            chapter_name="Chapter 6",
            subject="math",
            language_pref="english",
        )
        assert result.bypass_llm is True
        # Other detections should not matter since we bypassed
        # (they aren't checked after meta-question match)

    def test_order_language_before_confusion(self):
        """If not meta, language and confusion are both checked."""
        # A message that might look like confusion but is language switch
        result = preprocess_student_message(
            text="I don't understand hindi, speak english",
            chapter="ch1_square_and_cube",
            chapter_name="Chapter 6",
            subject="math",
            language_pref="hinglish",
        )
        assert result.bypass_llm is False
        assert result.language_switched is True
        assert result.new_language == "english"


class TestConfusionCountReset:
    """Test that confusion_count logic is correct."""

    def test_confusion_detected_increments(self):
        """When confusion is detected, it should be flagged for increment."""
        result = preprocess_student_message(
            text="nahi samjha",
            chapter="ch1_square_and_cube",
            chapter_name="Chapter 6",
            subject="math",
            language_pref="hinglish",
        )
        assert result.confusion_detected is True
