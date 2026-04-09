---
phase: 04A
slug: chat-backend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 04A — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | none |
| **Quick run command** | `cd backend && .venv/Scripts/python -m pytest tests/ -x -q` |
| **Full suite command** | `cd backend && .venv/Scripts/python -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~25 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| TBD | TBD | TBD | CHAT-01 | integration | `pytest tests/test_chat_router.py -x` | pending |
| TBD | TBD | TBD | CHAT-02 | unit | `pytest tests/test_rag_chain.py -x` | pending |
| TBD | TBD | TBD | CHAT-03 | unit | `pytest tests/test_rag_chain.py -x` | pending |
| TBD | TBD | TBD | CHAT-04 | integration | `pytest tests/test_chat_router.py -x` | pending |
| TBD | TBD | TBD | CHAT-05 | integration | `pytest tests/test_chat_router.py -x` | pending |
| TBD | TBD | TBD | CHAT-06 | integration | `pytest tests/test_chat_router.py -x` | pending |
| TBD | TBD | TBD | CHAT-07 | integration | `pytest tests/test_chat_router.py -x` | pending |
