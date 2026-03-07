# IDNA Phase Gates

Strict sequential gates. No skipping.

## P0 — Live Student Test (GATE)

**Status:** NOT PASSED
**Criteria:**
- [ ] Real student completes a full session (GREETING → TEACHING → PRACTICE → SESSION_END)
- [ ] Voice pipeline works end-to-end (student speaks → Didi responds in voice)
- [ ] No crashes or unhandled errors during session
- [ ] Student can switch language mid-session
- [ ] Parent receives session summary

**Blocker:** ALL subsequent phases are blocked until P0 passes.

## P1 — Schema Evolution (Weeks 2-4)

**Criteria:**
- [ ] All 6 P1 bugs fixed (see p1-backlog.md)
- [ ] v8.1.0 schema deployed (boards, textbooks, content_units, student_profiles)
- [ ] Alembic migrations working on Railway PostgreSQL
- [ ] Content bank queries DB by student context, not flat files
- [ ] 152+ tests still passing after all changes

## P2 — Multi-Board + Bench L1 (Months 2-3)

**Criteria:**
- [ ] BSETS Telangana board content loaded
- [ ] MSBSHSE Maharashtra board content loaded
- [ ] ICSE content loaded
- [ ] IDNA-Bench Layer 1 (Language Fidelity ≥75%) passing for all boards
- [ ] Content factory pipeline operational
- [ ] New board = data insert, zero code change (proven)

## P3 — Platform + Memory-R1 (Months 4-6)

**Criteria:**
- [ ] RL-based memory layer (Memory-R1 style) operational
- [ ] Student-level session continuity across days
- [ ] Parent dashboard with emotional transformation narrative
- [ ] API versioned at /api/v1/
- [ ] Performance: <2s end-to-end latency per turn

## P4 — Device + Government (Months 6-12)

**Criteria:**
- [ ] Offline tablet prototype (7-8", camera, on-device SLM+TTS/STT)
- [ ] BharathCloud Hyderabad integration (P3 GPU)
- [ ] IndiaAI/NEP2020 grant application submitted
- [ ] 22 scheduled languages supported
- [ ] 33+ examination boards content loaded
