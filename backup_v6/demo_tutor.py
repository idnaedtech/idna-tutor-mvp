"""
IDNA EdTech - Single Concept Demo
=================================
Demonstrates human-like teaching behavior for one concept:
- Adding fractions with same denominator

Flow:
1. Explain the concept step by step
2. Ask exactly one checking question
3. Evaluate the answer
4. If wrong: corrective feedback + one retry
5. If correct: acknowledge and end session

Run: python demo_tutor.py
"""

from evaluator import check_answer

# ============================================================
# THE CONCEPT: Adding fractions with same denominator
# ============================================================

CONCEPT = {
    "name": "Adding Fractions (Same Denominator)",
    "explanation": [
        "When you add fractions with the SAME denominator, the bottom number stays the same.",
        "You only add the top numbers (numerators).",
        "For example: 2/7 + 3/7. The 7 stays. Add the tops: 2 + 3 = 5. Answer: 5/7.",
    ],
    "check_question": {
        "text": "What is -3/7 + 2/7?",
        "answer": "-1/7",
        "hint": "The denominator stays 7. What is -3 plus 2?",
        "explanation": "The 7 stays the same. Add -3 and 2: that's -1. So the answer is -1/7.",
    },
}


def print_tutor(message: str):
    """Print tutor message with formatting."""
    print(f"\nTutor: {message}")


def get_student_input() -> str:
    """Get input from student."""
    return input("\nYou: ").strip()


def run_demo():
    """Run the single-concept demo interaction."""

    print("\n" + "=" * 60)
    print("IDNA Math Tutor - Demo")
    print("=" * 60)

    # Step 1: Explain the concept step by step
    print_tutor("Today we'll learn to add fractions with the same denominator.")

    for step in CONCEPT["explanation"]:
        print_tutor(step)

    # Step 2: Ask exactly one checking question
    question = CONCEPT["check_question"]
    print_tutor(f"Now you try. {question['text']}")

    # Step 3: Evaluate the student's answer
    # Note: check_answer() handles normalization internally (spoken variants like "minus 1 by 7")
    student_answer = get_student_input()
    is_correct = check_answer(question["answer"], student_answer)

    if is_correct:
        # Correct on first try - acknowledge and end
        print_tutor(f"Yes! {question['explanation']}")
        print_tutor("You got it. Well done today!")
        return

    # Step 4: Wrong answer - give corrective feedback
    print_tutor(f"Not quite. {question['hint']}")
    print_tutor("Try once more.")

    # One retry
    student_answer = get_student_input()
    is_correct = check_answer(question["answer"], student_answer)

    if is_correct:
        print_tutor(f"That's it! {question['explanation']}")
        print_tutor("Good work figuring it out!")
    else:
        # Still wrong - reveal and end gracefully
        print_tutor(f"The answer is {question['answer']}. {question['explanation']}")
        print_tutor("That's okay. Practice makes perfect!")

    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
