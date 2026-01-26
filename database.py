"""
IDNA EdTech - Database Module
SQLite persistence for students, sessions, and attempts
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict
import json


DATABASE_PATH = "idna_tutor.db"


def get_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Students table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            pin TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            student_id INTEGER,
            chapter TEXT,
            score INTEGER DEFAULT 0,
            total_questions INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)
    
    # Attempts table (every question attempt)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            student_id INTEGER,
            question_id TEXT NOT NULL,
            chapter TEXT,
            student_answer TEXT,
            correct_answer TEXT,
            is_correct BOOLEAN,
            attempt_number INTEGER,
            hint_used INTEGER DEFAULT 0,
            time_taken_seconds REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id),
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)
    
    # Topic performance (aggregated)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS topic_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            chapter TEXT NOT NULL,
            total_questions INTEGER DEFAULT 0,
            correct_answers INTEGER DEFAULT 0,
            total_hints_used INTEGER DEFAULT 0,
            avg_time_seconds REAL,
            last_practiced TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id),
            UNIQUE(student_id, chapter)
        )
    """)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")


# ============ STUDENT FUNCTIONS ============

def create_student(name: str, pin: str) -> int:
    """Create a new student profile"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO students (name, pin) VALUES (?, ?)",
        (name, pin)
    )
    student_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return student_id


def get_student_by_pin(name: str, pin: str) -> Optional[Dict]:
    """Get student by name and PIN"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM students WHERE name = ? AND pin = ?",
        (name, pin)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def get_student_by_id(student_id: int) -> Optional[Dict]:
    """Get student by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def update_student_activity(student_id: int):
    """Update last active timestamp"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE students SET last_active = ? WHERE id = ?",
        (datetime.now(), student_id)
    )
    
    conn.commit()
    conn.close()


def get_all_students() -> List[Dict]:
    """Get all students (for parent dashboard)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM students ORDER BY last_active DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# ============ SESSION FUNCTIONS ============

def create_session(session_id: str, student_id: int = None) -> None:
    """Create a new session"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO sessions (session_id, student_id) VALUES (?, ?)",
        (session_id, student_id)
    )
    
    conn.commit()
    conn.close()


def get_session(session_id: str) -> Optional[Dict]:
    """Get session by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def update_session(session_id: str, **kwargs):
    """Update session fields"""
    conn = get_connection()
    cursor = conn.cursor()
    
    valid_fields = ['chapter', 'score', 'total_questions', 'status', 'ended_at', 'student_id']
    updates = []
    values = []
    
    for field, value in kwargs.items():
        if field in valid_fields:
            updates.append(f"{field} = ?")
            values.append(value)
    
    if updates:
        values.append(session_id)
        cursor.execute(
            f"UPDATE sessions SET {', '.join(updates)} WHERE session_id = ?",
            values
        )
    
    conn.commit()
    conn.close()


def get_student_sessions(student_id: int, limit: int = 10) -> List[Dict]:
    """Get recent sessions for a student"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT * FROM sessions 
           WHERE student_id = ? 
           ORDER BY started_at DESC 
           LIMIT ?""",
        (student_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# ============ ATTEMPT FUNCTIONS ============

def log_attempt(
    session_id: str,
    student_id: int,
    question_id: str,
    chapter: str,
    student_answer: str,
    correct_answer: str,
    is_correct: bool,
    attempt_number: int,
    hint_used: int = 0,
    time_taken_seconds: float = None
):
    """Log a question attempt"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """INSERT INTO attempts 
           (session_id, student_id, question_id, chapter, student_answer, 
            correct_answer, is_correct, attempt_number, hint_used, time_taken_seconds)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, student_id, question_id, chapter, student_answer,
         correct_answer, is_correct, attempt_number, hint_used, time_taken_seconds)
    )
    
    conn.commit()
    conn.close()


def get_session_attempts(session_id: str) -> List[Dict]:
    """Get all attempts for a session"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM attempts WHERE session_id = ? ORDER BY created_at",
        (session_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# ============ ANALYTICS FUNCTIONS ============

def update_topic_performance(student_id: int, chapter: str, is_correct: bool, hints_used: int, time_seconds: float):
    """Update aggregated topic performance"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if record exists
    cursor.execute(
        "SELECT * FROM topic_performance WHERE student_id = ? AND chapter = ?",
        (student_id, chapter)
    )
    existing = cursor.fetchone()
    
    if existing:
        # Update existing
        new_total = existing['total_questions'] + 1
        new_correct = existing['correct_answers'] + (1 if is_correct else 0)
        new_hints = existing['total_hints_used'] + hints_used
        
        # Calculate new average time
        old_avg = existing['avg_time_seconds'] or 0
        new_avg = ((old_avg * existing['total_questions']) + time_seconds) / new_total if time_seconds else old_avg
        
        cursor.execute(
            """UPDATE topic_performance 
               SET total_questions = ?, correct_answers = ?, total_hints_used = ?, 
                   avg_time_seconds = ?, last_practiced = ?
               WHERE student_id = ? AND chapter = ?""",
            (new_total, new_correct, new_hints, new_avg, datetime.now(), student_id, chapter)
        )
    else:
        # Insert new
        cursor.execute(
            """INSERT INTO topic_performance 
               (student_id, chapter, total_questions, correct_answers, total_hints_used, avg_time_seconds, last_practiced)
               VALUES (?, ?, 1, ?, ?, ?, ?)""",
            (student_id, chapter, 1 if is_correct else 0, hints_used, time_seconds, datetime.now())
        )
    
    conn.commit()
    conn.close()


def get_student_performance(student_id: int) -> List[Dict]:
    """Get performance by topic for a student"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT chapter, total_questions, correct_answers, total_hints_used, avg_time_seconds,
                  ROUND(correct_answers * 100.0 / total_questions, 1) as accuracy
           FROM topic_performance 
           WHERE student_id = ?
           ORDER BY accuracy ASC""",
        (student_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_weak_topics(student_id: int, threshold: float = 70.0) -> List[Dict]:
    """Get topics where accuracy is below threshold"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT chapter, total_questions, correct_answers,
                  ROUND(correct_answers * 100.0 / total_questions, 1) as accuracy
           FROM topic_performance 
           WHERE student_id = ? AND (correct_answers * 100.0 / total_questions) < ?
           ORDER BY accuracy ASC""",
        (student_id, threshold)
    )
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_student_summary(student_id: int) -> Dict:
    """Get overall summary for a student"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Total sessions
    cursor.execute(
        "SELECT COUNT(*) as count FROM sessions WHERE student_id = ?",
        (student_id,)
    )
    total_sessions = cursor.fetchone()['count']
    
    # Total questions and accuracy
    cursor.execute(
        """SELECT SUM(total_questions) as total_q, SUM(correct_answers) as total_correct
           FROM topic_performance WHERE student_id = ?""",
        (student_id,)
    )
    row = cursor.fetchone()
    total_questions = row['total_q'] or 0
    total_correct = row['total_correct'] or 0
    
    # Recent activity
    cursor.execute(
        "SELECT * FROM sessions WHERE student_id = ? ORDER BY started_at DESC LIMIT 5",
        (student_id,)
    )
    recent_sessions = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    
    return {
        "total_sessions": total_sessions,
        "total_questions": total_questions,
        "total_correct": total_correct,
        "overall_accuracy": round(total_correct * 100.0 / total_questions, 1) if total_questions > 0 else 0,
        "recent_sessions": recent_sessions
    }


# Initialize database on import
if not os.path.exists(DATABASE_PATH):
    init_database()


# Test the module
if __name__ == "__main__":
    print("Testing Database Module...")
    print("-" * 40)
    
    # Initialize
    init_database()
    
    # Create a test student
    student_id = create_student("Test Student", "1234")
    print(f"Created student with ID: {student_id}")
    
    # Get student
    student = get_student_by_pin("Test Student", "1234")
    print(f"Retrieved student: {student}")
    
    # Create a session
    import uuid
    session_id = str(uuid.uuid4())
    create_session(session_id, student_id)
    print(f"Created session: {session_id}")
    
    # Log an attempt
    log_attempt(
        session_id=session_id,
        student_id=student_id,
        question_id="le_001",
        chapter="linear_equations",
        student_answer="7",
        correct_answer="7",
        is_correct=True,
        attempt_number=1,
        hint_used=0,
        time_taken_seconds=5.5
    )
    print("Logged attempt")
    
    # Update topic performance
    update_topic_performance(student_id, "linear_equations", True, 0, 5.5)
    print("Updated topic performance")
    
    # Get performance
    performance = get_student_performance(student_id)
    print(f"Performance: {performance}")
    
    print("-" * 40)
    print("Database test complete!")
