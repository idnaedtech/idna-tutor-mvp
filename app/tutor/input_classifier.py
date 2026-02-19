"""
IDNA EdTech v7.0 — Input Classifier
Classifies student or parent voice input into actionable categories.
Pure functions — no API calls, no side effects.

Categories (Student):
    ACK        — "haan", "samajh gaya", "okay"
    IDK        — "nahi samjha", "pata nahi"
    ANSWER     — any numeric, mathematical, or substantive response
    CONCEPT    — "explain karo", "kya hai ye"
    COMFORT    — "bahut mushkil", "I give up", frustration signals
    STOP       — "bye", "band karo"
    TROLL      — off-topic, jokes
    REPEAT     — "phir se bolo", "I didn't hear"
    DISPUTE    — "maine sahi bola", "galat check kiya" (challenges Didi's verdict)
    HOMEWORK   — "homework hai", "photo bhejta hoon"
    SUBJECT    — "math padha", "science padhi" (topic discovery)

Categories (Parent):
    PROGRESS   — "kaisa chal raha hai", "aaj kya padha"
    INSTRUCTION — "fractions pe dhyan do", "zyada practice karao"
    CHITCHAT   — off-topic, greetings
    GOODBYE    — "bye", "theek hai", "chalo"
"""

import re
from typing import Literal

# ─── Type Definitions ────────────────────────────────────────────────────────

StudentCategory = Literal[
    "ACK", "IDK", "ANSWER", "CONCEPT", "COMFORT", "STOP",
    "TROLL", "REPEAT", "DISPUTE", "HOMEWORK", "SUBJECT", "SILENCE"
]
ParentCategory = Literal["PROGRESS", "INSTRUCTION", "CHITCHAT", "GOODBYE"]

# ─── Phrase Banks ────────────────────────────────────────────────────────────
# Lowercase. Checked via substring match.

_ACK_PHRASES = [
    "haan", "haa", "ha", "yes", "okay", "ok", "theek", "thik",
    "samajh gaya", "samajh gayi", "samajh aa gaya", "samjha",
    "pata hai", "maloom", "sahi", "correct",
    "हां", "हाँ", "ठीक", "समझ गया", "समझ गयी", "समझा",
    "accha", "acha", "अच्छा",
    "hmm", "got it", "understood",
    "next", "agle", "aage", "आगे",
]

_IDK_PHRASES = [
    # English
    "i don't know", "don't know", "dont know", "no idea", "not sure", "idk",
    # Romanized Hindi
    "nahi samjha", "nahi samajh", "samajh nahi", "nahi pata",
    "pata nahi", "nahi maloom", "maloom nahi", "confused",
    "kuch samajh nahi", "samajh nahi aaya", "mujhe nahi pata",
    # Devanagari Hindi - CRITICAL for real student input
    "पता नहीं", "नहीं पता", "मुझे नहीं पता",
    "समझ में नहीं आया", "कुछ समझ में नहीं आया", "समझ नहीं आया",
    "नहीं समझा", "मालूम नहीं", "अभी भी नहीं पता",
    # Word order variations - Hindi allows flexible word order
    "नहीं समझ में आया", "नहीं समझ आया", "समझ में आया नहीं",
    "नहीं समझे", "समझाओ फिर से", "फिर से समझाओ",
    "फिर से समझाइए", "फिर से समझाएंगे", "दोबारा समझाओ",
    # Re-explain requests (overlap with IDK intent)
    "ek baar phir", "phir se", "dobara", "explain again",
    "phir se batao", "फिर से बताओ", "फिर से",
]

_COMFORT_PHRASES = [
    # English
    "i give up", "give up", "too hard", "too difficult", "can't do this",
    "hopeless", "crying", "sad", "frustrated",
    # Romanized Hindi
    "haar gaya", "haar gayi", "bahut mushkil", "bohot mushkil",
    "nahi kar sakta", "nahi kar sakti", "mujhse nahi hoga",
    "bore", "boring", "thak gaya", "thak gayi", "tired",
    "gussa", "angry", "kuch nahi hoga", "chhod do",
    "ro raha", "ro rahi", "nahi ho raha",
    # Devanagari Hindi - CRITICAL
    "बहुत मुश्किल", "हार गया", "हार गयी", "थक गया",
    "मुझसे नहीं होगा", "छोड़ दो", "नहीं हो रहा",
    "कुछ समझ में नहीं आया",  # Can also be IDK, but comfort takes priority
]

_STOP_PHRASES = [
    "bye", "goodbye", "stop", "band karo", "band kar do",
    "bas", "khatam", "finish", "done", "chalo",
    "let's stop", "i want to stop", "enough",
    "बंद करो", "बस", "खतम", "चलो",
    "good night", "good bye",
]

_REPEAT_PHRASES = [
    "phir se bolo", "repeat", "say again", "kya bola",
    "sunai nahi", "didn't hear", "what did you say",
    "dobara bolo", "ek baar phir bolo",
    "फिर से बोलो", "दोबारा", "सुनाई नहीं",
]

_DISPUTE_PHRASES = [
    "maine sahi bola", "sahi tha", "mera answer sahi",
    "galat check", "wrong check", "i said correct",
    "मैंने सही बोला", "सही था", "गलत चेक",
    "listen again", "suno phir se",
]

_HOMEWORK_PHRASES = [
    "homework", "home work", "गृहकार्य", "grahkarya",
    "photo", "camera", "picture", "image",
    "homework hai", "homework mila", "homework dikhaata",
]

_SUBJECT_PHRASES = {
    "math": [
        "math", "maths", "mathematics", "गणित", "ganit", "hisaab",
        # Whisper garbled versions
        "मैथ", "मैथ्स", "मेथ", "मेथ्स", "मादस", "मेट्स", "मेठ",
        "mathe", "mats", "meth", "meths",
    ],
    "science": ["science", "विज्ञान", "vigyan", "साइंस"],
    "hindi": ["hindi", "हिंदी", "हिन्दी"],
}

# Parent-specific
_PROGRESS_PHRASES = [
    "kaisa chal", "kaise chal", "how is", "progress", "kya padha",
    "aaj kya", "score", "marks", "result", "report",
    "कैसा चल", "कैसे चल", "क्या पढ़ा", "आज क्या",
    "kitna padha", "homework kiya", "practice kiya",
]

_INSTRUCTION_PHRASES = [
    "dhyan do", "dhyan de", "focus", "zyada practice",
    "concentrate", "weak", "kamzor", "improve",
    "ध्यान दो", "ध्यान दे", "ज़्यादा",
    "karwao", "karao", "sikhao", "teach more",
]

_GOODBYE_PHRASES = [
    "bye", "goodbye", "theek hai", "chalo", "bas",
    "okay thanks", "thank you", "dhanyavaad", "shukriya",
    "बाय", "धन्यवाद", "शुक्रिया", "ठीक है",
]


# ─── Classification Functions ────────────────────────────────────────────────

def _has_match(text: str, phrases: list[str]) -> bool:
    """Check if any phrase is a substring of the text."""
    text_lower = text.lower().strip()
    for phrase in phrases:
        if phrase in text_lower:
            return True
    return False


def _looks_like_math_answer(text: str) -> bool:
    """Detect if text contains a mathematical answer."""
    text = text.strip()
    # Contains digits
    if re.search(r'\d', text):
        return True
    # Contains Hindi number words
    hindi_numbers = [
        "ek", "do", "teen", "char", "paanch", "panch", "chhe", "saat",
        "aath", "nau", "das", "gyarah", "barah",
        "एक", "दो", "तीन", "चार", "पांच", "छह", "सात", "आठ", "नौ", "दस",
    ]
    text_lower = text.lower()
    for num in hindi_numbers:
        if num in text_lower:
            return True
    # Contains fraction words
    fraction_words = [
        "half", "third", "quarter", "fifth",
        "aadha", "tihaayi", "chauthai",
        "by", "baata", "upon", "over",
    ]
    for word in fraction_words:
        if word in text_lower:
            return True
    return False


def classify_student_input(
    text: str,
    current_state: str = "",
    subject: str = "math",
) -> StudentCategory:
    """
    Classify student input. Order matters — more specific checks first.
    
    Args:
        text: Transcribed student speech
        current_state: Current FSM state (affects classification)
        subject: Current subject (affects whether text is treated as answer)
    
    Returns:
        StudentCategory string
    """
    if not text or not text.strip():
        return "REPEAT"  # Empty input = ask to repeat

    text_lower = text.lower().strip()

    # 0. SILENCE — frontend silence timer (don't send through LLM)
    if text_lower == "[silence]":
        return "SILENCE"

    # 1. STOP — highest priority (student wants to leave)
    if _has_match(text, _STOP_PHRASES):
        return "STOP"

    # 2. COMFORT — student is upset (must catch before generic classification)
    if _has_match(text, _COMFORT_PHRASES):
        return "COMFORT"

    # 3. DISPUTE — student challenges Didi's verdict
    if _has_match(text, _DISPUTE_PHRASES):
        return "DISPUTE"

    # 4. REPEAT — student didn't hear
    if _has_match(text, _REPEAT_PHRASES):
        return "REPEAT"

    # 5. HOMEWORK — student mentions homework/photo
    if _has_match(text, _HOMEWORK_PHRASES):
        return "HOMEWORK"

    # 6. SUBJECT — student names a subject (not used in MVP, math only)
    # Kept for future multi-subject support via UI selection
    # if current_state in ("GREETING", "DISCOVERING_TOPIC"):
    #     for subj, phrases in _SUBJECT_PHRASES.items():
    #         if _has_match(text, phrases):
    #             return "SUBJECT"

    # 7. IDK — student doesn't understand
    if _has_match(text, _IDK_PHRASES):
        return "IDK"

    # 8. CONCEPT — student asks for explanation (check before ACK to avoid "ha" in "hai" matching)
    concept_phrases = [
        # English
        "explain", "what is", "how", "why", "what is this",
        "explain please", "explain karo",
        # Romanized Hindi
        "batao", "bataiye", "kya hai", "samjhao", "samjhaiye",
        "aap samjhaiye", "kaise", "kyun", "kaun sa", "kis",
        "yeh kya hai", "chapter", "topic", "lesson",
        # Devanagari Hindi - CRITICAL
        "बताओ", "बताइये", "बताइए", "क्या है", "यह क्या है",
        "समझाओ", "समझाइए", "समझाइये", "आप समझाइए",
        "कैसे", "क्यों", "किस", "कौन सा", "कौन सा चैप्टर",
    ]
    if _has_match(text, concept_phrases):
        return "CONCEPT"

    # 9. ACK — student acknowledges understanding
    if _has_match(text, _ACK_PHRASES):
        # In WAITING_ANSWER state, "haan"/"yes" could be actual answers
        # to yes/no questions (e.g., "Kya 49 ek perfect square hai?")
        if current_state == "WAITING_ANSWER":
            return "ANSWER"  # Let answer_checker evaluate it
        return "ACK"

    # 10. ANSWER — if we're waiting for an answer and text looks numeric/mathematical
    if current_state == "WAITING_ANSWER":
        if _looks_like_math_answer(text):
            return "ANSWER"
        # During answer phase, anything that's not clearly another category
        # is treated as an answer attempt (student might express answer in words)
        if len(text_lower.split()) <= 10:  # Short response = likely answer
            return "ANSWER"

    # 11. TROLL — very short off-topic (during non-answer states)
    if len(text_lower.split()) <= 3 and current_state != "WAITING_ANSWER":
        return "TROLL"

    # 12. Default: treat as CONCEPT request if we can't classify
    return "CONCEPT"


def classify_parent_input(text: str) -> ParentCategory:
    """
    Classify parent input. Simpler than student classification.
    """
    if not text or not text.strip():
        return "CHITCHAT"

    # 1. GOODBYE
    if _has_match(text, _GOODBYE_PHRASES):
        return "GOODBYE"

    # 2. INSTRUCTION — parent telling Didi what to focus on
    if _has_match(text, _INSTRUCTION_PHRASES):
        return "INSTRUCTION"

    # 3. PROGRESS — parent asking about child's progress
    if _has_match(text, _PROGRESS_PHRASES):
        return "PROGRESS"

    # 4. Default: CHITCHAT
    # But longer messages that mention academic topics → PROGRESS
    academic_words = [
        "padhai", "study", "exam", "test", "chapter",
        "question", "answer", "school", "class",
        "पढ़ाई", "परीक्षा", "स्कूल",
    ]
    if _has_match(text, academic_words):
        return "PROGRESS"

    return "CHITCHAT"
