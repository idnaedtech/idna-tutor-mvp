-- schema.sql (IDNA tutor MVP) — Option B (session-level seen) + keep existing PK behavior intact

BEGIN;

-- =========================
-- Core tables
-- =========================

CREATE TABLE IF NOT EXISTS topics (
  topic_id TEXT PRIMARY KEY,
  title TEXT,
  grade TEXT,
  subject TEXT
);

CREATE TABLE IF NOT EXISTS concepts (
  concept_id TEXT PRIMARY KEY,
  topic_id TEXT NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
  title TEXT,
  explain_text TEXT
);

CREATE TABLE IF NOT EXISTS questions (
  question_id TEXT PRIMARY KEY,
  topic_id TEXT NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
  qtype TEXT,
  prompt TEXT NOT NULL,
  answer_key TEXT,
  hint1 TEXT,
  hint2 TEXT,
  reveal_explain TEXT
);

-- =========================
-- Sessions
-- Notes:
-- - Keep your existing columns.
-- - status/state naming is inconsistent in code you pasted; schema keeps both fields.
-- - attempt_count/frustration_counter/updated_at are used by your db.py code; add them here.
-- =========================

CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  student_id TEXT NOT NULL,
  topic_id TEXT NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,

  -- keep existing behavior
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  state TEXT,

  -- used by code
  attempt_count INT NOT NULL DEFAULT 0,
  frustration_counter INT NOT NULL DEFAULT 0,
  current_question_id TEXT REFERENCES questions(question_id),

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

-- =========================
-- Attempts
-- Notes:
-- - Your current schema uses attempt_id; your db.py earlier had id SERIAL.
-- - We standardize to attempt_id BIGSERIAL (matches your existing schema).
-- - Add user_answer nullable (your db.py tries to drop NOT NULL).
-- =========================

CREATE TABLE IF NOT EXISTS attempts (
  attempt_id BIGSERIAL PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  student_id TEXT NOT NULL,
  topic_id TEXT NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
  question_id TEXT NOT NULL REFERENCES questions(question_id) ON DELETE CASCADE,

  user_answer TEXT, -- nullable by design
  is_correct BOOLEAN NOT NULL DEFAULT FALSE,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================
-- Seen questions (LIFETIME / per-student per-topic)
-- This stays EXACTLY as your existing primary key behavior:
-- PRIMARY KEY (student_id, topic_id, question_id)
-- =========================

CREATE TABLE IF NOT EXISTS seen_questions (
  student_id TEXT NOT NULL,
  topic_id TEXT NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
  question_id TEXT NOT NULL REFERENCES questions(question_id) ON DELETE CASCADE,
  seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (student_id, topic_id, question_id)
);

-- =========================
-- Option B: Session-level "seen"
-- Separate table so we DO NOT alter existing seen_questions PK behavior.
-- =========================

CREATE TABLE IF NOT EXISTS session_seen_questions (
  session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  question_id TEXT NOT NULL REFERENCES questions(question_id) ON DELETE CASCADE,
  seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (session_id, question_id)
);

-- =========================
-- Indexes
-- =========================

CREATE INDEX IF NOT EXISTS idx_questions_topic ON questions(topic_id);

CREATE INDEX IF NOT EXISTS idx_attempts_session ON attempts(session_id);
CREATE INDEX IF NOT EXISTS idx_attempts_student_topic ON attempts(student_id, topic_id);

CREATE INDEX IF NOT EXISTS idx_session_seen_session ON session_seen_questions(session_id);
CREATE INDEX IF NOT EXISTS idx_session_seen_question ON session_seen_questions(question_id);

COMMIT;
