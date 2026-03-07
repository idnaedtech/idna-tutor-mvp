# IDNA Kanban — AI Development Pipeline

Adapted from [cyanluna.skills](https://github.com/cyanluna-git/cyanluna.skills)
for IDNA EdTech's voice tutor development.

## What This Does

Write a card. Type `/kanban run <ID>`. Walk away. Six IDNA-aware agents
handle planning, review, implementation, testing, and deployment — all
enforcing your non-negotiable rules automatically.

## Install

```bash
# Copy skill to Claude Code skills directory
cp -R idna-kanban ~/.claude/skills/

# Navigate to your IDNA project
cd /path/to/idna-tutor-mvp

# Initialize (creates SQLite DB + project config)
python ~/.claude/skills/idna-kanban/scripts/init.py
```

## Quick Start

```bash
# View board
/kanban list

# Add a task
/kanban add Fix: Same-Q reload on page refresh

# Run full pipeline
/kanban run 1

# Run next step only
/kanban step 1

# Seed all P1 bugs as cards
/kanban p1
```

## Works With

- **idna-edtech-tutor** skill (domain knowledge)
- **idna-kanban** skill (workflow automation)

Both skills complement each other. Agents consult `idna-edtech-tutor`
for architecture context while `idna-kanban` manages the workflow.

## Requirements

- Claude Code CLI
- Python 3.11+
- SQLite3 (built into Python)
- IDNA project with `verify.py` and `pytest` configured
