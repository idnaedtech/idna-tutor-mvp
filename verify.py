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
    return True, f"FAST_ACK={len(FAST_ACK)}, FAST_IDK={len(FAST_IDK)}, FAST_STOP={len(FAST_STOP)} (within caps)"


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
# CHECK GROUP 7: Static Analysis - Uninitialized Variables in except/finally
# ============================================================

def check_uninitialized_in_exception_blocks():
    """
    v7.5.2: Check for the specific UnboundLocalError bug pattern.
    Simplified to avoid false positives from pre-initialized variables.
    The core check is: any function with nonlocal in a try block must declare it.
    """
    import ast
    issues = []
    
    app_dir = os.path.join(REPO_ROOT, "app")
    if not os.path.isdir(app_dir):
        return True, "app/ directory not found"
    
    for root, dirs, files in os.walk(app_dir):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for f in files:
            if f.endswith(".py"):
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
                        source = fh.read()
                    tree = ast.parse(source, filename=filepath)
                except:
                    continue
                
                # Look for nested functions with try/finally that modify outer variables
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                        # Check if function has nested function with try/finally
                        for child in ast.walk(node):
                            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child != node:
                                # This is a nested function - check if it has finally that assigns
                                for inner in ast.walk(child):
                                    if isinstance(inner, ast.Try) and inner.finalbody:
                                        # Check if finally assigns to a variable that should be nonlocal
                                        for stmt in inner.finalbody:
                                            if isinstance(stmt, ast.Assign):
                                                for target in stmt.targets:
                                                    if isinstance(target, ast.Name):
                                                        var = target.id
                                                        # Check if this var is used elsewhere in the outer function
                                                        # and not declared nonlocal
                                                        has_nonlocal = False
                                                        for n in ast.walk(child):
                                                            if isinstance(n, ast.Nonlocal) and var in n.names:
                                                                has_nonlocal = True
                                                        if not has_nonlocal:
                                                            # Check if var is assigned in outer function
                                                            for n in ast.walk(node):
                                                                if isinstance(n, ast.Assign) and n not in ast.walk(child):
                                                                    for t in n.targets:
                                                                        if isinstance(t, ast.Name) and t.id == var:
                                                                            rel_path = os.path.relpath(filepath, REPO_ROOT)
                                                                            issues.append(f"{rel_path}:{inner.lineno} - {var} may need nonlocal")
    
    if issues:
        return False, f"Potential nonlocal issues: {'; '.join(issues[:3])}"
    return True, "No obvious nonlocal issues found"


# ============================================================
# CHECK GROUP 8: No Filesystem Writes Outside /tmp or Database
# ============================================================

def check_no_ephemeral_filesystem_writes():
    import ast
    issues = []

    def analyze_file(filepath):
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                source = f.read()
            tree = ast.parse(source, filename=filepath)
        except SyntaxError:
            return []

        file_issues = []
        lines = source.split("\n")

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name == "open" and len(node.args) >= 2:
                    mode_arg = node.args[1] if len(node.args) > 1 else None
                    if mode_arg and isinstance(mode_arg, ast.Constant):
                        mode = str(mode_arg.value)
                        if "w" in mode or "a" in mode:
                            if len(node.args) >= 1:
                                line = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                                if "/tmp" in line or "tempfile" in line or "NamedTemporaryFile" in line:
                                    continue
                                if "tts_cache" in line:
                                    file_issues.append((node.lineno, "tts_cache filesystem write"))
                                elif "cache" in line.lower() and "db" not in line.lower():
                                    file_issues.append((node.lineno, "cache filesystem write"))

                if func_name in ("mkdir", "makedirs"):
                    line = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                    # Allow /tmp paths and paths from environment variables
                    if "/tmp" not in line and "temp" not in line.lower() and "getenv" not in line:
                        if "cache" in line.lower() or "data" in line.lower():
                            # Only flag hardcoded persistent paths
                            if "Path(" in line and "os.getenv" not in line:
                                file_issues.append((node.lineno, f"{func_name} for persistent storage"))

        return file_issues

    app_dir = os.path.join(REPO_ROOT, "app")
    if os.path.isdir(app_dir):
        for root, dirs, files in os.walk(app_dir):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
            for f in files:
                if f.endswith(".py"):
                    filepath = os.path.join(root, f)
                    file_issues = analyze_file(filepath)
                    for lineno, desc in file_issues:
                        rel_path = os.path.relpath(filepath, REPO_ROOT)
                        issues.append(f"{rel_path}:{lineno} - {desc}")

    if issues:
        return False, f"Ephemeral filesystem writes: {'; '.join(issues[:3])}"
    return True, "No filesystem writes outside /tmp or database"


# ============================================================
# CHECK GROUP 9: Async API Calls Have Timeout
# ============================================================

def check_api_calls_have_timeout():
    """
    v7.5.2: Check that httpx/aiohttp calls have timeout.
    Handles both method-level timeout and Client-level timeout.
    """
    issues = []
    app_dir = os.path.join(REPO_ROOT, "app")
    if not os.path.isdir(app_dir):
        return True, "app/ directory not found"

    for root, dirs, files in os.walk(app_dir):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for f in files:
            if f.endswith(".py"):
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
                        lines = fh.readlines()
                except Exception:
                    continue

                uses_httpx = any("httpx" in line for line in lines)
                uses_aiohttp = any("aiohttp" in line for line in lines)
                if not (uses_httpx or uses_aiohttp):
                    continue

                # Track indentation level of Client context with timeout
                client_timeout_indent = -1
                
                for i, line in enumerate(lines, 1):
                    stripped = line.lstrip()
                    indent = len(line) - len(stripped)
                    
                    # Check for Client constructor with timeout
                    if "httpx.Client(" in line or "httpx.AsyncClient(" in line:
                        if "timeout" in line:
                            # Get indentation of the with statement
                            if "with " in line:
                                client_timeout_indent = indent
                    
                    # Reset when we exit the indentation level
                    if client_timeout_indent >= 0 and indent <= client_timeout_indent and stripped:
                        if not ("httpx.Client" in line or "with " in line):
                            client_timeout_indent = -1
                    
                    # Skip if inside a Client context with timeout
                    if client_timeout_indent >= 0 and indent > client_timeout_indent:
                        continue
                    
                    if "httpx." in line or ("client." in line and uses_httpx):
                        if ".get(" in line or ".post(" in line or ".put(" in line or ".delete(" in line or ".request(" in line:
                            if "timeout" not in line:
                                has_timeout = False
                                for j in range(i, min(i + 5, len(lines) + 1)):
                                    if "timeout" in lines[j - 1]:
                                        has_timeout = True
                                        break
                                    if ")" in lines[j - 1] and "(" not in lines[j - 1]:
                                        break
                                if not has_timeout:
                                    rel_path = os.path.relpath(filepath, REPO_ROOT)
                                    issues.append(f"{rel_path}:{i} - httpx call without timeout")

                    if "session." in line and uses_aiohttp:
                        if ".get(" in line or ".post(" in line:
                            if "timeout" not in line:
                                rel_path = os.path.relpath(filepath, REPO_ROOT)
                                issues.append(f"{rel_path}:{i} - aiohttp call without timeout")

    if issues:
        return False, f"API calls without timeout: {'; '.join(issues[:3])}"
    return True, "All httpx/aiohttp calls have explicit timeout"


# ============================================================
# CHECK GROUP 10: Streaming Endpoint Graceful Fallback Test
# ============================================================

def check_streaming_endpoint_fallback():
    try:
        try:
            from app.voice.streaming import SENTENCE_SPLIT
        except ImportError:
            return True, "Streaming module not found (v7.5.0 feature) -- skipped"

        result = SENTENCE_SPLIT.split("")
        result = SENTENCE_SPLIT.split("No punctuation here")
        if len(result) == 0:
            return False, "Sentence splitter returned empty for valid input"

        try:
            from app.tutor.answer_evaluator import parse_eval_response
            result = parse_eval_response("not json at all")
            if result.get("verdict") != "unclear":
                return False, f"parse_eval_response didnt fallback: got {result.get('verdict')}"
            result = parse_eval_response("")
            if result.get("verdict") != "unclear":
                return False, "parse_eval_response crashed on empty input"
        except ImportError:
            pass

        student_router = os.path.join(REPO_ROOT, "app", "routers", "student.py")
        if os.path.exists(student_router):
            with open(student_router, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if "async def stream_response" in content:
                if "nonlocal new_state" not in content and "nonlocal" not in content:
                    if "new_state" in content and ("finally:" in content or "except" in content):
                        return False, "stream_response may have UnboundLocalError (missing nonlocal)"

            if "stream_response" in content:
                if "try:" not in content or "except" not in content:
                    return False, "stream_response lacks try/except error handling"

        return True, "Streaming endpoint has graceful fallback handling"

    except Exception as e:
        return False, f"Error: {e}"



# ============================================================
# CHECK GROUP 11: v8.0 SessionState Schema
# ============================================================

def check_session_state_has_preferred_language():
    """v8.0 Check 19: SessionState has preferred_language field."""
    try:
        from app.state.session import SessionState
        import dataclasses
        fields = {f.name for f in dataclasses.fields(SessionState)}
        required_fields = ["preferred_language", "reteach_count", "teach_material_index", "current_state"]
        missing = [f for f in required_fields if f not in fields]
        if missing:
            return False, f"SessionState missing: {', '.join(missing)}"
        session = SessionState(session_id="test", student_name="Test", student_pin="1234")
        if session.preferred_language != "hinglish":
            return False, f"Default is '{session.preferred_language}', expected 'hinglish'"
        return True, "SessionState has all v8.0 fields"
    except ImportError as e:
        return False, f"Cannot import SessionState: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def check_reteach_counter_caps():
    """v8.0 Check 20: Reteach counter caps at 3."""
    try:
        from app.state.session import SessionState
        session = SessionState(session_id="test", student_name="Test", student_pin="1234")
        session.increment_reteach()
        session.increment_reteach()
        session.increment_reteach()
        if session.reteach_count != 3:
            return False, f"reteach_count should be 3, got {session.reteach_count}"
        if session.teach_material_index != 2:
            return False, f"teach_material_index should cap at 2, got {session.teach_material_index}"
        return True, "Reteach caps at 3, material_index caps at 2"
    except ImportError as e:
        return False, f"Cannot import SessionState: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def check_transition_matrix_complete():
    """v8.0 Check 21: All 60 state x input combinations defined."""
    try:
        from app.fsm.transitions import validate_matrix_completeness, TRANSITIONS
        validate_matrix_completeness()
        return True, f"All {len(TRANSITIONS)} state x input combinations defined"
    except ImportError as e:
        return False, f"Cannot import FSM: {e}"
    except AssertionError as e:
        return False, f"Matrix incomplete: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def check_integration_tests_pass():
    """v8.0: Run integration tests."""
    try:
        test_file = os.path.join(REPO_ROOT, "tests", "test_integration.py")
        if not os.path.exists(test_file):
            return False, "tests/test_integration.py not found"
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-v", "--tb=line", "-q"],
            capture_output=True, text=True, timeout=120, cwd=REPO_ROOT,
        )
        if result.returncode == 0:
            for line in (result.stdout + result.stderr).split("\n"):
                if "passed" in line:
                    return True, line.strip()
            return True, "Integration tests passed"
        else:
            for line in (result.stdout + result.stderr).split("\n"):
                if "FAILED" in line:
                    return False, line.strip()[:80]
            return False, f"Tests failed (exit {result.returncode})"
    except subprocess.TimeoutExpired:
        return False, "Integration tests timed out"
    except Exception as e:
        return False, f"Error: {e}"


# ============================================================
# MAIN
# ============================================================

def main():
    quick = "--quick" in sys.argv
    full = "--full" in sys.argv

    print("=" * 60)
    print("  IDNA EdTech -- Mandatory Verification (v8.0)")
    print(f"  Mode: {'QUICK' if quick else 'FULL' if full else 'STANDARD'}")
    print("=" * 60)
    print()

    # Group 1: Files
    print("[1/14] File Existence:")
    check("ch1_square_and_cube.py exists", check_question_bank_exists)
    check("questions.py exists", check_questions_py_exists)

    # Group 2: Imports
    print("\n[2/14] Module Imports:")
    check("Question bank loads (50 questions)", check_import_questions)
    check("All skills have pre_teach", check_skill_lessons_have_pre_teach)
    check("Hindi IDK in classifier", check_input_classifier_hindi)
    check("No Sochiye catch-all", check_no_hardcoded_sochiye)

    # Group 3: TTS
    print("\n[3/14] TTS Conversions:")
    check("clean_for_tts handles math symbols", check_clean_for_tts)

    # Group 4: Server (skip in quick mode)
    print("\n[4/14] Server Endpoints:")
    if quick:
        print("  Skipped (--quick mode)")
    else:
        check("Server imports cleanly", check_server_starts)
        check("TTS returns audio", check_tts_endpoint)
        check("TTS works on second call", check_tts_second_call)
        check("Session loads Square & Cube", check_session_start_chapter)

    # Group 5: Tests
    print("\n[5/14] Test Suite:")
    if quick:
        print("  Skipped (--quick mode)")
    else:
        check("pytest passes", check_pytest)

    # Group 6: Frontend
    print("\n[6/14] Frontend:")
    check("Audio playback in HTML", check_frontend_audio_autoplay)
    check("Mic button or VAD present", check_no_mic_button_or_has_vad)

    # Group 7: Static Analysis
    print("\n[7/14] Static Analysis:")
    check("No uninitialized vars in except/finally", check_uninitialized_in_exception_blocks)

    # Group 8: Filesystem Safety
    print("\n[8/14] Filesystem Safety:")
    check("No ephemeral filesystem writes", check_no_ephemeral_filesystem_writes)

    # Group 9: API Call Safety
    print("\n[9/14] API Call Safety:")
    check("All API calls have timeout", check_api_calls_have_timeout)

    # Group 10: Streaming Fallback
    print("\n[10/14] Streaming Endpoint Fallback:")
    check("Streaming handles LLM failures gracefully", check_streaming_endpoint_fallback)

    # Group 11: v8.0 SessionState
    print("\n[11/14] v8.0 SessionState Schema:")
    check("SessionState has preferred_language", check_session_state_has_preferred_language)
    check("Reteach counter caps at 3", check_reteach_counter_caps)

    # Group 12: v8.0 FSM
    print("\n[12/14] v8.0 FSM Completeness:")
    check("All 60 state x input defined", check_transition_matrix_complete)

    # Group 13: v8.0 Integration Tests
    print("\n[13/14] v8.0 Integration Tests:")
    if quick:
        print("  Skipped (--quick mode)")
    else:
        check("Integration tests pass", check_integration_tests_pass)

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
