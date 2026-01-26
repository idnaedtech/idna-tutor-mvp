"""
IDNA EdTech - FastAPI Backend (v2)
RESTful API for student management, sessions, and parent dashboard.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import json

from models import (
    Database, Student, LearningSession, TopicProgress, 
    ParentReport, Language, Subject
)

app = FastAPI(
    title="IDNA EdTech API",
    description="Voice-based AI Tutor for K-10 Students in India",
    version="2.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database instance
db = Database("idna_edtech.db")
db.initialize()


# Pydantic models for API
class StudentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    age: int = Field(..., ge=5, le=18)
    grade: int = Field(..., ge=1, le=10)
    preferred_language: str = "en"
    secondary_language: Optional[str] = None
    parent_phone: str = Field(..., pattern=r'^\+?[0-9]{10,15}$')
    parent_name: str = Field(..., min_length=2, max_length=100)
    school_name: Optional[str] = None
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    learning_pace: str = "normal"
    voice_preference: str = "female"
    session_duration_minutes: int = 30


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    grade: Optional[int] = None
    preferred_language: Optional[str] = None
    learning_pace: Optional[str] = None
    voice_preference: Optional[str] = None
    session_duration_minutes: Optional[int] = None
    current_subject: Optional[str] = None
    current_topic: Optional[str] = None
    current_difficulty: Optional[int] = None


class SessionCreate(BaseModel):
    student_id: int
    subject: str
    topic: str
    difficulty_level: int = 2


class SessionEnd(BaseModel):
    duration_seconds: int
    questions_asked: int
    correct_answers: int
    hints_used: int = 0
    engagement_score: float = 0.5
    frustration_indicators: int = 0
    celebration_moments: int = 0
    transcript: str = "[]"
    voice_interactions: int = 0


class ProgressUpdate(BaseModel):
    student_id: int
    subject: str
    topic: str
    mastery_level: float
    time_spent_seconds: int
    common_mistakes: str = "[]"


# ==================== STUDENT ENDPOINTS ====================

@app.post("/api/students", response_model=dict)
async def create_student(student: StudentCreate):
    """Register a new student."""
    try:
        student_obj = Student(
            name=student.name,
            age=student.age,
            grade=student.grade,
            preferred_language=student.preferred_language,
            secondary_language=student.secondary_language,
            parent_phone=student.parent_phone,
            parent_name=student.parent_name,
            school_name=student.school_name,
            city=student.city,
            state=student.state,
            learning_pace=student.learning_pace,
            voice_preference=student.voice_preference,
            session_duration_minutes=student.session_duration_minutes
        )
        student_id = db.create_student(student_obj)
        return {"success": True, "student_id": student_id, "message": "Student registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/students/{student_id}")
async def get_student(student_id: int):
    """Get student details."""
    student = db.get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"success": True, "student": student.__dict__}


@app.get("/api/students")
async def get_students_by_parent(phone: str = Query(..., description="Parent phone number")):
    """Get all students for a parent."""
    students = db.get_students_by_parent_phone(phone)
    return {"success": True, "students": [s.__dict__ for s in students]}


@app.put("/api/students/{student_id}")
async def update_student(student_id: int, updates: StudentUpdate):
    """Update student details."""
    student = db.get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Apply updates
    for field, value in updates.dict(exclude_none=True).items():
        setattr(student, field, value)
    
    db.update_student(student)
    return {"success": True, "message": "Student updated successfully"}


# ==================== SESSION ENDPOINTS ====================

@app.post("/api/sessions")
async def start_session(session: SessionCreate):
    """Start a new learning session."""
    student = db.get_student(session.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    session_obj = LearningSession(
        student_id=session.student_id,
        subject=session.subject,
        topic=session.topic,
        difficulty_level=session.difficulty_level
    )
    session_id = db.create_session(session_obj)
    
    # Update student's current progress
    student.current_subject = session.subject
    student.current_topic = session.topic
    student.current_difficulty = session.difficulty_level
    db.update_student(student)
    
    return {"success": True, "session_id": session_id}


@app.put("/api/sessions/{session_id}/end")
async def end_session(session_id: int, data: SessionEnd):
    """End a learning session."""
    session = LearningSession(
        duration_seconds=data.duration_seconds,
        questions_asked=data.questions_asked,
        correct_answers=data.correct_answers,
        hints_used=data.hints_used,
        engagement_score=data.engagement_score,
        frustration_indicators=data.frustration_indicators,
        celebration_moments=data.celebration_moments,
        transcript=data.transcript,
        voice_interactions=data.voice_interactions
    )
    
    success = db.end_session(session_id, session)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"success": True, "message": "Session ended successfully"}


@app.get("/api/students/{student_id}/sessions")
async def get_student_sessions(student_id: int, limit: int = 10):
    """Get recent sessions for a student."""
    sessions = db.get_student_sessions(student_id, limit)
    return {"success": True, "sessions": [s.__dict__ for s in sessions]}


# ==================== PROGRESS ENDPOINTS ====================

@app.post("/api/progress")
async def update_progress(progress: ProgressUpdate):
    """Update topic progress."""
    progress_obj = TopicProgress(
        student_id=progress.student_id,
        subject=progress.subject,
        topic=progress.topic,
        mastery_level=progress.mastery_level,
        time_spent_seconds=progress.time_spent_seconds,
        common_mistakes=progress.common_mistakes
    )
    db.update_topic_progress(progress_obj)
    return {"success": True, "message": "Progress updated"}


@app.get("/api/students/{student_id}/progress")
async def get_student_progress(student_id: int, subject: Optional[str] = None):
    """Get progress for a student."""
    progress = db.get_student_progress(student_id, subject)
    return {"success": True, "progress": [p.__dict__ for p in progress]}


# ==================== PARENT DASHBOARD ENDPOINTS ====================

@app.get("/api/dashboard/{student_id}")
async def get_dashboard(student_id: int):
    """Get parent dashboard data for a student."""
    student = db.get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    dashboard = db.get_student_dashboard_data(student_id)
    
    return {
        "success": True,
        "student": {
            "id": student.id,
            "name": student.name,
            "age": student.age,
            "grade": student.grade,
            "current_subject": student.current_subject,
            "current_topic": student.current_topic
        },
        "dashboard": dashboard
    }


@app.get("/api/dashboard/parent/{phone}")
async def get_parent_dashboard(phone: str):
    """Get dashboard data for all children of a parent."""
    students = db.get_students_by_parent_phone(phone)
    if not students:
        raise HTTPException(status_code=404, detail="No students found for this phone number")
    
    children_data = []
    for student in students:
        dashboard = db.get_student_dashboard_data(student.id)
        children_data.append({
            "student": {
                "id": student.id,
                "name": student.name,
                "age": student.age,
                "grade": student.grade,
                "current_subject": student.current_subject
            },
            "dashboard": dashboard
        })
    
    return {"success": True, "children": children_data}


# ==================== REPORT ENDPOINTS ====================

@app.post("/api/reports/{student_id}/generate")
async def generate_report(student_id: int, report_type: str = "daily"):
    """Generate a parent report for a student."""
    student = db.get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    dashboard = db.get_student_dashboard_data(student_id)
    
    # Generate voice message text (emotionally resonant)
    accuracy = dashboard['average_accuracy']
    time_mins = dashboard['total_study_time_minutes']
    mastered_count = len(dashboard['topics_mastered'])
    
    # Emotional transformation narrative
    if accuracy >= 80:
        emotional_tone = "proud and confident"
        message = f"Namaste! I'm so happy to share that {student.name} is doing wonderfully! "
        message += f"This week, they studied for {time_mins} minutes and achieved {accuracy}% accuracy. "
        message += f"They've mastered {mastered_count} topics! You should be very proud of their progress."
    elif accuracy >= 60:
        emotional_tone = "encouraging and hopeful"
        message = f"Hello! {student.name} is making steady progress. "
        message += f"They've put in {time_mins} minutes of study time this week with {accuracy}% accuracy. "
        message += f"With a little more practice, they'll soon master these topics. Keep encouraging them!"
    else:
        emotional_tone = "supportive and caring"
        message = f"Hi there. {student.name} is working hard on their studies. "
        message += f"This week they practiced for {time_mins} minutes. "
        message += "Some topics are challenging, but every step forward is progress. "
        message += "Together, we'll help them build confidence."
    
    # Create report
    report = ParentReport(
        student_id=student_id,
        report_type=report_type,
        total_study_time_minutes=time_mins,
        sessions_completed=dashboard['sessions_completed'],
        average_accuracy=accuracy,
        subjects_practiced=json.dumps([s['subject'] for s in dashboard['subjects_time']]),
        topics_mastered=json.dumps([t['topic'] for t in dashboard['topics_mastered']]),
        areas_needing_attention=json.dumps([t['topic'] for t in dashboard['topics_needing_attention']]),
        emotional_summary=emotional_tone,
        voice_message_text=message
    )
    
    report_id = db.create_parent_report(report)
    
    return {
        "success": True,
        "report_id": report_id,
        "voice_message": message,
        "emotional_tone": emotional_tone,
        "summary": {
            "study_time_minutes": time_mins,
            "sessions": dashboard['sessions_completed'],
            "accuracy": accuracy,
            "topics_mastered": mastered_count,
            "needs_attention": len(dashboard['topics_needing_attention'])
        }
    }


@app.get("/api/reports/{student_id}/latest")
async def get_latest_report(student_id: int):
    """Get the latest parent report."""
    report = db.get_latest_parent_report(student_id)
    if not report:
        raise HTTPException(status_code=404, detail="No reports found")
    return {"success": True, "report": report.__dict__}


# ==================== ACHIEVEMENTS ENDPOINTS ====================

@app.post("/api/students/{student_id}/achievements")
async def add_achievement(student_id: int, achievement_type: str, name: str, description: str, points: int = 10):
    """Add an achievement for a student."""
    student = db.get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    achievement_id = db.add_achievement(student_id, achievement_type, name, description, points)
    return {"success": True, "achievement_id": achievement_id}


# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0", "service": "IDNA EdTech API"}


@app.get("/")
async def root():
    return {
        "name": "IDNA EdTech API",
        "version": "2.0.0",
        "description": "Voice-based AI Tutor for K-10 Students in India",
        "docs": "/docs",
        "endpoints": {
            "students": "/api/students",
            "sessions": "/api/sessions",
            "progress": "/api/progress",
            "dashboard": "/api/dashboard/{student_id}",
            "reports": "/api/reports/{student_id}"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
