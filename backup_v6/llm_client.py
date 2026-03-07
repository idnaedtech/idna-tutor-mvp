"""
IDNA EdTech - Model-Agnostic LLM Client
=========================================
Supports OpenAI, Anthropic, and Google providers via environment variables.

Config (env vars):
    LLM_PROVIDER=openai       # or "anthropic" or "google"
    LLM_MODEL=gpt-4o-mini     # swap to any model
    LLM_TEMPERATURE=0.5
    LLM_MAX_TOKENS=60
    LLM_TIMEOUT=15.0

Does NOT touch Whisper STT — that stays as direct OpenAI.
"""

import os
import json
import time
import logging
from typing import Optional
from datetime import datetime, timezone

# Structured logger
_llm_logger = logging.getLogger("idna.llm")
if not _llm_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    _llm_logger.addHandler(handler)
    _llm_logger.setLevel(logging.INFO)


def _log(message: str, **ctx):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "level": "INFO",
        "message": message,
        **{k: v for k, v in ctx.items() if v is not None},
    }
    _llm_logger.info(json.dumps(entry))


# ---------------------------------------------------------------------------
# Configuration (read once, cached at module level)
# ---------------------------------------------------------------------------

LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai").lower()
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.5"))
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "60"))
LLM_TIMEOUT: float = float(os.getenv("LLM_TIMEOUT", "15.0"))

# Feature flag for LLM-as-planner (Stage 3, defaults to off)
LLM_AS_PLANNER: bool = os.getenv("LLM_AS_PLANNER", "false").lower() == "true"


# ---------------------------------------------------------------------------
# Lazy-initialized clients (one per provider)
# ---------------------------------------------------------------------------

_openai_client = None
_anthropic_client = None
_google_model = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=LLM_TIMEOUT,
            max_retries=1,
        )
    return _openai_client


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        try:
            import anthropic
            _anthropic_client = anthropic.Anthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                timeout=LLM_TIMEOUT,
                max_retries=1,
            )
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")
    return _anthropic_client


def _get_google_model():
    global _google_model
    if _google_model is None:
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            _google_model = genai.GenerativeModel(LLM_MODEL)
        except ImportError:
            raise RuntimeError("google-generativeai package not installed. Run: pip install google-generativeai")
    return _google_model


# ---------------------------------------------------------------------------
# Core generation functions
# ---------------------------------------------------------------------------

def generate(
    system_prompt: str,
    user_prompt: str,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    model: Optional[str] = None,
) -> str:
    """
    Generate text from the configured LLM provider.

    Returns plain text string. Falls back to empty string on error.
    """
    _max_tokens = max_tokens or LLM_MAX_TOKENS
    _temperature = temperature if temperature is not None else LLM_TEMPERATURE
    _model = model or LLM_MODEL

    # Cost guard check (imported here to avoid circular imports)
    try:
        from cost_guard import check_and_increment
        allowed, reason = check_and_increment()
        if not allowed:
            _log("LLM call blocked by cost guard", event="llm_blocked", reason=reason)
            return ""
    except ImportError:
        pass  # cost_guard not yet available

    start = time.perf_counter()

    try:
        if LLM_PROVIDER == "openai":
            result = _generate_openai(system_prompt, user_prompt, _model, _max_tokens, _temperature)
        elif LLM_PROVIDER == "anthropic":
            result = _generate_anthropic(system_prompt, user_prompt, _model, _max_tokens, _temperature)
        elif LLM_PROVIDER == "google":
            result = _generate_google(system_prompt, user_prompt, _model, _max_tokens, _temperature)
        else:
            _log(f"Unknown LLM provider: {LLM_PROVIDER}", event="llm_error")
            return ""

        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        _log(
            "LLM response generated",
            event="llm_complete",
            provider=LLM_PROVIDER,
            model=_model,
            latency_ms=latency_ms,
            response_length=len(result),
        )
        return result

    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        _log(
            f"LLM error: {e}",
            event="llm_error",
            provider=LLM_PROVIDER,
            model=_model,
            latency_ms=latency_ms,
            error_type=type(e).__name__,
        )
        return ""


def generate_json(
    system_prompt: str,
    user_prompt: str,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    model: Optional[str] = None,
) -> Optional[dict]:
    """
    Generate structured JSON output from the LLM.

    Returns parsed dict, or None on error / invalid JSON.
    """
    # Add JSON instruction to system prompt
    json_system = system_prompt + "\n\nYou MUST respond with valid JSON only. No markdown, no explanation."

    raw = generate(json_system, user_prompt, max_tokens, temperature, model)
    if not raw:
        return None

    # Strip markdown code fences if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last line if they're code fences
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        _log("Failed to parse LLM JSON output", event="llm_json_error", raw_output=text[:200])
        return None


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

def _generate_openai(
    system_prompt: str, user_prompt: str,
    model: str, max_tokens: int, temperature: float,
) -> str:
    client = _get_openai_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    result = response.choices[0].message.content.strip()
    return result.strip('"').strip("'")


def _generate_anthropic(
    system_prompt: str, user_prompt: str,
    model: str, max_tokens: int, temperature: float,
) -> str:
    client = _get_anthropic_client()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text.strip()


def _generate_google(
    system_prompt: str, user_prompt: str,
    model: str, max_tokens: int, temperature: float,
) -> str:
    gen_model = _get_google_model()
    # Google uses a combined prompt
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    response = gen_model.generate_content(
        full_prompt,
        generation_config={
            "max_output_tokens": max_tokens,
            "temperature": temperature,
        },
    )
    return response.text.strip()
