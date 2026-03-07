"""
IDNA Guardrails - Python Enforces Teaching Rules
=================================================
The agent proposes. Guardrails dispose.
"""


def check_guardrails(tool_name: str, args: dict, session: dict) -> dict:
    """
    Override agent decisions that violate teaching rules.

    Returns:
        {
            "blocked": bool,
            "override_tool": str or None,
            "override_args": dict or None,
            "reason": str or None
        }
    """
    result = {
        "blocked": False,
        "override_tool": None,
        "override_args": None,
        "reason": None
    }

    hint_count = session.get("hint_count", 0)
    attempt_count = session.get("attempt_count", 0)
    idk_count = session.get("idk_count", 0)
    duration = session.get("duration_minutes", 0)
    language = session.get("language", "hinglish")

    # GUARDRAIL 1: Can't explain_solution before giving 2 hints
    if tool_name == "explain_solution" and hint_count < 2:
        result["blocked"] = True
        result["override_tool"] = "give_hint"
        result["override_args"] = {
            "hint_level": hint_count + 1,
            "student_mistake": "Student needs more support before full explanation"
        }
        result["reason"] = f"Blocked explain_solution: only {hint_count} hints given"

    # GUARDRAIL 2: Can't skip to hint level 2 without hint level 1
    if tool_name == "give_hint":
        if args.get("hint_level") == 2 and hint_count == 0:
            args["hint_level"] = 1
            result["reason"] = "Downgraded hint to level 1"

    # GUARDRAIL 3: Session time limit (25 minutes)
    if duration >= 25 and tool_name not in ["end_session", "praise_and_continue"]:
        result["blocked"] = True
        result["override_tool"] = "end_session"
        result["override_args"] = {"reason": "time_limit"}
        result["reason"] = "Session time limit reached"

    # GUARDRAIL 4: Max 5 attempts per question - force explanation
    if attempt_count >= 5 and tool_name not in ["explain_solution", "end_session", "praise_and_continue"]:
        result["blocked"] = True
        result["override_tool"] = "explain_solution"
        result["override_args"] = {"acknowledge_struggle": "This one's tricky. Let me walk you through it."}
        result["reason"] = "Max attempts reached"

    # GUARDRAIL 5: Can't praise if answer was wrong
    if tool_name == "praise_and_continue":
        last_eval = session.get("last_eval", {})
        if not last_eval.get("is_correct", False):
            result["blocked"] = True
            result["override_tool"] = "give_hint"
            result["override_args"] = {
                "hint_level": min(hint_count + 1, 2),
                "student_mistake": "Answer was not correct"
            }
            result["reason"] = "Blocked praise: answer was wrong"

    # GUARDRAIL 6: Escalate after multiple IDKs - don't loop forever
    if tool_name == "encourage_attempt":
        if idk_count >= 3:
            result["blocked"] = True
            result["override_tool"] = "explain_solution"
            result["override_args"] = {
                "acknowledge_struggle": "Let me explain this one."
            }
            result["reason"] = f"IDK count {idk_count} - explaining solution"
        elif idk_count >= 2:
            result["blocked"] = True
            result["override_tool"] = "give_hint"
            result["override_args"] = {
                "hint_level": 1,
                "student_mistake": "Student needs a hint"
            }
            result["reason"] = f"IDK count {idk_count} - giving hint"

    return result
