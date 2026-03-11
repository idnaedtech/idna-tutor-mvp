"""
IDNA EdTech v10.3.1 — Session Review API
CTO dashboard for reviewing student sessions, transcripts, and quality flags.
Auth: simple query param key=idna2026 (temporary, pre-pilot).
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func

from app.database import get_db
from app.models import Student, Session, SessionTurn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/review", tags=["review"])

REVIEW_KEY = "idna2026"


def _check_key(key: str = Query(...)):
    if key != REVIEW_KEY:
        raise HTTPException(status_code=403, detail="Invalid review key")


def _parse_date(date_str: str) -> tuple[datetime, datetime]:
    """Parse date string to start/end of day in UTC."""
    try:
        day = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="Date format must be YYYY-MM-DD")
    return day, day + timedelta(days=1)


def _detect_flags(turns: list[SessionTurn]) -> list[str]:
    """Auto-detect quality issues in a session's turns."""
    flags = []

    # answer_loop: same question_id in 3+ consecutive student turns
    consecutive_q = 0
    last_q = None
    for t in turns:
        if t.speaker == "student" and t.question_id:
            if t.question_id == last_q:
                consecutive_q += 1
            else:
                consecutive_q = 1
                last_q = t.question_id
            if consecutive_q >= 3 and "answer_loop" not in flags:
                flags.append("answer_loop")

    # correct_ignored: verdict=CORRECT but next student turn has same question_id
    for i, t in enumerate(turns):
        if t.speaker == "student" and t.verdict == "CORRECT":
            # Look for next student turn
            for j in range(i + 1, len(turns)):
                if turns[j].speaker == "student":
                    if turns[j].question_id == t.question_id:
                        if "correct_ignored" not in flags:
                            flags.append("correct_ignored")
                    break

    # comfort_loop: 3+ consecutive COMFORT state turns
    consecutive_comfort = 0
    for t in turns:
        if "COMFORT" in (t.state_before or "") or "COMFORT" in (t.state_after or ""):
            consecutive_comfort += 1
        else:
            consecutive_comfort = 0
        if consecutive_comfort >= 3 and "comfort_loop" not in flags:
            flags.append("comfort_loop")

    # meta_ignored: META_QUESTION category but response doesn't contain chapter info
    for i, t in enumerate(turns):
        if t.input_category == "META_QUESTION":
            # Find next didi turn
            for j in range(i + 1, len(turns)):
                if turns[j].speaker == "didi" and turns[j].didi_response:
                    resp_lower = turns[j].didi_response.lower()
                    if "chapter" not in resp_lower and "squares" not in resp_lower and "cubes" not in resp_lower:
                        if "meta_ignored" not in flags:
                            flags.append("meta_ignored")
                    break

    return flags


# ─── Daily Summary ──────────────────────────────────────────────────────────

@router.get("/daily")
def daily_summary(
    date: str = Query(default=None),
    key: str = Query(...),
    db: DBSession = Depends(get_db),
):
    _check_key(key)
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    day_start, day_end = _parse_date(date)

    sessions = (
        db.query(Session)
        .filter(Session.started_at >= day_start, Session.started_at < day_end)
        .all()
    )

    # Filter real sessions (at least 1 question attempted)
    real_sessions = [s for s in sessions if s.questions_attempted > 0]
    student_ids = set(s.student_id for s in sessions)

    # Per-student breakdown
    by_student = []
    for sid in student_ids:
        student = db.query(Student).filter(Student.id == sid).first()
        if not student:
            continue
        student_sessions = [s for s in sessions if s.student_id == sid]
        by_student.append({
            "pin": student.pin,
            "name": student.name,
            "sessions_today": len(student_sessions),
            "questions_correct": sum(s.questions_correct for s in student_sessions),
            "questions_attempted": sum(s.questions_attempted for s in student_sessions),
        })

    total_attempted = sum(s.questions_attempted for s in sessions)
    total_correct = sum(s.questions_correct for s in sessions)

    # Avg duration
    durations = []
    for s in real_sessions:
        if s.ended_at and s.started_at:
            dur = (s.ended_at - s.started_at).total_seconds()
            if dur > 0:
                durations.append(dur)

    # Quality flags across all sessions
    answer_loops = 0
    correct_ignored = 0
    for s in real_sessions:
        flags = _detect_flags(s.turns)
        if "answer_loop" in flags:
            answer_loops += 1
        if "correct_ignored" in flags:
            correct_ignored += 1

    quality_score = 1.0
    if len(real_sessions) > 0:
        quality_score = max(0, 1.0 - (answer_loops + correct_ignored) / len(real_sessions))

    return {
        "date": date,
        "students_active": len(student_ids),
        "total_sessions": len(sessions),
        "real_sessions": len(real_sessions),
        "avg_duration_seconds": round(sum(durations) / len(durations)) if durations else 0,
        "avg_questions_attempted": round(total_attempted / len(real_sessions), 1) if real_sessions else 0,
        "total_questions_correct": total_correct,
        "total_questions_attempted": total_attempted,
        "interaction_quality": {
            "answer_loops": answer_loops,
            "correct_ignored": correct_ignored,
            "quality_score": round(quality_score, 2),
        },
        "by_student": by_student,
    }


# ─── Session List ───────────────────────────────────────────────────────────

@router.get("/sessions")
def session_list(
    date: str = Query(default=None),
    key: str = Query(...),
    db: DBSession = Depends(get_db),
):
    _check_key(key)
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    day_start, day_end = _parse_date(date)

    sessions = (
        db.query(Session)
        .filter(Session.started_at >= day_start, Session.started_at < day_end)
        .order_by(Session.started_at.desc())
        .all()
    )

    result = []
    for s in sessions:
        student = db.query(Student).filter(Student.id == s.student_id).first()
        flags = _detect_flags(s.turns)
        duration = 0
        if s.ended_at and s.started_at:
            duration = int((s.ended_at - s.started_at).total_seconds())

        result.append({
            "session_id": s.id,
            "student_name": student.name if student else "Unknown",
            "student_pin": student.pin if student else "?",
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "duration_seconds": duration,
            "questions_attempted": s.questions_attempted,
            "questions_correct": s.questions_correct,
            "total_turns": len(s.turns),
            "flags": flags,
        })

    return {"sessions": result}


# ─── Transcript ─────────────────────────────────────────────────────────────

@router.get("/transcript/{session_id}")
def session_transcript(
    session_id: str,
    key: str = Query(...),
    db: DBSession = Depends(get_db),
):
    _check_key(key)
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    student = db.query(Student).filter(Student.id == session.student_id).first()

    turns = []
    for t in session.turns:
        text = t.didi_response if t.speaker == "didi" else t.transcript
        timestamp = t.created_at.strftime("%H:%M:%S") if t.created_at else ""
        turns.append({
            "turn_number": t.turn_number,
            "speaker": t.speaker,
            "text": text or "",
            "timestamp": timestamp,
            "state": t.state_after or t.state_before or "",
            "classified_as": t.input_category,
            "question_id": t.question_id,
            "verdict": t.verdict,
        })

    return {
        "session_id": session_id,
        "student_name": student.name if student else "Unknown",
        "turns": turns,
    }


# ─── HTML Dashboard ─────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
def review_dashboard(key: str = Query(...)):
    _check_key(key)
    return DASHBOARD_HTML.replace("__REVIEW_KEY__", REVIEW_KEY)


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IDNA Review Dashboard</title>
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; padding: 20px; }
    h1 { margin-bottom: 10px; }
    .summary { background: #fff; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .summary .stats { display: flex; gap: 20px; flex-wrap: wrap; margin-top: 10px; }
    .stat { background: #f0f4ff; padding: 12px 16px; border-radius: 6px; min-width: 120px; }
    .stat .label { font-size: 12px; color: #666; }
    .stat .value { font-size: 24px; font-weight: bold; color: #2563eb; }
    .quality { margin-top: 10px; }
    .quality .bad { color: #dc2626; font-weight: bold; }
    .sessions { background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #eee; font-size: 14px; }
    th { background: #f8f9fa; font-weight: 600; }
    tr:hover { background: #f0f4ff; cursor: pointer; }
    .flag { background: #fef2f2; color: #dc2626; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-right: 4px; }
    .transcript { background: #fff; border-radius: 8px; padding: 20px; margin-top: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); display: none; }
    .turn { padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
    .turn.student { padding-left: 20px; }
    .turn .speaker { font-weight: bold; font-size: 12px; }
    .turn .speaker.didi { color: #2563eb; }
    .turn .speaker.student { color: #059669; }
    .turn .text { margin-top: 2px; }
    .turn .meta { font-size: 11px; color: #999; font-family: monospace; margin-top: 2px; }
    .back-btn { background: #2563eb; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; margin-bottom: 10px; }
    .date-input { padding: 6px 10px; border: 1px solid #ddd; border-radius: 4px; margin-left: 10px; }
    .date-btn { padding: 6px 12px; background: #2563eb; color: #fff; border: none; border-radius: 4px; cursor: pointer; margin-left: 5px; }
</style>
</head>
<body>
<h1>IDNA Review Dashboard</h1>
<div>
    <label>Date:</label>
    <input type="date" id="dateInput" class="date-input">
    <button onclick="loadDate()" class="date-btn">Load</button>
</div>

<div class="summary" id="summarySection">Loading...</div>

<div class="sessions" id="sessionsSection">
    <h2>Sessions</h2>
    <table id="sessionsTable"><thead><tr><th>Student</th><th>PIN</th><th>Started</th><th>Duration</th><th>Q</th><th>Correct</th><th>Turns</th><th>Flags</th></tr></thead><tbody></tbody></table>
</div>

<div class="transcript" id="transcriptSection">
    <button class="back-btn" onclick="hideTranscript()">Back to Sessions</button>
    <h2 id="transcriptTitle">Transcript</h2>
    <div id="transcriptBody"></div>
</div>

<script>
const KEY = '__REVIEW_KEY__';
const API = window.location.origin;

document.getElementById('dateInput').value = new Date().toISOString().split('T')[0];
loadDate();

function loadDate() {
    const date = document.getElementById('dateInput').value;
    loadSummary(date);
    loadSessions(date);
}

async function loadSummary(date) {
    try {
        const resp = await fetch(`${API}/api/review/daily?key=${KEY}&date=${date}`);
        const d = await resp.json();
        document.getElementById('summarySection').innerHTML = `
            <h2>Daily Summary — ${d.date}</h2>
            <div class="stats">
                <div class="stat"><div class="label">Students</div><div class="value">${d.students_active}</div></div>
                <div class="stat"><div class="label">Sessions</div><div class="value">${d.real_sessions}/${d.total_sessions}</div></div>
                <div class="stat"><div class="label">Avg Duration</div><div class="value">${Math.round(d.avg_duration_seconds/60)}m</div></div>
                <div class="stat"><div class="label">Avg Questions</div><div class="value">${d.avg_questions_attempted}</div></div>
                <div class="stat"><div class="label">Accuracy</div><div class="value">${d.total_questions_attempted ? Math.round(d.total_questions_correct/d.total_questions_attempted*100) : 0}%</div></div>
            </div>
            <div class="quality">
                Quality Score: <b>${d.interaction_quality.quality_score}</b>
                ${d.interaction_quality.answer_loops ? '<span class="bad"> | Answer Loops: ' + d.interaction_quality.answer_loops + '</span>' : ''}
                ${d.interaction_quality.correct_ignored ? '<span class="bad"> | Correct Ignored: ' + d.interaction_quality.correct_ignored + '</span>' : ''}
            </div>`;
    } catch(e) { document.getElementById('summarySection').textContent = 'Error loading summary'; }
}

async function loadSessions(date) {
    try {
        const resp = await fetch(`${API}/api/review/sessions?key=${KEY}&date=${date}`);
        const d = await resp.json();
        const tbody = document.querySelector('#sessionsTable tbody');
        tbody.innerHTML = '';
        for (const s of d.sessions) {
            const tr = document.createElement('tr');
            tr.onclick = () => loadTranscript(s.session_id, s.student_name);
            const time = s.started_at ? new Date(s.started_at).toLocaleTimeString() : '?';
            const dur = s.duration_seconds > 0 ? Math.round(s.duration_seconds/60) + 'm' : '-';
            const flags = s.flags.map(f => `<span class="flag">${f}</span>`).join('');
            tr.innerHTML = `<td>${s.student_name}</td><td>${s.student_pin}</td><td>${time}</td><td>${dur}</td><td>${s.questions_attempted}</td><td>${s.questions_correct}</td><td>${s.total_turns}</td><td>${flags}</td>`;
            tbody.appendChild(tr);
        }
    } catch(e) { console.error('Error loading sessions:', e); }
}

async function loadTranscript(sessionId, name) {
    try {
        const resp = await fetch(`${API}/api/review/transcript/${sessionId}?key=${KEY}`);
        const d = await resp.json();
        document.getElementById('transcriptTitle').textContent = `Transcript — ${name}`;
        const body = document.getElementById('transcriptBody');
        body.innerHTML = '';
        for (const t of d.turns) {
            const div = document.createElement('div');
            div.className = `turn ${t.speaker}`;
            const meta = [t.timestamp, t.state, t.classified_as, t.verdict, t.question_id ? 'q:' + t.question_id.substring(0,8) : ''].filter(Boolean).join(' | ');
            div.innerHTML = `<div class="speaker ${t.speaker}">${t.speaker === 'didi' ? 'Didi' : 'Student'}</div><div class="text">${t.text}</div><div class="meta">[${meta}]</div>`;
            body.appendChild(div);
        }
        document.getElementById('sessionsSection').style.display = 'none';
        document.getElementById('transcriptSection').style.display = 'block';
    } catch(e) { console.error('Error loading transcript:', e); }
}

function hideTranscript() {
    document.getElementById('sessionsSection').style.display = 'block';
    document.getElementById('transcriptSection').style.display = 'none';
}
</script>
</body>
</html>"""
