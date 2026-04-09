---
phase: 04B-chat-frontend
plan: "01"
subsystem: frontend
tags: [react, sse, streaming, chat, i18n]
dependency_graph:
  requires: [04A-chat-backend]
  provides: [chat-sse-client, settings-state, citation-rendering]
  affects: [frontend/src/api/chatApi.js, frontend/src/components/ChatArea.jsx, frontend/src/App.jsx, frontend/src/components/SettingsPanel.jsx]
tech_stack:
  added: []
  patterns: [fetch-ReadableStream-SSE, lifted-state, controlled-components, immutable-updates, abort-controller]
key_files:
  created:
    - frontend/src/api/chatApi.js
    - .planning/phases/04B-chat-frontend/04B-01-PLAN.md
  modified:
    - frontend/src/components/ChatArea.jsx
    - frontend/src/App.jsx
    - frontend/src/components/SettingsPanel.jsx
    - frontend/src/locales/en.json
    - frontend/src/locales/vi.json
    - frontend/src/components/ChatArea.css
decisions:
  - "fetch + ReadableStream for SSE (EventSource is GET-only; chat needs POST with JSON body)"
  - "Settings applied live on change (no Save button needed for v1 single-user tool)"
  - "Immutable message updates via spread operator (prev.map returning new objects)"
  - "AbortController cleanup on component unmount prevents memory leaks from in-flight streams"
metrics:
  duration_minutes: 2
  tasks_completed: 4
  tasks_total: 4
  files_created: 2
  files_modified: 6
  completed_date: "2026-04-09"
requirements_satisfied: [UI-01, UI-02, UI-03, UI-04]
---

# Phase 4B Plan 01: Chat Frontend SSE Integration Summary

**One-liner:** React chat UI wired to backend SSE endpoint via fetch + ReadableStream with incremental token streaming, citation rendering, and live settings propagation from SettingsPanel.

---

## What Was Built

Four tasks implemented the complete frontend chat integration:

1. **chatApi.js** — New SSE streaming client using `fetch + ReadableStream`. Handles three SSE event types: `{text}` tokens appended incrementally, `{done, citations}` terminal event, and `{error}` mid-stream failures. `AbortController` allows cancellation.

2. **ChatArea.jsx** — Complete rewrite from static mock to live stateful component. Messages stored as `[{id, role, text, citations, isStreaming}]` array. Immutable updates via `prev.map(spread)`. Auto-scroll on new messages. Streaming cursor visible while AI response is in-flight. Citations rendered after stream completes.

3. **App.jsx + SettingsPanel.jsx** — Settings state lifted to `App` with `DEFAULT_SETTINGS`. SettingsPanel converted from uncontrolled (`defaultValue`) to controlled (`value=` + `onChange`). All 5 settings (provider, api_key, temperature, max_tokens, project_id) flow into each `streamChat()` call.

4. **i18n + CSS** — Added `streaming`, `error_prefix`, `citation_label` keys to both `en.json` and `vi.json`. Added `streaming-cursor` blink animation and `citations-container` layout to `ChatArea.css`.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create chatApi.js SSE client | 68c94f9 | frontend/src/api/chatApi.js |
| 2 | Rewrite ChatArea.jsx with streaming | c4baa85 | frontend/src/components/ChatArea.jsx |
| 3 | Lift settings state to App.jsx | 379f9a0 | frontend/src/App.jsx, frontend/src/components/SettingsPanel.jsx |
| 4 | Add i18n keys and streaming CSS | c348650 | frontend/src/locales/en.json, frontend/src/locales/vi.json, frontend/src/components/ChatArea.css |

---

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| fetch + ReadableStream (not EventSource) | EventSource is GET-only; POST required for JSON body with message + settings |
| Settings applied live on change | No save button needed — single-user local tool; live updates simplify UX |
| Immutable message state updates | Spread operator on prev array and message object — follows CLAUDE.md immutability rule |
| AbortController on unmount | Prevents dangling fetch reads when ChatArea unmounts mid-stream |
| try/catch around SSE JSON.parse | Malformed SSE lines skipped silently — stream continues rather than crashing |

---

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

---

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| project_id dropdown only shows "General" option | frontend/src/components/SettingsPanel.jsx line ~82 | Project list not fetched from backend in this plan; future plan will wire Sidebar project selection into settings |

The stub does not prevent the plan's goal: `project_id=null` is a valid value that the backend accepts (queries all projects). The dropdown will be populated when Sidebar project selection is connected to settings state.

---

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced. Client-side only changes.

---

## Self-Check: PASSED

Files exist:
- frontend/src/api/chatApi.js: FOUND
- frontend/src/components/ChatArea.jsx: FOUND (modified)
- frontend/src/App.jsx: FOUND (modified)
- frontend/src/components/SettingsPanel.jsx: FOUND (modified)
- frontend/src/locales/en.json: FOUND (modified)
- frontend/src/locales/vi.json: FOUND (modified)
- frontend/src/components/ChatArea.css: FOUND (modified)

Commits exist:
- 68c94f9: feat(04B-01): create chatApi.js
- c4baa85: feat(04B-01): rewrite ChatArea.jsx
- 379f9a0: feat(04B-01): lift settings state
- c348650: feat(04B-01): add i18n keys
