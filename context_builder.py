"""
IDNA Context Builder - What the Agent Sees
==========================================
The context packet gives the agent full awareness of the teaching situation.
Evaluation happens BEFORE this is called - agent doesn't decide correctness.
"""


def build_context(session: dict, student_input: str, eval_result: dict = None) -> str:
    """
    Build the context packet for the agent.

    Key design: evaluation result is INCLUDED so the agent doesn't decide correctness.
    The agent sees "Correct: True/False" and acts accordingly.
    """
    q = session.get("current_question", {})

    # Session info
    context = f"""## CURRENT TEACHING SITUATION

### Session
- Student: {session.get('student_name', 'Student')} (Class 8)
- Chapter: {session.get('chapter', 'Math')}
- Questions done: {session.get('questions_completed', 0)}/{session.get('total_questions', 10)}
- Score: {session.get('score', 0)}/{session.get('questions_completed', 0)}
- Time: {session.get('duration_minutes', 0)} minutes

### Current Question
- Question: {q.get('text', q.get('question_text', 'No question'))}
- Topic: {q.get('topic', 'math')}
- Hints given: {session.get('hint_count', 0)}/2
- Attempts: {session.get('attempt_count', 0)}
"""

    # Evaluation result (computed by Python, not agent)
    if eval_result:
        context += f"""
### Evaluation Result (computed by system - do not override)
- Student said: "{student_input}"
- Normalized: "{eval_result.get('normalized_answer', student_input)}"
- Correct: {eval_result.get('is_correct', False)}
"""
        # Add diagnosis if available (from common_mistakes matching)
        if eval_result.get('diagnosis'):
            context += f"- Diagnosis: {eval_result.get('diagnosis')}\n"
        if eval_result.get('micro_hint'):
            context += f"- Suggested micro-hint: {eval_result.get('micro_hint')}\n"
        if eval_result.get('feedback_tag') and eval_result.get('feedback_tag') != 'UNKNOWN':
            context += f"- Error type: {eval_result.get('feedback_tag')}\n"

        # Special cases
        if eval_result.get('is_idk'):
            context += "- Student said they don't know (IDK detected)\n"
        if eval_result.get('is_offtopic'):
            context += "- Student went off-topic\n"
        if eval_result.get('is_stop'):
            context += "- Student wants to stop the session\n"

    else:
        context += f"""
### Student Said
"{student_input}"
"""

    # Hint directions (for agent to craft hints, NOT the answer)
    context += f"""
### Hint Directions (DO NOT reveal answer to student)
- Hint 1: {q.get('hint_1', q.get('hint', 'Think about the concept'))}
- Hint 2: {q.get('hint_2', 'Try the first step')}
"""

    # Recent history for context
    history = session.get('history', [])[-4:]  # Last 2 exchanges
    if history:
        context += "\n### Recent Exchange\n"
        for h in history:
            context += f"- Student: {h.get('student', '')}\n"
            context += f"- Teacher: {h.get('teacher', '')}\n"

    # Decision guidance
    context += """
### Your Decision
Based on the evaluation result above:
- If Correct → praise_and_continue
- If Wrong + attempts = 1 → consider ask_what_they_did (diagnose first)
- If Wrong + hints < 2 → give_hint
- If Wrong + hints >= 2 → explain_solution
- If IDK → encourage_attempt
- If Stop requested → end_session

Remember: Reference the student's SPECIFIC answer in your response.
"""

    return context


def build_start_context(session: dict) -> str:
    """Build context for session start (no student input yet)."""
    return f"""## SESSION START

Student: {session.get('student_name', 'Student')} (Class 8)
Chapter: {session.get('chapter', 'Math')}
Total questions: {session.get('total_questions', 10)}

First question: {session.get('current_question', {}).get('text', '')}

Greet the student briefly and ask the first question.
Keep it short - max 2 sentences for greeting, then the question.
"""
