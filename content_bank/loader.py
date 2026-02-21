"""
IDNA Content Bank Loader — Singleton pattern for O(1) concept/question lookup.
Loads all JSON content banks from content_bank/ directory.
"""

import json
import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

_instance: Optional["ContentBank"] = None


def get_content_bank() -> "ContentBank":
    """Get singleton ContentBank instance."""
    global _instance
    if _instance is None:
        _instance = ContentBank()
    return _instance


class ContentBank:
    """
    Loads and indexes all content bank JSON files for O(1) lookup.

    Usage:
        bank = get_content_bank()
        definition = bank.get_definition_tts("math_8_ch6_perfect_square")
        questions = bank.get_questions("math_8_ch6_perfect_square", level="easy")
    """

    def __init__(self, content_dir: str = None):
        if content_dir is None:
            content_dir = Path(__file__).parent
        else:
            content_dir = Path(content_dir)

        self._concepts: Dict[str, Dict] = {}  # concept_id → concept data
        self._questions: Dict[str, Dict] = {}  # question_id → question data
        self._chapters: Dict[str, Dict] = {}  # chapter_key → chapter meta + concepts

        self._load_all(content_dir)

    def _load_all(self, content_dir: Path):
        """Load all JSON files from content directory."""
        for json_file in content_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Extract chapter key from filename (e.g., math_8_ch6.json → math_8_ch6)
                chapter_key = json_file.stem

                # Store chapter metadata
                chapter_meta = data.get("chapter_meta", {})
                self._chapters[chapter_key] = {
                    "meta": chapter_meta,
                    "skill_progression": chapter_meta.get("skill_progression", []),
                    "concepts": [],
                }

                # Index concepts
                for concept in data.get("concepts", []):
                    concept_id = concept.get("concept_id")
                    if concept_id:
                        self._concepts[concept_id] = concept
                        self._chapters[chapter_key]["concepts"].append(concept_id)

                        # Index questions within concept
                        for q in concept.get("questions", []):
                            q_id = q.get("question_id")
                            if q_id:
                                q["concept_id"] = concept_id
                                q["chapter"] = chapter_key
                                q["target_skill"] = concept_id
                                self._questions[q_id] = q

                logger.info(f"Loaded content bank: {json_file.name} ({len(data.get('concepts', []))} concepts)")

            except Exception as e:
                logger.error(f"Failed to load content bank {json_file}: {e}")

    # ─── Concept Methods ─────────────────────────────────────────────────────

    def get_concept(self, concept_id: str) -> Optional[Dict]:
        """Get full concept data by ID."""
        return self._concepts.get(concept_id)

    def get_definition_tts(self, concept_id: str) -> Optional[str]:
        """Get TTS-safe definition for a concept."""
        concept = self._concepts.get(concept_id)
        if concept:
            return concept.get("definition_tts") or concept.get("definition")
        return None

    def get_teaching_hook(self, concept_id: str) -> Optional[str]:
        """Get teaching methodology hook for a concept."""
        concept = self._concepts.get(concept_id)
        if concept:
            methodology = concept.get("teaching_methodology", {})
            return methodology.get("hook")
        return None

    def get_teaching_analogy(self, concept_id: str) -> Optional[str]:
        """Get teaching analogy for a concept."""
        concept = self._concepts.get(concept_id)
        if concept:
            methodology = concept.get("teaching_methodology", {})
            return methodology.get("analogy")
        return None

    def get_teaching_methodology(self, concept_id: str) -> Optional[Dict]:
        """Get full teaching methodology for a concept."""
        concept = self._concepts.get(concept_id)
        if concept:
            return concept.get("teaching_methodology")
        return None

    # ─── Example Methods ─────────────────────────────────────────────────────

    def get_examples(self, concept_id: str, level: str = None) -> List[Dict]:
        """Get examples for a concept, optionally filtered by level."""
        concept = self._concepts.get(concept_id)
        if not concept:
            return []

        examples = concept.get("examples", [])
        if level:
            return [e for e in examples if e.get("level") == level]
        return examples

    # ─── Misconception Methods ───────────────────────────────────────────────

    def get_misconceptions(self, concept_id: str) -> List[Dict]:
        """Get common misconceptions for a concept."""
        concept = self._concepts.get(concept_id)
        if concept:
            return concept.get("misconceptions", [])
        return []

    def match_misconception(self, concept_id: str, student_answer: str) -> Optional[Dict]:
        """Check if student answer matches a known misconception pattern."""
        misconceptions = self.get_misconceptions(concept_id)
        student_lower = student_answer.lower().strip()

        for m in misconceptions:
            # Check if the misconception has trigger patterns
            triggers = m.get("trigger_patterns", [])
            for trigger in triggers:
                if trigger.lower() in student_lower:
                    return m
        return None

    # ─── Question Methods ────────────────────────────────────────────────────

    def get_questions(self, concept_id: str, level: str = None) -> List[Dict]:
        """Get questions for a concept, optionally filtered by level."""
        concept = self._concepts.get(concept_id)
        if not concept:
            return []

        questions = concept.get("questions", [])
        if level:
            return [q for q in questions if q.get("level") == level]
        return questions

    def get_question_by_id(self, question_id: str) -> Optional[Dict]:
        """Get a question by its unique ID."""
        return self._questions.get(question_id)

    def get_hints(self, question_id: str) -> List[str]:
        """Get hints for a question."""
        question = self._questions.get(question_id)
        if question:
            return question.get("hints", [])
        return []

    def get_full_solution_tts(self, question_id: str) -> Optional[str]:
        """Get TTS-safe full solution for a question."""
        question = self._questions.get(question_id)
        if question:
            return question.get("full_solution_tts")
        return None

    def get_acceptable_answers(self, question_id: str) -> List[str]:
        """Get all acceptable answers for a question (expected + alternates)."""
        question = self._questions.get(question_id)
        if not question:
            return []

        expected = question.get("expected_answer", "")
        alternates = question.get("acceptable_alternates", [])

        if expected:
            return [expected] + alternates
        return alternates

    # ─── Chapter/Progression Methods ─────────────────────────────────────────

    def get_chapter_concepts(self, chapter_key: str) -> List[Dict]:
        """Get all concepts for a chapter, ordered by skill progression."""
        chapter = self._chapters.get(chapter_key)
        if not chapter:
            return []

        # Return concepts in skill_progression order
        progression = chapter.get("skill_progression", [])
        concepts = []
        for concept_id in progression:
            concept = self._concepts.get(concept_id)
            if concept:
                concepts.append(concept)

        # Add any concepts not in progression
        for concept_id in chapter.get("concepts", []):
            if concept_id not in progression:
                concept = self._concepts.get(concept_id)
                if concept:
                    concepts.append(concept)

        return concepts

    def get_next_concept(self, current_concept_id: str) -> Optional[str]:
        """Get the next concept in skill progression."""
        # Find which chapter this concept belongs to
        for chapter_key, chapter in self._chapters.items():
            progression = chapter.get("skill_progression", [])
            if current_concept_id in progression:
                idx = progression.index(current_concept_id)
                if idx + 1 < len(progression):
                    return progression[idx + 1]
        return None

    def get_chapter_questions(self, chapter_key: str) -> List[Dict]:
        """Get all questions for a chapter, ordered by skill progression and difficulty."""
        concepts = self.get_chapter_concepts(chapter_key)
        questions = []

        for concept in concepts:
            concept_id = concept.get("concept_id")
            for level in ["easy", "medium", "hard"]:
                for q in self.get_questions(concept_id, level):
                    questions.append(q)

        return questions

    # ─── Stats ───────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, int]:
        """Get content bank statistics."""
        return {
            "chapters": len(self._chapters),
            "concepts": len(self._concepts),
            "questions": len(self._questions),
        }
