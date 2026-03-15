# Teaching Flow — v10.7.0 Reference

## FSM States (v7.3)

GREETING, TEACHING, WAITING_ANSWER, HINT_1, HINT_2, FULL_SOLUTION, NEXT_QUESTION, SESSION_COMPLETE

## Session Flow

```
GREETING
  → Student responds → ACK → TEACHING (chapter intro if questions_attempted == 0)

TEACHING (turn 0, first time)
  → Chapter intro: NCERT-style explanation with tile analogy
  → Student ACKs → TEACHING (turn 1: assessment bridge)
  → Student ACKs → WAITING_ANSWER (first L2 question, prefers square-type)

TEACHING (reteach, questions_attempted > 0)
  → turn 0: Content Bank L1 definition
  → turn 1: Content Bank L2 analogy/example
  → turn 2: Content Bank L3 vedic trick
  → turn 3: Guided question (stop explaining)
  → turn 4+: Offer break

WAITING_ANSWER
  → ANSWER (correct) → NEXT_QUESTION → WAITING_ANSWER
  → ANSWER (incorrect) → HINT_1
  → IDK → HINT_1
  → CONCEPT_REQUEST → TEACHING (reteach)
  → META_QUESTION → answer, stay in WAITING_ANSWER

HINT_1
  → ANSWER (correct) → NEXT_QUESTION
  → ANSWER (incorrect) → HINT_2
  → IDK → HINT_2
  → CONCEPT_REQUEST → HINT_2 (don't escape to TEACHING)

HINT_2
  → ANSWER (correct) → NEXT_QUESTION
  → ANSWER (incorrect) → FULL_SOLUTION
  → IDK → FULL_SOLUTION
  → CONCEPT_REQUEST → FULL_SOLUTION (don't escape to TEACHING)

FULL_SOLUTION
  → ANY input → NEXT_QUESTION (always advance, never loop back)

NEXT_QUESTION
  → Transient — immediately becomes WAITING_ANSWER
  → If max questions reached → SESSION_COMPLETE
```

## 5-Level System (v10.4.0)

| Level | Type | Example |
|-------|------|---------|
| L1 | Multiplication recall | "What is 3 times 3?" |
| L2 | Square/cube numbers | "What is the square of 8?" |
| L3 | Square/cube roots | "What is √49?" |
| L4 | Patterns/properties | "Is 50 a perfect square?" |
| L5 | Application/methods | "Find side of square with area 441" |

- First question: Level 2 (prefer square-type, not cube)
- 3 correct in a row → level up
- 2 wrong in a row → level down
- Question picker: memory.py pick_next_question() — strict WHERE level = current_level

## Key Functions

| Action | Function | File |
|--------|----------|------|
| Build any prompt | build_prompt() | instruction_builder.py |
| Teach concept | _build_teach_concept() | instruction_builder.py |
| Read question | _build_read_question() | instruction_builder.py |
| Evaluate answer | _build_evaluate_answer() | instruction_builder.py |
| Give hint | _build_give_hint() | instruction_builder.py |
| Show solution | _build_show_solution() | instruction_builder.py |
| Answer meta-Q | _build_answer_meta_question() | instruction_builder.py |
| Pick next question | pick_next_question() | memory.py |
| Inline eval | build_inline_eval_prompt() | instruction_builder.py |

## Chapter Introduction (v10.7.0)

When questions_attempted == 0, TEACHING uses CHAPTER_INTRO content:
- turn_0: NCERT tile analogy ("3 rows of 3 tiles = 9, a square!")
- turn_1: Square root + assessment bridge ("Let's see what you know")
- Content in ch1_square_and_cube.py CHAPTER_INTRO dict (4 languages)
