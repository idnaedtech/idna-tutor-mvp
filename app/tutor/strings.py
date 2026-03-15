"""
IDNA v10 — Centralized Language Strings
Every hardcoded user-facing string lives here.
Adding a new language = adding entries to STRINGS dict. Zero code changes.
"""

from typing import Optional

STRINGS = {
    # ── Session Start ──────────────────────────────────────────────
    "warmup_greeting": {
        "english": "Hello {name}! Welcome! How are you doing today? How was your day?",
        "hindi": "नमस्ते {name}! कैसी हो आज? आज का दिन कैसा रहा?",
        "hinglish": "Hey {name}! कैसी हो आज? आज का दिन कैसा रहा?",
        "telugu": "హలో {name}! ఎలా ఉన్నావు? ఈ రోజు ఎలా జరిగింది?",
    },
    "warmup_transition": {
        "english": "Nice! So today we're going to look at something interesting in {topic}. Ready when you are!",
        "hindi": "Achha! Toh aaj hum {topic} mein kuch interesting dekhenge. Jab ready ho, batao!",
        "hinglish": "Nice! Toh aaj hum {topic} mein kuch interesting dekhenge. Ready when you are!",
        "telugu": "Bagundi! Ippudu manaṁ {topic} lo interesting ga chuddaam. Ready ayyaka cheppu!",
    },
    "no_content_available": {
        "english": "Let me find the right explanation for that. Can we try a question instead?",
        "hindi": "Iska sahi explanation dhundhti hoon. Kya hum ek question try karein?",
        "hinglish": "Iska sahi explanation dhundhti hoon. Ek question try karein?",
        "telugu": "Daniki sari explanation chuddaam. Oka question try cheddaamaa?",
    },
    "session_end": {
        "english": "Great work today, {name}! You got {correct} out of {total} right. See you next time!",
        "hindi": "{name}, aaj bahut achha kiya! {correct} mein se {total} sahi the. Kal milte hain!",
        "hinglish": "Great work today, {name}! {correct} out of {total} sahi the. See you next time!",
        "telugu": "Chaala baagaa chesaav {name}! {correct} out of {total} correct. Next time kaluddaam!",
    },
    "language_switched": {
        "english": "Sure, English from now on!",
        "hindi": "Theek hai, ab Hindi mein!",
        "hinglish": "Theek hai, Hinglish it is!",
        "telugu": "Sure, Telugu lo cheptaa ippati nundi!",
    },
    "chapter_info": {
        "english": "We're learning {chapter_name}.",
        "hindi": "Hum {chapter_name} padh rahe hain.",
        "hinglish": "Hum {chapter_name} padh rahe hain.",
        "telugu": "Manaṁ {chapter_name} chaduvutunnaam.",
    },
    "listening": {
        "english": "I'm listening! Go ahead, tell me.",
        "hindi": "Haan, sun rahi hoon! Batao.",
        "hinglish": "Haan, I'm listening! Batao.",
        "telugu": "Vintunna! Cheppu.",
    },
    "idle_prompt": {
        "english": "Are you still there? Take your time, no rush!",
        "hindi": "Aap wahan ho? Apna time lo, koi jaldi nahi!",
        "hinglish": "Aap wahan ho? Take your time, koi jaldi nahi!",
        "telugu": "Akkada unnav kadaa? Time teesko, rush emi ledhu!",
    },
    "offer_break": {
        "english": "Want to try an easier question, or take a break and come back fresh?",
        "hindi": "Ek easy question try karein, ya break lekar fresh start karein?",
        "hinglish": "Ek easy question try karein, ya break lekar wapas aayein?",
        "telugu": "Oka easy question try cheddaamaa, ledaa break teesukundaam?",
    },
    "correction_acknowledged": {
        "english": "Oh, you're right — thank you for catching that! Let me correct myself.",
        "hindi": "Are haan, aap sahi keh rahe ho — thank you! Main correct karti hoon.",
        "hinglish": "Oh right, thank you for catching that! Let me correct myself.",
        "telugu": "Oh avunu, nuvvu cheppindi correct — thanks! Nenu correct chestaa.",
    },
}


def get_text(key: str, language: str, **kwargs) -> str:
    """Get a localized string. Falls back to English if language not found.

    Usage:
        get_text("warmup_greeting", "telugu", name="Priya")
        get_text("chapter_info", "english", chapter_name="Squares and Square Roots")
    """
    templates = STRINGS.get(key, {})
    template = templates.get(language, templates.get("english", ""))
    if not template:
        return ""
    try:
        return template.format(**kwargs) if kwargs else template
    except KeyError:
        return template
