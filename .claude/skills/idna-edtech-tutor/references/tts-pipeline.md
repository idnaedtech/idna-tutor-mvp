# TTS Pipeline — Architecture Reference (v6.2.4)

## Current Pipeline

```
Student speaks
  → Groq Whisper STT (~300ms, language="hi")
  → Confidence check (threshold 0.4)
  → [if low confidence: "Ek baar phir boliye?" → re-listen]
  → Input Classifier
  → State Machine → Instruction Builder
  → GPT-4o (~800-1200ms)
  → clean_for_tts()
  → Sarvam TTS (single API call, full text)
  → Audio plays in browser
```

## Latency Breakdown

| Step | Before v6.2.4 | After v6.2.4 |
|------|--------------|-------------|
| STT | ~500ms (OpenAI) | ~300ms (Groq) |
| LLM | ~1200ms | ~1200ms (unchanged) |
| TTS | ~800ms (full text) | ~800ms (single call) |
| **Total to first audio** | **~2500ms** | **~2300ms** |

Note: Sentence-level chunking was removed in v6.2.4 because concatenating
multiple MP3 files produces invalid audio that browsers can't play. The single
Sarvam call handles long text (up to 2500 chars) and returns one valid MP3.

## Sarvam Bulbul v3 Config

```python
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_SPEAKER = "simran"       # v6.2 change — DO NOT CHANGE without approval
SARVAM_LANGUAGE = "hi-IN"       # DO NOT CHANGE
SARVAM_MODEL = "bulbul:v3"
SARVAM_PACE = 0.90              # Tunable: 0.85-1.0
SARVAM_TEMPERATURE = 0.7        # Tunable: 0.5-0.9
```

No OpenAI TTS fallback. No Google Cloud TTS. One voice, always.

## clean_for_tts() Rules

| Input | Output |
|-------|--------|
| `-3/7` | `minus 3 by 7` |
| `2/3` | `2 by 3` |
| ` + ` | ` plus ` |
| ` - ` | ` minus ` |
| ` × ` | ` multiplied by ` |
| ` = ` | ` equals ` |
| `**bold**` | `bold` (strip markdown) |

## Text Length Limit

Sarvam v3 REST API handles up to 2500 chars. The `sarvam_tts()` function
truncates at 2000 chars (at sentence boundary) as a safety margin.
If text exceeds limit, it retries with first 500 chars.

## Groq Whisper Config

```python
GROQ_WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_WHISPER_MODEL = "whisper-large-v3-turbo"
language = "hi"  # ALWAYS forced for Hindi-medium students
response_format = "verbose_json"  # Needed for confidence scores
```

## Hallucination Detection

Reject transcriptions matching:
- `Thank you for watching`, `Subscribe`, `Like and subscribe`
- `[Music]`, `[Applause]`, `(silence)`
- Only punctuation/symbols
- Text shorter than 2 characters
- Confidence < 0.4
