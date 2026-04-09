---
phase: 04B
slug: chat-frontend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 04B — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | ESLint + manual smoke test |
| **Config file** | frontend/.eslintrc.cjs |
| **Quick run command** | `cd frontend && npx eslint src/ --no-error-on-unmatched-pattern` |
| **Full suite command** | `cd frontend && npx eslint src/ && npm run build` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run ESLint on modified files
- **After every plan wave:** Run full build
- **Before verification:** Full build must succeed
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| T1 | 04B-01 | 1 | UI-01 | lint+build | `eslint src/services/chatApi.js && npm run build` | pending |
| T2 | 04B-01 | 1 | UI-04 | lint+build | `eslint src/App.jsx src/components/SettingsPanel.jsx` | pending |
| T1 | 04B-02 | 2 | UI-01,02,03 | lint+build | `eslint src/components/ChatArea.jsx && npm run build` | pending |
| T2 | 04B-02 | 2 | UI-02,03 | human | Visual verification — streaming + citations | pending |
