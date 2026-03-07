# IDNA Phase Roadmap & Board Expansion

## Phase Execution Timeline

### Phase 0: Validate (Week 1) — GATE
Must verify before ANY architecture work:
1. Student sets language once → ALL subsequent turns respect it
2. Student says IDK 4 times → caps at 3, advances on 4th
3. Content Bank material appears in TEACHING
4. Full 5-question session without crash or loop
5. LLM evaluator correctly grades answers
6. Hint progression: wrong → hint 1 → wrong → hint 2 → wrong → full solution

### Phase 1: Foundation Refactor (Weeks 2-4)
- Add boards, textbooks, content_units, student_profiles via Alembic
- Extend SessionState with board/class/textbook fields
- Parameterize FSM content injection (DB queries replace flat files)
- API v1 versioning (/api/v1/session/start with board_id)
- Fix P1 backlog (6 bugs)
- Exit gate: new board = zero code changes, only DB inserts

### Phase 2: Multi-Board MVP (Months 2-3)
- BSETS, MSBSHSE, ICSE content banks
- IDNA-Bench Layer 1
- gosseract handwriting evaluation

### Phase 3: Platform (Months 4-6)
- Full IDNA-Bench suite
- Memory-R1 RL-based student memory
- Parent dashboard + WhatsApp voice reports
- Multi-language routing

### Phase 4: Infrastructure Layer (Months 6-12)
- On-device SLM on 7-8" tablets
- BharathCloud GPU
- Government partnerships (IndiaAI, NEP 2020, NCERT)
- Research publication (NeurIPS/ACL/AIED)

## Board Expansion Strategy

| Tier | Boards | Phase |
|------|--------|-------|
| Tier 1 | CBSE (done), ICSE | MVP + P2 |
| Tier 2 | BSETS Telangana, MSBSHSE Maharashtra, UPMSP, TN SSLC, BSEB Bihar | P2 |
| Tier 3 | KSEEB, KBPE, GSEB, RBSE, MPBSE, WBBSE | P2-3 |
| Tier 4 | All remaining state boards | P3-4 |
| International | IB (MYP+DP), Cambridge IGCSE | P3-4 |

### 22 Scheduled Languages
Hindi, Bengali, Telugu, Marathi, Tamil, Urdu, Gujarati, Malayalam, Kannada, Odia,
Punjabi, Assamese, Maithili, Sanskrit, Santali, Konkani, Nepali, Sindhi, Dogri,
Manipuri (Meitei), Kashmiri, Bodo.

## Strategic Positioning

The 22-language, 33-board ambition is the moat. IDNA-Bench is the instrument that
ensures quality at every point across that moat. Vision: transform from EdTech
product to India's education AI infrastructure layer.
