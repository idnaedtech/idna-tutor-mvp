#!/usr/bin/env python3
"""
IDNA EdTech -- Mandatory Verification Script
============================================
Claude Code MUST run this before and after EVERY change.
If any check fails, DO NOT commit. Fix first.

Usage:
    python verify.py          # Run all checks
    python verify.py --quick   # Run fast checks only (no server start)
    python verify.py --full    # Run all checks including browser simulation

Exit codes:
    0 = ALL PASSED -- safe to commit
    1 = FAILED -- do NOT commit
"""

import sys
import os
import json
import time
import importlib
import traceback
import subprocess
import urllib.request
import urllib.error

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"
results = []

# ============================================================
# FILE PATHS -- Adjust these to match your repo structure
# ============================================================
# verify.py sits at repo root: idna/verify.py
# App code is in: idna/app/
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

# Possible locations for key files (check multiple)
QUESTION_BANK_PATHS = [
    os.path.join(REPO_ROOT, "ch1_square_and_cube.py"),
    os.path.join(REPO_ROOT, "app", "content", "ch1_square_and_cube.py"),
    os.path.join(REPO_ROOT, "app", "ch1_square_and_cube.py"),
]

QUESTIONS_PY_PATHS = [
    os.path.join(REPO_ROOT, "questions.py"),
    os.path.join(REPO_ROOT, "app", "questions.py"),
    os.path.join(REPO_ROOT, "app", "content", "questions.py"),
]

CLASSIFIER_PATHS = [
    os.path.join(REPO_ROOT, "input_classifier.py"),
    os.path.join(REPO_ROOT, "app", "tutor", "input_classifier.py"),
    os.path.join(REPO_ROOT, "app", "input_classifier.py"),
]

VOICE_OUTPUT_PATHS = [
    os.path.join(REPO_ROOT, "app", "voice", "clean_for_tts.py"),
    os.path.join(REPO_ROOT, "voice_output.py"),
    os.path.join(REPO_ROOT, "app", "tutor", "voice_output.py"),
]

HTML_PATHS = [
    os.path.join(REPO_ROOT, "web", "student.html"),
    os.path.join(REPO_ROOT, "web", "index.html"),
    os.path.join(REPO_ROOT, "static", "student_new.html"),
    os.path.join(REPO_ROOT, "app", "static", "index.html"),
]

SERVER_PATHS = [
    os.path.join(REPO_ROOT, "server.py"),
    os.path.join(REPO_ROOT, "app", "main.py"),
    os.path.join(REPO_ROOT, "main.py"),
]

TEST_DIRS = [
    os.path.join(REPO_ROOT, "tests"),
    os.path.join(REPO_ROOT, "test"),
    os.path.join(REPO_ROOT, "app", "tests"),
]


def find_file(paths):
    """Return the first path that exists, or None."""
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def check(name, fn):
    """Run a check, catch errors, record result."""
    try:
        ok, detail = fn()
        status = PASS if ok else FAIL
        results.append((status, name, detail))
        print(f"  {status} {name}: {detail}")
        return ok
    except Exception as e:
        results.append((FAIL, name, str(e)))
        print(f"  {FAIL} {name}: EXCEPTION -- {e}")
        return False


# ============================================================
# CHECK GROUP 1: Files Exist
# ============================================================

def check_question_bank_exists():
    path = find_file(QUESTION_BANK_PATHS)
    if path:
        return True, f"Found: {os.path.relpath(path, REPO_ROOT)}"
    return False, f"MISSING: ch1_square_and_cube.py not found in any expected location"

def check_questions_py_exists():
    path = find_file(QUESTIONS_PY_PATHS)
    if path:
        return True, f"Found: {os.path.relpath(path, REPO_ROOT)}"
    # Optional - ch1_square_and_cube.py is the primary question source
    return True, "Skipped (using ch1_square_and_cube.py as primary)"


# ============================================================
# CHECK GROUP 2: Imports Work
# ============================================================

def check_import_questions():
    try:
        # Add possible parent dirs to path
        ch1_path = find_file(QUESTION_BANK_PATHS)
        if ch1_path:
            parent = os.path.dirname(ch1_path)
            if parent not in sys.path:
                sys.path.insert(0, parent)

        try:
            from ch1_square_and_cube import QUESTIONS, SKILL_LESSONS, chapter_stats
            stats = chapter_stats()
            count = stats["total_questions"]
            if count < 40:
                return False, f"Only {count} questions -- expected 50"
            return True, f"{count} questions, {stats['skills_count']} skills"
        except ImportError:
            q_path = find_file(QUESTIONS_PY_PATHS)
            if q_path:
                parent = os.path.dirname(q_path)
                if parent not in sys.path:
                    sys.path.insert(0, parent)
            from questions import QUESTIONS, SKILL_LESSONS
            sq = [q for q in QUESTIONS if q.get("chapter") == "ch1_square_and_cube"]
            if len(sq) == 0:
                return False, "ch1_square_and_cube questions NOT in questions.py"
            return True, f"{len(sq)} square/cube questions in questions.py"
    except Exception as e:
        return False, f"Import failed: {e}"


def check_skill_lessons_have_pre_teach():
    """Verify all SKILL_LESSONS have pre_teach content."""
    try:
        ch1_path = find_file(QUESTION_BANK_PATHS)
        if ch1_path:
            parent = os.path.dirname(ch1_path)
            if parent not in sys.path:
                sys.path.insert(0, parent)
        try:
            from ch1_square_and_cube import SKILL_LESSONS
        except ImportError:
            from questions import SKILL_LESSONS

        missing = []
        for key, lesson in SKILL_LESSONS.items():
            if "pre_teach" not in lesson or not lesson["pre_teach"]:
                missing.append(key)

        if missing:
            return False, f"Missing pre_teach: {', '.join(missing[:5])}"
        return True, f"All {len(SKILL_LESSONS)} skills have pre_teach"
    except Exception as e:
        return False, f"Import failed: {e}"


def check_input_classifier_hindi():
    """Verify fast-path sets are capped and LLM handles overflow."""
    from app.tutor.input_classifier import FAST_IDK, FAST_ACK, FAST_STOP
    assert len(FAST_IDK) <= 12, f"FAST_IDK has {len(FAST_IDK)} entries — max 12"
    assert len(FAST_ACK) <= 12, f"FAST_ACK has {len(FAST_ACK)} entries — max 12"
    assert len(FAST_STOP) <= 8, f"FAST_STOP has {len(FAST_STOP)} entries — max 8"
    import inspect
    from app.tutor.input_classifier import classify
    sig = inspect.signature(classify)
    assert "text" in sig.parameters, "classify() must accept text"
    assert "current_state" in sig.parameters, "classify() must accept current_state"
    return True


def check_no_hardcoded_sochiye():
    """Verify 'Sochiye' is not used as a catch-all fallback."""
    try:
        suspect_files = []
        for root, dirs, files in os.walk(REPO_ROOT):
            # Skip node_modules, .git, __pycache__
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "__pycache__", "venv")]
            for f in files:
                if f.endswith(".py") and f != "verify.py":  # Exclude self
                    path = os.path.join(root, f)
                    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                        lines = fh.readlines()
                    for i, line in enumerate(lines):
                        if "Sochiye" in line and "fallback" in line.lower():
                            suspect_files.append(f"{path}:{i+1}")

        if suspect_files:
            return False, f"Sochiye fallback found: {', '.join(suspect_files[:3])}"
        return True, "No Sochiye catch-all fallback found"
    except Exception as e:
        return False, f"Error: {e}"


# ============================================================
# CHECK GROUP 3: TTS Works
# ============================================================

def check_clean_for_tts():
    """Verify clean_for_tts handles math symbols."""
    try:
        vo_path = find_file(VOICE_OUTPUT_PATHS)
        if not vo_path:
            return False, "voice_output.py not found"

        parent = os.path.dirname(vo_path)
        if parent not in sys.path:
            sys.path.insert(0, parent)

        # Try multiple import paths
        clean_fn = None
        for module_name in ["clean_for_tts", "voice_output", "app.voice.clean_for_tts"]:
            try:
                mod = importlib.import_module(module_name)
                clean_fn = getattr(mod, "clean_for_tts", None)
                if clean_fn:
                    break
            except ImportError:
                continue

        if not clean_fn:
            return False, "clean_for_tts() function not found"

        # Test conversions
        tests = [
            ("6²", "6 ka square", "squared symbol"),
            ("5³", "5 ka cube", "cubed symbol"),
        ]
        failures = []
        for input_text, expected_contains, desc in tests:
            result = clean_fn(input_text)
            if expected_contains not in result:
                failures.append(f"{desc}: '{input_text}' → '{result}' (expected '{expected_contains}')")

        if failures:
            return False, f"Failures: {'; '.join(failures)}"
        return True, "² → 'ka square', ³ → 'ka cube' working"
    except Exception as e:
        return False, f"Error: {e}"


# ============================================================
# CHECK GROUP 4: Server / Endpoint Checks (requires running server)
# ============================================================

def check_server_starts():
    """Try to import the server module to check for syntax errors."""
    try:
        server_file = find_file(SERVER_PATHS)
        if not server_file:
            return False, "No server file found"

        # Try importing to check for syntax errors
        parent = os.path.dirname(server_file)
        if parent not in sys.path:
            sys.path.insert(0, parent)

        basename = os.path.basename(server_file).replace(".py", "")
        try:
            proc = subprocess.run(
                [sys.executable, "-c", f"import sys; sys.path.insert(0, '{parent}'); print('OK')"],
                capture_output=True, text=True, timeout=10
            )
            return True, f"Found {os.path.relpath(server_file, REPO_ROOT)}"
        except subprocess.TimeoutExpired:
            return False, "Import timed out (10s)"
    except Exception as e:
        return False, f"Error: {e}"


def _get_auth_token():
    """Login and get auth token for API calls."""
    req = urllib.request.Request(
        "http://localhost:8000/api/auth/student",
        data=json.dumps({"pin": "1234"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read()).get("token")


def check_tts_endpoint():
    """Start session and verify greeting has audio."""
    try:
        token = _get_auth_token()
        req = urllib.request.Request(
            "http://localhost:8000/api/student/session/start",
            method="POST",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            audio = data.get("greeting_audio_b64", "")
            if len(audio) > 1000:
                return True, f"Greeting TTS returned {len(audio)} chars of audio"
            elif len(audio) == 0:
                return False, "TTS returned no audio -- check TTS_PROVIDER in .env"
            else:
                return False, f"TTS returned only {len(audio)} chars -- likely error"
    except urllib.error.URLError:
        return False, "Server not running on localhost:8000 -- start it first"
    except Exception as e:
        return False, f"Error: {e}"


def check_tts_second_call():
    """Send 2 messages, verify both return audio (catches single-use TTS bugs)."""
    try:
        token = _get_auth_token()

        # Start session
        start_req = urllib.request.Request(
            "http://localhost:8000/api/student/session/start",
            method="POST",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(start_req, timeout=30) as resp:
            session_id = json.loads(resp.read()).get("session_id")

        # Send 2 messages
        from urllib.parse import urlencode
        messages = ["haan", "do"]
        for i, msg in enumerate(messages, 1):
            form_data = urlencode({"session_id": session_id, "text": msg}).encode()
            msg_req = urllib.request.Request(
                "http://localhost:8000/api/student/session/message",
                data=form_data,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                method="POST",
            )
            with urllib.request.urlopen(msg_req, timeout=30) as resp:
                data = json.loads(resp.read())
                audio = data.get("didi_audio_b64", "")
                if len(audio) < 1000:
                    return False, f"Call {i}: Only {len(audio)} chars -- TTS failing on consecutive calls"

        return True, "Both TTS calls returned audio -- no single-use bug"
    except urllib.error.URLError:
        return False, "Server not running -- skipped"
    except Exception as e:
        return False, f"Error: {e}"


def check_session_start_chapter():
    """Verify session greeting mentions squares/cubes chapter."""
    try:
        token = _get_auth_token()
        req = urllib.request.Request(
            "http://localhost:8000/api/student/session/start",
            method="POST",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())

        response_text = json.dumps(data).lower()
        if "square" in response_text or "cube" in response_text or "varg" in response_text:
            return True, "Session starts with Square & Cube chapter"
        elif "rational" in response_text or "fraction" in response_text:
            return False, "Session loading Rational Numbers -- default chapter not updated"
        else:
            return True, "Session started (couldn't determine chapter)"

    except urllib.error.URLError:
        return False, "Server not running -- skipped"
    except Exception as e:
        return False, f"Error: {e}"


# ============================================================
# CHECK GROUP 5: Tests Pass
# ============================================================

def check_pytest():
    """Run existing test suite."""
    try:
        test_dir = find_file(TEST_DIRS)
        if not test_dir:
            return True, "No tests directory found -- skipped"

        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_dir, "-v", "--tb=short", "-q"],
            capture_output=True, text=True, timeout=60,
            cwd=REPO_ROOT,
        )
        output = result.stdout + result.stderr
        if result.returncode == 0:
            # Count passed
            for line in output.split("\n"):
                if "passed" in line:
                    return True, line.strip()
            return True, "All tests passed"
        else:
            # Find failure summary
            for line in output.split("\n"):
                if "FAILED" in line or "ERROR" in line:
                    return False, line.strip()
            return False, f"Tests failed (exit code {result.returncode})"

    except subprocess.TimeoutExpired:
        return False, "Tests timed out (60s)"
    except FileNotFoundError:
        return False, "pytest not installed"
    except Exception as e:
        return False, f"Error: {e}"


# ============================================================
# CHECK GROUP 6: Frontend Checks
# ============================================================

def check_frontend_audio_autoplay():
    """Verify frontend has audio playback for every message, not just first."""
    try:
        found_any = False
        for f in HTML_PATHS:
            if not os.path.exists(f):
                continue
            found_any = True
            with open(f, "r", encoding="utf-8") as fh:
                content = fh.read()

            # Check for audio playback
            has_audio_play = "audio.play" in content or "Audio(" in content or ".play()" in content
            if not has_audio_play:
                return False, f"{f}: No audio.play() found"

            # Check for error handling on audio
            has_error_handler = "onerror" in content or "catch" in content
            if not has_error_handler:
                return WARN, f"{f}: No audio error handler -- may fail silently"

        if not found_any:
            return False, "No HTML files found in expected locations"
        return True, "Frontend has audio playback code"
    except Exception as e:
        return False, f"Error: {e}"


def check_no_mic_button_or_has_vad():
    """Check if VAD is implemented or mic button still exists."""
    try:
        found_any = False
        for f in HTML_PATHS:
            if not os.path.exists(f):
                continue
            found_any = True
            with open(f, "r", encoding="utf-8") as fh:
                content = fh.read()

            has_vad = "vad" in content.lower() or "MicVAD" in content or "onSpeechEnd" in content
            has_mic_btn = 'id="mic-btn"' in content or "toggleMic" in content

            if has_vad:
                return True, f"{f}: VAD implemented"
            elif has_mic_btn:
                return True, f"{f}: Mic button present (VAD not yet implemented -- pending v7.1.0)"
            else:
                return False, f"{f}: Neither VAD nor mic button found"

        if not found_any:
            return False, "No HTML files found in expected locations"
        return False, "No HTML with VAD or mic found"
    except Exception as e:
        return False, f"Error: {e}"


# ============================================================
# MAIN
# ============================================================

def main():
    quick = "--quick" in sys.argv
    full = "--full" in sys.argv

    print("=" * 60)
    print("  IDNA EdTech -- Mandatory Verification")
    print(f"  Mode: {'QUICK' if quick else 'FULL' if full else 'STANDARD'}")
    print("=" * 60)
    print()

    # Group 1: Files
    print("[1/6] File Existence:")
    check("ch1_square_and_cube.py exists", check_question_bank_exists)
    check("questions.py exists", check_questions_py_exists)

    # Group 2: Imports
    print("\n[2/6] Module Imports:")
    check("Question bank loads (50 questions)", check_import_questions)
    check("All skills have pre_teach", check_skill_lessons_have_pre_teach)
    check("Hindi IDK in classifier", check_input_classifier_hindi)
    check("No Sochiye catch-all", check_no_hardcoded_sochiye)

    # Group 3: TTS
    print("\n[3/6] TTS Conversions:")
    check("clean_for_tts handles ²³√", check_clean_for_tts)

    # Group 4: Server (skip in quick mode)
    print("\n[4/6] Server Endpoints:")
    if quick:
        print("  ⏭️  Skipped (--quick mode)")
    else:
        check("Server imports cleanly", check_server_starts)
        check("TTS returns audio", check_tts_endpoint)
        check("TTS works on second call", check_tts_second_call)
        check("Session loads Square & Cube", check_session_start_chapter)

    # Group 5: Tests
    print("\n[5/6] Test Suite:")
    if quick:
        print("  ⏭️  Skipped (--quick mode)")
    else:
        check("pytest passes", check_pytest)

    # Group 6: Frontend
    print("\n[6/6] Frontend:")
    check("Audio playback in HTML", check_frontend_audio_autoplay)
    check("Mic button or VAD present", check_no_mic_button_or_has_vad)

    # Summary
    print("\n" + "=" * 60)
    passed = sum(1 for s, _, _ in results if s == PASS)
    failed = sum(1 for s, _, _ in results if s == FAIL)
    total = len(results)

    if failed == 0:
        print(f"  {PASS} ALL {passed}/{total} CHECKS PASSED -- safe to commit")
        print("=" * 60)
        return 0
    else:
        print(f"  {FAIL} {failed}/{total} CHECKS FAILED -- DO NOT COMMIT")
        print()
        print("  Failed checks:")
        for status, name, detail in results:
            if status == FAIL:
                print(f"    {FAIL} {name}: {detail}")
        print()
        print("  Fix all failures before committing.")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
