"""
Tests for IDNA Content Bank loader and data integrity.
"""

import pytest
import re
from content_bank.loader import ContentBank, get_content_bank


class TestContentBankLoader:
    """Test ContentBank loading and singleton pattern."""

    def test_content_bank_loads(self):
        """Content bank JSON loads without errors."""
        bank = ContentBank()
        stats = bank.get_stats()
        assert stats["concepts"] > 0, "No concepts loaded"
        assert stats["questions"] > 0, "No questions loaded"

    def test_content_bank_singleton(self):
        """ContentBank returns same instance on repeated calls."""
        bank1 = get_content_bank()
        bank2 = get_content_bank()
        assert bank1 is bank2, "Singleton pattern broken"

    def test_ch6_loaded(self):
        """Chapter 6 content bank is loaded."""
        bank = get_content_bank()
        concepts = bank.get_chapter_concepts("math_8_ch6")
        assert len(concepts) >= 10, f"Expected 10+ concepts, got {len(concepts)}"


class TestConceptFields:
    """Test that all concepts have required fields."""

    def test_all_concepts_have_required_fields(self):
        """Every concept has definition, definition_tts, examples, misconceptions, questions."""
        bank = get_content_bank()

        for concept_id, concept in bank._concepts.items():
            assert "definition" in concept, f"{concept_id}: missing definition"
            assert "definition_tts" in concept, f"{concept_id}: missing definition_tts"
            assert "examples" in concept, f"{concept_id}: missing examples"
            assert len(concept["examples"]) >= 3, f"{concept_id}: needs 3 examples"
            assert "misconceptions" in concept, f"{concept_id}: missing misconceptions"
            assert len(concept["misconceptions"]) >= 2, f"{concept_id}: needs 2 misconceptions"
            assert "questions" in concept, f"{concept_id}: missing questions"
            assert len(concept["questions"]) >= 3, f"{concept_id}: needs 3 questions"
            assert "teaching_methodology" in concept, f"{concept_id}: missing teaching_methodology"

    def test_all_questions_have_answers(self):
        """Every question has expected_answer and acceptable_alternates."""
        bank = get_content_bank()

        for q_id, question in bank._questions.items():
            assert "expected_answer" in question, f"{q_id}: missing expected_answer"
            assert "acceptable_alternates" in question, f"{q_id}: missing acceptable_alternates"
            assert isinstance(question["acceptable_alternates"], list), f"{q_id}: acceptable_alternates not a list"


class TestQuestionLookup:
    """Test question retrieval methods."""

    def test_question_lookup_by_id(self):
        """Can retrieve any question by question_id."""
        bank = get_content_bank()

        # Get first question from Ch6
        questions = bank.get_chapter_questions("math_8_ch6")
        assert len(questions) > 0, "No questions in Ch6"

        first_q = questions[0]
        q_id = first_q.get("question_id")
        assert q_id is not None, "Question has no ID"

        # Lookup by ID
        retrieved = bank.get_question_by_id(q_id)
        assert retrieved is not None, f"Could not find question {q_id}"
        assert retrieved["expected_answer"] == first_q["expected_answer"]

    def test_get_hints(self):
        """Questions have retrievable hints."""
        bank = get_content_bank()
        questions = bank.get_chapter_questions("math_8_ch6")

        for q in questions[:5]:  # Test first 5
            q_id = q.get("question_id")
            hints = bank.get_hints(q_id)
            assert len(hints) >= 2, f"{q_id}: needs 2 hints, got {len(hints)}"

    def test_get_acceptable_answers(self):
        """Can get all acceptable answers for a question."""
        bank = get_content_bank()
        questions = bank.get_chapter_questions("math_8_ch6")

        for q in questions[:5]:
            q_id = q.get("question_id")
            answers = bank.get_acceptable_answers(q_id)
            assert len(answers) >= 1, f"{q_id}: needs at least 1 acceptable answer"


class TestSkillProgression:
    """Test skill progression ordering."""

    def test_skill_progression_order(self):
        """Prerequisites are satisfied — no concept requires a concept that comes later."""
        bank = get_content_bank()
        concepts = bank.get_chapter_concepts("math_8_ch6")

        seen_concepts = set()
        for concept in concepts:
            concept_id = concept.get("concept_id")
            prerequisites = concept.get("prerequisite_concepts", [])

            for prereq in prerequisites:
                # Prerequisites should either be from previous chapters or already seen
                if prereq.startswith("math_8_ch6_"):
                    assert prereq in seen_concepts, \
                        f"{concept_id} requires {prereq} which comes later in progression"

            seen_concepts.add(concept_id)


class TestTTSFields:
    """Test TTS field quality."""

    # Symbols that should NOT appear in TTS fields
    FORBIDDEN_SYMBOLS = re.compile(r'[√²³×÷±∞≠≤≥∈∉⊂⊃∪∩∀∃]')

    def test_tts_fields_have_no_symbols(self):
        """No _tts field contains raw math symbols."""
        bank = get_content_bank()

        for concept_id, concept in bank._concepts.items():
            # Check definition_tts
            def_tts = concept.get("definition_tts", "")
            assert not self.FORBIDDEN_SYMBOLS.search(def_tts), \
                f"{concept_id}.definition_tts contains forbidden symbols"

            # Check example solution_tts
            for i, ex in enumerate(concept.get("examples", [])):
                sol_tts = ex.get("solution_tts", "")
                assert not self.FORBIDDEN_SYMBOLS.search(sol_tts), \
                    f"{concept_id}.examples[{i}].solution_tts contains forbidden symbols"

            # Check misconception correction_tts
            for i, m in enumerate(concept.get("misconceptions", [])):
                corr_tts = m.get("correction_tts", "")
                assert not self.FORBIDDEN_SYMBOLS.search(corr_tts), \
                    f"{concept_id}.misconceptions[{i}].correction_tts contains forbidden symbols"

            # Check question full_solution_tts (hints go through clean_for_tts at runtime)
            for q in concept.get("questions", []):
                q_id = q.get("question_id", "unknown")
                # Note: Regular hints may contain symbols - they go through clean_for_tts() when served
                # Only check _tts fields which should be pre-cleaned
                full_sol = q.get("full_solution_tts", "")
                assert not self.FORBIDDEN_SYMBOLS.search(full_sol), \
                    f"{q_id}.full_solution_tts contains forbidden symbols"


class TestHindiNumerals:
    """Test Hindi/Devanagari answer support."""

    def test_hindi_numeral_in_alternates(self):
        """Some questions accept Hindi numeral answers."""
        bank = get_content_bank()
        questions = bank.get_chapter_questions("math_8_ch6")

        # At least some questions should have Hindi alternates
        hindi_pattern = re.compile(r'[०-९]|इक्यासी|बयासी|तिरासी|चौरासी|पचासी')
        found_hindi = False

        for q in questions:
            alternates = q.get("acceptable_alternates", [])
            for alt in alternates:
                if hindi_pattern.search(str(alt)):
                    found_hindi = True
                    break
            if found_hindi:
                break

        assert found_hindi, "No Hindi numerals found in acceptable_alternates"
