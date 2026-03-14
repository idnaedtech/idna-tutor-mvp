"""Tests for v10.7.0 chapter introduction warmup."""
import pytest
from app.content.ch1_square_and_cube import CHAPTER_INTRO


def test_chapter_intro_has_all_languages():
    """All 4 languages must have turn_0 and turn_1."""
    for lang in ["hinglish", "english", "hindi", "telugu"]:
        assert lang in CHAPTER_INTRO, f"Missing language: {lang}"
        assert "turn_0" in CHAPTER_INTRO[lang], f"Missing turn_0 for {lang}"
        assert "turn_1" in CHAPTER_INTRO[lang], f"Missing turn_1 for {lang}"


def test_chapter_intro_turn_0_has_tile_analogy():
    """Turn 0 must contain the tile/visual analogy."""
    for lang in ["hinglish", "english", "hindi", "telugu"]:
        text = CHAPTER_INTRO[lang]["turn_0"]
        assert "tile" in text.lower() or "tiles" in text.lower() or \
            "టైల్స్" in text or "టైల" in text or \
            "टाइल्स" in text or "टाइल" in text, \
            f"Missing tile analogy in {lang} turn_0"


def test_chapter_intro_turn_0_has_3_times_3():
    """Turn 0 must contain the 3x3=9 example."""
    for lang in ["hinglish", "english", "hindi", "telugu"]:
        text = CHAPTER_INTRO[lang]["turn_0"]
        assert "3" in text and "9" in text, \
            f"Missing 3x3=9 example in {lang} turn_0"


def test_chapter_intro_turn_1_has_assessment_bridge():
    """Turn 1 must contain the assessment framing."""
    for lang in ["hinglish", "english"]:
        text = CHAPTER_INTRO[lang]["turn_1"]
        assert "know" in text.lower() or "aata" in text.lower() or "question" in text.lower(), \
            f"Missing assessment bridge in {lang} turn_1"


def test_chapter_intro_turn_1_has_square_root():
    """Turn 1 must explain square root (the reverse)."""
    for lang in ["hinglish", "english"]:
        text = CHAPTER_INTRO[lang]["turn_1"]
        assert "root" in text.lower() or "reverse" in text.lower() or "ulta" in text.lower(), \
            f"Missing square root explanation in {lang} turn_1"


def test_chapter_intro_voice_length():
    """Each turn must be <= 500 chars for TTS comfort."""
    for lang in CHAPTER_INTRO:
        for turn in ["turn_0", "turn_1"]:
            text = CHAPTER_INTRO[lang][turn]
            assert len(text) <= 500, \
                f"{lang}/{turn} is {len(text)} chars (max 500)"


def test_chapter_intro_no_formula_symbols():
    """Voice content must not contain symbols TTS can't speak."""
    bad_symbols = ["\u221a", "\u00b2", "\u00b3", "\u00d7", "\u00f7", "="]
    for lang in CHAPTER_INTRO:
        for turn in ["turn_0", "turn_1"]:
            text = CHAPTER_INTRO[lang][turn]
            for sym in bad_symbols:
                # "equals" as a word is fine, only bare "=" is bad
                if sym == "=":
                    # Check for bare = not part of "equals"
                    import re
                    bare_equals = re.findall(r'(?<!\w)=(?!\w)', text)
                    assert not bare_equals, \
                        f"Bare '=' symbol in {lang}/{turn}"
                else:
                    assert sym not in text, \
                        f"Bad TTS symbol '{sym}' in {lang}/{turn}"


def test_chapter_intro_builder_first_teaching():
    """instruction_builder uses chapter intro when questions_attempted == 0."""
    from app.tutor.state_machine import Action
    from app.tutor.instruction_builder import build_prompt

    action = Action("teach_concept", question_id="sq_b01", student_text="okay")
    ctx = {
        "student_name": "Test",
        "class_level": 8,
        "board_name": "NCERT",
        "language_pref": "english",
        "questions_attempted": 0,
        "teaching_turn": 0,
    }
    q = {"id": "sq_b01", "question_voice": "What is 3 squared?", "answer": "9",
         "target_skill": "perfect_square_concept", "chapter": "ch1_square_and_cube"}

    result = build_prompt(action, ctx, q, {}, [])
    user_msg = result[-1]["content"]
    # Should contain chapter intro instructions, not regular teach
    assert "FIRST TIME" in user_msg or "introducing the chapter" in user_msg, \
        f"Expected chapter intro prompt, got: {user_msg[:200]}"


def test_chapter_intro_not_used_after_questions():
    """instruction_builder uses normal teach when questions_attempted > 0."""
    from app.tutor.state_machine import Action
    from app.tutor.instruction_builder import build_prompt

    action = Action("teach_concept", question_id="sq_b01", student_text="I don't understand")
    ctx = {
        "student_name": "Test",
        "class_level": 8,
        "board_name": "NCERT",
        "language_pref": "english",
        "questions_attempted": 3,
        "teaching_turn": 0,
    }
    q = {"id": "sq_b01", "question_voice": "What is 3 squared?", "answer": "9",
         "target_skill": "perfect_square_concept", "chapter": "ch1_square_and_cube"}

    result = build_prompt(action, ctx, q, {}, [])
    user_msg = result[-1]["content"]
    # Should NOT contain chapter intro
    assert "FIRST TIME" not in user_msg and "introducing the chapter" not in user_msg, \
        f"Chapter intro should not fire when questions_attempted > 0: {user_msg[:200]}"


def test_fsm_ack_in_teaching_stays_during_chapter_intro():
    """ACK in TEACHING stays in TEACHING when questions_attempted == 0 (chapter intro)."""
    from app.tutor.state_machine import transition
    ctx = {"student_text": "okay", "teaching_turn": 0, "questions_attempted": 0}
    new_state, action = transition("TEACHING", "ACK", ctx)
    assert new_state == "TEACHING", f"Expected TEACHING, got {new_state}"
    assert action.action_type == "teach_concept"
    assert action.teaching_turn == 1


def test_fsm_ack_in_teaching_advances_after_chapter_intro():
    """ACK in TEACHING at turn_1 (after chapter intro turn_0) goes to WAITING_ANSWER."""
    from app.tutor.state_machine import transition
    ctx = {"student_text": "samajh gaya", "teaching_turn": 1, "questions_attempted": 0}
    new_state, action = transition("TEACHING", "ACK", ctx)
    assert new_state == "WAITING_ANSWER", f"Expected WAITING_ANSWER, got {new_state}"
    assert action.action_type == "read_question"
