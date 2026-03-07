# IDNA Tech Stack — Phase 2-4 (Future)

These technologies are NOT part of the current MVP (v8.0.1). Do not implement
or integrate any of these without explicit phase-gate approval.

## Phase 2-3 Additions

| Technology | Purpose | Phase |
|-----------|---------|-------|
| PersonaPlex 7B | On-device SLM candidate (eval first) | P2 eval, P4 deploy |
| Ollama/LocalAI | Local model serving | P3 |
| Asynq | Task queue for async jobs | P2 |
| Milvus | Vector DB for semantic search | P3 |
| RuleGo | Multi-subject FSM orchestration | P3 |
| Gorse | Adaptive question recommendation | P3 |
| gosseract | Handwriting OCR evaluation | P2 |
| Smol2Operator | GUI agent for worksheets/dashboards (HuggingFace) | P3 |
| checkpoint-engine | Rapid model weight updates (MoonshotAI) | P3-4 |
| Memory-R1 | RL-based long-term student memory (arXiv:2508.19828) | P3 |
| Claude Code Security | Trail of Bits config, PR review | P2 |
| PydanticAI | output_validator + ModelRetry + RunContext for FSM hardening | P2 |

## Phase 4

| Technology | Purpose |
|-----------|---------|
| On-device SLM | 7-8" tablets with camera |
| On-device TTS/STT | Offline-first architecture |
| Kani-TTS-2 | Future tablet TTS candidate |
| gRPC | Device-cloud sync |
| BharathCloud Hyderabad P3 GPU | Fine-tuning/serving |

## Integration Notes

- Memory-R1: Not a commercial product. Academic paper (Aug 2025). Build internal
  memory module using RL (PPO/GRPO) into the Whisper → LLM → TTS pipeline.
- Smol2Operator: HuggingFace open-source pipeline for training small VLMs into
  GUI-operating agents. Relevant for tutor interacting with worksheets/dashboards.
- checkpoint-engine: MoonshotAI middleware for rapid model weight updates.
  Not essential for MVP, useful for scaling.
