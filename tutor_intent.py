"""
IDNA EdTech - TutorIntent Layer
================================
This module implements the TutorIntent system for natural, human-like teaching behavior.

Architecture (per PRD):
- Brain = FSM (flow control) + Evaluator (deterministic)
- LLM = Language layer ONLY (phrasing, not judging)
- TutorIntent = Controls teaching micro-behaviors

Key Principles:
1. Voice pacing: max 2 sentences per turn
2. One idea per sentence
3. Avoid robotic transitions ("Now," "Therefore," "Next,")
4. Warm, encouraging tone for Tier 2/3 Indian students
5. USE GPT for natural phrasing - never sound robotic
"""

from enum import Enum
from typing import Optional, Dict, Any, List
import random
import os
import time
import json
import logging
from datetime import datetime, timezone
from functools import lru_cache
from openai import OpenAI


# Simple structured logger for GPT calls
_gpt_logger = logging.getLogger("idna.gpt")
if not _gpt_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    _gpt_logger.addHandler(handler)
    _gpt_logger.setLevel(logging.INFO)


def _log_gpt_call(message: str, **context):
    """Log GPT call with structured JSON."""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "level": "INFO",
        "message": message,
        **{k: v for k, v in context.items() if v is not None}
    }
    _gpt_logger.info(json.dumps(log_entry))

# Initialize OpenAI client for natural response generation
_openai_client = None

def get_openai_client():
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=15.0,  # Reduced timeout - fail fast
            max_retries=1  # Reduce retries, use fallback instead
        )
    return _openai_client


# ============================================================
# RESPONSE CACHING - Reduces GPT API calls significantly
# ============================================================

# Pre-generated responses - VERY SHORT for voice
_cached_responses: Dict[str, List[str]] = {
    "session_start": [
        "Hello! Great to see you. Which chapter would you like to practice today?",
        "Hi there! Ready to learn something new? Pick a chapter to begin.",
        "Welcome back! Let's make today's practice count. Choose a chapter.",
    ],
    "session_end": [
        "Good work today!",
        "Nice practice!",
    ],
    "move_on": [
        "Next one.",
        "Let's try another.",
        "Next question.",
    ],
    "confirm_correct": [
        "Yes!",
        "Correct!",
        "That's right!",
        "Exactly!",
        "You got it!",
    ],
}

# Time-based cache for GPT responses (avoids repeated calls)
_gpt_response_cache: Dict[str, tuple] = {}  # key -> (response, timestamp)
_CACHE_TTL_SECONDS = 300  # 5 minutes

def get_cached_response(intent_key: str) -> str:
    """Get a random pre-cached response for common intents."""
    responses = _cached_responses.get(intent_key, [])
    if responses:
        return random.choice(responses)
    return ""

def get_gpt_cache_key(intent: str, question: str = "", student_answer: str = "") -> str:
    """Generate cache key for GPT responses."""
    # For question-specific intents, include question hash
    if question:
        q_hash = hash(question) % 10000
        return f"{intent}:{q_hash}:{student_answer[:20] if student_answer else ''}"
    return intent

def get_cached_gpt_response(cache_key: str) -> Optional[str]:
    """Get cached GPT response if still valid."""
    if cache_key in _gpt_response_cache:
        response, timestamp = _gpt_response_cache[cache_key]
        if time.time() - timestamp < _CACHE_TTL_SECONDS:
            return response
        # Expired - remove
        del _gpt_response_cache[cache_key]
    return None

def set_cached_gpt_response(cache_key: str, response: str):
    """Cache a GPT response with timestamp."""
    # Limit cache size
    if len(_gpt_response_cache) > 100:
        # Remove oldest entries
        oldest_keys = sorted(_gpt_response_cache.keys(),
                           key=lambda k: _gpt_response_cache[k][1])[:20]
        for k in oldest_keys:
            del _gpt_response_cache[k]
    _gpt_response_cache[cache_key] = (response, time.time())


# System prompt for the tutor persona
TUTOR_PERSONA = """You are a friendly math tutor for Class 8 students in India (CBSE/NCERT).

CRITICAL RULES:
1. MAX 1-2 SHORT SENTENCES. This is spoken aloud - long responses get cut off.
2. NO Hindi words. Speak only in English.
3. Be conversational, like chatting with a student sitting next to you.

WHEN CORRECT:
- One sentence confirmation + why it works
- Example: "Yes! When denominators match, you just add the top numbers."

WHEN WRONG:
- One guiding question or hint
- Example: "Close! What's -3 plus 2?"

WHEN EXPLAINING:
- Maximum 2 sentences. Keep it simple.
- Example: "The 7 stays the same. You just add -3 and 2, which gives -1."

NEVER:
- Write paragraphs
- Use filler words (Hmm, Alright, So, Now)
- Sound like a textbook
- Mix Hindi words

ALWAYS:
- Sound like a real person talking
- Keep responses SHORT (under 20 words ideally)
- One idea per response
"""


class TutorIntent(Enum):
    """
    Teaching intents that map to FSM states.
    Each intent has specific phrasing rules and emotional tone.
    """
    ASK_FRESH = "ask_fresh"           # Present new question
    CONFIRM_CORRECT = "confirm_correct"  # Celebrate right answer
    GUIDE_THINKING = "guide_thinking"    # Hint 1 - Socratic nudge
    NUDGE_CORRECTION = "nudge_correction"  # Hint 2 - Direct guidance
    EXPLAIN_ONCE = "explain_once"        # Show solution after 3 attempts
    EXPLAIN_STEPS = "explain_steps"      # Student asked for step-by-step help
    MOVE_ON = "move_on"                  # Transition to next question
    ENCOURAGE_RETRY = "encourage_retry"  # Gentle encouragement to try again
    SESSION_START = "session_start"      # Welcome message
    SESSION_END = "session_end"          # Closing message


# Phrases that indicate student wants help, not submitting an answer
HELP_REQUEST_PHRASES = [
    "explain", "help", "don't understand", "dont understand",
    "how do i", "how do you", "show me", "what do you mean",
    "i'm confused", "im confused", "can you explain",
    "step by step", "simple terms", "break it down",
    "i don't get it", "i dont get it", "what does that mean",
    "how does", "why does", "tell me how", "teach me",
    "hint", "clue", "stuck", "lost", "confused"
]


def is_help_request(text: str) -> bool:
    """Check if student is asking for help rather than submitting an answer."""
    text_lower = text.lower().strip()
    return any(phrase in text_lower for phrase in HELP_REQUEST_PHRASES)


# ============================================================
# OFF-TOPIC DETECTION (PRD: Redirect unrelated speech)
# ============================================================

# Patterns that indicate off-topic conversation
OFF_TOPIC_PATTERNS = {
    # Greetings and small talk
    "greetings": [
        "hello", "hi there", "hey", "good morning", "good afternoon",
        "good evening", "how are you", "what's up", "wassup", "howdy",
        "namaste", "namaskar",
    ],
    # Personal questions about the tutor
    "personal": [
        "what's your name", "who are you", "are you a robot",
        "are you human", "are you real", "where are you from",
        "how old are you", "what do you look like", "are you ai",
        "are you chatgpt", "are you claude",
    ],
    # Weather and environment
    "weather": [
        "what's the weather", "is it raining", "is it sunny",
        "what's the temperature", "how's the weather",
    ],
    # Time and date
    "time": [
        "what time is it", "what's the time", "what day is it",
        "what's the date", "what's today",
    ],
    # Entertainment and games
    "entertainment": [
        "tell me a joke", "sing a song", "play a game",
        "tell me a story", "let's play", "can we play",
        "i'm bored", "this is boring",
    ],
    # Food and breaks
    "breaks": [
        "i'm hungry", "i'm thirsty", "can i take a break",
        "i want to stop", "i'm tired", "can we stop",
    ],
    # Complaints and refusals
    "complaints": [
        "i don't want to", "i don't like math", "math is hard",
        "this is too hard", "i hate this", "i can't do this",
        "i give up", "forget it", "never mind",
    ],
    # Random topics
    "random": [
        "do you like", "what's your favorite", "have you ever",
        "can you tell me about", "what do you think about",
        "do you know", "where is", "who is", "when is",
    ],
}

# Redirect messages (PRD: Acknowledge briefly, redirect immediately)
OFF_TOPIC_REDIRECTS = [
    "Let's focus on the question. What's your answer?",
    "We can chat later! Right now, tell me your answer.",
    "Let's get back to math. What do you think the answer is?",
    "Good question, but let's solve this first. Your answer?",
    "I'd love to chat, but let's finish this question first!",
    "Let's stay focused. What's your answer to this one?",
]

# Specific redirects for certain categories
CATEGORY_REDIRECTS = {
    "greetings": [
        "Hi! Let's get back to the question. What's your answer?",
        "Hello! Now, what do you think the answer is?",
    ],
    "complaints": [
        "I know it's tough, but you can do this! Try answering.",
        "Don't give up! Take a guess - what do you think?",
        "It's okay to find it hard. Just try your best!",
    ],
    "breaks": [
        "Almost done! Just answer this one, then we can take a break.",
        "Let's finish this question first, then you can rest.",
    ],
}


def _contains_math_answer(text: str) -> bool:
    """
    Check if text contains a valid math answer, even mixed with other words.

    Examples that should return True:
    - "11 by 12" → True
    - "hi, it's 11 by 12" → True (contains fraction)
    - "the answer is 5" → True
    - "two thirds" → True
    - "hello" → False
    - "i don't know" → False

    This prevents off-topic detection from rejecting valid answers
    that happen to include greetings or other words.
    """
    import re
    text_lower = text.lower().strip()

    # Pattern 1: Contains digits (most common for math answers)
    if re.search(r'\d', text_lower):
        return True

    # Pattern 2: Contains number words that could be an answer
    answer_words = [
        "zero", "one", "two", "three", "four", "five", "six", "seven",
        "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
        "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
        "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
        "hundred", "thousand", "million",
        # Fractions
        "half", "halves", "third", "thirds", "fourth", "fourths", "quarter",
        "quarters", "fifth", "fifths", "sixth", "sixths", "seventh", "sevenths",
        "eighth", "eighths", "ninth", "ninths", "tenth", "tenths",
        # Math operations that indicate an answer
        "minus", "negative", "plus", "positive", "percent",
    ]

    for word in answer_words:
        if re.search(rf'\b{word}\b', text_lower):
            return True

    # Pattern 3: Contains fraction indicators with words around them
    # "by", "over", "divided by" often indicate fractions
    if re.search(r'\b(by|over|divided)\b', text_lower):
        # Only count as answer if there are also numbers or number words nearby
        if re.search(r'(\d|one|two|three|four|five|six|seven|eight|nine|ten)', text_lower):
            return True

    return False


def detect_off_topic(text: str) -> dict:
    """
    Detect if student's response is off-topic (not an answer attempt).

    PRD behavior:
    - Acknowledge briefly
    - Redirect immediately
    - Example: "We'll talk later. Tell me the answer to this question."

    IMPORTANT: If the text contains ANY valid math answer (even mixed with
    greetings like "hi, it's 11 by 12"), we treat it as an answer attempt,
    NOT off-topic. This prevents rejecting valid answers.

    Args:
        text: The student's spoken/typed response

    Returns:
        dict with:
        - is_off_topic: True if response is off-topic
        - category: Which category of off-topic (greetings, personal, etc.)
        - redirect_message: Message to redirect student back to question
    """
    text_lower = text.lower().strip()

    # CRITICAL FIX: Check for valid math answer FIRST
    # If text contains any math answer, it's NOT off-topic
    # This handles cases like "hi, it's 11 by 12"
    if _contains_math_answer(text_lower):
        return {"is_off_topic": False, "category": None, "redirect_message": None}

    # Legacy checks (kept for backwards compatibility but _contains_math_answer should catch these)
    import re
    if re.match(r'^[\d\s\.\-\+\/\*xX=]+$', text_lower):
        return {"is_off_topic": False, "category": None, "redirect_message": None}

    # Check each category of off-topic patterns
    for category, patterns in OFF_TOPIC_PATTERNS.items():
        for pattern in patterns:
            if pattern in text_lower:
                # Get category-specific redirect or general one
                if category in CATEGORY_REDIRECTS:
                    redirect = random.choice(CATEGORY_REDIRECTS[category])
                else:
                    redirect = random.choice(OFF_TOPIC_REDIRECTS)

                return {
                    "is_off_topic": True,
                    "category": category,
                    "redirect_message": redirect,
                }

    # Not off-topic
    return {"is_off_topic": False, "category": None, "redirect_message": None}


# Phrasing templates for each intent
# Format: List of templates with {placeholders} for dynamic content
INTENT_PHRASES = {
    TutorIntent.ASK_FRESH: {
        "style": "curious, inviting",
        "max_sentences": 2,
        "templates": [
            "Here's your question. {question}",
            "Let's try this one. {question}",
            "Ready? {question}",
            "Okay, here we go. {question}",
            "Try this one. {question}",
        ]
    },
    
    TutorIntent.CONFIRM_CORRECT: {
        "style": "warm",
        "max_sentences": 2,
        "templates": [
            "Yes, that's right.",
            "Correct! You got it.",
            "Exactly right.",
            "That's it. Nice work.",
        ]
    },

    TutorIntent.GUIDE_THINKING: {
        "style": "helpful",
        "max_sentences": 2,
        "templates": [
            "Not quite. {hint} Try again.",
            "Close, but not exactly. {hint}",
            "Think about this: {hint}",
        ]
    },

    TutorIntent.NUDGE_CORRECTION: {
        "style": "supportive",
        "max_sentences": 2,
        "templates": [
            "Let me help. {hint}",
            "Here's a bigger hint: {hint}",
        ]
    },

    TutorIntent.EXPLAIN_ONCE: {
        "style": "teaching",
        "max_sentences": 3,
        "templates": [
            "Here's how it works: {solution}",
            "Let me explain. {solution}",
        ]
    },

    TutorIntent.MOVE_ON: {
        "style": "brief",
        "max_sentences": 1,
        "templates": [
            "Let's try another one.",
            "On to the next one.",
        ]
    },

    TutorIntent.ENCOURAGE_RETRY: {
        "style": "supportive",
        "max_sentences": 1,
        "templates": [
            "Take your time. Think it through.",
            "No rush. You can do this.",
        ]
    },

    TutorIntent.SESSION_START: {
        "style": "warm",
        "max_sentences": 1,
        "templates": [
            "Hi! Ready to practice some math?",
            "Let's do some math together.",
        ]
    },

    TutorIntent.SESSION_END: {
        "style": "encouraging",
        "max_sentences": 2,
        "templates": [
            "Good work today. Keep practicing!",
            "Nice effort. See you next time.",
        ]
    },
}


# SSML templates for natural voice synthesis
# SSML with natural pauses - tutor-like warmth
PHRASES_SSML = {
    TutorIntent.ASK_FRESH: [
        "<speak>{question}</speak>",
    ],
    TutorIntent.CONFIRM_CORRECT: [
        "<speak>Yes, that's right.</speak>",
        "<speak>Correct.<break time='150ms'/> You got it.</speak>",
        "<speak>Exactly right.</speak>",
    ],
    TutorIntent.GUIDE_THINKING: [
        "<speak>Not quite.<break time='200ms'/> {hint}<break time='150ms'/> Try again.</speak>",
        "<speak>Close, but not exactly.<break time='200ms'/> {hint}</speak>",
    ],
    TutorIntent.NUDGE_CORRECTION: [
        "<speak>Let me help.<break time='200ms'/> {hint}</speak>",
    ],
    TutorIntent.EXPLAIN_ONCE: [
        "<speak>Here's how it works.<break time='200ms'/> {solution}</speak>",
    ],
    TutorIntent.MOVE_ON: [
        "<speak>Let's try another one.</speak>",
    ],
    TutorIntent.ENCOURAGE_RETRY: [
        "<speak>Take your time.<break time='150ms'/> Think it through.</speak>",
    ],
    TutorIntent.SESSION_START: [
        "<speak>Hi!<break time='150ms'/> Ready to practice some math?</speak>",
    ],
    TutorIntent.SESSION_END: [
        "<speak>Good work today.<break time='150ms'/> Keep practicing!</speak>",
    ],
}


def generate_ssml_response(intent: TutorIntent, **kwargs) -> str:
    """
    Generate SSML response for given intent with placeholders filled.

    Args:
        intent: The TutorIntent to generate SSML for
        **kwargs: Placeholder values (question, hint, solution, etc.)

    Returns:
        SSML string ready for Google Cloud TTS
    """
    templates = PHRASES_SSML.get(intent, ["<speak>{text}</speak>"])
    template = random.choice(templates)

    # Fill placeholders safely
    try:
        return template.format(**kwargs) if kwargs else template
    except KeyError:
        # If placeholder not provided, return template as-is
        return template


def strip_ssml(ssml: str) -> str:
    """
    Strip SSML tags to get plain text for fallback TTS.

    Args:
        ssml: SSML string

    Returns:
        Plain text without SSML tags
    """
    import re
    # Remove <speak> tags
    text = re.sub(r'</?speak>', '', ssml)
    # Remove <break> tags
    text = re.sub(r'<break[^>]*/?>', ' ', text)
    # Clean up extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


class TutorVoice:
    """
    Generates natural tutor responses based on intent and context.
    Ensures voice-friendly pacing and warm tone.
    """
    
    def __init__(self, language: str = "en"):
        """
        Initialize the tutor voice.
        
        Args:
            language: Language code (default: "en" for English)
                      Future: "hi" for Hindi, "te" for Telugu, etc.
        """
        self.language = language
        self.phrases = INTENT_PHRASES
    
    def get_response(
        self,
        intent: TutorIntent,
        question: Optional[str] = None,
        hint: Optional[str] = None,
        solution: Optional[str] = None,
        student_answer: Optional[str] = None,
        correct_answer: Optional[str] = None,
        attempt_number: int = 0,
        score: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        Generate a natural tutor response for the given intent.
        
        Args:
            intent: The TutorIntent to respond with
            question: The math question (for ASK_FRESH)
            hint: The hint text (for GUIDE_THINKING, NUDGE_CORRECTION)
            solution: The solution explanation (for EXPLAIN_ONCE)
            student_answer: What the student answered
            correct_answer: The correct answer
            attempt_number: Which attempt this is (1, 2, or 3)
            score: Dict with 'correct' and 'total' keys
            
        Returns:
            A natural, voice-friendly tutor response string
        """
        phrase_config = self.phrases.get(intent)
        if not phrase_config:
            return "Let's continue."
        
        # Select a random template
        template = random.choice(phrase_config["templates"])
        
        # Fill in placeholders
        response = template
        if question:
            response = response.replace("{question}", question)
        if hint:
            response = response.replace("{hint}", hint)
        if solution:
            response = response.replace("{solution}", solution)
        if correct_answer:
            response = response.replace("{correct_answer}", correct_answer)
        
        return response
    
    def determine_intent(
        self,
        is_correct: bool,
        attempt_number: int,
        is_session_start: bool = False,
        is_session_end: bool = False,
        is_new_question: bool = False,
    ) -> TutorIntent:
        """
        Determine the appropriate TutorIntent based on FSM state.
        
        FSM Transitions → Intent Mapping:
        - Correct answer → CONFIRM_CORRECT
        - Wrong attempt 1 → GUIDE_THINKING
        - Wrong attempt 2 → NUDGE_CORRECTION  
        - Wrong attempt 3 → EXPLAIN_ONCE
        - New question → ASK_FRESH
        - Session start → SESSION_START
        - Session end → SESSION_END
        
        Args:
            is_correct: Whether the answer was correct
            attempt_number: Current attempt number (1, 2, or 3)
            is_session_start: Whether this is the start of a session
            is_session_end: Whether this is the end of a session
            is_new_question: Whether presenting a new question
            
        Returns:
            The appropriate TutorIntent
        """
        if is_session_start:
            return TutorIntent.SESSION_START
        
        if is_session_end:
            return TutorIntent.SESSION_END
        
        if is_new_question:
            return TutorIntent.ASK_FRESH
        
        if is_correct:
            return TutorIntent.CONFIRM_CORRECT
        
        # Wrong answer - escalate hints
        if attempt_number == 1:
            return TutorIntent.GUIDE_THINKING
        elif attempt_number == 2:
            return TutorIntent.NUDGE_CORRECTION
        else:  # attempt_number >= 3
            return TutorIntent.EXPLAIN_ONCE
    
    def build_full_response(
        self,
        is_correct: bool,
        attempt_number: int,
        question: Optional[str] = None,
        hint_1: Optional[str] = None,
        hint_2: Optional[str] = None,
        solution: Optional[str] = None,
        correct_answer: Optional[str] = None,
        move_to_next: bool = False,
    ) -> Dict[str, Any]:
        """
        Build a complete response with intent, text, and metadata.
        
        This is the main method to call from the API endpoint.
        
        Args:
            is_correct: Whether the answer was correct
            attempt_number: Current attempt number
            question: The current question text
            hint_1: First hint (Socratic)
            hint_2: Second hint (direct)
            solution: Full solution explanation
            correct_answer: The correct answer
            move_to_next: Whether to transition to next question
            
        Returns:
            Dict with:
                - intent: TutorIntent name
                - response: The tutor's spoken response
                - move_to_next: Whether to show next question
                - show_answer: Whether to reveal the answer
        """
        intent = self.determine_intent(
            is_correct=is_correct,
            attempt_number=attempt_number,
        )
        
        # Select appropriate hint based on attempt
        hint = None
        if intent == TutorIntent.GUIDE_THINKING:
            hint = hint_1 or "Think about what operation you need."
        elif intent == TutorIntent.NUDGE_CORRECTION:
            hint = hint_2 or hint_1 or "Check your calculation carefully."
        
        # Build the main response (plain text)
        response = self.get_response(
            intent=intent,
            question=question,
            hint=hint,
            solution=solution or f"The answer is {correct_answer}.",
            correct_answer=correct_answer,
            attempt_number=attempt_number,
        )

        # Build SSML response for warmer voice
        ssml_kwargs = {
            "question": question or "",
            "hint": hint or "",
            "solution": solution or f"The answer is {correct_answer}.",
            "correct_answer": correct_answer or "",
        }
        ssml_response = generate_ssml_response(intent, **ssml_kwargs)

        # Add transition if moving to next question
        should_move = is_correct or attempt_number >= 3
        if should_move and move_to_next:
            move_phrase = self.get_response(TutorIntent.MOVE_ON)
            response = f"{response} {move_phrase}"
            # Add SSML transition
            ssml_move = generate_ssml_response(TutorIntent.MOVE_ON)
            # Combine SSML (strip outer <speak> tags and re-wrap)
            ssml_inner = ssml_response.replace("<speak>", "").replace("</speak>", "")
            ssml_move_inner = ssml_move.replace("<speak>", "").replace("</speak>", "")
            ssml_response = f"<speak>{ssml_inner}<break time='400ms'/> {ssml_move_inner}</speak>"

        return {
            "intent": intent.value,
            "response": response,
            "ssml": ssml_response,
            "move_to_next": should_move,
            "show_answer": intent == TutorIntent.EXPLAIN_ONCE,
            "attempt_number": attempt_number,
        }


def generate_gpt_response(
    intent: TutorIntent,
    question: str = "",
    student_answer: str = "",
    hint: str = "",
    solution: str = "",
    correct_answer: str = "",
    attempt_number: int = 1,
    use_cache: bool = True,
) -> str:
    """
    Use GPT-4o-mini to generate a warm, natural tutor response.

    This is the key to making the tutor sound human, not robotic.
    The FSM decides WHAT to say (intent), GPT decides HOW to say it.

    PERFORMANCE: Uses caching to reduce API calls:
    - Common intents (SESSION_START, SESSION_END, MOVE_ON) use pre-cached responses
    - Question-specific responses are cached for 5 minutes
    """

    # OPTIMIZATION: Use pre-cached responses only for simple transitions
    # Let GPT handle substantive responses for more natural conversation
    if use_cache:
        intent_cache_map = {
            TutorIntent.SESSION_START: "session_start",
            TutorIntent.SESSION_END: "session_end",
            TutorIntent.MOVE_ON: "move_on",
        }
        if intent in intent_cache_map:
            cached = get_cached_response(intent_cache_map[intent])
            if cached:
                _log_gpt_call(
                    "GPT cache hit (pre-cached)",
                    event="gpt_cache_hit",
                    intent=intent.value,
                    cache_type="pre_cached",
                )
                return cached

    # OPTIMIZATION: Check time-based cache for recent similar queries
    cache_key = get_gpt_cache_key(intent.value, question, student_answer)
    if use_cache:
        cached_response = get_cached_gpt_response(cache_key)
        if cached_response:
            _log_gpt_call(
                "GPT cache hit (time-based)",
                event="gpt_cache_hit",
                intent=intent.value,
                cache_type="time_based",
            )
            return cached_response

    # Build the context for GPT - STRICT length limits for voice
    intent_instructions = {
        TutorIntent.ASK_FRESH: f"""Say this question: {question}

ONE sentence only. Just ask the question naturally.""",

        TutorIntent.CONFIRM_CORRECT: f"""Student said "{student_answer}" - CORRECT!

Reply in ONE short sentence. Confirm and briefly say why.
Examples:
- "Yes! Denominators match, so you just add the tops."
- "Exactly right!"
- "That's it! -3 plus 2 is -1."

MAX 15 WORDS. No paragraphs.""",

        TutorIntent.GUIDE_THINKING: f"""Student said "{student_answer}" but answer is {correct_answer}.

Give ONE short hint as a question. Guide them to think.
Examples:
- "Close! What's -3 plus 2?"
- "Almost. The bottom stays 7, what about the top?"
- "Think again - if you owe 3 and get 2, what do you owe?"

MAX 15 WORDS. ONE sentence only.""",

        TutorIntent.NUDGE_CORRECTION: f"""Student stuck. Said "{student_answer}", answer is {correct_answer}.
Hint: {hint}

Give a direct mini-hint. ONE sentence.
Examples:
- "-3 plus 2 equals -1. Put that over 7."
- "Add the tops: -3 + 2 = ?"
- "The denominator stays same. Just add -3 and 2."

MAX 20 WORDS.""",

        TutorIntent.EXPLAIN_ONCE: f"""Student couldn't get it. Answer was {correct_answer}.
Solution: {solution}

Explain simply in 2 SHORT sentences max.
Example:
- "The answer is -1/7. When denominators match, add the numerators: -3 + 2 = -1."

MAX 25 WORDS total. No long explanations.""",

        TutorIntent.EXPLAIN_STEPS: f"""Question: {question}
Solution: {solution}

Give 2-3 very short steps. One line each.
Example:
- "Step 1: Denominators are same, so keep 7."
- "Step 2: Add tops: -3 + 2 = -1."
- "Answer: -1/7."

MAX 30 WORDS total.""",

        TutorIntent.MOVE_ON: "Say: 'Next one.' or 'Let's try another.' MAX 5 WORDS.",

        TutorIntent.SESSION_START: "Say: 'Ready to practice?' MAX 5 WORDS.",

        TutorIntent.SESSION_END: "Say: 'Good work today!' MAX 5 WORDS.",
    }

    user_prompt = intent_instructions.get(intent, "Respond helpfully.")

    try:
        client = get_openai_client()

        # STRICT token limits - short responses for voice
        if intent in [TutorIntent.EXPLAIN_STEPS, TutorIntent.EXPLAIN_ONCE]:
            max_tokens = 60  # 2-3 short sentences max
        elif intent in [TutorIntent.GUIDE_THINKING, TutorIntent.NUDGE_CORRECTION]:
            max_tokens = 40  # One sentence hint
        else:
            max_tokens = 30  # Very short confirmations

        # Time the GPT API call
        start_time = time.perf_counter()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": TUTOR_PERSONA},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7,  # Lower temperature for more consistent short responses
        )
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        result = response.choices[0].message.content.strip()
        # Remove quotes if GPT wrapped the response
        result = result.strip('"').strip("'")

        # Log GPT call completion
        _log_gpt_call(
            "GPT response generated",
            event="gpt_complete",
            intent=intent.value,
            model="gpt-4o-mini",
            latency_ms=latency_ms,
            max_tokens=max_tokens,
            response_length=len(result),
            cached=False,
        )

        # Cache the response for future use
        set_cached_gpt_response(cache_key, result)

        return result
    except Exception as e:
        _log_gpt_call(
            f"GPT error: {str(e)}",
            event="gpt_error",
            intent=intent.value,
            error_type=type(e).__name__,
            error_message=str(e),
        )
        # Fallback to template if GPT fails
        tutor = TutorVoice()
        return tutor.get_response(intent, question=question, hint=hint, solution=solution)


@lru_cache(maxsize=256)
def _wrap_in_ssml_cached(text: str, seed: int) -> str:
    """
    Internal cached SSML wrapping. Seed provides variation while enabling cache hits
    for same text within short time windows.
    """
    import re

    # Use seed for reproducible "randomness" within cache window
    rng = random.Random(seed)

    # Short, natural pauses
    short_pause = rng.choice(["100ms", "120ms", "150ms"])
    med_pause = rng.choice(["200ms", "250ms", "220ms"])
    long_pause = rng.choice(["300ms", "350ms", "280ms"])

    result = text

    # Brief pauses after sentences
    def varied_sentence_pause(match):
        pause = rng.choice(["250ms", "300ms", "280ms"])
        return f'{match.group(1)}<break time="{pause}"/> '

    result = re.sub(r'([.!?])\s+', varied_sentence_pause, result)

    # Natural pause for "..." (thinking)
    result = re.sub(r'\.\.\.', f'<break time="{med_pause}"/>', result)

    # Brief pause after colons
    result = re.sub(r':\s+', f':<break time="{short_pause}"/> ', result)

    # Short pauses after commas
    def varied_comma_pause(match):
        pause = rng.choice(["80ms", "100ms", "120ms"])
        return f',<break time="{pause}"/> '

    result = re.sub(r',\s+', varied_comma_pause, result)

    # Excited/praise words - slight emphasis
    praise_words = [
        "perfect", "exactly", "correct", "amazing", "brilliant",
        "excellent", "great", "nice", "wonderful"
    ]
    for word in praise_words:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        result = pattern.sub(
            lambda m: f'<emphasis level="moderate">{m.group(0)}</emphasis>',
            result
        )

    # Encouraging words - gentle emphasis
    encourage_words = [
        "try", "close", "almost", "nearly", "good", "okay"
    ]
    for word in encourage_words:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        result = pattern.sub(
            lambda m: f'<emphasis level="moderate">{m.group(0)}</emphasis>',
            result
        )

    # Add pitch rise for questions
    if "?" in result:
        result = re.sub(
            r'([^.!?]+\?)',
            r'<prosody pitch="+6%">\1</prosody>',
            result
        )

    # Detect emotion and set base prosody
    text_lower = result.lower()

    # Celebration/excitement - slightly faster, higher pitch
    if any(w in text_lower for w in ["yes!", "perfect", "correct", "excellent", "brilliant", "great"]):
        result = f'<prosody rate="105%" pitch="+3%">{result}</prosody>'
    # Comfort/encouragement when wrong - normal pace, warm
    elif any(w in text_lower for w in ["no problem", "that's okay", "try again", "almost", "close"]):
        result = f'<prosody rate="98%" pitch="-1%">{result}</prosody>'
    # Explanation mode - slightly slower for clarity
    elif any(w in text_lower for w in ["so", "step", "let me", "here's how", "first", "then"]):
        result = f'<prosody rate="95%">{result}</prosody>'
    # Default - normal pace
    else:
        result = f'<prosody rate="100%">{result}</prosody>'

    return f"<speak>{result}</speak>"


def wrap_in_ssml(text: str) -> str:
    """
    Wrap plain text in SSML with natural prosody for human-like speech.

    PERFORMANCE: Uses LRU cache with time-bucketed seeds for efficiency.
    Same text within 10-second windows gets cached result.

    Features:
    - Natural pace for clarity
    - Brief pauses for rhythm
    - Emphasis on praise words
    - Pitch variations for emotions
    """
    # Use time-bucketed seed for cache hits (same text within 10s = same result)
    seed = int(time.time() // 10)
    return _wrap_in_ssml_cached(text, seed)


def generate_step_explanation(
    question: str,
    solution: str,
    correct_answer: str,
) -> Dict[str, Any]:
    """
    Generate a step-by-step explanation when student asks for help.
    Uses GPT to explain in simple, conversational terms.
    """
    response = generate_gpt_response(
        intent=TutorIntent.EXPLAIN_STEPS,
        question=question,
        solution=solution,
        correct_answer=correct_answer,
    )

    ssml = wrap_in_ssml(response)

    return {
        "intent": TutorIntent.EXPLAIN_STEPS.value,
        "response": response,
        "ssml": ssml,
        "is_help_response": True,
    }


# Convenience function for API integration
def generate_tutor_response(
    is_correct: bool,
    attempt_number: int,
    question: str = "",
    hint_1: str = "",
    hint_2: str = "",
    solution: str = "",
    correct_answer: str = "",
    student_answer: str = "",
) -> Dict[str, Any]:
    """
    Generate a tutor response using GPT for natural phrasing.

    The FSM decides the intent (WHAT to say).
    GPT decides the phrasing (HOW to say it).

    PERFORMANCE: Optimized to minimize GPT calls:
    - Uses cached responses for move_on transitions (no extra GPT call)
    - Main response may use cache for common intents
    """
    # Determine intent from FSM state
    tutor = TutorVoice()
    intent = tutor.determine_intent(
        is_correct=is_correct,
        attempt_number=attempt_number,
    )

    # Select appropriate hint based on attempt
    hint = ""
    if intent == TutorIntent.GUIDE_THINKING:
        hint = hint_1 or "Think about what operation you need."
    elif intent == TutorIntent.NUDGE_CORRECTION:
        hint = hint_2 or hint_1 or "Check your calculation carefully."

    # Generate natural response using GPT (with caching)
    response = generate_gpt_response(
        intent=intent,
        question=question,
        student_answer=student_answer,
        hint=hint,
        solution=solution or f"The answer is {correct_answer}",
        correct_answer=correct_answer,
        attempt_number=attempt_number,
    )

    # Determine if we should move to next question
    should_move = is_correct or attempt_number >= 3

    # DON'T append move_on phrase - keep response short for TTS
    # UI handles transition separately

    # Wrap in SSML for natural voice pauses
    ssml = wrap_in_ssml(response)

    return {
        "intent": intent.value,
        "response": response,
        "ssml": ssml,
        "move_to_next": should_move,
        "show_answer": intent == TutorIntent.EXPLAIN_ONCE,
        "attempt_number": attempt_number,
    }


# For testing
if __name__ == "__main__":
    print("=== TutorIntent Layer Test ===\n")

    tutor = TutorVoice()

    # Test scenarios
    scenarios = [
        {"is_correct": True, "attempt": 1, "desc": "Correct on first try"},
        {"is_correct": False, "attempt": 1, "desc": "Wrong - Attempt 1"},
        {"is_correct": False, "attempt": 2, "desc": "Wrong - Attempt 2"},
        {"is_correct": False, "attempt": 3, "desc": "Wrong - Attempt 3"},
    ]

    for s in scenarios:
        result = generate_tutor_response(
            is_correct=s["is_correct"],
            attempt_number=s["attempt"],
            question="What is 2/3 + 1/4?",
            hint_1="Find a common denominator first.",
            hint_2="The common denominator of 3 and 4 is 12.",
            solution="2/3 = 8/12 and 1/4 = 3/12. So 8/12 + 3/12 = 11/12.",
            correct_answer="11/12",
        )
        print(f"📚 {s['desc']}")
        print(f"   Intent: {result['intent']}")
        print(f"   Response: {result['response']}")
        print(f"   SSML: {result['ssml']}")
        print(f"   Move to next: {result['move_to_next']}")
        print()

    # Test SSML generation directly
    print("=== SSML Direct Test ===\n")
    ssml = generate_ssml_response(
        TutorIntent.ASK_FRESH,
        question="What is 5 times 6?"
    )
    print(f"SSML: {ssml}")
    print(f"Plain: {strip_ssml(ssml)}")
