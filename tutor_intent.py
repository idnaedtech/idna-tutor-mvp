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
from typing import Optional, Dict, Any
import random
import os
from openai import OpenAI

# Initialize OpenAI client for natural response generation
_openai_client = None

def get_openai_client():
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=30.0,  # Increased for longer explanations
            max_retries=2
        )
    return _openai_client


# System prompt for the tutor persona
TUTOR_PERSONA = """You're a friend helping with math homework. Chat naturally, don't teach formally.

BE SPONTANEOUS:
- Never start two responses the same way
- React in the moment, don't follow a script
- Sometimes just "yep!" or "mmhmm" or "oh I see"
- Interrupt yourself: "so you— wait actually let's try..."
- Think out loud: "hmm okay so if we..."

SOUND REAL:
- Use "like", "kinda", "sorta", "basically", "right?"
- Pause words: "umm", "uh", "hmm", "soo..."
- Reactions: "ooh!", "ah!", "wait—", "oh okay"
- Casual Hindi: "accha", "haan", "theek", "sahi"

KEEP SUPER SHORT - this is spoken:
- 1 sentence usually, 2 max
- Fragments are fine: "Nice one!" "Hmm close though."
- Don't over-explain

WHEN EXPLAINING STEPS:
- Walk through like you're figuring it out together
- "okay so first we... then... and that gives us..."
- Make it feel collaborative, not lecturing

NEVER SOUND LIKE:
- A textbook: "The correct answer is..."
- A robot: "Well done. That is correct."
- A formal teacher: "Let us proceed to..."
- Reading a script: same openings every time
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
# Uses pauses (<break>) and Hinglish phrases for warmth
PHRASES_SSML = {
    TutorIntent.ASK_FRESH: [
        "<speak>Achha beta,<break time='300ms'/> {question}<break time='400ms'/> Take your time.</speak>",
        "<speak>Okay,<break time='250ms'/> here's your question.<break time='400ms'/> {question}</speak>",
        "<speak>Let's try this one.<break time='300ms'/> {question}</speak>",
        "<speak>Ready beta?<break time='300ms'/> {question}</speak>",
    ],
    TutorIntent.CONFIRM_CORRECT: [
        "<speak>Bahut accha!<break time='300ms'/> That's exactly right, beta!</speak>",
        "<speak>Perfect!<break time='250ms'/> Well done!<break time='300ms'/> You got it!</speak>",
        "<speak>Excellent!<break time='300ms'/> I knew you could do it!</speak>",
        "<speak>Shabash!<break time='300ms'/> That's correct!</speak>",
    ],
    TutorIntent.GUIDE_THINKING: [
        "<speak>Hmm,<break time='400ms'/> not quite beta.<break time='300ms'/> {hint}<break time='400ms'/> Try again?</speak>",
        "<speak>Close!<break time='300ms'/> Think about this:<break time='400ms'/> {hint}</speak>",
        "<speak>Almost there.<break time='300ms'/> {hint}<break time='400ms'/> What do you think?</speak>",
    ],
    TutorIntent.NUDGE_CORRECTION: [
        "<speak>Let me help more.<break time='400ms'/> {hint}<break time='400ms'/> Try once more, beta.</speak>",
        "<speak>Okay beta,<break time='300ms'/> step by step.<break time='400ms'/> {hint}</speak>",
        "<speak>Don't worry.<break time='300ms'/> {hint}<break time='400ms'/> One more try!</speak>",
    ],
    TutorIntent.EXPLAIN_ONCE: [
        "<speak>Koi baat nahi beta,<break time='400ms'/> let me explain.<break time='500ms'/> {solution}<break time='400ms'/> Samajh aaya?</speak>",
        "<speak>No problem.<break time='400ms'/> Watch this:<break time='500ms'/> {solution}<break time='400ms'/> Got it?</speak>",
        "<speak>That's okay beta.<break time='400ms'/> Here's how:<break time='500ms'/> {solution}</speak>",
    ],
    TutorIntent.MOVE_ON: [
        "<speak>Chalo,<break time='300ms'/> let's try the next one.</speak>",
        "<speak>Okay,<break time='250ms'/> moving on.<break time='300ms'/> Next question!</speak>",
        "<speak>Aage badhte hain.<break time='300ms'/> Next one!</speak>",
    ],
    TutorIntent.ENCOURAGE_RETRY: [
        "<speak>Take your time beta.<break time='300ms'/> No rush.</speak>",
        "<speak>Sochke batao.<break time='300ms'/> You've got this.</speak>",
    ],
    TutorIntent.SESSION_START: [
        "<speak>Namaste beta!<break time='400ms'/> Ready to learn today?<break time='300ms'/> Let's go!</speak>",
        "<speak>Hello!<break time='300ms'/> Great to see you.<break time='400ms'/> Let's practice together.</speak>",
        "<speak>Aao beta!<break time='300ms'/> Time for some math practice.</speak>",
    ],
    TutorIntent.SESSION_END: [
        "<speak>Bahut accha kiya aaj!<break time='400ms'/> Well done beta.<break time='300ms'/> See you next time!</speak>",
        "<speak>Great work today!<break time='400ms'/> Keep practicing.<break time='300ms'/> Bye beta!</speak>",
        "<speak>Shabash!<break time='300ms'/> You did well today.<break time='400ms'/> Phir milenge!</speak>",
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
) -> str:
    """
    Use GPT-4o-mini to generate a warm, natural tutor response.

    This is the key to making the tutor sound human, not robotic.
    The FSM decides WHAT to say (intent), GPT decides HOW to say it.
    """

    # Build the context for GPT - include student's answer for contextual responses
    student_said = f"Student said: '{student_answer}'" if student_answer else ""

    intent_instructions = {
        TutorIntent.ASK_FRESH: f"Toss out this question super casually: '{question}'. Like 'Okay so...' or 'Alright here's one...' Just say it naturally, don't introduce it formally.",

        TutorIntent.CONFIRM_CORRECT: f"""Student answered: '{student_answer}'
Correct answer: {correct_answer}
They got it right! React to THEIR answer specifically. Like 'Yep, {student_answer} is right!' or 'Oh nice, exactly!' Keep it short.""",

        TutorIntent.GUIDE_THINKING: f"""Question: {question}
Correct answer: {correct_answer}
Student said: '{student_answer}' (this is wrong, attempt {attempt_number}/3)
Hint to give: {hint}

Respond to what THEY said specifically. If they said a number, acknowledge it: 'Hmm {student_answer}... not quite, but...'
Guide them with the hint. Don't just give generic response.""",

        TutorIntent.NUDGE_CORRECTION: f"""Question: {question}
Correct answer: {correct_answer}
Student said: '{student_answer}' (wrong, attempt {attempt_number}/3)
Hint: {hint}

Acknowledge their attempt, then give direct help. Like 'Okay so {student_answer} isn't it, but here's the thing...' """,

        TutorIntent.EXPLAIN_ONCE: f"""Question: {question}
Student's last attempt: '{student_answer}'
Correct answer: {correct_answer}
Solution: {solution}

They tried 3 times. Gently explain: 'Okay so {student_answer} was close but actually...' then walk through the solution simply.""",

        TutorIntent.EXPLAIN_STEPS: f"""Student asked for help. Walk them through step by step.

Question: {question}
Solution: {solution}
Answer: {correct_answer}

Explain it like talking to a friend - break it into simple steps, end with the answer.""",

        TutorIntent.MOVE_ON: "Super quick transition. Just 'Okay next!' or 'Alright...' 3-4 words max.",

        TutorIntent.SESSION_START: "Quick casual hi. 'Hey!' or 'Yo ready for some math?' 4-5 words.",

        TutorIntent.SESSION_END: "Quick bye. 'Nice one, later!' or 'Good stuff!' 3-4 words.",
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
        return result
    except Exception as e:
        print(f"GPT response error: {e}")
        # Fallback to template if GPT fails
        tutor = TutorVoice()
        return tutor.get_response(intent, question=question, hint=hint, solution=solution)


def wrap_in_ssml(text: str) -> str:
    """
    Wrap plain text in SSML with natural prosody for human-like speech.

    Uses pitch variations, emphasis, and varied pauses to sound less robotic.
    """
    import re
    import random

    # Vary pause lengths for naturalness (not uniform)
    short_pause = random.choice(["150ms", "200ms", "180ms"])
    med_pause = random.choice(["300ms", "350ms", "280ms"])
    long_pause = random.choice(["450ms", "500ms", "400ms"])

    # Add varied pauses after sentences
    def varied_sentence_pause(match):
        pause = random.choice(["350ms", "400ms", "450ms", "300ms"])
        return f'{match.group(1)}<break time="{pause}"/> '

    text = re.sub(r'([.!?])\s+', varied_sentence_pause, text)

    # Natural pause for "..." (thinking)
    text = re.sub(r'\.\.\.', f'<break time="{med_pause}"/>', text)

    # Shorter varied pauses after commas
    def varied_comma_pause(match):
        pause = random.choice(["120ms", "150ms", "180ms", "100ms"])
        return f',<break time="{pause}"/> '

    text = re.sub(r',\s+', varied_comma_pause, text)

    # Add emphasis to excited words
    excitement_words = ["nice", "great", "awesome", "perfect", "exactly", "yes", "yeah", "accha", "bahut", "shabash"]
    for word in excitement_words:
        # Case insensitive replacement with emphasis
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        text = pattern.sub(f'<emphasis level="moderate">{word}</emphasis>', text)

    # Add slight pitch rise for questions
    if "?" in text:
        # Wrap the question part with rising pitch
        text = re.sub(
            r'([^.!?]+\?)',
            r'<prosody pitch="+5%">\1</prosody>',
            text
        )

    # Add natural speech rate variation - slightly faster for excitement, slower for explanation
    if any(w in text.lower() for w in ["nice", "great", "yes", "yeah", "correct"]):
        # Excited = slightly faster
        text = f'<prosody rate="105%">{text}</prosody>'
    elif any(w in text.lower() for w in ["so", "okay so", "let me", "here's how", "basically"]):
        # Explaining = slightly slower
        text = f'<prosody rate="95%">{text}</prosody>'

    return f"<speak>{text}</speak>"


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

    This makes every response unique, warm, and human-like.
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

    # Generate natural response using GPT
    response = generate_gpt_response(
        intent=intent,
        question=question,
        student_answer=student_answer,
        hint=hint,
        solution=solution or f"The answer is {correct_answer}",
        correct_answer=correct_answer,
        attempt_number=attempt_number,
    )

    # Wrap in SSML for natural voice pauses
    ssml = wrap_in_ssml(response)

    # Determine if we should move to next question
    should_move = is_correct or attempt_number >= 3

    # If moving on, add transition
    if should_move:
        move_response = generate_gpt_response(TutorIntent.MOVE_ON)
        response = f"{response} {move_response}"
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
