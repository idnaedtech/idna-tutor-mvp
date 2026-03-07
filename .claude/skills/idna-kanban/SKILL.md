---
name: idna-kanban
description: >
  AI-powered kanban pipeline for IDNA EdTech development with Claude Code.
  Six IDNA-aware agents automate planning, review, implementation, testing,
  and deployment. Use when: creating tasks, running pipeline, managing backlog,
  sprint planning, bug fixes, feature development, content bank creation,
  FSM changes, schema migrations, or any structured IDNA development work.
  Trigger on: "/kanban", "create task", "run pipeline", "sprint", "backlog",
  "plan feature", "fix bug", "add chapter content", "schema migration",
  "board expansion work". Every agent enforces IDNA's non-negotiable rules:
  FSM=skeleton, bench_score gates, verify.py 22/22, 152+ tests passing.
  Do NOT trigger for general project management discussions or non-IDNA work.
---

# IDNA Kanban — AI Development Pipeline (v1.0.0)

Adapted from [cyanluna.skills](https://github.com/cyanluna-git/cyanluna.skills)
for IDNA EdTech's specific architecture, constraints, and development rules.

## 1. What This Does

You write a card describing what you need — feature, bug fix, content bank,
schema migration — and type `/kanban run <ID>`. Six AI agents handle the rest:

```
Req → Plan → Review Plan → Impl → Review Impl → Test → Done
```

Every agent reads `IDNA_v8_ARCHITECTURE.md` and enforces the non-negotiable
rules before writing a single line of code.

## 2. The Pipeline

| Column | Agent | Model | IDNA-Specific Behavior |
|--------|-------|-------|----------------------|
| **Requirements** | User (you) | — | Describe task with IDNA context |
| **Plan** | `Planner` | opus | Reads architecture spec, plans with FSM awareness |
| **Review Plan** | `Critic` | sonnet | Enforces FSM=skeleton rule, checks phase gates |
| **Implement** | `Builder` + `Shield` | opus + sonnet | Builder codes; Shield writes tests |
| **Review Impl** | `Inspector` | sonnet | Code review against IDNA dev rules |
| **Test** | `Ranger` | sonnet | Runs verify.py + pytest, commits if green |
| **Done** | — | — | Auto-commits with `[idna-kanban #ID]` tag |

## 3. Pipeline Levels

| Level | Path | IDNA Use Cases |
|-------|------|---------------|
| **L1 Quick** | Req → Impl → Done | Config changes, env vars, typo fixes, TTS param tweaks |
| **L2 Standard** | Req → Plan → Impl → Review → Done | Bug fixes (P1 backlog), content bank chapters, endpoint changes |
| **L3 Full** | Req → Plan → Plan Rev → Impl → Impl Rev → Test → Done | New FSM states, schema migrations, board expansion, new features |

**Default level:** L2 for bug fixes, L3 for anything touching FSM or schema.

## 4. The AI Team

| Nickname | Role | Model | Reads | Writes |
|----------|------|-------|-------|--------|
| `Planner` | Plan Agent | opus | description, IDNA_v8_ARCHITECTURE.md | plan |
| `Critic` | Plan Review | sonnet | description, plan, SKILL.md rules | plan_review_comments |
| `Builder` | Worker | opus | description, plan, review comments | implementation_notes |
| `Shield` | TDD Tester | sonnet | description, implementation_notes | test code (appended) |
| `Inspector` | Code Review | sonnet | description, plan, impl notes, dev rules | review_comments |
| `Ranger` | Test Runner | sonnet | implementation_notes | test_results, commit hash |

**Signature rule** — every agent prepends:
```
> **Planner** `opus` · 2026-02-25T10:00:00Z · IDNA v8.0.1
```

## 5. IDNA-Specific Agent Rules

### ALL agents MUST:
1. Read `IDNA_v8_ARCHITECTURE.md` before any work
2. Never create `app/models/` directory (shadows `app/models.py`)
3. Never change TTS voice (Sarvam simran only)
4. Never rewrite DIDI_PROMPT (append rules only)
5. Treat FSM as skeleton — new board = data insert, zero code change
6. Respect phase gates: P0 (live test) must pass before P1 features

### Planner MUST:
- Reference specific files in `app/` that will be touched
- Flag if task crosses phase boundaries (e.g., P2 work during P1)
- Include rollback strategy for schema changes

### Critic MUST reject plans that:
- Add code where data insert suffices (violates FSM=skeleton)
- Skip Alembic for any schema change
- Touch TTS voice settings
- Introduce new dependencies without justification
- Lack test strategy

### Builder MUST:
- Follow atomic commit rule (one change per commit)
- Use commit format: `v{major}.{minor}.{patch}: brief description`
- Run `python -m pytest tests/ -v` after every change
- Never edit MEMORY.md mid-session

### Shield MUST:
- Write tests that integrate with existing 152-test suite
- Test Hindi-English mixed inputs for any user-facing change
- Include edge cases from P1 backlog (empty TTS, Devanagari parsing)

### Inspector MUST check:
- No `app/models/` directory created
- Alembic migration exists for schema changes
- clean_for_tts() handles new math symbols
- SessionState fields properly initialized
- Language persistence not broken

### Ranger MUST:
- Run `python verify.py` — all 22 checks must pass
- Run `python -m pytest tests/ -v` — all tests must pass
- Only commit if BOTH pass
- Commit with `[idna-kanban #ID]` tag

## 6. Commands

| Command | What it does |
|---------|-------------|
| `/kanban` or `/kanban list` | Show board as markdown table |
| `/kanban context` | Board state + in-progress + next todos |
| `/kanban add <title>` | Create new task (prompts for level, priority) |
| `/kanban run <ID>` | Run full pipeline for task |
| `/kanban run <ID> --auto` | Fully automatic (circuit breaker at 3 review loops) |
| `/kanban step <ID>` | Execute only next pipeline step |
| `/kanban move <ID> <status>` | Manual column move |
| `/kanban review <ID>` | Trigger code review |
| `/kanban edit <ID>` | Edit task fields |
| `/kanban remove <ID>` | Delete task |
| `/kanban stats` | Task counts per column |
| `/kanban p1` | Show P1 backlog items as cards |

## 7. Task Card Schema

See `references/schema.md` for full SQLite schema.

Key fields per card:
```
id, title, description, status, level, priority,
plan, plan_review_comments,
implementation_notes, review_comments,
test_results, commit_hash,
idna_files_touched (JSON array of file paths),
idna_phase (P0/P1/P2/P3/P4),
created_at, updated_at
```

## 8. IDNA Task Templates

When creating tasks, use these templates for common IDNA work:

**Bug Fix (P1 backlog):**
```
/kanban add Fix: Same-Q reload on page refresh
> Level: L2
> Priority: high
> Phase: P1
> Files: app/routers/student.py, app/content/ch1_square_and_cube.py
> Description: Page refresh re-serves the same question. Need to track
  served question IDs in SessionState and exclude them from next selection.
```

**Content Bank:**
```
/kanban add Content: Chapter 2 Linear Equations bank
> Level: L2
> Priority: medium
> Phase: P1
> Files: app/content/ch2_linear_equations.py
> Description: Create content bank following ch1_square_and_cube.py pattern.
  50 questions, 20 skills, 3 teaching layers (definition, analogy, vedic_trick).
  Indian examples only. Must integrate with FSM content injection.
```

**Schema Migration:**
```
/kanban add Schema: Add boards and textbooks tables (v8.1.0)
> Level: L3
> Priority: high
> Phase: P1
> Files: app/models.py, alembic/versions/
> Description: Add boards, textbooks, content_units tables per schema-v81.md.
  Alembic migration required. Do NOT create app/models/ directory.
```

**FSM Change:**
```
/kanban add FSM: Add HOMEWORK_HELP input category
> Level: L3
> Priority: high
> Phase: P1
> Files: app/fsm/transitions.py, app/tutor/input_classifier.py, app/fsm/handlers.py
> Description: New input category for homework help requests. Must define
  transitions for all 6 states × HOMEWORK_HELP. Update classifier prompt.
  60-combo matrix becomes 66-combo (6 states × 11 inputs).
```

## 9. Integration with Existing IDNA Skill

This kanban skill works alongside the `idna-edtech-tutor` skill:
- **idna-edtech-tutor** provides domain knowledge (FSM, voice pipeline, teaching principles)
- **idna-kanban** provides workflow automation (pipeline, agents, task management)

When agents need IDNA-specific context, they should consult `idna-edtech-tutor`
SKILL.md and its references.

## 10. Storage

- Database: `~/.claude/kanban-dbs/idna-tutor.db` (SQLite)
- Project config: `.claude/kanban.json` → `{"project": "idna-tutor"}`
- Agent templates: `templates/` directory in this skill

## 11. Agent Templates

Read these when spawning each agent:

| Template | Agent |
|----------|-------|
| `templates/plan-agent.md` | Planner |
| `templates/review-agent.md` | Critic |
| `templates/worker-agent.md` | Builder |
| `templates/tdd-tester.md` | Shield |
| `templates/code-review-agent.md` | Inspector |
| `templates/test-runner.md` | Ranger |

## 12. Reference Files

| File | Contents | When to read |
|------|----------|--------------|
| `references/schema.md` | SQLite schema for kanban database | Setup, debugging |
| `references/p1-backlog.md` | Current P1 bugs with full context | Creating bug fix tasks |
| `references/phase-gates.md` | Phase gate criteria | Plan review, task scoping |
