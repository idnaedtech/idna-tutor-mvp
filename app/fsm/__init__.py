"""
IDNA EdTech v8.0 — FSM Package

Complete finite state machine for tutor interactions.
All 60 state × input combinations are defined.
"""
from app.fsm.transitions import TRANSITIONS, TransitionResult, get_transition
from app.fsm.handlers import handle_state

__all__ = ["TRANSITIONS", "TransitionResult", "get_transition", "handle_state"]
