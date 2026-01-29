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
from functools import lru_cache
from openai import OpenAI

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

# Pre-generated responses for common intents (no GPT needed)
# These are refreshed periodically or on startup
_cached_responses: Dict[str, List[str]] = {
    "session_start": [
        "Namaste beta! Ready for math? Chalo!",
        "Aao champ! Let's practice together!",
        "Hello beta! Kaise ho? Math time!",
        "Namaste! Excited to learn today? Let's go!",
    ],
    "session_end": [
        "Bahut accha kiya aaj! Bye beta!",
        "Great job champ! Phir milenge!",
        "Shabash! Keep practicing. See you!",
        "Well done beta! Proud of you!",
    ],
    "move_on": [
        "Chalo next!",
        "Aage badhein!",
        "Okay, next one!",
        "Ready? Here we go!",
        "Let's try another!",
    ],
    "confirm_correct": [
        "Arre wah! Ekdum sahi!",
        "Kya baat hai! Perfect beta!",
        "Shabash! That's exactly right!",
        "Brilliant! You got it!",
        "Wah wah! First class!",
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
TUTOR_PERSONA = """You're a warm, encouraging didi/bhaiya helping a younger student with math. You LOVE seeing them learn. Mix Hindi naturally.

EMOTIONAL WARMTH (most important!):
- Show genuine excitement: "Arre wah!", "Kya baat hai!", "Maza aa gaya!"
- Be encouraging when wrong: "Koi nahi beta, hota hai", "Tension mat lo"
- Celebrate small wins: "Dekha! Tumne kar liya!", "Shabash mere bacche!"
- Use affectionate terms: "beta", "bacche", "champ"

HINGLISH MIX (use naturally):
- Reactions: "Accha accha", "Haan bilkul", "Sahi pakde", "Wah wah!"
- Encouragement: "Koshish karo", "Thoda aur socho", "Bas ho gaya almost"
- Transitions: "Chalo", "Dekho", "Suno", "Accha toh"
- Praise: "Bahut badhiya!", "Ekdum sahi!", "First class!"
- Comfort: "Koi baat nahi", "Dhire dhire", "No tension"

BE SPONTANEOUS:
- Never start two responses the same way
- React to THEIR specific answer: "Hmm 5... not quite but close!"
- Think out loud: "Accha toh... agar hum yeh karein..."
- Natural pauses: "Soo... let me think... haan!"

KEEP SHORT (this is spoken aloud):
- 1-2 sentences max
- Fragments are perfect: "Sahi!" "Hmm close!" "Ek minute..."
- Don't over-explain, let them think

WHEN THEY'RE WRONG:
- NEVER make them feel bad
- "Accha, close hai but..." not "Wrong!"
- Always give hope: "Ek aur try, you'll get it"

WHEN EXPLAINING:
- Walk through together: "Dekho, pehle yeh... phir yeh..."
- Make it collaborative: "Toh humne kya kiya? Haan, yahi!"
- Celebrate understanding: "Ab samjhe? See, easy tha!"

NEVER SOUND LIKE:
- A textbook or robot
- Cold or formal
- Disappointed in them
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
        "style": "warm, celebratory",
        "max_sentences": 2,
        "templates": [
            "Yes! That's correct. Well done!",
            "Perfect! You got it right.",
            "Excellent work! That's the answer.",
            "Great job! You nailed it.",
            "Correct! I knew you could do it.",
            "Brilliant! That's exactly right.",
            "Wonderful! You're doing great.",
            "That's it! Nice thinking.",
        ]
    },
    
    TutorIntent.GUIDE_THINKING: {
        "style": "calm, Socratic",
        "max_sentences": 2,
        "templates": [
            "Hmm, not quite. {hint} Think about it again.",
            "Close, but not exactly. {hint}",
            "Let me give you a hint. {hint}",
            "Not quite right. {hint} Give it another try.",
            "Almost there. {hint}",
            "Think about this: {hint}",
        ]
    },
    
    TutorIntent.NUDGE_CORRECTION: {
        "style": "supportive, direct",
        "max_sentences": 2,
        "templates": [
            "Let me help more. {hint} Try once more.",
            "Here's a bigger hint. {hint}",
            "Don't worry, you're close. {hint} One more try!",
            "You can do this. {hint}",
            "Last hint: {hint} Give it your best shot.",
        ]
    },
    
    TutorIntent.EXPLAIN_ONCE: {
        "style": "patient, clear",
        "max_sentences": 3,
        "templates": [
            "No problem, let me show you. {solution}",
            "That's okay. Here's how it works: {solution}",
            "Let me explain. {solution}",
            "Don't worry. The answer is: {solution}",
            "Here's the solution: {solution}",
        ]
    },
    
    TutorIntent.MOVE_ON: {
        "style": "encouraging, forward-looking",
        "max_sentences": 1,
        "templates": [
            "Let's try the next one.",
            "Ready for the next question?",
            "Moving on to a new one.",
            "Let's keep going.",
            "Here comes the next one.",
        ]
    },
    
    TutorIntent.ENCOURAGE_RETRY: {
        "style": "warm, supportive",
        "max_sentences": 1,
        "templates": [
            "Take your time.",
            "No rush. Think it through.",
            "You've got this.",
            "Relax and try again.",
        ]
    },
    
    TutorIntent.SESSION_START: {
        "style": "warm, welcoming",
        "max_sentences": 2,
        "templates": [
            "Hello! Ready to practice math? Let's begin.",
            "Welcome back! Let's do some math together.",
            "Hi there! Time for some practice. Let's start.",
            "Great to see you! Let's learn together today.",
        ]
    },
    
    TutorIntent.SESSION_END: {
        "style": "proud, encouraging",
        "max_sentences": 2,
        "templates": [
            "Great practice today! See you next time.",
            "Well done! You worked hard today.",
            "Nice work! Keep practicing and you'll get even better.",
            "Fantastic effort! See you soon.",
        ]
    },
}


# SSML templates for warmer, more natural voice synthesis
# Uses pauses (<break>), prosody for emotions, and Hinglish for warmth
PHRASES_SSML = {
    TutorIntent.ASK_FRESH: [
        "<speak><prosody rate='95%'>Accha beta,<break time='400ms'/></prosody> {question}<break time='500ms'/> <prosody pitch='+5%'>Take your time.</prosody></speak>",
        "<speak><prosody rate='93%'>Chalo dekho,<break time='350ms'/></prosody> {question}</speak>",
        "<speak>Okay so,<break time='300ms'/> {question}<break time='400ms'/> <prosody pitch='+3%'>Socho...</prosody></speak>",
        "<speak><prosody rate='95%'>Ready beta?<break time='400ms'/></prosody> Yeh try karo.<break time='300ms'/> {question}</speak>",
        "<speak>Accha,<break time='300ms'/> next question.<break time='400ms'/> {question}</speak>",
    ],
    TutorIntent.CONFIRM_CORRECT: [
        "<speak><prosody rate='105%' pitch='+10%'>Arre wah!</prosody><break time='350ms'/> <emphasis level='strong'>Ekdum sahi!</emphasis><break time='300ms'/> Bahut badhiya beta!</speak>",
        "<speak><prosody pitch='+8%'>Kya baat hai!</prosody><break time='300ms'/> <emphasis level='strong'>Perfect!</emphasis><break time='350ms'/> Dekha, tumne kar liya!</speak>",
        "<speak><emphasis level='strong'>Shabash!</emphasis><break time='350ms'/> <prosody pitch='+5%'>That's exactly right!</prosody><break time='300ms'/> Proud of you beta!</speak>",
        "<speak><prosody rate='105%' pitch='+10%'>Wah wah!</prosody><break time='300ms'/> First class answer!<break time='350ms'/> <prosody pitch='+5%'>Maza aa gaya!</prosody></speak>",
        "<speak><prosody pitch='+8%'>Yes!</prosody><break time='300ms'/> <emphasis level='strong'>Bilkul sahi!</emphasis><break time='350ms'/> You're doing amazing beta!</speak>",
    ],
    TutorIntent.GUIDE_THINKING: [
        "<speak><prosody rate='92%'>Hmm,<break time='450ms'/> {hint}</prosody><break time='500ms'/> <prosody pitch='+3%'>Ek aur try?</prosody></speak>",
        "<speak><prosody rate='90%'>Accha, close hai but<break time='400ms'/></prosody> thoda aur socho.<break time='450ms'/> {hint}</speak>",
        "<speak>Almost beta!<break time='400ms'/> <prosody rate='92%'>Dekho,<break time='300ms'/> {hint}</prosody><break time='400ms'/> <prosody pitch='+3%'>Kya lagta hai?</prosody></speak>",
        "<speak><prosody rate='92%'>Koi nahi,<break time='350ms'/> try again.</prosody><break time='400ms'/> Hint:<break time='300ms'/> {hint}</speak>",
    ],
    TutorIntent.NUDGE_CORRECTION: [
        "<speak><prosody rate='90%'>Accha sunno beta,<break time='450ms'/> step by step karein.</prosody><break time='500ms'/> {hint}<break time='450ms'/> <prosody pitch='+3%'>Ek aur chance!</prosody></speak>",
        "<speak>Tension mat lo!<break time='400ms'/> <prosody rate='90%'>Dekho,<break time='350ms'/> {hint}</prosody><break time='450ms'/> You can do it!</speak>",
        "<speak><prosody rate='92%'>Koi baat nahi,<break time='400ms'/> let me help more.</prosody><break time='450ms'/> {hint}<break time='400ms'/> <prosody pitch='+3%'>Try karo!</prosody></speak>",
    ],
    TutorIntent.EXPLAIN_ONCE: [
        "<speak><prosody rate='88%' pitch='-2%'>Koi baat nahi beta,<break time='500ms'/> yeh tricky tha.</prosody><break time='550ms'/> <prosody rate='90%'>Dekho kaise karte hain:<break time='450ms'/> {solution}</prosody><break time='500ms'/> <prosody pitch='+5%'>Samajh aaya? Next time pakka!</prosody></speak>",
        "<speak><prosody rate='90%'>That's okay!<break time='450ms'/> Hota hai.</prosody><break time='500ms'/> <prosody rate='88%'>Watch this:<break time='400ms'/> {solution}</prosody><break time='450ms'/> <prosody pitch='+3%'>Ab clear hai?</prosody></speak>",
        "<speak>No problem beta!<break time='450ms'/> <prosody rate='88%'>Chalo, together dekhte hain.<break time='450ms'/> {solution}</prosody><break time='500ms'/> <prosody pitch='+5%'>Dekha, easy tha!</prosody></speak>",
    ],
    TutorIntent.MOVE_ON: [
        "<speak><prosody rate='105%' pitch='+5%'>Chalo!</prosody><break time='350ms'/> Next one!</speak>",
        "<speak>Okay,<break time='300ms'/> <prosody pitch='+3%'>aage badhein!</prosody></speak>",
        "<speak><prosody rate='105%'>Ready?</prosody><break time='300ms'/> Next question!</speak>",
        "<speak><prosody pitch='+5%'>Chalein!</prosody><break time='300ms'/> Another one!</speak>",
    ],
    TutorIntent.ENCOURAGE_RETRY: [
        "<speak><prosody rate='90%'>Dhire dhire beta,<break time='400ms'/> no rush.</prosody><break time='350ms'/> <prosody pitch='+3%'>Sochke batao.</prosody></speak>",
        "<speak><prosody rate='92%'>Take your time.<break time='400ms'/></prosody> <prosody pitch='+3%'>You've got this!</prosody></speak>",
        "<speak>Relax beta,<break time='350ms'/> <prosody rate='92%'>aaram se socho.</prosody></speak>",
    ],
    TutorIntent.SESSION_START: [
        "<speak><prosody rate='105%' pitch='+8%'>Namaste beta!</prosody><break time='450ms'/> Ready to learn today?<break time='400ms'/> <prosody pitch='+5%'>Let's go!</prosody></speak>",
        "<speak><prosody pitch='+5%'>Hello champ!</prosody><break time='400ms'/> Kaise ho?<break time='350ms'/> <prosody rate='105%'>Chalo practice karein!</prosody></speak>",
        "<speak><prosody rate='105%' pitch='+8%'>Aao beta!</prosody><break time='400ms'/> Math time!<break time='350ms'/> <prosody pitch='+5%'>Maza aayega!</prosody></speak>",
    ],
    TutorIntent.SESSION_END: [
        "<speak><prosody pitch='+8%'>Bahut accha kiya aaj!</prosody><break time='450ms'/> <prosody rate='95%'>Proud of you beta.</prosody><break time='400ms'/> <prosody pitch='+5%'>Phir milenge!</prosody></speak>",
        "<speak><prosody rate='105%' pitch='+8%'>Great job champ!</prosody><break time='400ms'/> Keep practicing.<break time='350ms'/> <prosody pitch='+5%'>Bye beta!</prosody></speak>",
        "<speak><emphasis level='strong'>Shabash!</emphasis><break time='400ms'/> <prosody rate='95%'>You worked hard today.</prosody><break time='400ms'/> <prosody pitch='+8%'>See you soon!</prosody></speak>",
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

    # OPTIMIZATION: Use pre-cached responses for common intents (no GPT call)
    if use_cache:
        intent_cache_map = {
            TutorIntent.SESSION_START: "session_start",
            TutorIntent.SESSION_END: "session_end",
            TutorIntent.MOVE_ON: "move_on",
        }
        if intent in intent_cache_map:
            cached = get_cached_response(intent_cache_map[intent])
            if cached:
                return cached

        # For CONFIRM_CORRECT, use cached ~50% of time for variety
        if intent == TutorIntent.CONFIRM_CORRECT and random.random() < 0.5:
            cached = get_cached_response("confirm_correct")
            if cached:
                return cached

    # OPTIMIZATION: Check time-based cache for recent similar queries
    cache_key = get_gpt_cache_key(intent.value, question, student_answer)
    if use_cache:
        cached_response = get_cached_gpt_response(cache_key)
        if cached_response:
            return cached_response

    # Build the context for GPT - include student's answer for contextual responses
    intent_instructions = {
        TutorIntent.ASK_FRESH: f"""Present this question warmly: '{question}'
Use Hinglish like 'Accha beta, yeh try karo...' or 'Chalo dekho...' or 'Okay so...'
Keep it short and inviting, not formal.""",

        TutorIntent.CONFIRM_CORRECT: f"""Student answered: '{student_answer}'
Correct answer: {correct_answer}
CELEBRATE! They got it right! Be genuinely excited with Hinglish:
'Arre wah! {student_answer} - ekdum sahi!' or 'Kya baat hai beta! Perfect!' or 'Shabash! Dekha, tumne kar liya!'
React to THEIR specific answer. Show you're proud of them.""",

        TutorIntent.GUIDE_THINKING: f"""Question: {question}
Correct answer: {correct_answer}
Student said: '{student_answer}' (wrong, attempt {attempt_number}/3)
Hint to give: {hint}

Be warm and encouraging, NOT disappointed. Use Hinglish:
'Accha {student_answer}... close hai but thoda aur socho...' or 'Hmm, almost beta! Dekho, {hint}'
Make them feel they CAN do it.""",

        TutorIntent.NUDGE_CORRECTION: f"""Question: {question}
Correct answer: {correct_answer}
Student said: '{student_answer}' (wrong, attempt {attempt_number}/3)
Hint: {hint}

More direct help but still warm. Use Hinglish:
'Koi nahi beta, let me help. Dekho, {hint}' or 'Accha sunno, step by step karein...'
Give them confidence for one more try.""",

        TutorIntent.EXPLAIN_ONCE: f"""Question: {question}
Student's last attempt: '{student_answer}'
Correct answer: {correct_answer}
Solution: {solution}

They tried 3 times - be EXTRA kind and supportive:
'Koi baat nahi beta! Yeh tricky tha. Dekho kaise karte hain...' then explain simply.
End with encouragement: 'Samajh aaya? Next time pakka hoga!'""",

        TutorIntent.EXPLAIN_STEPS: f"""Student asked for help - they want to learn! Be a supportive didi/bhaiya.

Question: {question}
Solution: {solution}
Answer: {correct_answer}

Walk through warmly: 'Accha dekho beta, step by step... pehle yeh... phir yeh... aur answer hai {correct_answer}!'
Make them feel smart for asking.""",

        TutorIntent.MOVE_ON: "Quick warm transition. 'Chalo next!' or 'Aage badhein!' or 'Okay ready?' 3-5 words with energy.",

        TutorIntent.SESSION_START: "Warm excited greeting! 'Namaste beta! Ready for math?' or 'Aao champ, let's go!' 5-7 words.",

        TutorIntent.SESSION_END: "Proud farewell! 'Bahut accha kiya aaj! Bye beta!' or 'Great job champ! Phir milenge!' 5-7 words.",
    }

    user_prompt = intent_instructions.get(intent, "Respond helpfully.")

    try:
        client = get_openai_client()

        # More tokens for explanations, fewer for quick reactions
        max_tokens = 150 if intent == TutorIntent.EXPLAIN_STEPS else 60

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": TUTOR_PERSONA},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.95,  # High creativity for varied responses
        )
        result = response.choices[0].message.content.strip()
        # Remove quotes if GPT wrapped the response
        result = result.strip('"').strip("'")

        # Cache the response for future use
        set_cached_gpt_response(cache_key, result)

        return result
    except Exception as e:
        print(f"GPT response error: {e}")
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

    # Vary pause lengths for naturalness (longer pauses for better rhythm)
    short_pause = rng.choice(["180ms", "220ms", "200ms"])
    med_pause = rng.choice(["350ms", "400ms", "320ms"])
    long_pause = rng.choice(["500ms", "550ms", "450ms"])

    result = text

    # Add varied pauses after sentences (longer for clarity)
    def varied_sentence_pause(match):
        pause = rng.choice(["400ms", "450ms", "500ms", "380ms"])
        return f'{match.group(1)}<break time="{pause}"/> '

    result = re.sub(r'([.!?])\s+', varied_sentence_pause, result)

    # Natural pause for "..." (thinking) - longer for effect
    result = re.sub(r'\.\.\.', f'<break time="{long_pause}"/>', result)

    # Pauses after colons (before explanations)
    result = re.sub(r':\s+', f':<break time="{med_pause}"/> ', result)

    # Varied pauses after commas (slightly longer)
    def varied_comma_pause(match):
        pause = rng.choice(["150ms", "180ms", "200ms", "160ms"])
        return f',<break time="{pause}"/> '

    result = re.sub(r',\s+', varied_comma_pause, result)

    # Excited/praise words - strong emphasis with pitch lift
    praise_words = [
        "wah", "bahut", "shabash", "perfect", "exactly", "correct", "sahi",
        "badhiya", "amazing", "brilliant", "excellent", "great", "nice",
        "accha", "maza", "first class", "proud"
    ]
    for word in praise_words:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        result = pattern.sub(
            lambda m: f'<emphasis level="strong"><prosody pitch="+8%">{m.group(0)}</prosody></emphasis>',
            result
        )

    # Encouraging words - moderate emphasis, warm pitch
    encourage_words = [
        "try", "koshish", "socho", "dekho", "close", "almost", "nearly",
        "good", "okay", "can do", "you've got", "no problem", "koi baat"
    ]
    for word in encourage_words:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        result = pattern.sub(
            lambda m: f'<emphasis level="moderate"><prosody pitch="+3%">{m.group(0)}</prosody></emphasis>',
            result
        )

    # Affectionate terms - warm, slightly slower
    affection_words = ["beta", "bacche", "champ"]
    for word in affection_words:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        result = pattern.sub(
            lambda m: f'<prosody rate="90%" pitch="-2%">{m.group(0)}</prosody>',
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

    # Celebration/excitement - faster, higher pitch
    if any(w in text_lower for w in ["wah", "shabash", "yes!", "perfect", "correct", "sahi", "bahut accha"]):
        result = f'<prosody rate="102%" pitch="+5%">{result}</prosody>'
    # Comfort/encouragement when wrong - slower, warmer
    elif any(w in text_lower for w in ["koi baat", "tension mat", "no problem", "that's okay", "hota hai"]):
        result = f'<prosody rate="88%" pitch="-3%">{result}</prosody>'
    # Explanation mode - slower, clear
    elif any(w in text_lower for w in ["dekho", "so", "pehle", "step", "let me", "here's how"]):
        result = f'<prosody rate="88%">{result}</prosody>'
    # Default - slightly slow for clarity
    else:
        result = f'<prosody rate="92%">{result}</prosody>'

    return f"<speak>{result}</speak>"


def wrap_in_ssml(text: str) -> str:
    """
    Wrap plain text in SSML with natural prosody for human-like speech.

    PERFORMANCE: Uses LRU cache with time-bucketed seeds for efficiency.
    Same text within 10-second windows gets cached result.

    Features:
    - Slower base rate (92%) for clarity
    - Varied pauses for natural rhythm
    - Emphasis on excited/praise words
    - Pitch variations for emotions
    - Support for Hindi/Hinglish expressions
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

    # OPTIMIZATION: Use cached move_on response instead of GPT call
    if should_move:
        move_response = get_cached_response("move_on")
        response = f"{response} {move_response}"

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
