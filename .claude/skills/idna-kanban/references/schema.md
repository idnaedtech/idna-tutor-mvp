# IDNA Kanban — Database Schema

SQLite database at `~/.claude/kanban-dbs/idna-tutor.db`

## Tasks Table

```sql
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'requirements',
    -- Valid statuses: requirements, plan, plan_review, impl, impl_review, test, done
    level TEXT NOT NULL DEFAULT 'L2',
    -- L1 (quick), L2 (standard), L3 (full pipeline)
    priority TEXT NOT NULL DEFAULT 'medium',
    -- low, medium, high, critical

    -- Agent outputs
    plan TEXT,
    plan_review_comments TEXT,
    implementation_notes TEXT,
    review_comments TEXT,
    test_results TEXT,
    commit_hash TEXT,

    -- IDNA-specific fields
    idna_files_touched TEXT,         -- JSON array of file paths
    idna_phase TEXT DEFAULT 'P1',    -- P0, P1, P2, P3, P4
    idna_verify_status TEXT,         -- "22/22" or failure details
    idna_test_count TEXT,            -- "155/155" or failure details
    idna_p1_bug_id INTEGER,          -- Links to P1 backlog item number

    -- Metadata
    tags TEXT,                       -- comma-separated
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);
```

## Agent Log Table

```sql
CREATE TABLE IF NOT EXISTS agent_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    agent TEXT NOT NULL,              -- Planner, Critic, Builder, Shield, Inspector, Ranger
    model TEXT NOT NULL,              -- opus, sonnet
    action TEXT NOT NULL,             -- plan, review, implement, test, commit, reject
    content TEXT,                     -- Full agent output
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);
```

## Valid Status Transitions

```
requirements → plan
plan → plan_review
plan_review → plan (rejected) | impl (approved)
impl → impl_review
impl_review → impl (rejected) | test (approved)
test → impl (failed) | done (passed)
done → (terminal)
```

### Level-based shortcuts
- **L1:** requirements → impl → done
- **L2:** requirements → plan → impl → impl_review → done
- **L3:** requirements → plan → plan_review → impl → impl_review → test → done
