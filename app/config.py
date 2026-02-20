"""
IDNA EdTech v7.3 — Configuration
All environment variables and constants. Single source of truth.
No other file reads os.environ directly.
"""

import os
from pathlib import Path

# Load .env file if present
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_CACHE_DIR = Path(os.getenv("AUDIO_CACHE_DIR", "/tmp/idna_audio_cache"))
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ─── API Keys ────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")

# ─── Provider Selection (swap by changing these) ─────────────────────────────
STT_PROVIDER = os.getenv("STT_PROVIDER", "sarvam_saarika")
# Options: sarvam_saarika (default, handles Hindi-English code-mixing) | groq_whisper | sarvam_saaras
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "sarvam_bulbul")
# Options: sarvam_bulbul (only option for now)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai_gpt4o")
# Options: openai_gpt4o | sarvam_m | self_hosted

# ─── Database ────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'idna.db'}"
)
# Railway sets DATABASE_URL to postgresql://... automatically.
# If DATABASE_URL starts with "postgres://", fix for SQLAlchemy:
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ─── JWT / Auth ──────────────────────────────────────────────────────────────
JWT_SECRET = os.getenv("JWT_SECRET", "idna-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15

# ─── TTS Settings ────────────────────────────────────────────────────────────
TTS_SPEAKER = os.getenv("TTS_SPEAKER", "simran")
TTS_PACE = float(os.getenv("TTS_PACE", "0.90"))
TTS_TEMPERATURE = float(os.getenv("TTS_TEMPERATURE", "0.6"))
TTS_MODEL = os.getenv("TTS_MODEL", "bulbul:v3")
TTS_SAMPLE_RATE = int(os.getenv("TTS_SAMPLE_RATE", "24000"))
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_TTS_STREAM_URL = "wss://api.sarvam.ai/text-to-speech/stream"

# ─── STT Settings ────────────────────────────────────────────────────────────
GROQ_WHISPER_MODEL = "whisper-large-v3-turbo"
GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
STT_CONFIDENCE_THRESHOLD = float(os.getenv("STT_CONFIDENCE_THRESHOLD", "0.4"))
# Force Hindi for student sessions (prevents English garbage from Hindi speech)
STT_DEFAULT_LANGUAGE = "hi"

# ─── LLM Settings ────────────────────────────────────────────────────────────
# Didi tutor LLM - gpt-4.1-mini for better instruction following
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "200"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

# ─── Session Settings ────────────────────────────────────────────────────────
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
MAX_QUESTIONS_PER_SESSION = int(os.getenv("MAX_QUESTIONS_PER_SESSION", "10"))
MAX_RETEACH_ATTEMPTS = 3
SILENCE_TIMEOUT_SECONDS = 15
MAX_HINT_LEVELS = 3  # hint_1 → hint_2 → full_solution

# ─── Response Enforcer Limits ────────────────────────────────────────────────
MAX_RESPONSE_WORDS = 40  # Reduced from 55 for faster TTS
MAX_RESPONSE_SENTENCES = 2
MAX_ENFORCE_RETRIES = 3  # Re-prompt LLM this many times before falling back

# ─── Answer Checker ──────────────────────────────────────────────────────────
DECIMAL_TOLERANCE = 0.01  # For comparing decimal equivalents of fractions

# ─── Supported Languages ─────────────────────────────────────────────────────
# BCP-47 codes for Sarvam Bulbul v3 (11 languages)
SUPPORTED_LANGUAGES = {
    "hi-IN": "Hindi",
    "bn-IN": "Bengali",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "gu-IN": "Gujarati",
    "kn-IN": "Kannada",
    "ml-IN": "Malayalam",
    "mr-IN": "Marathi",
    "pa-IN": "Punjabi",
    "od-IN": "Odia",
    "en-IN": "English (Indian)",
}

# Default languages
DEFAULT_STUDENT_LANGUAGE = "hi-IN"  # Hinglish for students
DEFAULT_PARENT_LANGUAGE = "hi-IN"   # Overridden per parent profile

# ─── CORS ────────────────────────────────────────────────────────────────────
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# ─── Logging ─────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "json"  # json | text

# ─── Feature Flags ───────────────────────────────────────────────────────────
ENABLE_HOMEWORK_OCR = os.getenv("ENABLE_HOMEWORK_OCR", "true").lower() == "true"
ENABLE_PARENT_VOICE = os.getenv("ENABLE_PARENT_VOICE", "true").lower() == "true"
ENABLE_SCIENCE = os.getenv("ENABLE_SCIENCE", "false").lower() == "true"
ENABLE_HINDI = os.getenv("ENABLE_HINDI", "false").lower() == "true"

# MVP: Math only. Science and Hindi behind feature flags.
# Flip to "true" when content is ready and tested.
