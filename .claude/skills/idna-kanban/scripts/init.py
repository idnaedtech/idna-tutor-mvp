#!/usr/bin/env python3
"""
IDNA Kanban — Project Initialization Script
Run this inside your IDNA project directory to set up the kanban database.
"""

import json
import os
import sqlite3
from pathlib import Path

# Paths
CLAUDE_DIR = Path.home() / ".claude"
KANBAN_DBS_DIR = CLAUDE_DIR / "kanban-dbs"
PROJECT_NAME = "idna-tutor"
DB_PATH = KANBAN_DBS_DIR / f"{PROJECT_NAME}.db"
PROJECT_CONFIG_DIR = Path(".claude")
PROJECT_CONFIG = PROJECT_CONFIG_DIR / "kanban.json"

def create_database():
    """Create SQLite database with IDNA kanban schema."""
    KANBAN_DBS_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'requirements',
            level TEXT NOT NULL DEFAULT 'L2',
            priority TEXT NOT NULL DEFAULT 'medium',
            plan TEXT,
            plan_review_comments TEXT,
            implementation_notes TEXT,
            review_comments TEXT,
            test_results TEXT,
            commit_hash TEXT,
            idna_files_touched TEXT,
            idna_phase TEXT DEFAULT 'P1',
            idna_verify_status TEXT,
            idna_test_count TEXT,
            idna_p1_bug_id INTEGER,
            tags TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            agent TEXT NOT NULL,
            model TEXT NOT NULL,
            action TEXT NOT NULL,
            content TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    """)

    conn.commit()
    conn.close()
    print(f"✅ Database created: {DB_PATH}")

def create_project_config():
    """Create .claude/kanban.json in project directory."""
    PROJECT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    config = {
        "project": PROJECT_NAME,
        "db_path": str(DB_PATH),
        "pipeline_defaults": {
            "bug_fix": "L2",
            "content_bank": "L2",
            "schema_migration": "L3",
            "fsm_change": "L3",
            "config_change": "L1"
        },
        "idna_version": "v8.0.1",
        "verify_required": True,
        "min_tests": 152
    }

    PROJECT_CONFIG.write_text(json.dumps(config, indent=2))
    print(f"✅ Project config created: {PROJECT_CONFIG}")

def seed_p1_backlog():
    """Optionally seed P1 backlog as kanban cards."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    p1_bugs = [
        ("Fix: Same-Q reload on page refresh",
         "Page refresh re-serves the same question. Track served question IDs in SessionState.",
         "high", "L2", 1),
        ("Fix: HOMEWORK_HELP trap in classifier",
         "Classifier doesn't handle homework help. New input category + 6 new transitions.",
         "high", "L3", 2),
        ("Fix: Devanagari बटा fraction parser",
         "Hindi fraction input not parsed. Need Devanagari numeral mapping + बटा→/ conversion.",
         "medium", "L2", 3),
        ("Fix: Empty TTS sentence wastes API quota",
         "Add empty string check before Sarvam TTS API call.",
         "medium", "L1", 4),
        ("Fix: Parent name split()[0] bug",
         "Single names break split(). Use safe split with fallback.",
         "low", "L1", 5),
        ("Fix: Weakest-skill dead end in adaptive flow",
         "Flow stuck when no weak skill found. Need fallback to next chapter.",
         "medium", "L2", 6),
    ]

    for title, desc, priority, level, bug_id in p1_bugs:
        cursor.execute("""
            INSERT INTO tasks (title, description, priority, level, idna_phase, idna_p1_bug_id)
            VALUES (?, ?, ?, ?, 'P1', ?)
        """, (title, desc, priority, level, bug_id))

    conn.commit()
    conn.close()
    print(f"✅ Seeded {len(p1_bugs)} P1 backlog items as kanban cards")

if __name__ == "__main__":
    print("🚀 Initializing IDNA Kanban...")
    create_database()
    create_project_config()

    seed = input("Seed P1 backlog as kanban cards? (y/n): ").strip().lower()
    if seed == 'y':
        seed_p1_backlog()

    print(f"\n✅ IDNA Kanban ready!")
    print(f"   Database: {DB_PATH}")
    print(f"   Config: {PROJECT_CONFIG}")
    print(f"\n   Use '/kanban list' to view board")
    print(f"   Use '/kanban run <ID>' to run pipeline")
