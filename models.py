"""
IDNA EdTech - Database Models (v2)
Student profiles, learning sessions, progress tracking, and parent dashboard data.
"""

from datetime import datetime
from typing import Optional, List
import sqlite3
import json
from dataclasses import dataclass, asdict
from enum import Enum


class Language(Enum):
    ENGLISH = "en"
    HINDI = "hi"
    TELUGU = "te"
    TAMIL = "ta"
    KANNADA = "kn"
    MARATHI = "mr"


class Subject(Enum):
    MATH = "math"
    SCIENCE = "science"
    ENGLISH = "english"
    HINDI = "hindi"
    SOCIAL_STUDIES = "social_studies"
    EVS = "evs"  # Environmental Studies


class DifficultyLevel(Enum):
    BEGINNER = 1
    EASY = 2
    MEDIUM = 3
    HARD = 4
    ADVANCED = 5


@dataclass
class Student:
    id: Optional[int] = None
    name: str = ""
    age: int = 0
    grade: int = 1  # 1-10
    preferred_language: str = "en"
    secondary_language: Optional[str] = None
    parent_phone: str = ""
    parent_name: str = ""
    school_name: Optional[str] = None
    city: str = ""
    state: str = ""
    created_at: Optional[str] = None
    last_active: Optional[str] = None
    
    # Learning preferences
    learning_pace: str = "normal"  # slow, normal, fast
    voice_preference: str = "female"  # male, female
    session_duration_minutes: int = 30
    
    # Current progress
    current_subject: str = "math"
    current_topic: str = ""
    current_difficulty: int = 2


@dataclass
class LearningSession:
    id: Optional[int] = None
    student_id: int = 0
    subject: str = ""
    topic: str = ""
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    duration_seconds: int = 0
    
    # Performance metrics
    questions_asked: int = 0
    correct_answers: int = 0
    hints_used: int = 0
    difficulty_level: int = 2
    
    # Emotional tracking
    engagement_score: float = 0.0  # 0-1
    frustration_indicators: int = 0
    celebration_moments: int = 0
    
    # Session data
    transcript: str = ""  # JSON of conversation
    voice_interactions: int = 0


@dataclass
class TopicProgress:
    id: Optional[int] = None
    student_id: int = 0
    subject: str = ""
    topic: str = ""
    mastery_level: float = 0.0  # 0-100%
    attempts: int = 0
    last_practiced: Optional[str] = None
    time_spent_seconds: int = 0
    common_mistakes: str = ""  # JSON list


@dataclass
class ParentReport:
    id: Optional[int] = None
    student_id: int = 0
    generated_at: Optional[str] = None
    report_type: str = "daily"  # daily, weekly, monthly
    
    # Summary metrics
    total_study_time_minutes: int = 0
    sessions_completed: int = 0
    average_accuracy: float = 0.0
    subjects_practiced: str = ""  # JSON list
    
    # Growth indicators
    topics_mastered: str = ""  # JSON list
    areas_needing_attention: str = ""  # JSON list
    emotional_summary: str = ""
    
    # Voice message content
    voice_message_text: str = ""
    voice_message_audio_path: Optional[str] = None


class Database:
    def __init__(self, db_path: str = "idna_edtech.db"):
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def close(self):
        if self.conn:
            self.conn.close()
            
    def initialize(self):
        """Create all database tables."""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Students table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                grade INTEGER NOT NULL,
                preferred_language TEXT DEFAULT 'en',
                secondary_language TEXT,
                parent_phone TEXT NOT NULL,
                parent_name TEXT NOT NULL,
                school_name TEXT,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_active TEXT,
                learning_pace TEXT DEFAULT 'normal',
                voice_preference TEXT DEFAULT 'female',
                session_duration_minutes INTEGER DEFAULT 30,
                current_subject TEXT DEFAULT 'math',
                current_topic TEXT DEFAULT '',
                current_difficulty INTEGER DEFAULT 2
            )
        """)
        
        # Learning sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                topic TEXT NOT NULL,
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                ended_at TEXT,
                duration_seconds INTEGER DEFAULT 0,
                questions_asked INTEGER DEFAULT 0,
                correct_answers INTEGER DEFAULT 0,
                hints_used INTEGER DEFAULT 0,
                difficulty_level INTEGER DEFAULT 2,
                engagement_score REAL DEFAULT 0.0,
                frustration_indicators INTEGER DEFAULT 0,
                celebration_moments INTEGER DEFAULT 0,
                transcript TEXT DEFAULT '[]',
                voice_interactions INTEGER DEFAULT 0,
                FOREIGN KEY (student_id) REFERENCES students(id)
            )
        """)
        
        # Topic progress table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topic_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                topic TEXT NOT NULL,
                mastery_level REAL DEFAULT 0.0,
                attempts INTEGER DEFAULT 0,
                last_practiced TEXT,
                time_spent_seconds INTEGER DEFAULT 0,
                common_mistakes TEXT DEFAULT '[]',
                FOREIGN KEY (student_id) REFERENCES students(id),
                UNIQUE(student_id, subject, topic)
            )
        """)
        
        # Parent reports table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parent_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                report_type TEXT DEFAULT 'daily',
                total_study_time_minutes INTEGER DEFAULT 0,
                sessions_completed INTEGER DEFAULT 0,
                average_accuracy REAL DEFAULT 0.0,
                subjects_practiced TEXT DEFAULT '[]',
                topics_mastered TEXT DEFAULT '[]',
                areas_needing_attention TEXT DEFAULT '[]',
                emotional_summary TEXT DEFAULT '',
                voice_message_text TEXT DEFAULT '',
                voice_message_audio_path TEXT,
                FOREIGN KEY (student_id) REFERENCES students(id)
            )
        """)
        
        # Achievements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                achievement_type TEXT NOT NULL,
                achievement_name TEXT NOT NULL,
                description TEXT,
                earned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                points INTEGER DEFAULT 0,
                FOREIGN KEY (student_id) REFERENCES students(id)
            )
        """)
        
        conn.commit()
        self.close()
        
    # Student CRUD operations
    def create_student(self, student: Student) -> int:
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO students (
                name, age, grade, preferred_language, secondary_language,
                parent_phone, parent_name, school_name, city, state,
                learning_pace, voice_preference, session_duration_minutes,
                current_subject, current_topic, current_difficulty
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            student.name, student.age, student.grade, student.preferred_language,
            student.secondary_language, student.parent_phone, student.parent_name,
            student.school_name, student.city, student.state, student.learning_pace,
            student.voice_preference, student.session_duration_minutes,
            student.current_subject, student.current_topic, student.current_difficulty
        ))
        conn.commit()
        student_id = cursor.lastrowid
        self.close()
        return student_id
    
    def get_student(self, student_id: int) -> Optional[Student]:
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
        row = cursor.fetchone()
        self.close()
        if row:
            return Student(**dict(row))
        return None
    
    def get_students_by_parent_phone(self, phone: str) -> List[Student]:
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE parent_phone = ?", (phone,))
        rows = cursor.fetchall()
        self.close()
        return [Student(**dict(row)) for row in rows]
    
    def update_student(self, student: Student) -> bool:
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE students SET
                name = ?, age = ?, grade = ?, preferred_language = ?,
                secondary_language = ?, parent_phone = ?, parent_name = ?,
                school_name = ?, city = ?, state = ?, last_active = ?,
                learning_pace = ?, voice_preference = ?, session_duration_minutes = ?,
                current_subject = ?, current_topic = ?, current_difficulty = ?
            WHERE id = ?
        """, (
            student.name, student.age, student.grade, student.preferred_language,
            student.secondary_language, student.parent_phone, student.parent_name,
            student.school_name, student.city, student.state, datetime.now().isoformat(),
            student.learning_pace, student.voice_preference, student.session_duration_minutes,
            student.current_subject, student.current_topic, student.current_difficulty,
            student.id
        ))
        conn.commit()
        self.close()
        return cursor.rowcount > 0
    
    # Session operations
    def create_session(self, session: LearningSession) -> int:
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO learning_sessions (
                student_id, subject, topic, difficulty_level
            ) VALUES (?, ?, ?, ?)
        """, (session.student_id, session.subject, session.topic, session.difficulty_level))
        conn.commit()
        session_id = cursor.lastrowid
        self.close()
        return session_id
    
    def end_session(self, session_id: int, session: LearningSession) -> bool:
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE learning_sessions SET
                ended_at = ?, duration_seconds = ?, questions_asked = ?,
                correct_answers = ?, hints_used = ?, engagement_score = ?,
                frustration_indicators = ?, celebration_moments = ?,
                transcript = ?, voice_interactions = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(), session.duration_seconds,
            session.questions_asked, session.correct_answers, session.hints_used,
            session.engagement_score, session.frustration_indicators,
            session.celebration_moments, session.transcript, session.voice_interactions,
            session_id
        ))
        conn.commit()
        self.close()
        return cursor.rowcount > 0
    
    def get_student_sessions(self, student_id: int, limit: int = 10) -> List[LearningSession]:
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM learning_sessions 
            WHERE student_id = ? 
            ORDER BY started_at DESC 
            LIMIT ?
        """, (student_id, limit))
        rows = cursor.fetchall()
        self.close()
        return [LearningSession(**dict(row)) for row in rows]
    
    # Topic progress operations
    def update_topic_progress(self, progress: TopicProgress) -> bool:
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO topic_progress (
                student_id, subject, topic, mastery_level, attempts,
                last_practiced, time_spent_seconds, common_mistakes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(student_id, subject, topic) DO UPDATE SET
                mastery_level = excluded.mastery_level,
                attempts = topic_progress.attempts + 1,
                last_practiced = excluded.last_practiced,
                time_spent_seconds = topic_progress.time_spent_seconds + excluded.time_spent_seconds,
                common_mistakes = excluded.common_mistakes
        """, (
            progress.student_id, progress.subject, progress.topic,
            progress.mastery_level, progress.attempts, datetime.now().isoformat(),
            progress.time_spent_seconds, progress.common_mistakes
        ))
        conn.commit()
        self.close()
        return True
    
    def get_student_progress(self, student_id: int, subject: Optional[str] = None) -> List[TopicProgress]:
        conn = self.connect()
        cursor = conn.cursor()
        if subject:
            cursor.execute("""
                SELECT * FROM topic_progress 
                WHERE student_id = ? AND subject = ?
                ORDER BY mastery_level DESC
            """, (student_id, subject))
        else:
            cursor.execute("""
                SELECT * FROM topic_progress 
                WHERE student_id = ?
                ORDER BY subject, mastery_level DESC
            """, (student_id,))
        rows = cursor.fetchall()
        self.close()
        return [TopicProgress(**dict(row)) for row in rows]
    
    # Parent report operations
    def create_parent_report(self, report: ParentReport) -> int:
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO parent_reports (
                student_id, report_type, total_study_time_minutes,
                sessions_completed, average_accuracy, subjects_practiced,
                topics_mastered, areas_needing_attention, emotional_summary,
                voice_message_text, voice_message_audio_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report.student_id, report.report_type, report.total_study_time_minutes,
            report.sessions_completed, report.average_accuracy, report.subjects_practiced,
            report.topics_mastered, report.areas_needing_attention, report.emotional_summary,
            report.voice_message_text, report.voice_message_audio_path
        ))
        conn.commit()
        report_id = cursor.lastrowid
        self.close()
        return report_id
    
    def get_latest_parent_report(self, student_id: int) -> Optional[ParentReport]:
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM parent_reports 
            WHERE student_id = ? 
            ORDER BY generated_at DESC 
            LIMIT 1
        """, (student_id,))
        row = cursor.fetchone()
        self.close()
        if row:
            return ParentReport(**dict(row))
        return None
    
    # Dashboard aggregations
    def get_student_dashboard_data(self, student_id: int) -> dict:
        """Get aggregated data for parent dashboard."""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Total study time (last 7 days)
        cursor.execute("""
            SELECT COALESCE(SUM(duration_seconds), 0) as total_time
            FROM learning_sessions
            WHERE student_id = ? 
            AND started_at >= datetime('now', '-7 days')
        """, (student_id,))
        total_time = cursor.fetchone()['total_time']
        
        # Average accuracy (last 7 days)
        cursor.execute("""
            SELECT 
                COALESCE(SUM(correct_answers), 0) as correct,
                COALESCE(SUM(questions_asked), 0) as total
            FROM learning_sessions
            WHERE student_id = ?
            AND started_at >= datetime('now', '-7 days')
        """, (student_id,))
        row = cursor.fetchone()
        accuracy = (row['correct'] / row['total'] * 100) if row['total'] > 0 else 0
        
        # Sessions count (last 7 days)
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM learning_sessions
            WHERE student_id = ?
            AND started_at >= datetime('now', '-7 days')
        """, (student_id,))
        sessions_count = cursor.fetchone()['count']
        
        # Top subjects by time
        cursor.execute("""
            SELECT subject, SUM(duration_seconds) as time
            FROM learning_sessions
            WHERE student_id = ?
            GROUP BY subject
            ORDER BY time DESC
            LIMIT 5
        """, (student_id,))
        subjects_time = [dict(row) for row in cursor.fetchall()]
        
        # Topics mastered (mastery >= 80%)
        cursor.execute("""
            SELECT subject, topic, mastery_level
            FROM topic_progress
            WHERE student_id = ? AND mastery_level >= 80
            ORDER BY mastery_level DESC
        """, (student_id,))
        mastered = [dict(row) for row in cursor.fetchall()]
        
        # Topics needing attention (mastery < 50%)
        cursor.execute("""
            SELECT subject, topic, mastery_level
            FROM topic_progress
            WHERE student_id = ? AND mastery_level < 50 AND attempts > 0
            ORDER BY mastery_level ASC
        """, (student_id,))
        needs_attention = [dict(row) for row in cursor.fetchall()]
        
        # Recent achievements
        cursor.execute("""
            SELECT achievement_name, description, earned_at, points
            FROM achievements
            WHERE student_id = ?
            ORDER BY earned_at DESC
            LIMIT 5
        """, (student_id,))
        achievements = [dict(row) for row in cursor.fetchall()]
        
        # Daily activity (last 7 days)
        cursor.execute("""
            SELECT 
                DATE(started_at) as date,
                COUNT(*) as sessions,
                SUM(duration_seconds) as duration
            FROM learning_sessions
            WHERE student_id = ?
            AND started_at >= datetime('now', '-7 days')
            GROUP BY DATE(started_at)
            ORDER BY date
        """, (student_id,))
        daily_activity = [dict(row) for row in cursor.fetchall()]
        
        self.close()
        
        return {
            "total_study_time_seconds": total_time,
            "total_study_time_minutes": total_time // 60,
            "average_accuracy": round(accuracy, 1),
            "sessions_completed": sessions_count,
            "subjects_time": subjects_time,
            "topics_mastered": mastered,
            "topics_needing_attention": needs_attention,
            "recent_achievements": achievements,
            "daily_activity": daily_activity
        }
    
    # Achievement operations
    def add_achievement(self, student_id: int, achievement_type: str, 
                       name: str, description: str, points: int = 10) -> int:
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO achievements (student_id, achievement_type, achievement_name, description, points)
            VALUES (?, ?, ?, ?, ?)
        """, (student_id, achievement_type, name, description, points))
        conn.commit()
        achievement_id = cursor.lastrowid
        self.close()
        return achievement_id


# Seed data for testing
def seed_test_data(db: Database):
    """Create sample data for testing."""
    
    # Create sample students
    students = [
        Student(
            name="Aarav Sharma",
            age=10,
            grade=5,
            preferred_language="hi",
            secondary_language="en",
            parent_phone="+919876543210",
            parent_name="Priya Sharma",
            school_name="Delhi Public School",
            city="Nizamabad",
            state="Telangana",
            learning_pace="normal",
            current_subject="math",
            current_topic="fractions"
        ),
        Student(
            name="Ananya Reddy",
            age=8,
            grade=3,
            preferred_language="te",
            secondary_language="en",
            parent_phone="+919876543211",
            parent_name="Lakshmi Reddy",
            school_name="Saraswati Vidyalaya",
            city="Warangal",
            state="Telangana",
            learning_pace="slow",
            current_subject="evs",
            current_topic="plants"
        ),
        Student(
            name="Rohan Patel",
            age=12,
            grade=7,
            preferred_language="en",
            secondary_language="hi",
            parent_phone="+919876543212",
            parent_name="Amit Patel",
            school_name="Kendriya Vidyalaya",
            city="Hyderabad",
            state="Telangana",
            learning_pace="fast",
            current_subject="science",
            current_topic="electricity"
        )
    ]
    
    student_ids = []
    for student in students:
        sid = db.create_student(student)
        student_ids.append(sid)
        print(f"Created student: {student.name} (ID: {sid})")
    
    # Create sample sessions
    import random
    subjects = ["math", "science", "english", "hindi", "evs"]
    topics = {
        "math": ["addition", "subtraction", "fractions", "decimals", "geometry"],
        "science": ["plants", "animals", "electricity", "magnets", "water_cycle"],
        "english": ["grammar", "vocabulary", "reading", "writing", "speaking"],
        "hindi": ["vyakaran", "kavita", "kahani", "lekhan", "vachan"],
        "evs": ["plants", "animals", "weather", "family", "transport"]
    }
    
    for sid in student_ids:
        # Create 5-10 sessions per student
        for _ in range(random.randint(5, 10)):
            subject = random.choice(subjects)
            topic = random.choice(topics[subject])
            
            session = LearningSession(
                student_id=sid,
                subject=subject,
                topic=topic,
                difficulty_level=random.randint(1, 4)
            )
            session_id = db.create_session(session)
            
            # End session with random data
            session.duration_seconds = random.randint(300, 1800)
            session.questions_asked = random.randint(5, 20)
            session.correct_answers = random.randint(0, session.questions_asked)
            session.hints_used = random.randint(0, 5)
            session.engagement_score = random.uniform(0.5, 1.0)
            session.frustration_indicators = random.randint(0, 3)
            session.celebration_moments = random.randint(0, 5)
            session.voice_interactions = random.randint(10, 50)
            db.end_session(session_id, session)
            
            # Update topic progress
            mastery = (session.correct_answers / session.questions_asked * 100) if session.questions_asked > 0 else 0
            progress = TopicProgress(
                student_id=sid,
                subject=subject,
                topic=topic,
                mastery_level=mastery,
                time_spent_seconds=session.duration_seconds
            )
            db.update_topic_progress(progress)
    
    # Add some achievements
    achievement_types = [
        ("streak", "7-Day Streak!", "Studied for 7 days in a row", 50),
        ("mastery", "Math Master", "Mastered 5 math topics", 100),
        ("speed", "Quick Thinker", "Answered 10 questions in under 2 minutes", 30),
        ("accuracy", "Perfect Score", "Got 100% on a practice session", 25)
    ]
    
    for sid in student_ids:
        for _ in range(random.randint(1, 3)):
            ach = random.choice(achievement_types)
            db.add_achievement(sid, ach[0], ach[1], ach[2], ach[3])
    
    print(f"\nSeeded data for {len(student_ids)} students")
    return student_ids


if __name__ == "__main__":
    # Initialize and seed database
    db = Database("idna_edtech.db")
    db.initialize()
    print("Database initialized successfully!")
    
    # Seed test data
    student_ids = seed_test_data(db)
    
    # Test dashboard data
    print("\n--- Dashboard Data Test ---")
    for sid in student_ids:
        student = db.get_student(sid)
        dashboard = db.get_student_dashboard_data(sid)
        print(f"\n{student.name}:")
        print(f"  Study time: {dashboard['total_study_time_minutes']} mins")
        print(f"  Accuracy: {dashboard['average_accuracy']}%")
        print(f"  Sessions: {dashboard['sessions_completed']}")
        print(f"  Topics mastered: {len(dashboard['topics_mastered'])}")
        print(f"  Needs attention: {len(dashboard['topics_needing_attention'])}")
