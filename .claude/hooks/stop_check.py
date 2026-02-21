#!/usr/bin/env python3
"""Stop hook for IDNA - checks if modified files were verified."""
import json, sys, subprocess, os

# Read input from stdin
input_data = json.load(sys.stdin)

# CRITICAL: Prevent infinite loops
if input_data.get("stop_hook_active", False):
    # Already in a stop hook cycle, allow stop
    print(json.dumps({}))
    sys.exit(0)

# Check if any Python files were modified in this session
result = subprocess.run(
    ["git", "diff", "--name-only", "HEAD"],
    capture_output=True, text=True, cwd=input_data.get("cwd", ".")
)

modified_py = [f for f in result.stdout.strip().split("\n")
               if f.endswith(".py") and f and not f.startswith(".claude/")]

if modified_py:
    # Files modified — check if verify.py was run
    # Simple heuristic: check if last commit is recent (within 60s)
    output = {
        "decision": "block",
        "reason": f"Modified files detected: {', '.join(modified_py[:5])}. "
                  f"Run verify.py and confirm ALL checks PASSED before completing. "
                  f"Use the wiring-checker subagent to verify cross-file connections."
    }
    print(json.dumps(output))
else:
    # No modifications, allow stop
    print(json.dumps({}))
