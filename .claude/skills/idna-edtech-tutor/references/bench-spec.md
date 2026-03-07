# IDNA-Bench v1 — Benchmark Specification

7 evaluation layers, 3 tiers, 31 total benchmarks.

## Layer Overview

| Layer | Name | Threshold | Key Dimensions |
|-------|------|-----------|----------------|
| 1 | Foundation Reasoning | Per-benchmark | ARC-AGI-2, GSM8K, GPQA Diamond |
| 2 | Foundation STEM+Agentic | Per-benchmark | Minerva, HumanEval, TruthfulQA, SWE-bench |
| 3 | IDNA-Lang | 75/100 per language | STT accuracy, code-switching, TTS naturalness, script rendering |
| 4 | IDNA-Reason | Per class level | Multi-step arithmetic, science reasoning, novel problems |
| 5 | IDNA-Curriculum | 85/100 per board | Syllabus alignment, textbook fidelity, exam pattern match |
| 6 | IDNA-Truth | Math: 98%, Other: 90% | Board-specific claims, language-specific errors |
| 7 | IDNA-Interact | 80/100 composite | Tool orchestration, confusion detection, adaptive difficulty, session memory |

**Layer 5 is the unique moat.** No other benchmark evaluates board-specific syllabus alignment.

## Content Factory Pipeline

```
Textbook PDF → LLM extracts topics → Generate L1/L2/L3 content →
IDNA-Bench scores → Human expert review (flagged items only) → Production
```

IDNA-Bench gates between generation and human review (60-70% review burden reduction).

## Strategic Value

1. **Research publication:** No multilingual multi-board pedagogical AI benchmark exists for India. Target: NeurIPS/ACL/AIED.
2. **Government partnership:** IndiaAI, NCERT need rigorous evaluation frameworks.
3. **Investor narrative:** Benchmark dataset + evaluation infra = defensible moat.
4. **B2B platform:** Other EdTechs use IDNA-Bench to evaluate their AI tools.
5. **Competitive moat:** Dataset compounds with every board and language added.

## Reference Documents

- `IDNA_BENCH_v1_Specification.docx` — Full specification
- `IDNA_CTO_Architecture_Roadmap_v1.docx` — Architecture context
