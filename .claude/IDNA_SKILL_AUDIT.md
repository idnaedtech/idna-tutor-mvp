# IDNA EdTech Skill — CTO Audit Report

**Date:** 2026-02-25  
**Auditor:** Claude (CTO)  
**Current Version:** v8.0.1  
**Skill Location:** `/mnt/skills/user/idna-edtech-tutor/SKILL.md`

---

## Verdict: Functional but structurally overweight. Needs refactor.

The skill works — it triggers correctly and contains accurate architecture info. But it violates several best practices from Anthropic's Skills Guide that will hurt you as IDNA scales.

---

## Critical Findings

### 1. SKILL.md is 407 lines — approaching the 500-line danger zone

**Problem:** The guide recommends keeping SKILL.md under 500 lines, ideally much less. At 407 lines, every time the skill triggers, Claude loads ~17KB of context. This includes database schemas, phase timelines, board expansion tables, and strategic positioning — most of which are irrelevant to any single task.

**Impact:** Token waste, slower responses, context window pressure in long sessions. When you're debugging a TTS issue, Claude doesn't need the v8.1.0 schema planning or NeurIPS publication strategy in context.

**Fix:** Apply progressive disclosure. Move Sections 9-12, 15, 17 to `references/` files. Keep SKILL.md focused on "what Claude needs to write correct IDNA code right now."

### 2. No `references/` directory — zero progressive disclosure

**Problem:** The entire skill is a single monolithic file. The guide's three-level system (frontmatter → body → linked files) is collapsed to two levels. Claude loads everything or nothing.

**Fix:** Split into:
- `SKILL.md` — Core architecture, FSM, voice pipeline, dev rules, P1 backlog (~200 lines)
- `references/schema-v81.md` — Database schema evolution
- `references/bench-spec.md` — IDNA-Bench layers and thresholds
- `references/roadmap.md` — Phase timeline, board expansion, strategic positioning
- `references/stack-future.md` — Phase 2-4 tech stack

### 3. No `scripts/` directory — missing deterministic enforcement

**Problem:** The guide explicitly says: "For critical validations, consider bundling a script that performs the checks programmatically rather than relying on language instructions. Code is deterministic; language interpretation isn't."

Your verify.py and test suite exist in the repo, but the skill doesn't bundle helper scripts. Claude has to remember rules like "don't create app/models/ directory" purely from text instructions.

**Fix:** Add a `scripts/pre-check.sh` that Claude can run before committing:
```bash
#!/bin/bash
# Quick sanity checks before any IDNA code change
[ -d "app/models" ] && echo "ERROR: app/models/ directory exists, shadows app/models.py" && exit 1
python -m pytest tests/ -x -q 2>/dev/null || echo "WARN: Tests failing"
python verify.py --quick 2>/dev/null || echo "WARN: verify.py failing"
```

### 4. Description is good but could be tighter on negative triggers

**Problem:** The description correctly lists many trigger phrases. But it doesn't specify what NOT to trigger on, which the guide recommends for skills that could over-trigger. Since IDNA touches FastAPI, Python, PostgreSQL — all generic topics — there's risk of triggering on non-IDNA FastAPI questions.

**Fix:** Add negative triggers:
```
Do NOT trigger for generic FastAPI tutorials, general PostgreSQL questions, 
or Python coding unrelated to the IDNA codebase.
```

### 5. Phase 2-4 tech stack is dead weight in the MVP skill

**Problem:** 20+ lines dedicated to technologies (PersonaPlex 7B, Milvus, RuleGo, Gorse, etc.) that explicitly "not for MVP." Every skill load pays the token cost for info Claude should never act on right now.

**Fix:** Move entirely to `references/stack-future.md`. Reference it from SKILL.md with: "For Phase 2+ tech stack, consult `references/stack-future.md`."

### 6. Missing error handling patterns

**Problem:** The guide emphasizes including troubleshooting sections. Your skill has dev rules and the P1 backlog, but no "if you see X error, do Y" patterns for common IDNA-specific failures like Sarvam API timeouts, Railway deploy failures, or SessionState corruption.

**Fix:** Add a troubleshooting section covering the top 5 failure modes.

### 7. Version metadata says 8.0.1 but schema section describes 8.1.0

**Problem:** Sections 9 and 263-264 describe v8.1.0 planned changes (new tables, SessionState extensions) mixed with v8.0.1 production state. Claude can't distinguish "what exists now" from "what's planned."

**Fix:** Clearly label planned sections as `## PLANNED (v8.1.0)` or move them entirely to references.

### 8. No examples section

**Problem:** The guide recommends concrete examples of user requests and expected Claude behavior. Your skill has none.

**Fix:** Add 3-4 examples like:
```
Example 1: Fix a bug
User: "The TTS is returning empty audio for some responses"
Claude should:
1. Check app/voice/tts.py for empty string handling
2. Check clean_for_tts() in the pipeline
3. Run relevant tests
4. Never change TTS voice settings
```

---

## What's Already Good

- **Description field** is comprehensive with strong trigger phrases
- **FSM documentation** is excellent — the 60-combo matrix is exactly the kind of domain knowledge that belongs in a skill
- **Teaching principles** (Section 8) are perfectly placed — Claude needs these for every content-related task
- **Dev rules** (Section 14) are clear and actionable
- **Non-negotiable principles** (Section 3) are well-positioned at the top
- **Metadata** includes version, author, stack — good practice

---

## Recommended Structure (Post-Refactor)

```
idna-edtech-tutor/
├── SKILL.md              (~220 lines — core only)
│   ├── Frontmatter
│   ├── What is IDNA
│   ├── Current Status
│   ├── Architecture Principles
│   ├── Current Tech Stack (v8.0.1 only)
│   ├── Codebase Structure
│   ├── FSM Architecture
│   ├── Voice Pipeline
│   ├── Teaching Principles
│   ├── P1 Backlog
│   ├── Development Rules
│   ├── Troubleshooting (NEW)
│   └── Examples (NEW)
├── scripts/
│   └── pre-check.sh       # Deterministic validation
├── references/
│   ├── schema-v81.md       # Database evolution plan
│   ├── bench-spec.md       # IDNA-Bench 7 layers
│   ├── roadmap.md          # Phases, board expansion, strategy
│   └── stack-future.md     # Phase 2-4 technologies
└── assets/                 # (empty for now, future templates)
```

---

## Action Items

| # | Action | Priority | Effort |
|---|--------|----------|--------|
| 1 | Split SKILL.md → core + 4 reference files | P0 | 30 min |
| 2 | Add negative triggers to description | P0 | 5 min |
| 3 | Add troubleshooting section | P1 | 15 min |
| 4 | Add examples section | P1 | 15 min |
| 5 | Create scripts/pre-check.sh | P1 | 10 min |
| 6 | Remove v8.1.0 planned content from main body | P0 | 10 min |
| 7 | Update version metadata to reflect skill version (not app version) | P2 | 2 min |
| 8 | Run trigger tests (10 positive, 5 negative queries) | P1 | 20 min |

**Total estimated effort: ~2 hours for full refactor.**
