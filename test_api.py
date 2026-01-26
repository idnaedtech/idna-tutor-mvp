"""
IDNA EdTech - API Tests
Test all endpoints for student management, sessions, and parent dashboard.
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"


def test_health():
    """Test health endpoint."""
    print("\n1. Testing Health Endpoint...")
    resp = requests.get(f"{BASE_URL}/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    print(f"   ✅ Health check passed: {data}")


def test_root():
    """Test root endpoint."""
    print("\n2. Testing Root Endpoint...")
    resp = requests.get(f"{BASE_URL}/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "IDNA EdTech API"
    print(f"   ✅ Root endpoint: {data['name']} v{data['version']}")


def test_create_student():
    """Test student creation."""
    print("\n3. Testing Student Creation...")
    student_data = {
        "name": "Test Student",
        "age": 9,
        "grade": 4,
        "preferred_language": "en",
        "parent_phone": "+919999888877",
        "parent_name": "Test Parent",
        "city": "Nizamabad",
        "state": "Telangana"
    }
    resp = requests.post(f"{BASE_URL}/api/students", json=student_data)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == True
    student_id = data["student_id"]
    print(f"   ✅ Created student with ID: {student_id}")
    return student_id


def test_get_student(student_id):
    """Test getting student details."""
    print(f"\n4. Testing Get Student (ID: {student_id})...")
    resp = requests.get(f"{BASE_URL}/api/students/{student_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == True
    assert data["student"]["name"] == "Test Student"
    print(f"   ✅ Retrieved student: {data['student']['name']}")


def test_get_students_by_parent():
    """Test getting students by parent phone."""
    print("\n5. Testing Get Students by Parent Phone...")
    resp = requests.get(f"{BASE_URL}/api/students", params={"phone": "+919876543210"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == True
    print(f"   ✅ Found {len(data['students'])} students for parent")


def test_update_student(student_id):
    """Test updating student."""
    print(f"\n6. Testing Update Student (ID: {student_id})...")
    updates = {
        "learning_pace": "fast",
        "current_subject": "science",
        "current_difficulty": 3
    }
    resp = requests.put(f"{BASE_URL}/api/students/{student_id}", json=updates)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == True
    print(f"   ✅ Updated student successfully")


def test_create_session(student_id):
    """Test session creation."""
    print(f"\n7. Testing Create Session (Student ID: {student_id})...")
    session_data = {
        "student_id": student_id,
        "subject": "math",
        "topic": "multiplication",
        "difficulty_level": 2
    }
    resp = requests.post(f"{BASE_URL}/api/sessions", json=session_data)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == True
    session_id = data["session_id"]
    print(f"   ✅ Created session with ID: {session_id}")
    return session_id


def test_end_session(session_id):
    """Test ending a session."""
    print(f"\n8. Testing End Session (ID: {session_id})...")
    session_data = {
        "duration_seconds": 900,
        "questions_asked": 15,
        "correct_answers": 12,
        "hints_used": 2,
        "engagement_score": 0.85,
        "celebration_moments": 3,
        "voice_interactions": 25
    }
    resp = requests.put(f"{BASE_URL}/api/sessions/{session_id}/end", json=session_data)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == True
    print(f"   ✅ Session ended successfully")


def test_get_student_sessions(student_id):
    """Test getting student sessions."""
    print(f"\n9. Testing Get Student Sessions (ID: {student_id})...")
    resp = requests.get(f"{BASE_URL}/api/students/{student_id}/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == True
    print(f"   ✅ Found {len(data['sessions'])} sessions")


def test_update_progress(student_id):
    """Test progress update."""
    print(f"\n10. Testing Update Progress (Student ID: {student_id})...")
    progress_data = {
        "student_id": student_id,
        "subject": "math",
        "topic": "multiplication",
        "mastery_level": 80.0,
        "time_spent_seconds": 900
    }
    resp = requests.post(f"{BASE_URL}/api/progress", json=progress_data)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == True
    print(f"   ✅ Progress updated")


def test_get_progress(student_id):
    """Test getting student progress."""
    print(f"\n11. Testing Get Student Progress (ID: {student_id})...")
    resp = requests.get(f"{BASE_URL}/api/students/{student_id}/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == True
    print(f"   ✅ Found {len(data['progress'])} topic progress records")


def test_dashboard(student_id):
    """Test parent dashboard endpoint."""
    print(f"\n12. Testing Parent Dashboard (Student ID: {student_id})...")
    resp = requests.get(f"{BASE_URL}/api/dashboard/{student_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == True
    assert "dashboard" in data
    dashboard = data["dashboard"]
    print(f"   ✅ Dashboard data:")
    print(f"      - Study time: {dashboard['total_study_time_minutes']} mins")
    print(f"      - Accuracy: {dashboard['average_accuracy']}%")
    print(f"      - Sessions: {dashboard['sessions_completed']}")
    print(f"      - Topics mastered: {len(dashboard['topics_mastered'])}")


def test_parent_dashboard_multi():
    """Test parent dashboard for multiple children."""
    print("\n13. Testing Parent Dashboard (Multiple Children)...")
    resp = requests.get(f"{BASE_URL}/api/dashboard/parent/+919876543210")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == True
    print(f"   ✅ Found data for {len(data['children'])} children")


def test_generate_report(student_id):
    """Test report generation."""
    print(f"\n14. Testing Generate Report (Student ID: {student_id})...")
    resp = requests.post(f"{BASE_URL}/api/reports/{student_id}/generate", params={"report_type": "daily"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == True
    assert "voice_message" in data
    print(f"   ✅ Report generated:")
    print(f"      - Emotional tone: {data['emotional_tone']}")
    print(f"      - Voice message: {data['voice_message'][:80]}...")


def test_get_latest_report(student_id):
    """Test getting latest report."""
    print(f"\n15. Testing Get Latest Report (Student ID: {student_id})...")
    resp = requests.get(f"{BASE_URL}/api/reports/{student_id}/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == True
    print(f"   ✅ Retrieved latest report from {data['report']['generated_at']}")


def test_add_achievement(student_id):
    """Test adding achievement."""
    print(f"\n16. Testing Add Achievement (Student ID: {student_id})...")
    params = {
        "achievement_type": "streak",
        "name": "Test Champion",
        "description": "Completed all API tests",
        "points": 100
    }
    resp = requests.post(f"{BASE_URL}/api/students/{student_id}/achievements", params=params)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] == True
    print(f"   ✅ Added achievement with ID: {data['achievement_id']}")


def run_all_tests():
    """Run all API tests."""
    print("=" * 60)
    print("IDNA EdTech API Test Suite")
    print("=" * 60)
    
    try:
        test_health()
        test_root()
        
        # Student tests
        student_id = test_create_student()
        test_get_student(student_id)
        test_get_students_by_parent()
        test_update_student(student_id)
        
        # Session tests
        session_id = test_create_session(student_id)
        test_end_session(session_id)
        test_get_student_sessions(student_id)
        
        # Progress tests
        test_update_progress(student_id)
        test_get_progress(student_id)
        
        # Dashboard tests
        test_dashboard(student_id)
        test_parent_dashboard_multi()
        
        # Report tests
        test_generate_report(student_id)
        test_get_latest_report(student_id)
        
        # Achievement tests
        test_add_achievement(student_id)
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Could not connect to server at {BASE_URL}")
        print("   Make sure the API server is running: python api.py")
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
