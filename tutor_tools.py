"""
IDNA Tutor Tools - OpenAI Function Calling Definitions
======================================================
Tools for judging answers. Order matters - correct answer tool is FIRST.
"""

TUTOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "praise_and_continue",
            "description": "CORRECT ANSWER. Student got it right. Use this.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ask_what_they_did",
            "description": "WRONG ANSWER. Ask what they did before correcting.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "give_hint",
            "description": "WRONG ANSWER + already asked. Give a hint.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hint_level": {
                        "type": "integer",
                        "enum": [1, 2],
                        "description": "1 = nudge, 2 = first step"
                    }
                },
                "required": ["hint_level"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "explain_solution",
            "description": "STUCK. Show full solution after 2 hints.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "encourage_attempt",
            "description": "IDK. Student doesn't know, encourage them.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "end_session",
            "description": "END. Student wants to stop.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]
