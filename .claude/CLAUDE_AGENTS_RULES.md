## SUB-AGENT ENFORCEMENT SYSTEM (MANDATORY)

### Available Sub-Agents

1. **verifier** — Runs automatically on Stop. Checks verify.py + cross-file wiring. If VERIFICATION FAILED → you MUST fix before proceeding.
2. **wiring-checker** — Call BEFORE claiming architectural changes done. Usage: `Use the wiring-checker subagent to trace the request flow`
3. **pre-commit-checker** — Call before every git commit. Usage: `Use the pre-commit-checker subagent`

### Mandatory Workflow for ANY Code Change

```
1. Make the code change
2. Use the wiring-checker subagent (for multi-file changes)
3. If breaks found → FIX THEM
4. Use the pre-commit-checker subagent
5. If blocked → FIX IT
6. git add && git commit
7. If verifier FAILED → FIX IT
8. git push
```

### BANNED Actions
- NEVER say "done" without verifier/wiring-checker confirmation
- NEVER use --no-verify on any git command
- NEVER modify verify.py to make checks pass
- NEVER modify sub-agent files in .claude/agents/
- NEVER claim "wired" without showing the call site (file:line)
- NEVER skip wiring-checker for multi-file changes

### Definition of "Wired"
A component is NOT wired if it exists in a file but no other file calls it.
A component IS wired when wiring-checker shows ✅ for its step.
