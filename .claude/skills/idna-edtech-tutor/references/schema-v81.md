# IDNA Database Schema — v8.1.0 Evolution Plan

**Status:** PLANNED — Not yet deployed. Requires Phase 1 completion.

## Existing Tables (v8.0.1 — Production)

- `Student` — Student records
- `Question` — Question bank entries
- `Session` — Tutoring session records

## New Tables (v8.1.0)

### boards
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| code | VARCHAR UNIQUE | CBSE, MSBSHSE, BSETS |
| bench_score | FLOAT NULL | Threshold: 85 |
| is_active | BOOLEAN | Only active boards served |

### textbooks
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| board_id | FK → boards | |
| subject | VARCHAR | mathematics, science |
| class_level | INT | 8 |
| language | VARCHAR | hi, en, mr, ta |

### content_units
Multi-dimensional content graph. Replaces flat-file content bank.

| Column | Type | Notes |
|--------|------|-------|
| topic_id | VARCHAR | Canonical topic identifier |
| board_id | FK → boards | |
| layer | ENUM | L1 (Curriculum), L2 (Teaching), L3 (Conversation) |
| content | JSONB | Structured content payload |
| bench_score | FLOAT NULL | IDNA-Bench composite score |

**Composite unique index:** (topic_id, board_id, class_level, language, layer, version)

### student_profiles
| Column | Type | Notes |
|--------|------|-------|
| board_id | FK → boards | |
| preferred_language | VARCHAR | Student's preferred language |
| weak_topics | JSONB | Adaptive routing |
| mastery_map | JSONB | Per-topic mastery tracking |

## SessionState v8.1.0 Extensions

New fields to add to SessionState dataclass:
- `board_id` — Active board for this session
- `class_level` — Student's class (6-10)
- `textbook_id` — Active textbook reference
- `medium_of_instruction` — Language of instruction
- `parent_language` — Parent's preferred language for reports

## Migration Strategy

1. All schema changes via Alembic migrations
2. ContentBank queries DB by student context, not flat files
3. FSM injection becomes parameterized by board/class/language
4. Exit gate: new board = zero code changes, only DB inserts
