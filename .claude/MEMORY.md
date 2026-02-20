# IDNA Project Enforcement Rules

## MANDATORY WORKFLOW
1. After ANY file modification, run: `python verify.py`
2. Before ANY commit, use wiring-checker subagent
3. Never use `--no-verify` flag
4. Never claim "done" without verify.py showing 14/14 PASSED
5. Never modify verify.py itself

## DEFINITION OF "WIRED"
A component is "wired" only if you can show:
- The call site (file:line) where it's invoked
- The import statement that brings it in
File existence alone is NOT wiring.

## TASK TRACKING
Every task's TodoWrite list MUST end with:
- Run wiring-checker subagent
- Run verify.py — confirm 14/14 PASSED
- Commit and push (only when user asks)
Do NOT mark task as completed until these are done.

## LINT COMMAND
The lint/verify command for this project is: `python verify.py`
