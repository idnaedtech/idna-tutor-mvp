-- schema.sql (minimal for IDNA tutor MVP)

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

CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  student_id TEXT NOT NULL,
  topic_id TEXT NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'ACTIVE',
  state TEXT,
  current_question_id TEXT REFERENCES questions(question_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS attempts (
  attempt_id BIGSERIAL PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
  student_id TEXT NOT NULL,
  topic_id TEXT NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
  question_id TEXT NOT NULL REFERENCES questions(question_id) ON DELETE CASCADE,
  is_correct BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS seen_questions (
  student_id TEXT NOT NULL,
  topic_id TEXT NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
  question_id TEXT NOT NULL REFERENCES questions(question_id) ON DELETE CASCADE,
  seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (student_id, topic_id, question_id)
);

CREATE INDEX IF NOT EXISTS idx_questions_topic ON questions(topic_id);
CREATE INDEX IF NOT EXISTS idx_attempts_session ON attempts(session_id);
CREATE INDEX IF NOT EXISTS idx_attempts_student_topic ON attempts(student_id, topic_id);
