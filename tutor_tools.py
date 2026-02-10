"""
IDNA Tutor Tools - OpenAI Function Calling Definitions
======================================================
6 focused tools for teacher behavior. No generic "speak" tool.
"""

TUTOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "give_hint",
            "description": "Give a hint when student answered wrong. Reference their specific mistake. NEVER reveal the answer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hint_level": {
                        "type": "integer",
                        "enum": [1, 2],
                        "description": "1 = conceptual nudge, 2 = show first step"
                    },
                    "student_mistake": {
                        "type": "string",
                        "description": "What specifically the student got wrong, referencing their actual answer"
                    }
                },
                "required": ["hint_level", "student_mistake"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "praise_and_continue",
            "description": "Praise correct answer with specificity, then move to next question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "what_they_did_well": {
                        "type": "string",
                        "description": "Specific thing they did right (e.g., 'found LCM quickly', 'remembered the sign')"
                    }
                },
                "required": ["what_they_did_well"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "explain_solution",
            "description": "Walk through full solution. ONLY use after 2 hints have been given.",
            "parameters": {
                "type": "object",
                "properties": {
                    "acknowledge_struggle": {
                        "type": "string",
                        "description": "Brief acknowledgment like 'This one's tricky' or 'Let me show you'"
                    }
                },
                "required": ["acknowledge_struggle"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "encourage_attempt",
            "description": "Student said 'I don't know' or is stuck. Push them to try. NEVER give answer.",
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
            "name": "ask_what_they_did",
            "description": "Before correcting, ask the student to explain their thinking. Real teachers do this.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question_type": {
                        "type": "string",
                        "enum": ["what_did_you_do", "walk_me_through", "how_did_you_get_that"],
                        "description": "Type of diagnostic question"
                    }
                },
                "required": ["question_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "end_session",
            "description": "Wrap up the tutoring session with a warm summary.",
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
