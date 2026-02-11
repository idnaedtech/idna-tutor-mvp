"""
IDNA Tutor Tools - OpenAI Function Calling Definitions
======================================================
5 tools. No ask_what_they_did — it caused infinite loops.

Decision tree for the LLM:
  Student answer matches answer key exactly → praise_and_continue
  Student answer is partially correct       → guide_partial_answer
  Student answer is wrong                   → give_hint
  Student says IDK / is stuck               → encourage_attempt
  Student wants to stop                     → end_session
"""

TUTOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "praise_and_continue",
            "description": (
                "Student's answer is CORRECT — matches the answer key. "
                "Use this when the student gives the right final answer. "
                "Say 'Sahi hai' or 'Correct' briefly, then move to the next question. "
                "Do NOT ask them to explain their process. Just confirm and move on."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "what_they_did_well": {
                        "type": "string",
                        "description": "One specific thing (e.g. 'added numerators correctly', 'got the sign right')"
                    }
                },
                "required": ["what_they_did_well"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "guide_partial_answer",
            "description": (
                "Student's answer is PARTIALLY correct — they got part of the answer right "
                "but not the complete answer. Examples: said the numerator but forgot denominator, "
                "got the operation right but made a sign error, said '-1' when answer is '-1/7'. "
                "Acknowledge what's correct, then guide them to the missing piece."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "correct_part": {
                        "type": "string",
                        "description": "What the student got right (e.g. 'numerator is correct as minus 1')"
                    },
                    "missing_part": {
                        "type": "string",
                        "description": "What's missing or wrong (e.g. 'forgot to include the denominator 7')"
                    }
                },
                "required": ["correct_part", "missing_part"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "give_hint",
            "description": (
                "Student's answer is WRONG — does not match the answer key, not even partially. "
                "Point out their specific mistake gently, then give a hint. "
                "NEVER reveal the full answer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "hint_level": {
                        "type": "integer",
                        "enum": [1, 2],
                        "description": "1 = conceptual nudge pointing to their error, 2 = show the first step"
                    },
                    "student_mistake": {
                        "type": "string",
                        "description": "What specifically the student got wrong"
                    }
                },
                "required": ["hint_level", "student_mistake"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "encourage_attempt",
            "description": (
                "Student said 'I don't know', is confused, or hasn't attempted. "
                "Break the problem into a smaller piece. Ask for just the first step. "
                "NEVER give the answer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "approach": {
                        "type": "string",
                        "enum": ["break_down", "first_step", "reduce_pressure"],
                        "description": "How to encourage: break into smaller piece, ask for first step, or reduce anxiety"
                    }
                },
                "required": ["approach"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "end_session",
            "description": "Student wants to stop. Wrap up warmly.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "enum": ["completed", "student_requested", "time_limit"]
                    }
                },
                "required": ["reason"]
            }
        }
    }
]
