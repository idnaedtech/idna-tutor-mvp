"""
Tests for skill_graph.py — no circular deps, all skills referenced, structure validity.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skill_graph import SKILLS, get_skills_for_chapter, get_prerequisites, get_skill


# ============================================================
# Test: Basic structure
# ============================================================

def test_skills_not_empty():
    assert len(SKILLS) > 0


def test_all_skills_have_required_fields():
    required = {"skill_id", "display_name", "chapter", "prerequisites", "difficulty_band"}
    for skill_id, skill in SKILLS.items():
        missing = required - set(skill.keys())
        assert not missing, f"Skill {skill_id} missing fields: {missing}"


def test_skill_id_matches_key():
    """The dict key must match the skill_id field."""
    for key, skill in SKILLS.items():
        assert key == skill["skill_id"], f"Key '{key}' != skill_id '{skill['skill_id']}'"


def test_difficulty_band_valid():
    for skill_id, skill in SKILLS.items():
        assert skill["difficulty_band"] in (1, 2, 3), (
            f"Skill {skill_id} has invalid difficulty_band: {skill['difficulty_band']}"
        )


# ============================================================
# Test: No circular dependencies
# ============================================================

def test_no_circular_dependencies():
    """Walk the prerequisite graph and detect cycles via DFS."""
    def has_cycle(skill_id, visited, stack):
        visited.add(skill_id)
        stack.add(skill_id)
        for prereq in SKILLS[skill_id]["prerequisites"]:
            if prereq not in SKILLS:
                continue  # Missing prereq tested separately
            if prereq not in visited:
                if has_cycle(prereq, visited, stack):
                    return True
            elif prereq in stack:
                return True
        stack.discard(skill_id)
        return False

    visited = set()
    for skill_id in SKILLS:
        if skill_id not in visited:
            assert not has_cycle(skill_id, visited, set()), (
                f"Circular dependency detected involving skill: {skill_id}"
            )


# ============================================================
# Test: All prerequisites exist in SKILLS
# ============================================================

def test_all_prerequisites_exist():
    for skill_id, skill in SKILLS.items():
        for prereq in skill["prerequisites"]:
            assert prereq in SKILLS, (
                f"Skill '{skill_id}' has prerequisite '{prereq}' which does not exist in SKILLS"
            )


# ============================================================
# Test: All target_skills in questions exist in SKILLS
# ============================================================

def test_question_target_skills_exist():
    """Every target_skill referenced by enriched questions must exist in the skill graph."""
    from questions import ALL_CHAPTERS

    missing = []
    for chapter_name, questions in ALL_CHAPTERS.items():
        for q in questions:
            target = q.get("target_skill")
            if target and target not in SKILLS:
                missing.append((q.get("id", "?"), target))

    assert not missing, f"Questions reference unknown skills: {missing}"


# ============================================================
# Test: Chapter coverage
# ============================================================

def test_all_expected_chapters_present():
    expected_chapters = {
        "rational_numbers",
        "linear_equations",
        "squares_roots",
        "algebraic_expressions",
        "comparing_quantities",
    }
    actual_chapters = {s["chapter"] for s in SKILLS.values()}
    assert expected_chapters == actual_chapters, (
        f"Expected chapters {expected_chapters}, got {actual_chapters}"
    )


def test_each_chapter_has_skills():
    chapters = {s["chapter"] for s in SKILLS.values()}
    for ch in chapters:
        skills = get_skills_for_chapter(ch)
        assert len(skills) >= 1, f"Chapter '{ch}' has no skills"


# ============================================================
# Test: Helper functions
# ============================================================

def test_get_skill_found():
    skill = get_skill("rn_identify")
    assert skill is not None
    assert skill["display_name"] == "Identify rational numbers"


def test_get_skill_not_found():
    assert get_skill("nonexistent_skill_xyz") is None


def test_get_prerequisites_returns_list():
    prereqs = get_prerequisites("rn_add_same_denom")
    assert isinstance(prereqs, list)
    assert "rn_identify" in prereqs


def test_get_prerequisites_empty_for_root():
    prereqs = get_prerequisites("rn_identify")
    assert prereqs == []


def test_get_prerequisites_nonexistent():
    prereqs = get_prerequisites("nonexistent_skill_xyz")
    assert prereqs == []


def test_get_skills_for_chapter_returns_correct_count():
    rn_skills = get_skills_for_chapter("rational_numbers")
    rn_ids = {s["skill_id"] for s in rn_skills}
    # All rn_ skills should be in rational_numbers chapter
    for skill_id, skill in SKILLS.items():
        if skill["chapter"] == "rational_numbers":
            assert skill_id in rn_ids


def test_get_skills_for_chapter_empty():
    skills = get_skills_for_chapter("nonexistent_chapter")
    assert skills == []


# ============================================================
# Test: No self-referencing prerequisites
# ============================================================

def test_no_self_prerequisites():
    for skill_id, skill in SKILLS.items():
        assert skill_id not in skill["prerequisites"], (
            f"Skill '{skill_id}' lists itself as a prerequisite"
        )


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
