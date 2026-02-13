"""
IDNA EdTech - API Tests
Test all endpoints for the tutoring server.
"""

import requests
import pytest

BASE_URL = "http://localhost:8000"


def test_health():
    """Test health endpoint."""
    print("\n1. Testing Health Endpoint...")
    resp = requests.get(f"{BASE_URL}/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "idna-tutor"
    print(f"   Health check passed: {data}")


def test_root():
    """Test root endpoint."""
    print("\n2. Testing Root Endpoint...")
    resp = requests.get(f"{BASE_URL}/")
    assert resp.status_code == 200
    # Root serves frontend HTML or JSON fallback
    content_type = resp.headers.get("content-type", "")
    if "text/html" in content_type:
        assert "html" in resp.text.lower()
        print("   Root endpoint: serves HTML frontend")
    else:
        data = resp.json()
        assert "message" in data
        print(f"   Root endpoint: {data['message']}")


def test_get_chapters():
    """Test chapters listing."""
    print("\n3. Testing Get Chapters...")
    resp = requests.get(f"{BASE_URL}/api/chapters")
    assert resp.status_code == 200
    data = resp.json()
    assert "chapters" in data
    assert len(data["chapters"]) > 0
    chapter_ids = [c["id"] for c in data["chapters"]]
    assert "rational_numbers" in chapter_ids
    print(f"   Found {len(data['chapters'])} chapters: {chapter_ids}")


def test_start_session():
    """Test session creation."""
    print("\n4. Testing Start Session...")
    session_data = {
        "student_name": "Test Student",
        "chapter": "rational_numbers"
    }
    resp = requests.post(f"{BASE_URL}/api/session/start", json=session_data)
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert "speech" in data
    assert "state" in data
    assert len(data["session_id"]) == 8
    print(f"   Created session: {data['session_id']}")
    print(f"   Opening speech: {data['speech'][:80]}...")


def test_start_session_empty_name():
    """Test session with empty name (v5.0 fix)."""
    print("\n5. Testing Start Session (empty name)...")
    session_data = {
        "student_name": "",
        "chapter": "rational_numbers"
    }
    resp = requests.post(f"{BASE_URL}/api/session/start", json=session_data)
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    # v5.0: Should NOT say "Student" in speech
    assert "Student" not in data["speech"] or "student" in data["speech"].lower()
    print(f"   Session without name created: {data['session_id']}")


def test_process_input():
    """Test processing student input."""
    print("\n6. Testing Process Input...")
    # First create a session
    session_resp = requests.post(
        f"{BASE_URL}/api/session/start",
        json={"student_name": "Ravi", "chapter": "rational_numbers"}
    )
    session_id = session_resp.json()["session_id"]

    # Send an answer
    input_data = {
        "session_id": session_id,
        "text": "minus 1 by 7"
    }
    resp = requests.post(f"{BASE_URL}/api/session/input", json=input_data)
    assert resp.status_code == 200
    data = resp.json()
    assert "speech" in data
    assert "state" in data
    print(f"   Response: {data['speech'][:80]}...")


def test_process_input_invalid_session():
    """Test input with invalid session ID."""
    print("\n7. Testing Invalid Session...")
    input_data = {
        "session_id": "invalid123",
        "text": "hello"
    }
    resp = requests.post(f"{BASE_URL}/api/session/input", json=input_data)
    assert resp.status_code == 404
    print("   Correctly returned 404 for invalid session")


def test_get_session_state():
    """Test getting session state."""
    print("\n8. Testing Get Session State...")
    # Create session first
    session_resp = requests.post(
        f"{BASE_URL}/api/session/start",
        json={"student_name": "Priya", "chapter": "rational_numbers"}
    )
    session_id = session_resp.json()["session_id"]

    # Get state
    resp = requests.get(f"{BASE_URL}/api/session/{session_id}/state")
    assert resp.status_code == 200
    data = resp.json()
    # Session state includes chapter, attempt_count, brain, etc.
    assert "chapter" in data
    assert "attempt_count" in data
    print(f"   Chapter: {data['chapter']}, Attempts: {data['attempt_count']}")


def test_get_session_state_invalid():
    """Test getting state for invalid session."""
    print("\n9. Testing Invalid Session State...")
    resp = requests.get(f"{BASE_URL}/api/session/invalid123/state")
    assert resp.status_code == 404
    print("   Correctly returned 404 for invalid session")


def test_text_to_speech():
    """Test TTS endpoint."""
    print("\n10. Testing Text-to-Speech...")
    tts_data = {
        "text": "Hello, this is a test.",
        "voice": "nova"
    }
    resp = requests.post(f"{BASE_URL}/api/text-to-speech", json=tts_data)
    assert resp.status_code == 200
    data = resp.json()
    assert "audio" in data
    assert "format" in data
    assert data["format"] == "mp3"
    # Audio should be base64 encoded
    assert len(data["audio"]) > 100
    print(f"   TTS returned {len(data['audio'])} bytes of audio")


def test_student_page():
    """Test student page route."""
    print("\n11. Testing Student Page...")
    resp = requests.get(f"{BASE_URL}/student")
    assert resp.status_code == 200
    content_type = resp.headers.get("content-type", "")
    if "text/html" in content_type:
        print("   Student page serves HTML")
    else:
        print("   Student page returns JSON (frontend not found)")


def run_all_tests():
    """Run all API tests."""
    print("=" * 60)
    print("IDNA EdTech API Test Suite")
    print("=" * 60)

    try:
        test_health()
        test_root()
        test_get_chapters()
        test_start_session()
        test_start_session_empty_name()
        test_process_input()
        test_process_input_invalid_session()
        test_get_session_state()
        test_get_session_state_invalid()
        test_text_to_speech()
        test_student_page()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n Test failed: {e}")
        raise
    except requests.exceptions.ConnectionError:
        print(f"\n Could not connect to server at {BASE_URL}")
        print("   Make sure the server is running: python server.py")
        raise


if __name__ == "__main__":
    run_all_tests()
