"""
IDNA EdTech v7.3.0 — Curriculum Concept Graph

Structured representation of concepts with:
- Prerequisites for dependency ordering
- Multilingual teaching content (en, hi, hinglish)
- Multiple teaching approaches (definition, indian_example, visual_analogy, real_life)
- Question mappings

This replaces the flat SKILL_LESSONS dict with a proper DAG structure.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Concept:
    """A single teachable concept with multilingual content."""
    id: str                                     # "perfect_square"
    name: str                                   # "Perfect Square"
    name_hi: str                                # "पूर्ण वर्ग"
    prerequisites: list[str] = field(default_factory=list)  # ["multiplication"]
    teaching: dict = field(default_factory=dict)
    # teaching structure:
    # {
    #   "definition": {"en": "...", "hi": "...", "hinglish": "..."},
    #   "indian_example": {"en": "...", "hi": "...", "hinglish": "..."},
    #   "visual_analogy": {"en": "...", "hi": "...", "hinglish": "..."},
    #   "real_life": {"en": "...", "hi": "...", "hinglish": "..."},
    # }
    questions: list[str] = field(default_factory=list)  # Question IDs for this concept
    key_insight: str = ""  # One-liner insight for quick reference


@dataclass
class ChapterGraph:
    """A chapter's concept graph with ordered concepts and utility methods."""
    chapter_id: str
    chapter_name: str
    chapter_name_hi: str
    subject: str
    grade: int
    concepts: list[Concept] = field(default_factory=list)

    def get_concept(self, concept_id: str) -> Optional[Concept]:
        """Get a concept by its ID."""
        return next((c for c in self.concepts if c.id == concept_id), None)

    def get_next_concept(self, current_id: str) -> Optional[Concept]:
        """Get the next concept in sequence after current_id."""
        for i, c in enumerate(self.concepts):
            if c.id == current_id and i + 1 < len(self.concepts):
                return self.concepts[i + 1]
        return None

    def get_first_concept(self) -> Optional[Concept]:
        """Get the first concept in the chapter."""
        return self.concepts[0] if self.concepts else None

    def get_teaching_content(
        self,
        concept_id: str,
        approach: str,
        language: str
    ) -> str:
        """Get teaching content for a concept in a specific approach and language.

        Args:
            concept_id: The concept ID
            approach: One of 'definition', 'indian_example', 'visual_analogy', 'real_life'
            language: One of 'en', 'hi', 'hinglish'

        Returns:
            The teaching content string, or empty string if not found.
            Falls back to hinglish if requested language not available.
        """
        concept = self.get_concept(concept_id)
        if not concept:
            return ""
        content = concept.teaching.get(approach, {})
        return content.get(language, content.get("hinglish", ""))

    def get_questions_for_concept(self, concept_id: str) -> list[str]:
        """Get all question IDs for a concept."""
        concept = self.get_concept(concept_id)
        return concept.questions if concept else []

    def get_concept_for_question(self, question_id: str) -> Optional[Concept]:
        """Find which concept a question belongs to."""
        for concept in self.concepts:
            if question_id in concept.questions:
                return concept
        return None

    def get_all_question_ids(self) -> list[str]:
        """Get all question IDs in teaching order."""
        ids = []
        for concept in self.concepts:
            ids.extend(concept.questions)
        return ids

    def is_concept_complete(self, concept_id: str, answered_questions: set[str]) -> bool:
        """Check if all questions for a concept have been answered."""
        concept = self.get_concept(concept_id)
        if not concept or not concept.questions:
            return True
        return all(q in answered_questions for q in concept.questions)


# Teaching approach rotation order
APPROACH_ORDER = ["definition", "indian_example", "visual_analogy", "real_life"]


def get_next_approach(current_turn: int) -> str:
    """Get the teaching approach for a given turn number."""
    return APPROACH_ORDER[current_turn % len(APPROACH_ORDER)]


def advance_to_next_concept(session, chapter_graph: ChapterGraph) -> str:
    """Advance session to the next concept after mastering current one.

    Args:
        session: Session object with current_concept_id and concept_mastery
        chapter_graph: The chapter's concept graph

    Returns:
        New state: "TEACHING" if there's a next concept, "SESSION_COMPLETE" if done
    """
    # Mark current concept as mastered
    if session.current_concept_id:
        if session.concept_mastery is None:
            session.concept_mastery = {}
        session.concept_mastery[session.current_concept_id] = True

    # Get next concept
    next_concept = chapter_graph.get_next_concept(session.current_concept_id)
    if next_concept is None:
        return "SESSION_COMPLETE"

    # Update session for new concept
    session.current_concept_id = next_concept.id
    session.teaching_turn = 0
    return "TEACHING"
