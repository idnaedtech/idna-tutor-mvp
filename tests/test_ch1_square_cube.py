"""Tests for Chapter 1: A Square and A Cube question bank."""
import pytest
from app.content.ch1_square_and_cube import (
    QUESTIONS, SKILL_LESSONS, CHAPTER_META, ANSWER_CHECKER_RULES,
    get_questions_by_difficulty, get_questions_by_skill, get_question_by_id,
    get_skill_lesson, chapter_stats,
)


class TestQuestionBank:
    def test_total_questions(self):
        assert len(QUESTIONS) == 50

    def test_difficulty_distribution(self):
        easy = get_questions_by_difficulty("easy")
        medium = get_questions_by_difficulty("medium")
        hard = get_questions_by_difficulty("hard")
        assert len(easy) >= 15
        assert len(medium) >= 15
        assert len(hard) >= 10
        assert len(easy) + len(medium) + len(hard) == 50

    def test_no_duplicate_ids(self):
        ids = [q["id"] for q in QUESTIONS]
        assert len(ids) == len(set(ids))

    def test_all_questions_have_required_fields(self):
        required = ["id", "chapter", "type", "difficulty", "question",
                    "answer", "hints", "accept_patterns", "target_skill"]
        for q in QUESTIONS:
            for field in required:
                assert field in q, f"{q['id']} missing {field}"

    def test_all_skills_have_lessons(self):
        skills_used = set(q["target_skill"] for q in QUESTIONS)
        for skill in skills_used:
            assert skill in SKILL_LESSONS, f"Skill {skill} has no lesson"

    def test_teaching_order_complete(self):
        for skill in CHAPTER_META["teaching_order"]:
            assert skill in SKILL_LESSONS, f"{skill} in teaching_order but not in SKILL_LESSONS"

    def test_all_lessons_have_pre_teach(self):
        for key, lesson in SKILL_LESSONS.items():
            assert "pre_teach" in lesson, f"Skill {key} missing pre_teach"

    def test_get_question_by_id(self):
        q = get_question_by_id("sq_e01")
        assert q is not None
        assert q["answer"] == "haan"

    def test_get_question_by_id_not_found(self):
        assert get_question_by_id("nonexistent") is None

    def test_chapter_stats(self):
        stats = chapter_stats()
        assert stats["total_questions"] == 50
        assert stats["skills_count"] >= 15


class TestAnswerCheckerRules:
    def test_hindi_number_map_has_common_numbers(self):
        m = ANSWER_CHECKER_RULES["hindi_number_map"]
        assert m["ek"] == 1
        assert m["das"] == 10
        assert m["sau"] == 100

    def test_tts_conversions_exist(self):
        c = ANSWER_CHECKER_RULES["tts_conversions"]
        assert "²" in c
        assert "³" in c
        assert "√" in c
