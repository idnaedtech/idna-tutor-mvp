"""
IDNA EdTech v7.3 — Memory (Skill Mastery Read/Write)
Updates student's long-term skill data after every answer evaluation.
Also reads data for adaptive question selection and parent reports.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session as DBSession

from app.models import SkillMastery, Question, Session, ParentInstruction


# ─── Read ────────────────────────────────────────────────────────────────────

def get_student_skills(db: DBSession, student_id: str, subject: str = None) -> list[dict]:
    """Get all skill mastery records for a student, optionally filtered by subject."""
    query = db.query(SkillMastery).filter(SkillMastery.student_id == student_id)
    if subject:
        query = query.filter(SkillMastery.subject == subject)
    rows = query.all()
    return [
        {
            "skill_key": r.skill_key,
            "subject": r.subject,
            "mastery_score": r.mastery_score,
            "attempts": r.attempts,
            "correct": r.correct,
            "last_attempted": r.last_attempted,
            "teaching_notes": r.teaching_notes,
        }
        for r in rows
    ]


def get_skill(db: DBSession, student_id: str, skill_key: str) -> Optional[dict]:
    """Get mastery for a specific skill."""
    row = (
        db.query(SkillMastery)
        .filter(SkillMastery.student_id == student_id, SkillMastery.skill_key == skill_key)
        .first()
    )
    if not row:
        return None
    return {
        "skill_key": row.skill_key,
        "subject": row.subject,
        "mastery_score": row.mastery_score,
        "attempts": row.attempts,
        "correct": row.correct,
        "teaching_notes": row.teaching_notes,
    }


def get_weakest_skill(db: DBSession, student_id: str, subject: str = "math") -> Optional[str]:
    """Get the skill_key with lowest mastery (for topic discovery fallback)."""
    row = (
        db.query(SkillMastery)
        .filter(
            SkillMastery.student_id == student_id,
            SkillMastery.subject == subject,
            SkillMastery.mastery_score < 0.8,
        )
        .order_by(SkillMastery.mastery_score.asc())
        .first()
    )
    return row.skill_key if row else None


# ─── Write ───────────────────────────────────────────────────────────────────

def update_skill(
    db: DBSession,
    student_id: str,
    subject: str,
    skill_key: str,
    correct: bool,
    teaching_note: Optional[str] = None,
):
    """
    Update skill mastery after an answer evaluation.
    Creates the row if it doesn't exist.
    
    Mastery formula: exponential moving average
    new_score = old_score * 0.7 + (1.0 if correct else 0.0) * 0.3
    
    This weights recent performance more heavily while preserving history.
    """
    row = (
        db.query(SkillMastery)
        .filter(SkillMastery.student_id == student_id, SkillMastery.skill_key == skill_key)
        .first()
    )

    if not row:
        row = SkillMastery(
            student_id=student_id,
            subject=subject,
            skill_key=skill_key,
            mastery_score=0.0,
            attempts=0,
            correct=0,
        )
        db.add(row)

    row.attempts += 1
    if correct:
        row.correct += 1

    # Exponential moving average
    score_input = 1.0 if correct else 0.0
    row.mastery_score = row.mastery_score * 0.7 + score_input * 0.3

    row.last_attempted = datetime.now(timezone.utc)

    if teaching_note and teaching_note.strip():
        if row.teaching_notes:
            row.teaching_notes += f" | {teaching_note}"
        else:
            row.teaching_notes = teaching_note

    db.commit()


# ─── Question Selection ──────────────────────────────────────────────────────

def pick_next_question(
    db: DBSession,
    student_id: str,
    subject: str,
    chapter: str,
    asked_question_ids: list[str],
    difficulty_preference: Optional[str] = None,
    current_level: int = None,
) -> Optional[dict]:
    """
    v10.4.0: Level-aware question picker.

    Strategy:
    1. If current_level is set, pick from that level only
    2. Exclude already-asked questions
    3. If no questions at current level, advance to next level
    4. Falls back to old behavior if current_level is None
    """
    import random as _random

    # Build base query — active questions for this chapter
    base_q = db.query(Question).filter(
        Question.subject == subject,
        Question.chapter == chapter,
        Question.active == True,
    )

    # Exclude already-asked questions
    if asked_question_ids:
        base_q = base_q.filter(Question.id.notin_(asked_question_ids))

    # v10.4.0: Level-aware selection
    if current_level is not None:
        level_q = base_q.filter(Question.level == current_level)
        available = level_q.all()
        if available:
            return _question_to_dict(_random.choice(available))

        # No questions at current level — try next level up
        for next_level in range(current_level + 1, 6):
            level_q = base_q.filter(Question.level == next_level)
            available = level_q.all()
            if available:
                return _question_to_dict(_random.choice(available))

        # Try lower levels as last resort
        for prev_level in range(current_level - 1, 0, -1):
            level_q = base_q.filter(Question.level == prev_level)
            available = level_q.all()
            if available:
                return _question_to_dict(_random.choice(available))

        return None  # All questions exhausted

    # Legacy fallback: Check parent instructions, then weakest skill
    parent_instruction = (
        db.query(ParentInstruction)
        .filter(
            ParentInstruction.student_id == student_id,
            ParentInstruction.fulfilled == False,
        )
        .order_by(ParentInstruction.created_at.desc())
        .first()
    )

    if parent_instruction and parent_instruction.instruction:
        instruction_text = parent_instruction.instruction.lower().strip()
        matching = None
        if instruction_text:
            words = instruction_text.split()
            if words:
                matching = base_q.filter(
                    Question.target_skill.ilike(f"%{words[0]}%")
                ).first()
        if matching:
            parent_instruction.fulfilled = True
            db.commit()
            return _question_to_dict(matching)

    weakest = get_weakest_skill(db, student_id, subject)
    if weakest:
        q = base_q.filter(Question.target_skill == weakest).first()
        if q:
            return _question_to_dict(q)

    if difficulty_preference == "easy":
        q = base_q.filter(Question.difficulty <= 2).first()
        if q:
            return _question_to_dict(q)

    q = base_q.order_by(Question.difficulty.asc()).first()
    if q:
        return _question_to_dict(q)

    return None


def _question_to_dict(q: Question) -> dict:
    return {
        "id": q.id,
        "subject": q.subject,
        "chapter": q.chapter,
        "question_type": q.question_type,
        "question_text": q.question_text,
        "question_voice": q.question_voice,
        "answer": q.answer,
        "answer_variants": q.answer_variants or [],
        "key_concepts": q.key_concepts or [],
        "eval_method": q.eval_method,
        "hints": q.hints or [],
        "solution": q.solution or "",
        "target_skill": q.target_skill,
        "difficulty": q.difficulty,
        "level": getattr(q, 'level', 3),
    }


# ─── Session Stats (for parent reports) ──────────────────────────────────────

def get_student_summary(db: DBSession, student_id: str, days: int = 7) -> dict:
    """Get a summary of student activity for parent reporting."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    sessions = (
        db.query(Session)
        .filter(
            Session.student_id == student_id,
            Session.session_type == "student",
            Session.started_at >= cutoff,
        )
        .all()
    )

    total_sessions = len(sessions)
    total_questions = sum(s.questions_attempted for s in sessions)
    total_correct = sum(s.questions_correct for s in sessions)
    total_hints = sum(s.total_hints_used for s in sessions)

    skills = get_student_skills(db, student_id)
    weak_skills = [s for s in skills if s["mastery_score"] < 0.5]
    strong_skills = [s for s in skills if s["mastery_score"] >= 0.8]

    accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0

    return {
        "days": days,
        "total_sessions": total_sessions,
        "total_questions": total_questions,
        "total_correct": total_correct,
        "total_hints": total_hints,
        "accuracy_pct": round(accuracy, 1),
        "weak_skills": [s["skill_key"] for s in weak_skills],
        "strong_skills": [s["skill_key"] for s in strong_skills],
    }
