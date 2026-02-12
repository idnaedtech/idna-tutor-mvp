"""
IDNA Input Classifier — Pure Python, No LLM
=============================================
Classifies every student input into exactly one category.
Order matters: first match wins.

Categories (priority order):
1. STOP        → student wants to end session
2. LANGUAGE    → student wants to switch language
3. LANG_UNSUPPORTED → student wants a language we don't support
4. TROLL       → nonsense, spam, not engaging
5. ACK         → acknowledgment (yeah, okay, got it)
6. IDK         → doesn't know, wants help
7. OFFTOPIC    → unrelated to math
8. ANSWER      → an actual attempt at answering
"""

import re


def classify(text: str) -> dict:
    """
    Classify student input. Returns:
    {
        "category": str,     # one of the categories above
        "detail": str,       # extra info (e.g. which language)
        "cleaned": str       # cleaned input text
    }
    """
    raw = text.strip()
    t = raw.lower().strip().rstrip('.!,?')

    # 1. STOP — check first, always wins
    if _is_stop(t):
        return {"category": "STOP", "detail": "", "cleaned": raw}

    # 2. LANGUAGE SWITCH — English
    if _wants_english(t):
        return {"category": "LANGUAGE", "detail": "english", "cleaned": raw}

    # 3. UNSUPPORTED LANGUAGE
    lang = _wants_other_language(t)
    if lang:
        return {"category": "LANG_UNSUPPORTED", "detail": lang, "cleaned": raw}

    # 4. TROLL — before ack, because "lol" could be short like an ack
    if _is_troll(t):
        return {"category": "TROLL", "detail": "", "cleaned": raw}

    # 5. ACK — only matters when short (≤6 words)
    if _is_ack(t):
        return {"category": "ACK", "detail": "", "cleaned": raw}

    # 6. IDK — student doesn't know or wants explanation
    if _is_idk(t):
        return {"category": "IDK", "detail": "", "cleaned": raw}

    # 7. OFF-TOPIC
    if _is_offtopic(t):
        return {"category": "OFFTOPIC", "detail": "", "cleaned": raw}

    # 8. ANSWER — everything else is treated as an answer attempt
    return {"category": "ANSWER", "detail": "", "cleaned": raw}


# ============================================================
# INDIVIDUAL DETECTORS
# ============================================================

def _is_stop(t: str) -> bool:
    phrases = [
        "stop", "bye", "quit", "end", "done", "that's it", "the end",
        "i want to stop", "can we stop", "let's stop", "enough",
        "bas", "band karo", "ruko", "stop for today",
        "can we stop for today", "that's all for today",
        "let's stop for today", "stop here", "will stop here",
        "stop here for today", "we will stop", "let us stop",
        "that's enough", "i'm done", "let's end",
        "i want to end", "close", "khatam", "khatam karo"
    ]
    return any(p in t for p in phrases)


def _wants_english(t: str) -> bool:
    phrases = [
        "speak in english", "english please", "in english only",
        "can you speak english", "talk in english", "use english",
        "can you speak in english", "explain in english",
        "english only", "only english", "only in english"
    ]
    return any(p in t for p in phrases)


def _wants_other_language(t: str) -> str:
    """Returns language name or empty string."""
    languages = {
        "telugu": "Telugu", "tamil": "Tamil", "kannada": "Kannada",
        "malayalam": "Malayalam", "bengali": "Bengali", "bangla": "Bengali",
        "marathi": "Marathi", "gujarati": "Gujarati", "punjabi": "Punjabi",
        "odia": "Odia", "assamese": "Assamese", "urdu": "Urdu",
        "spanish": "Spanish", "french": "French", "german": "German",
        "chinese": "Chinese", "japanese": "Japanese", "korean": "Korean",
        "arabic": "Arabic"
    }
    triggers = ["speak", "talk", "language", "can you", "in ", "use "]
    if any(tr in t for tr in triggers):
        for key, name in languages.items():
            if key in t:
                return name
    return ""


def _is_troll(t: str) -> bool:
    phrases = [
        "subscribe", "like and subscribe", "thanks for watching",
        "thank you for watching", "hit the bell", "smash the like",
        "comment below", "share this video", "background chatter",
        "hello youtube", "hey guys", "what's up guys",
        "blah blah", "asdf", "test test", "testing",
        "aaa", "bbb", "zzz", "xyz", "abc",
        "lol", "lmao", "hahaha", "hehe", "rofl"
    ]
    if any(p in t for p in phrases):
        return True
    # Very short random text (1-2 chars, not a number)
    if len(t) <= 2 and not any(c.isdigit() for c in t):
        return True
    return False


def _is_ack(t: str) -> bool:
    """Short acknowledgment — student understood."""
    acks = [
        "yeah", "yes", "okay", "ok", "got it", "i got it", "makes sense",
        "i understand", "understood", "right", "alright", "fine", "sure",
        "haan", "theek hai", "theek", "samajh gaya", "samajh gayi",
        "accha", "oh okay", "oh ok", "yep", "yup", "hmm okay",
        "okay okay", "i see", "ah okay", "ah ok", "clear",
        "that's clear", "kind of", "sort of", "hmm", "mm",
        "yeah yeah", "yes yes", "ok ok", "ji", "ji haan",
        "samajh aa gaya", "samajh aa gayi", "haan samjha",
        "that makes sense", "oh i see", "ohh", "acha",
        "yeah i got it", "yes i understand", "hmm okay got it"
    ]
    if len(t.split()) <= 6:
        return any(t == ack or t.startswith(ack) for ack in acks)
    return False


def _is_idk(t: str) -> bool:
    phrases = [
        "i don't know", "i dont know", "idk", "no idea",
        "tell me the answer", "just tell me", "skip",
        "i can't", "i cant", "nahi pata", "pata nahi",
        "what is the answer", "give me the answer",
        "please explain", "explain to me", "please start",
        "mujhe nahi aata", "samajh nahi aa raha",
        "can you explain", "explain the chapter", "teach me",
        "what is fraction", "what are fractions", "what is a fraction",
        "can you teach me", "i'm confused", "i am confused",
        "help me", "no clue", "not sure", "i need help",
        "explain this", "explain it", "what does this mean",
        "i don't understand", "i dont understand",
        "how can i use", "how do we use", "daily life",
        "real life example", "where do we use this",
        "how is this useful", "give me example",
        # v4.3: Hindi IDK phrases
        "nahi aata", "nahi aate", "nahi aati",  # don't know how to
        "samajh nahi aata", "samajh nahi aati", "samajh nahi aaye",
        "nahi samjha", "nahi samjhi", "nahi samajh",
        "kaise karte hain", "kaise karu", "kaise karun",  # how do I do this
        "batao na", "bata do", "batao please",  # tell me
        "sikhao", "sikha do",  # teach me
        "kya hai ye", "ye kya hai",  # what is this
        "explain karo", "explain kar do",  # explain it
        # v4.3: Simpler English triggers
        "explain fraction", "explain fractions",
        "explain the fraction", "explain the fractions",
        "explain this topic", "explain the topic",
        "what is this", "how to do this", "how do i do this"
    ]
    return any(p in t for p in phrases)


def _is_offtopic(t: str) -> bool:
    # If it has numbers or fraction-like patterns, it's probably an answer
    if any(c.isdigit() for c in t):
        return False
    if "/" in t or "by" in t:
        return False

    phrases = [
        "who are you", "what is your name", "tell me a joke",
        "play a game", "sing a song", "what can you do",
        "how are you", "what's up",
        "help me with homework", "finish my homework",
        "finishing my homework", "do my homework",
        "help me in finishing", "try next chapter",
        "you try", "change chapter", "different chapter",
        "next chapter", "another chapter",
        "what else can you do", "are you a robot",
        "are you real", "are you human", "are you ai"
    ]
    return any(p in t for p in phrases)


def is_nonsensical(text: str) -> bool:
    """Detect if input is ambient noise / TV / unrelated to tutoring."""
    text_lower = text.strip().lower()

    # Very short input is likely noise
    if len(text_lower) <= 2:
        return True

    # Foreign language fragments, TV audio, etc.
    non_relevant = [
        "que é", "isso", "en la", "medida", "momento",
        "merci", "bonjour", "danke", "bitte", "gracias",
        "republic of congo", "cobalt", "your phone your laptop",
        "your ev", "back camera", "subtitles by", "subscribe",
        "like and subscribe", "thank you for watching",
        "thanks for watching", "all rights reserved",
        "copyright", "music playing", "applause",
        "rueldo", "basically what you expect",
    ]
    for phrase in non_relevant:
        if phrase in text_lower:
            return True

    return False
