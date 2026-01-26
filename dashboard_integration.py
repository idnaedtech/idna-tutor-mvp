"""
IDNA EdTech - Parent Dashboard Integration
==========================================

Add these routes to your existing web_server.py to enable the Parent Dashboard.

INSTRUCTIONS:
1. Copy the functions below into your web_server.py
2. Copy parent_dashboard.html to the same folder
3. Access dashboard at: http://localhost:8000/dashboard?student=1

"""

# ============================================================
# ADD THESE IMPORTS AT THE TOP OF YOUR web_server.py
# ============================================================

import json
from datetime import datetime, timedelta


# ============================================================
# ADD THESE DATABASE FUNCTIONS
# ============================================================

def get_student_dashboard_data(student_id):
    """Get aggregated dashboard data for a student."""
    conn = sqlite3.connect('idna.db')
    cursor = conn.cursor()
    
    # Get student info
    cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    student_row = cursor.fetchone()
    
    if not student_row:
        conn.close()
        return None
    
    # Student basic info (adjust column indices based on your schema)
    student = {
        "id": student_row[0],
        "name": student_row[1],
        "age": student_row[2] if len(student_row) > 2 else 10,
        "grade": student_row[3] if len(student_row) > 3 else 5,
        "current_subject": "math"
    }
    
    # Get sessions from last 7 days
    seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
    
    cursor.execute("""
        SELECT 
            SUM(duration_seconds) as total_time,
            SUM(correct_answers) as correct,
            SUM(questions_asked) as total_questions,
            COUNT(*) as session_count
        FROM sessions 
        WHERE student_id = ? AND started_at >= ?
    """, (student_id, seven_days_ago))
    
    stats = cursor.fetchone()
    total_time = stats[0] or 0
    correct = stats[1] or 0
    total_questions = stats[2] or 1
    session_count = stats[3] or 0
    accuracy = round((correct / total_questions) * 100, 1) if total_questions > 0 else 0
    
    # Get weak topics (from your existing weak_topics table)
    cursor.execute("""
        SELECT subject, topic, accuracy 
        FROM weak_topics 
        WHERE student_id = ?
        ORDER BY accuracy ASC
        LIMIT 5
    """, (student_id,))
    weak_topics = [{"subject": r[0], "topic": r[1], "mastery_level": r[2]} for r in cursor.fetchall()]
    
    # Get mastered topics (accuracy >= 80)
    cursor.execute("""
        SELECT subject, topic, accuracy 
        FROM weak_topics 
        WHERE student_id = ? AND accuracy >= 80
        ORDER BY accuracy DESC
    """, (student_id,))
    mastered = [{"subject": r[0], "topic": r[1], "mastery_level": r[2]} for r in cursor.fetchall()]
    
    # Get daily activity
    cursor.execute("""
        SELECT 
            DATE(started_at) as date,
            COUNT(*) as sessions,
            SUM(duration_seconds) as duration
        FROM sessions
        WHERE student_id = ? AND started_at >= ?
        GROUP BY DATE(started_at)
        ORDER BY date
    """, (student_id, seven_days_ago))
    daily_activity = [{"date": r[0], "sessions": r[1], "duration": r[2] or 0} for r in cursor.fetchall()]
    
    # Fill missing days
    all_days = []
    for i in range(7):
        date = (datetime.now() - timedelta(days=6-i)).strftime('%Y-%m-%d')
        existing = next((d for d in daily_activity if d['date'] == date), None)
        if existing:
            all_days.append(existing)
        else:
            all_days.append({"date": date, "sessions": 0, "duration": 0})
    
    # Get subject time breakdown
    cursor.execute("""
        SELECT subject, SUM(duration_seconds) as time
        FROM sessions
        WHERE student_id = ?
        GROUP BY subject
        ORDER BY time DESC
    """, (student_id,))
    subjects_time = [{"subject": r[0], "time": r[1] or 0} for r in cursor.fetchall()]
    
    conn.close()
    
    # Generate voice message
    voice_message = generate_voice_message(student['name'], total_time // 60, accuracy, len(mastered))
    
    return {
        "student": student,
        "dashboard": {
            "total_study_time_minutes": total_time // 60,
            "average_accuracy": accuracy,
            "sessions_completed": session_count,
            "streak_days": calculate_streak(student_id),
            "subjects_time": subjects_time if subjects_time else [{"subject": "math", "time": 0}],
            "topics_mastered": mastered,
            "topics_needing_attention": [t for t in weak_topics if t['mastery_level'] < 60],
            "recent_achievements": get_achievements(student_id),
            "daily_activity": all_days
        },
        "voice_message": voice_message
    }


def generate_voice_message(name, study_minutes, accuracy, mastered_count):
    """Generate emotionally resonant voice message for parents."""
    if accuracy >= 80:
        return f"Namaste! I'm so happy to share that {name} is doing wonderfully! This week, they studied for {study_minutes} minutes and achieved {accuracy}% accuracy. They've mastered {mastered_count} topics! You should be very proud of their progress."
    elif accuracy >= 60:
        return f"Hello! {name} is making steady progress. They've put in {study_minutes} minutes of study time this week with {accuracy}% accuracy. With a little more practice, they'll soon master these topics. Keep encouraging them!"
    else:
        return f"Hi there. {name} is working hard on their studies. This week they practiced for {study_minutes} minutes. Some topics are challenging, but every step forward is progress. Together, we'll help them build confidence."


def calculate_streak(student_id):
    """Calculate consecutive study days."""
    conn = sqlite3.connect('idna.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT DATE(started_at) as date
        FROM sessions
        WHERE student_id = ?
        ORDER BY date DESC
        LIMIT 30
    """, (student_id,))
    
    dates = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    if not dates:
        return 0
    
    streak = 1
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Check if studied today or yesterday
    if dates[0] not in [today, (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')]:
        return 0
    
    for i in range(1, len(dates)):
        current = datetime.strptime(dates[i-1], '%Y-%m-%d')
        previous = datetime.strptime(dates[i], '%Y-%m-%d')
        if (current - previous).days == 1:
            streak += 1
        else:
            break
    
    return streak


def get_achievements(student_id):
    """Get recent achievements (create sample if table doesn't exist)."""
    try:
        conn = sqlite3.connect('idna.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, description, points, earned_at, type
            FROM achievements
            WHERE student_id = ?
            ORDER BY earned_at DESC
            LIMIT 5
        """, (student_id,))
        achievements = [{"name": r[0], "description": r[1], "points": r[2], "date": r[3], "type": r[4]} 
                       for r in cursor.fetchall()]
        conn.close()
        return achievements
    except:
        # Return sample achievements if table doesn't exist
        return [
            {"name": "First Steps!", "description": "Completed first lesson", "points": 10, "date": datetime.now().strftime('%Y-%m-%d'), "type": "mastery"},
            {"name": "Quick Learner", "description": "Answered 5 questions correctly", "points": 20, "date": datetime.now().strftime('%Y-%m-%d'), "type": "accuracy"}
        ]


# ============================================================
# ADD THESE ROUTE HANDLERS
# ============================================================

# Add to your route handling in web_server.py

def handle_dashboard_request(self):
    """Handle /dashboard request."""
    # Parse student ID from query string
    query = urllib.parse.urlparse(self.path).query
    params = urllib.parse.parse_qs(query)
    student_id = int(params.get('student', [1])[0])
    
    # Serve the HTML file
    try:
        with open('parent_dashboard.html', 'rb') as f:
            content = f.read()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(content)
    except FileNotFoundError:
        self.send_error(404, 'Dashboard not found')


def handle_api_dashboard(self):
    """Handle /api/dashboard/{student_id} request."""
    # Extract student_id from path
    path_parts = self.path.split('/')
    student_id = int(path_parts[-1].split('?')[0])
    
    data = get_student_dashboard_data(student_id)
    
    if data:
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    else:
        self.send_error(404, 'Student not found')


# ============================================================
# MODIFY YOUR do_GET METHOD
# ============================================================

"""
In your existing do_GET method, add these routes:

def do_GET(self):
    if self.path == '/dashboard' or self.path.startswith('/dashboard?'):
        self.handle_dashboard_request()
    elif self.path.startswith('/api/dashboard/'):
        self.handle_api_dashboard()
    # ... your existing routes ...
"""


# ============================================================
# QUICK TEST
# ============================================================

if __name__ == "__main__":
    # Test the dashboard data function
    import sqlite3
    
    print("Testing dashboard data generation...")
    
    # Create sample data if needed
    conn = sqlite3.connect('idna.db')
    cursor = conn.cursor()
    
    # Check if students table exists and has data
    cursor.execute("SELECT COUNT(*) FROM students")
    count = cursor.fetchone()[0]
    
    if count > 0:
        cursor.execute("SELECT id FROM students LIMIT 1")
        student_id = cursor.fetchone()[0]
        conn.close()
        
        data = get_student_dashboard_data(student_id)
        if data:
            print(f"\n✅ Dashboard data for {data['student']['name']}:")
            print(f"   Study time: {data['dashboard']['total_study_time_minutes']} mins")
            print(f"   Accuracy: {data['dashboard']['average_accuracy']}%")
            print(f"   Sessions: {data['dashboard']['sessions_completed']}")
            print(f"   Streak: {data['dashboard']['streak_days']} days")
            print(f"\nVoice message preview:")
            print(f"   {data['voice_message'][:100]}...")
    else:
        print("No students found. Create a student first.")
        conn.close()
