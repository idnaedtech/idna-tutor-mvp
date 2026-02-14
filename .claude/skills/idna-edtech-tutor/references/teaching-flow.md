# Teaching Flow — State Machine Reference

## States and Transitions

```
GREETING
  ├── (auto) → TEACHING
  │
TEACHING
  ├── Student says ACK → ASKING_QUESTION
  ├── Student says IDK → RETEACHING (different example)
  ├── Student says CONCEPT_REQUEST → TEACHING (deeper)
  ├── Student says COMFORT → COMFORTING (stay in state)
  │
ASKING_QUESTION
  ├── (reads question, auto) → WAITING_ANSWER
  │
WAITING_ANSWER
  ├── Student gives ANSWER → EVALUATING
  ├── Student says IDK → HINTING
  ├── Student says CONCEPT_REQUEST → TEACHING (re-explain concept)
  ├── Student says COMFORT → COMFORTING (stay in state)
  │
EVALUATING
  ├── Correct → CORRECT_FEEDBACK → NEXT_QUESTION or ASKING_QUESTION
  ├── Wrong (1st attempt) → HINTING → WAITING_ANSWER
  ├── Wrong (2nd attempt) → EXPLAINING_SOLUTION → NEXT_QUESTION
  ├── Partial → GUIDING_SUBSTEP → WAITING_ANSWER
  │
HINTING
  ├── (gives hint, auto) → WAITING_ANSWER
  │
EXPLAINING_SOLUTION
  ├── (shows solution, auto) → NEXT_QUESTION
  │
COMFORTING
  ├── (comforts student, auto) → returns to previous state
  │
NEXT_QUESTION
  ├── Has more questions → ASKING_QUESTION
  ├── No more questions → SESSION_COMPLETE
```

## needs_first_question Flag

After TEACHING, when student says ACK, the `needs_first_question` flag triggers
reading the first question. This prevents Didi from teaching AND asking in one turn.

```python
# In process_input, before normal flow:
if self.session.get("needs_first_question"):
    self.session["needs_first_question"] = False
    category = classifier.classify(student_input)["category"]
    if category in ("ACK", "ANSWER"):
        # Read the first question
        q_text = self._current_question_text()
        speech = f"Bahut accha! Ab ek question try karte hain: {q_text}"
    elif category in ("IDK", "CONCEPT_REQUEST"):
        # Student needs more teaching — use DIFFERENT example
        speech = reteach_with_different_example()
```

## SubStepTracker Integration

For multi-step problems (fraction multiplication, etc.):

```python
tracker = self.session["substep_tracker"]
tracker.init_for_question(question_type, question_data)

# When student answers a sub-step correctly:
tracker.mark_current_done(student_answer)
next_step = tracker.get_current_step()

# Include in LLM instruction:
f"Steps completed (DO NOT re-ask): {tracker.get_completed_summary()}"
f"Ask ONLY about: {next_step['description']}"
```

## Instruction Builder Quick Reference

| Action | Builder Function | Max Words |
|--------|-----------------|-----------|
| Greet | `build_greet_instruction()` | 15-20 |
| Teach new concept | `build_teach_instruction()` | 50-60 |
| Reteach | `build_reteach_instruction()` | 40-50 |
| Read question | `build_question_instruction()` | 15-20 |
| Correct answer | `build_correct_instruction()` | 20-25 |
| Wrong (1st) | `build_wrong_instruction(attempt=1)` | 20-30 |
| Wrong (2nd) | `build_wrong_instruction(attempt=2)` | 50-60 |
| Comfort | `build_comfort_instruction()` | 20-25 |
| Repeat request | `build_repeat_instruction()` | 15 |
