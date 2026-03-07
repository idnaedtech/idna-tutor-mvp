---
name: pre-commit-checker
description: Quick quality gate before git commits. Runs verify.py --quick and basic checks.
tools:
  - Bash
  - Grep
model: haiku
maxTurns: 5
---

# Pre-Commit Quality Gate

Fast check before committing. 5 turns max.

## Checks
1. `python verify.py --quick 2>&1` — if FAIL → block
2. `git diff --cached --name-only -- "*.py" | xargs python -c "import py_compile; import sys; [py_compile.compile(f, doraise=True) for f in sys.argv[1:]]" 2>&1` — syntax check on staged files

## Output
`PRE-COMMIT: PASS ✅` or `PRE-COMMIT: BLOCKED ❌ <reason>`
