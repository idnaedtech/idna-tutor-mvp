# TTS Pipeline — v10.6.x Reference

## Current Pipeline

```
Student speaks into browser mic
  → Frontend sends audio to /api/student/session/message-stream
  → Sarvam Saarika v2.5 STT (~300ms)
  → Confidence check (threshold 0.4)
  → Preprocessing (meta-question, language switch, confusion, Telugu detection)
  → Input Classifier (GPT-4.1-mini, fast-path 0ms or LLM 500-1800ms)
  → v7.3 FSM transition → Action object
  → Instruction builder → build_prompt()
  → GPT-4.1 streaming (500-4200ms)
  → Enforcer checks (length, praise, language)
  → clean_for_tts() → math symbols to words
  → Sarvam Bulbul v3 TTS (3000-7000ms)
  → SSE stream to frontend → audio plays
```

## Latency Breakdown (Production, March 2026)

| Step | Latency | Notes |
|------|---------|-------|
| STT | ~300ms | Sarvam Saarika v2.5 |
| Classifier | 0-1800ms | Fast-path 0-3ms, LLM 500-1800ms |
| Answer eval | 0-2000ms | Only on ANSWER category (inline eval) |
| LLM response | 500-4200ms | GPT-4.1 streaming |
| TTS | 3000-7000ms | **THE BOTTLENECK** (65-88% of total) |
| **Total** | **5000-14000ms** | |

## Sarvam Config

```python
STT: Sarvam Saarika v2.5 (not Groq Whisper — changed in v10.x)
TTS: Sarvam Bulbul v3
  Speaker: simran          # NEVER CHANGE
  Language: hi-IN          # Default (te-IN for Telugu)
  Pace: 0.90
  Temperature: 0.7
```

## TTS Char Limits (State-Dependent)

| State | Max TTS Chars | Rationale |
|-------|--------------|-----------|
| TEACHING | 350 | Needs room to explain |
| HINT / WAITING_ANSWER / FULL_SOLUTION | 200 | Hints stay brief |
| GREETING / other | 150 | Keep greetings short |

## clean_for_tts() Rules

- Dashes → commas: `" - "` → `", "`
- Fractions: `-3/7` → `minus 3 by 7`
- Operators: `+` → plus, `-` → minus, `×` → multiplied by, `=` → equals
- Strip markdown formatting
- Strip "You asked" / "Aapne poocha" / "आपने पूछा" framing (v10.6.7)
- Em dash and long dash also replaced (v10.6.5)

## TTS Latency — Known Blocker

Sarvam REST API takes 3-7s per call. WebSocket streaming (`wss://api.sarvam.ai/text-to-speech/stream`) returns HTTP 403 — not enabled on current API plan. Email sent to Sarvam requesting access.

Text appears on screen immediately (~1-2s) before audio plays. Perceived latency is lower than actual.
