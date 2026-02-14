# Question Bank — Format & Schema

## Question JSON Schema

```python
{
    "id": str,                    # Unique ID: "rat_add_1", "rat_mul_3"
    "chapter": str,               # "ch1_rational_numbers"
    "type": str,                  # Question type (see types below)
    "question": str,              # The question text (read by Didi)
    "answer": str,                # Correct answer (exact)
    "simplified_answer": str,     # Simplified form (optional)
    "hints": list[str],           # Progressive hints (1st attempt, 2nd attempt)
    "target_skill": str,          # Maps to SKILL_LESSONS key
    "pre_teach": str,             # Concept explanation before question (optional)
    "difficulty": int,            # 1-3 (easy/medium/hard)
}
```

## Question Types

| Type | SubStepTracker Steps | Example |
|------|---------------------|---------|
| `fraction_add_same_denom` | Add numerators → Keep denominator → Simplify | -3/7 + 2/7 |
| `fraction_add_diff_denom` | Find LCM → Convert → Add → Simplify | 1/3 + 1/4 |
| `fraction_subtract` | Same as add (with subtraction) | 5/6 - 1/6 |
| `fraction_multiply` | Multiply numerators → Multiply denominators → Combine → Simplify | 2/3 × -3/4 |
| `fraction_divide` | Flip divisor → Multiply → Simplify | 2/3 ÷ 4/5 |
| `additive_inverse` | Identify number → Change sign | Additive inverse of 5/8 |
| `multiplicative_inverse` | Flip numerator/denominator | Multiplicative inverse of -3/7 |
| `property_identify` | Single step — identify property | Is addition commutative for rationals? |

## SKILL_LESSONS Dict

Maps `target_skill` → teaching text used for reteaching:

```python
SKILL_LESSONS = {
    "addition_same_denom": "When denominators are same, just add numerators. Denominator stays.",
    "addition_diff_denom": "Find LCM of denominators, convert both fractions, then add.",
    "subtraction": "Same as addition, but subtract numerators instead.",
    "multiplication": "Multiply numerator × numerator, denominator × denominator. Simplify.",
    "division": "Flip the second fraction (reciprocal), then multiply.",
    "additive_inverse": "The number you add to get zero. Just change the sign.",
    "multiplicative_inverse": "The number you multiply to get 1. Flip the fraction.",
}
```

## Adding New Questions

1. Add to `questions.py` following the schema above
2. If new `target_skill`, add entry to `SKILL_LESSONS`
3. If new `type`, add to `SubStepTracker.init_for_question()`
4. Run tests: `python -m pytest tests/test_answer_checker.py -v`
