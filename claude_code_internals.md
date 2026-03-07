# Claude Code Internals — IDNA Enforcement Reference

**Compiled:** Feb 20, 2026 | **Sources:** Piebald-AI/claude-code-system-prompts (v2.1.47), asgeirtj/system_prompts_leaks, CorridorSecurity/hookshot

---

## 1. STOP HOOK — EXACT SCHEMA (THIS FIXES TOMORROW'S BUG)

### The Problem We Had
Our stop hook output `{"decision": "allow"}` — Claude Code rejected it because `"allow"` is not a valid value.

### Correct Stop Hook JSON Schema

**StopInput** (what Claude Code sends TO your hook via stdin):
```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript",
  "cwd": "/c/Users/User/Documents/idna",
  "permission_mode": "default",
  "hook_event_name": "Stop",
  "stop_hook_active": false
}
```

**CRITICAL FIELD:** `stop_hook_active` — is `true` when Claude is already continuing as a result of a previous stop hook. **You MUST check this to prevent infinite loops.**

**StopOutput** (what your hook must output to stdout):
```json
{
  "decision": "block",
  "reason": "Files were modified but not verified. Run wiring-checker and verify.py before completing."
}
```

### Valid Fields for Stop Hook Output:
| Field | Type | Purpose |
|---|---|---|
| `decision` | `"block"` or omit | `"block"` prevents Claude from stopping. Omitting allows stop. |
| `reason` | string | Shown to Claude when decision is "block" — tells it what to fix |
| `continue` | boolean | Default true. Set false to stop Claude entirely |
| `stopReason` | string | Shown to user when continue is false |
| `suppressOutput` | boolean | Hides stdout from transcript |
| `systemMessage` | string | Warning shown to user in UI |

### Key Rules:
- **NOT** `"allow"` / `"deny"` / `"approve"` — those are for PreToolUse hooks
- For Stop hooks: `"block"` = keep working, omit decision = allow stop
- **ALWAYS check `stop_hook_active`** to prevent infinite loops
- Empty JSON `{}` = allow Claude to stop normally

---

## 2. CORRECT SETTINGS.JSON FOR IDNA

### Option A: Simple Command Hook (Recommended)
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/stop_check.py",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

### The stop_check.py script:
```python
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

modified_py = [f for f in result.stdout.strip().split("\n") if f.endswith(".py") and f]

if modified_py:
    # Files modified — check if verify.py was run
    # Simple heuristic: check if last commit is recent (within 60s)
    output = {
        "decision": "block",
        "reason": f"Modified files detected: {', '.join(modified_py[:5])}. "
                  f"Run verify.py and confirm 14/14 PASSED before completing. "
                  f"Use the wiring-checker subagent to verify cross-file connections."
    }
    print(json.dumps(output))
else:
    # No modifications, allow stop
    print(json.dumps({}))
```

### Option B: Agent Hook (More Powerful but Costlier)
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "agent",
            "prompt": "Verify that all modified files are properly wired into the request flow. Check verify.py passes 14/14. If not, return decision: block."
          }
        ]
      }
    ]
  }
}
```

Agent hooks spawn a separate Claude instance with Read/Edit/Bash tools. The agent prompt from Piebald-AI shows it receives:
> "You are verifying a stop condition in Claude Code. Your task is to verify that the agent completed the given plan. The conversation transcript is available at: ${TRANSCRIPT_PATH}. Use the available tools to inspect the codebase and verify the condition. Use as few steps as possible."

### Option C: Prompt Hook (Cheapest — LLM Evaluation, No Tools)
```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Were all modified Python files verified with verify.py? Did wiring-checker confirm no breaks? $ARGUMENTS"
          }
        ]
      }
    ]
  }
}
```
Note: Prompt hooks are only available for PreToolUse, PostToolUse, PermissionRequest — NOT for Stop events. Use command or agent for Stop hooks.

---

## 3. THREE HOOK TYPES COMPARED

| Feature | Command | Prompt | Agent |
|---|---|---|---|
| What it runs | Shell command | LLM evaluation (no tools) | Separate Claude with tools |
| Available for Stop? | ✅ Yes | ❌ No | ✅ Yes |
| Cost | Free | ~$0.001 | ~$0.005-0.01 |
| Can read files? | Via script | No | Yes (Read, Edit, Bash, Glob, Grep) |
| Can run tests? | Via script | No | Yes |
| Infinite loop risk | Must check `stop_hook_active` | N/A | Must check `stop_hook_active` |

**Recommendation for IDNA:** Use **Command Hook** (Option A) with the Python script. It's free, reliable, and checks `stop_hook_active` to prevent loops.

---

## 4. ALL HOOK EVENTS IN CLAUDE CODE

| Event | When It Fires | Use Case |
|---|---|---|
| `PreToolUse` | Before any tool executes | Block dangerous commands, validate inputs |
| `PostToolUse` | After any tool completes | Auto-format, logging, validation |
| `Stop` | When Claude finishes responding | **Our use case** — force verification |
| `UserPromptSubmit` | When user sends a message | Add context, modify input |
| `SessionStart` | When session begins | Inject project context |
| `PermissionRequest` | When Claude asks for permission | Auto-approve/deny specific tools |

### Matchers (for PreToolUse/PostToolUse):
```json
"matcher": "Bash"           // Match specific tool
"matcher": "Write|Edit"     // Match multiple tools
"matcher": "mcp__.*"        // Regex match MCP tools
```

Stop hooks don't use matchers — they fire on every response completion.

---

## 5. MEMORY.MD — PERSISTS ACROSS SESSIONS

From Claude Code's system prompt:
> "Your MEMORY.md is currently empty. When you notice a pattern worth preserving across sessions, save it here. Anything in MEMORY.md will be included in your system prompt next time."

**Location:** `.claude/MEMORY.md` in project root

### What to put in MEMORY.md for IDNA:
```markdown
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
- The data flow from request to the component

File existence alone is NOT wiring.

## TESTING CHECKLIST
Before declaring any task complete:
- [ ] verify.py 14/14 PASSED
- [ ] pytest 97+ tests PASSED  
- [ ] wiring-checker confirms no breaks
- [ ] git commit with descriptive message
- [ ] git push (pre-push hook validates)
```

This gets injected into Claude Code's system prompt on every session start — more durable than CLAUDE.md rules.

---

## 6. TODOWRITE — FORCE TASK TRACKING

From the system prompt:
> "Use these tools VERY frequently to ensure that you are tracking your tasks and giving the user visibility into your progress... If you do not use this tool when planning, you may forget to do important tasks - and that is unacceptable."

### How to leverage for enforcement:
Tell Claude Code to always include verification as a TodoWrite item:

```
For every task, your todo list MUST include:
1. [task items...]
2. Run wiring-checker subagent
3. Run verify.py — confirm 14/14 PASSED
4. Commit and push

Do NOT mark task as completed until items 2-4 are done.
```

TodoWrite has three states: `pending`, `in_progress`, `completed`.

### New Tasks API (v2.1.16+):
Claude Code now has a Tasks API that persists to disk (`~/.claude/tasks/`) instead of memory. If your Claude Code is v2.1.19+, the default is Tasks API, not TodoWrite. Set `CLAUDE_CODE_TASK_LIST_ID=idna-tutor` in your shell for project-specific task tracking.

---

## 7. KEY SYSTEM PROMPT RULES WE MUST WORK WITH

These are baked into Claude Code and CANNOT be overridden by CLAUDE.md:

1. **"NEVER commit changes unless the user explicitly asks you to"** — This means our CLAUDE.md rule "always commit after verify" gets ignored. Solution: Always explicitly tell Claude Code to commit.

2. **"IMPORTANT: Always use the TodoWrite tool to plan and track tasks"** — Works in our favor. Verification should be a todo item.

3. **"VERY IMPORTANT: When you have completed a task, you MUST run the lint and typecheck commands"** — We can leverage this by adding verify.py to the lint commands in CLAUDE.md.

4. **"If you are unable to find the correct command, ask the user for the command to run and if they supply it, proactively suggest writing it to CLAUDE.md"** — Claude Code is designed to learn from CLAUDE.md.

5. **Security policy blocks modifying hooks/settings** — Claude Code won't modify `.claude/settings.json` or hook scripts unless explicitly asked.

---

## 8. SUB-AGENTS ARCHITECTURE

Claude Code has three built-in sub-agents:

| Agent | Purpose | Tools Available |
|---|---|---|
| **Explore** (516 tks) | Research codebase | Read, Glob, Grep, Bash (read-only) |
| **Plan** (633 tks) | Create implementation plan | Read, Glob, Grep, Bash (read-only) |
| **Task** (1,055 tks) | Execute delegated work | All tools (Read, Write, Edit, Bash, etc.) |

Our custom sub-agents (verifier, wiring-checker, pre-commit-checker) are project-level agents defined in `.claude/agents/`. They work alongside the built-in ones.

### Agent Hook Agent Prompt (133 tokens):
> "You are verifying a stop condition in Claude Code. Your task is to verify that the agent completed the given plan. The conversation transcript is available at: ${TRANSCRIPT_PATH}. You can read this file to analyze the conversation history if needed. Use the available tools to inspect the codebase and verify the condition. Use as few steps as possible - be efficient and direct."

---

## 9. TWEAKCC — MODIFY SYSTEM PROMPT DIRECTLY

**Repo:** https://github.com/Piebald-AI/tweakcc

What it does:
- Lets you customize individual pieces of Claude Code's system prompt as markdown files
- Patches your npm or binary Claude Code installation
- Provides diffing and conflict management when Anthropic updates prompts

**Potential use:** Inject verification rules directly into the main system prompt (2,972 tks) so they can't be overridden by context drift. More powerful than CLAUDE.md but requires re-patching after Claude Code updates.

**Verdict:** Useful for advanced customization but overkill for now. MEMORY.md + correct Stop hook + CLAUDE.md covers 95% of enforcement needs.

---

## 10. TOMORROW'S EXECUTION PLAN

### Step 1: Create stop_check.py (2 min)
```bash
mkdir -p .claude/hooks
# Create the Python script from Section 2 above
```

### Step 2: Update settings.json (2 min)
Replace the broken stop hook with the correct command hook format from Section 2.

### Step 3: Create MEMORY.md (2 min)
Add the enforcement rules from Section 5 to `.claude/MEMORY.md`.

### Step 4: Test the loop prevention (5 min)
1. Open Claude Code
2. Ask it to make a trivial change to a Python file
3. When it tries to finish → stop hook should fire
4. Confirm it says "Run verify.py" instead of completing
5. Confirm `stop_hook_active` prevents infinite loop on second fire

### Step 5: Test v7.3.1 on Railway (5 min)
1. Login as Priya, test 3 scenarios
2. Check Railway logs for CLASSIFIER: lines
3. Report results

### Step 6: Start NCERT textbook content
Begin structured teaching scripts for Didi.

---

## APPENDIX: Useful Commands

```bash
# Check Claude Code version
claude --version

# View current settings
cat .claude/settings.json

# View MEMORY.md
cat .claude/MEMORY.md

# Check if Tasks API is enabled (v2.1.19+)
echo $CLAUDE_CODE_ENABLE_TASKS

# Set project-specific task list
export CLAUDE_CODE_TASK_LIST_ID=idna-tutor

# View Claude Code system prompts (via tweakcc)
npx tweakcc list
```
