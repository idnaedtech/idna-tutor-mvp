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
    detect_input_language,
    check_language_auto_switch,
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

    # Bug C fix: Test new Hindi confusion patterns
    def test_samajh_mein_nahi_aaya_devanagari(self):
        """Bug C: Devanagari 'samajh mein nahi aaya' must be detected."""
        assert detect_confusion("समझ में नहीं आया") is True

    def test_kuch_samajh_mein_nahi_devanagari(self):
        """Bug C: 'kuch samajh mein nahi' in Devanagari."""
        assert detect_confusion("कुछ समझ में नहीं") is True

    def test_mujhe_samajh_nahi_devanagari(self):
        """Bug C: 'mujhe samajh nahi' in Devanagari."""
        assert detect_confusion("मुझे कुछ समझ में नहीं आया") is True

    def test_samajh_mein_nahi_romanized(self):
        """Bug C: Romanized 'samajh mein nahi'."""
        assert detect_confusion("samajh mein nahi aaya") is True

    def test_cant_understand(self):
        """Bug C: English 'can't understand'."""
        assert detect_confusion("I can't understand this") is True

    def test_dont_understand(self):
        """Bug C: English 'don't understand'."""
        assert detect_confusion("I don't understand") is True


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
            chapter_name="Chapter 6, Squares and Square Roots",
            subject="math",
            current_skill="perfect_square_concept",
            language_pref="english",
        )
        assert "Chapter 6" in response
        assert "learning" in response.lower()

    def test_chapter_hindi(self):
        response = build_meta_response(
            meta_type="chapter",
            chapter="ch1_square_and_cube",
            chapter_name="Chapter 6, Squares and Square Roots",
            subject="math",
            current_skill="perfect_square_concept",
            language_pref="hinglish",
        )
        assert "Chapter 6" in response
        # v10.6.3: Hinglish meta-responses use Devanagari
        assert "पढ़ रहे हैं" in response

    def test_topic_with_skill_english(self):
        response = build_meta_response(
            meta_type="topic",
            chapter="ch1_square_and_cube",
            chapter_name="Chapter 6, Squares and Square Roots",
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
            chapter_name="Chapter 6, Squares and Square Roots",
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


# ─── Language Auto-Detection Tests ───────────────────────────────────────────


class TestDetectInputLanguage:
    """Test automatic language detection from student input."""

    def test_pure_english(self):
        assert detect_input_language("I didn't understand, please explain again") == 'english'

    def test_english_question(self):
        assert detect_input_language("What is the answer?") == 'english'

    def test_english_request(self):
        assert detect_input_language("Can you explain this differently?") == 'english'

    def test_english_with_example(self):
        assert detect_input_language("Not really. Give me some other example.") == 'english'

    def test_english_short(self):
        assert detect_input_language("Yes, let's start") == 'english'

    def test_hindi_devanagari(self):
        assert detect_input_language("हां, शुरू करते हैं") == 'hindi'

    def test_hindi_chapter_question(self):
        assert detect_input_language("कौन सा चैप्टर पढ़ रहे हैं") == 'hindi'

    def test_hindi_confusion(self):
        assert detect_input_language("मुझे समझ नहीं आया") == 'hindi'

    def test_hinglish_romanized(self):
        assert detect_input_language("Haan shuru karte hain") == 'hinglish'

    def test_hinglish_mixed(self):
        assert detect_input_language("Mujhe samajh nahi aaya yeh concept") == 'hinglish'

    def test_empty_string(self):
        assert detect_input_language("") == 'hinglish'

    def test_numbers_only(self):
        assert detect_input_language("49") == 'hinglish'

    def test_english_with_one_hindi_word(self):
        """Mostly English with one Hindi word should still be English."""
        assert detect_input_language("Yes didi I understand the concept now") == 'english'


class TestCheckLanguageAutoSwitch:
    """Test auto-switch logic based on consecutive English messages."""

    def test_first_english_message_no_switch(self):
        """First English message — don't switch yet, just count."""
        switch, lang, count = check_language_auto_switch('english', 'hinglish', 0)
        assert switch is False
        assert lang == 'hinglish'
        assert count == 1

    def test_second_english_message_switches(self):
        """Second consecutive English message — NOW switch."""
        switch, lang, count = check_language_auto_switch('english', 'hinglish', 1)
        assert switch is True
        assert lang == 'english'
        assert count == 2

    def test_no_switch_when_matching(self):
        """No switch needed when languages already match."""
        switch, lang, count = check_language_auto_switch('english', 'english', 0)
        assert switch is False
        assert lang == 'english'
        assert count == 0

    def test_counter_resets_on_hindi(self):
        """Counter resets when student sends Hindi after English."""
        switch, lang, count = check_language_auto_switch('english', 'hinglish', 0)
        assert count == 1

        switch, lang, count = check_language_auto_switch('hindi', 'hinglish', 1)
        assert count == 0

    def test_hinglish_session_english_input(self):
        """English input during Hindi session increments counter."""
        switch, lang, count = check_language_auto_switch('english', 'hindi', 0)
        assert switch is False
        assert count == 1

    def test_hindi_input_english_session_no_switch(self):
        """Hindi input during English session doesn't auto-switch."""
        switch, lang, count = check_language_auto_switch('hindi', 'english', 0)
        assert switch is False
        assert lang == 'english'
        assert count == 0

    def test_three_consecutive_english(self):
        """Third consecutive English still triggers switch."""
        switch, lang, count = check_language_auto_switch('english', 'hinglish', 2)
        assert switch is True
        assert lang == 'english'
        assert count == 3

    def test_hindi_input_hinglish_session_switches_to_hindi(self):
        """v10.1 FIX: Hindi (Devanagari) input during hinglish session switches to hindi."""
        switch, lang, count = check_language_auto_switch('hindi', 'hinglish', 0)
        assert switch is True
        assert lang == 'hindi'
        assert count == 0


class TestLanguageAutoDetectionIntegration:
    """Test the full flow: detect language → check auto-switch."""

    def test_two_english_messages_trigger_switch(self):
        """Simulate: student sends 2 English messages → should auto-switch."""
        lang1 = detect_input_language("I didn't understand, please explain again")
        assert lang1 == 'english'
        switch1, _, count1 = check_language_auto_switch(lang1, 'hinglish', 0)
        assert switch1 is False
        assert count1 == 1

        lang2 = detect_input_language("Can you explain this differently?")
        assert lang2 == 'english'
        switch2, new_lang, count2 = check_language_auto_switch(lang2, 'hinglish', count1)
        assert switch2 is True
        assert new_lang == 'english'
        assert count2 == 2

    def test_english_then_hinglish_resets(self):
        """Simulate: English then Hinglish → counter resets, no switch."""
        lang1 = detect_input_language("What is the answer?")
        assert lang1 == 'english'
        _, _, count1 = check_language_auto_switch(lang1, 'hinglish', 0)
        assert count1 == 1

        lang2 = detect_input_language("Haan batao aage kya hai")
        assert lang2 == 'hinglish'
        switch2, _, count2 = check_language_auto_switch(lang2, 'hinglish', count1)
        assert switch2 is False
        assert count2 == 0

    def test_first_message_english_in_greeting(self):
        """First student message in English during GREETING should be detected."""
        lang = detect_input_language("Yes, let's start")
        assert lang == 'english'


# ─── v10.2.0 Bug 5: Apostrophe Preservation Tests ────────────────────────────

class TestApostrophePreservation:
    """v10.2.0 Fix 5: Apostrophes must be preserved in _normalize for contractions."""

    def test_normalize_preserves_apostrophe(self):
        """_normalize should keep apostrophes for contractions."""
        from app.tutor.input_classifier import _normalize
        result = _normalize("I didn't understand")
        # Should preserve apostrophe OR have the no-apostrophe variant
        assert "didn't" in result or "didnt" in result

    def test_normalize_preserves_dont(self):
        """_normalize should keep 'don't' intact."""
        from app.tutor.input_classifier import _normalize
        result = _normalize("I don't know")
        assert "don't" in result or "dont" in result

    def test_fast_idk_has_apostrophe_variants(self):
        """FAST_IDK should have both apostrophe and no-apostrophe variants."""
        from app.tutor.input_classifier import FAST_IDK
        # Check that we have coverage for common contractions
        assert "didn't understand" in FAST_IDK or "didnt understand" in FAST_IDK
        assert "don't understand" in FAST_IDK or "dont understand" in FAST_IDK
