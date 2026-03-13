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
    current_question_id: str = None,
) -> Optional[dict]:
    """
    v10.6.0: Strict question picker with HARD RULES.

    HARD RULES:
    1. MUST filter by current_level (WHERE level = current_level)
    2. MUST exclude current question (WHERE id != current_question_id)
    3. MUST exclude all questions already answered (WHERE id NOT IN asked_question_ids)
    4. If no questions left at current level → advance level up, then down
    5. Log: QUESTION_PICKED with id, level, excluded count
    """
    import random as _random
    import logging
    logger = logging.getLogger(__name__)

    # Build full exclusion list: asked + current
    exclude_ids = list(set(asked_question_ids or []))
    if current_question_id and current_question_id not in exclude_ids:
        exclude_ids.append(current_question_id)

    logger.info(f"QUESTION_PICKER: level={current_level}, excluding={len(exclude_ids)} ids: {exclude_ids}")

    # HARD RULE: Level-aware selection
    if current_level is not None:
        # Step 1: Try unanswered questions at current level
        q_at_level = db.query(Question).filter(
            Question.subject == subject,
            Question.chapter == chapter,
            Question.active == True,
            Question.level == current_level,
        )
        if exclude_ids:
            q_at_level = q_at_level.filter(Question.id.notin_(exclude_ids))
        available = q_at_level.all()
        if available:
            picked = _random.choice(available)
            logger.info(f"QUESTION_PICKED: id={picked.id}, level={picked.level}, excluded={len(exclude_ids)}, pool={len(available)}")
            return _question_to_dict(picked)

        # Step 2: All unanswered exhausted at this level — re-use from same level
        # but still exclude current question to avoid immediate repeat
        all_at_level = db.query(Question).filter(
            Question.subject == subject,
            Question.chapter == chapter,
            Question.active == True,
            Question.level == current_level,
        )
        if current_question_id:
            all_at_level = all_at_level.filter(Question.id != current_question_id)
        reuse_pool = all_at_level.all()
        if reuse_pool:
            picked = _random.choice(reuse_pool)
            logger.info(f"QUESTION_PICKED (reuse): id={picked.id}, level={picked.level}, excluded_current={current_question_id}, pool={len(reuse_pool)}")
            return _question_to_dict(picked)

        # Step 3: No questions at this level at all — try adjacent levels
        logger.warning(f"LEVEL_EMPTY: No questions at level {current_level}, trying adjacent")
        for adj_level in range(current_level + 1, 6):
            adj_q = db.query(Question).filter(
                Question.subject == subject,
                Question.chapter == chapter,
                Question.active == True,
                Question.level == adj_level,
            )
            if exclude_ids:
                adj_q = adj_q.filter(Question.id.notin_(exclude_ids))
            adj_available = adj_q.all()
            if adj_available:
                picked = _random.choice(adj_available)
                logger.info(f"QUESTION_PICKED (adj_up): id={picked.id}, level={picked.level}")
                return _question_to_dict(picked)
        for adj_level in range(current_level - 1, 0, -1):
            adj_q = db.query(Question).filter(
                Question.subject == subject,
                Question.chapter == chapter,
                Question.active == True,
                Question.level == adj_level,
            )
            if exclude_ids:
                adj_q = adj_q.filter(Question.id.notin_(exclude_ids))
            adj_available = adj_q.all()
            if adj_available:
                picked = _random.choice(adj_available)
                logger.info(f"QUESTION_PICKED (adj_down): id={picked.id}, level={picked.level}")
                return _question_to_dict(picked)

        return None  # All questions exhausted

    # Legacy fallback (no level set)
    base_q = db.query(Question).filter(
        Question.subject == subject,
        Question.chapter == chapter,
        Question.active == True,
    )
    if exclude_ids:
        base_q = base_q.filter(Question.id.notin_(exclude_ids))

    q = base_q.order_by(Question.difficulty.asc()).first()
    if q:
        logger.info(f"QUESTION_PICKED (legacy): id={q.id}, level={q.level}")
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
