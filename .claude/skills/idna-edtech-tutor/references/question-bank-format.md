# Question Bank — v10.6.x Format

## Current Chapter: ch1_square_and_cube.py (Squares, Cubes & Roots)

84 questions total, 74 active. 5 levels: L1:10, L2:9, L3:14, L4:22, L5:19.

## Question Schema

```python
{
    "id": str,                  # e.g., "sq_b02", "cb_e01", "mult_05"
    "chapter": str,             # "ch1_square_and_cube"
    "type": str,                # "compute", "identify", "cube_root", etc.
    "difficulty": str,          # "easy", "medium", "hard"
    "question": str,            # Hindi/Hinglish question text
    "question_en": str,         # English question text
    "answer": str,              # Correct answer (exact)
    "hints": list[str],         # Progressive hints [hint1, hint2]
    "accept_patterns": list[str],  # Alternate accepted answers ["8", "aath", "eight"]
    "common_mistakes": list[str],  # Known wrong answers for feedback
    "target_skill": str,        # Maps to SKILL_TEACHING key
    "level": int,               # 1-5 (see 5-Level System)
    "explanation": str,         # Optional — step-by-step solution text
    "solution": str,            # Optional — brief solution
    "active": bool,             # True = served to students, False = hidden
}
```

## Level Rules

| Level | Question Type | ID Prefix |
|-------|--------------|-----------|
| L1 | Multiplication recall ("What is 3 times 3?") | mult_ |
| L2 | Square/cube compute ("What is 5²?") | sq_b, cb_b |
| L3 | Root finding ("What is √49?", "What is ∛512?") | sq_e, cb_e, rt_ |
| L4 | Patterns ("Is 50 a perfect square?", "Can a square end in 7?") | sq_h, cb_m |
| L5 | Application (word problems, prime factorisation) | sq_m, sq_a |

## Question Picker (memory.py)

```
pick_next_question(db, student_id, subject, chapter, asked_ids, current_level)
  1. WHERE level = current_level AND id NOT IN asked_ids
  2. If exhausted → reuse same-level (excluding current)
  3. If empty → try adjacent levels (up first, then down)
  4. prefer_square_first=True on first question (matches chapter intro)
```

## Adding New Questions

1. Add to QUESTIONS list in ch1_square_and_cube.py following schema above
2. Include: id, question, question_en, answer, hints, accept_patterns, level, target_skill
3. Run startup — _upsert_questions() syncs to DB automatically
4. Verify: /health/detail shows updated counts per level
5. Run: python -m pytest tests/test_ch1_square_cube.py -v

## Known Gaps (29 of 74 questions)

29 questions have no solution or explanation field. v10.6.7 auto-generates
from answer + last hint when these fields are missing. Long-term fix:
add solution/explanation to all questions.
