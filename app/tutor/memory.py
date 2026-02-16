"""
IDNA EdTech v7.0 — Memory (Skill Mastery Read/Write)
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
) -> Optional[dict]:
    """
    Pick the next question adaptively.
    
    Strategy:
    1. Check parent instructions (e.g., "focus on fractions")
    2. Find skills with lowest mastery
    3. Pick a question for that skill not already asked this session
    4. If all questions asked, return None (session complete)
    """
    # Check for parent instructions
    parent_instruction = (
        db.query(ParentInstruction)
        .filter(
            ParentInstruction.student_id == student_id,
            ParentInstruction.fulfilled == False,
        )
        .order_by(ParentInstruction.created_at.desc())
        .first()
    )

    # Build base query — active questions for this chapter
    base_q = db.query(Question).filter(
        Question.subject == subject,
        Question.chapter == chapter,
        Question.active == True,
    )

    # Exclude already-asked questions
    if asked_question_ids:
        base_q = base_q.filter(Question.id.notin_(asked_question_ids))

    # If parent instruction exists, try to match skill
    if parent_instruction and parent_instruction.instruction:
        instruction_text = parent_instruction.instruction.lower()
        # Try to find questions matching the instruction topic
        matching = base_q.filter(
            Question.target_skill.ilike(f"%{instruction_text.split()[0]}%")
        ).first()
        if matching:
            # Mark instruction as fulfilled
            parent_instruction.fulfilled = True
            db.commit()
            return _question_to_dict(matching)

    # Adaptive: find weakest skill, then pick question for it
    weakest = get_weakest_skill(db, student_id, subject)
    if weakest:
        q = base_q.filter(Question.target_skill == weakest).first()
        if q:
            return _question_to_dict(q)

    # Difficulty preference (after max reteach → pick easy)
    if difficulty_preference == "easy":
        q = base_q.filter(Question.difficulty <= 2).first()
        if q:
            return _question_to_dict(q)

    # Default: next available question, lowest difficulty first
    q = base_q.order_by(Question.difficulty.asc()).first()
    if q:
        return _question_to_dict(q)

    return None  # All questions asked


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
