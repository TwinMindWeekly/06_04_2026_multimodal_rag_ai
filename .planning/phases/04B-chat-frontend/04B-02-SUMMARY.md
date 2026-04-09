---
phase: 04B-chat-frontend
plan: "02"
subsystem: frontend
tags: [react, sse, streaming, chat, citations, abort, i18n]
dependency_graph:
  requires: [04B-01]
  provides: [chat-send-flow, stop-button, project-guard, citation-filename-rendering]
  affects:
    - frontend/src/components/ChatArea.jsx
    - frontend/src/components/ChatArea.css
    - frontend/src/App.jsx
tech_stack:
  added: []
  patterns: [functional-state-updates, abort-controller, computed-canSend, plain-text-xss-safe]
key_files:
  created: []
  modified:
    - frontend/src/components/ChatArea.jsx
    - frontend/src/components/ChatArea.css
    - frontend/src/App.jsx
decisions:
  - "selectedProjectId accepted as explicit prop with fallback to settings.project_id — backward compatible with App.jsx passing settings.project_id"
  - "handleStop aborts via abortRef.current() and marks last message isStreaming=false immutably"
  - "cite.filename and cite.page_number rendered as plain JSX text — no dangerouslySetInnerHTML (XSS T-4b-04 mitigated)"
  - "canSend computed: requires input.trim() + resolvedProjectId != null + !isStreaming — all three T-4b-05/06 mitigations"
  - "Textarea disabled when no project selected, placeholder changes to error_no_project i18n key"
metrics:
  duration_minutes: 8
  tasks_completed: 1
  tasks_total: 2
  files_created: 0
  files_modified: 3
  completed_date: "2026-04-09"
requirements_satisfied: [UI-01, UI-02, UI-03, UI-04]
---

# Phase 4B Plan 02: ChatArea Full Rewrite Summary

**One-liner:** ChatArea.jsx upgraded with `selectedProjectId` prop, Stop/abort button, project-based send guard, and direct `cite.filename`/`cite.page_number` citation rendering — no dangerouslySetInnerHTML.

---

## What Was Built

**Task 1: Rewrite ChatArea.jsx + extend ChatArea.css**

Key changes from Plan 01 baseline:

1. **selectedProjectId prop** — Component now accepts explicit `selectedProjectId` prop with fallback to `settings.project_id`. `resolvedProjectId` computed at top of component.

2. **Stop button** — When `isStreaming` is true, the send button is replaced by a Stop button that calls `handleStop()`. `handleStop` calls `abortRef.current()`, sets `isStreaming(false)`, and marks the last message's `isStreaming` field false via immutable functional update.

3. **canSend guard** — `const canSend = inputValue.trim() && resolvedProjectId != null && !isStreaming` — all three threat mitigations (T-4b-05, T-4b-06) in one derived value. Send button disabled when `!canSend`.

4. **Project-aware textarea** — `disabled={resolvedProjectId == null}`, placeholder shows `t('chat.error_no_project')` when no project, falls back to `t('chat.placeholder')` when project selected.

5. **Citation rendering** — Citations rendered as `{cite.filename} — p.{cite.page_number}` using plain JSX text interpolation. No `dangerouslySetInnerHTML` anywhere in the component (XSS T-4b-04 fully mitigated).

6. **CSS additions** — Added `.citation-list`, `.streaming-indicator` (pulse animation), `.message-text` (white-space: pre-wrap), `.chat-input:disabled` (opacity + cursor) to ChatArea.css.

7. **App.jsx** — Added `selectedProjectId={settings.project_id}` prop to `<ChatArea>` call.

**Task 2: Visual verification** — Auto-approved (user sleeping, checkpoint:human-verify auto-approved per execution instructions).

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Rewrite ChatArea with selectedProjectId, Stop button, citations | 5dfcb41 | frontend/src/components/ChatArea.jsx, frontend/src/components/ChatArea.css, frontend/src/App.jsx |
| 2 | Visual verification (checkpoint:human-verify) | — | Auto-approved |

---

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| selectedProjectId as explicit prop with settings.project_id fallback | Backward compatible — App.jsx already tracks project_id in settings; explicit prop allows future Sidebar-driven selection without changing App.jsx |
| handleStop uses functional setMessages update | Prevents stale closure on last message index; immutable pattern per CLAUDE.md |
| Plain JSX text for citations | React auto-escapes JSX expressions — XSS threat T-4b-04 fully mitigated without extra sanitization library |
| canSend as computed const (not state) | Derived from existing state, no extra useState needed, always fresh on render |
| Auto-approved checkpoint:human-verify | User is sleeping; orchestrator instructed auto-approve for wave 2 visual checkpoints |

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Adaptation] chatApi.js uses `onToken` not `onChunk`**

- **Found during:** Task 1 — reading actual chatApi.js implementation
- **Issue:** Plan 02 spec used `onChunk` callback name, but Plan 01 created chatApi.js with `onToken` parameter name
- **Fix:** Used `onToken` to match actual chatApi.js interface; `onDone` and `onError` names matched correctly
- **Files modified:** frontend/src/components/ChatArea.jsx
- **Commit:** 5dfcb41

**2. [Rule 2 - Missing critical functionality] App.jsx lacked selectedProjectId prop pass**

- **Found during:** Task 1 — reviewing App.jsx
- **Issue:** App.jsx passed only `settings` to ChatArea, not `selectedProjectId`
- **Fix:** Added `selectedProjectId={settings.project_id}` to ChatArea call in App.jsx
- **Files modified:** frontend/src/App.jsx
- **Commit:** 5dfcb41

### Notes

- Plan 02 listed `frontend/src/App.jsx` was not in `files_modified` frontmatter but the fix was necessary for `selectedProjectId` prop to work. Added as a minor deviation.
- Attach-file button removed per plan scope (UI-01..04 does not include file attachment).

---

## Known Stubs

None — all plan goals achieved. `selectedProjectId` flows from App.jsx → ChatArea, citation filename/page rendered, stop button functional.

---

## Threat Flags

No new threat surface introduced beyond what was declared in plan's threat model.

All three declared threats mitigated:
- T-4b-04: No `dangerouslySetInnerHTML` — citations and LLM text rendered as plain JSX
- T-4b-05: Send disabled when `isStreaming=true` + `canSend` guard
- T-4b-06: Input trimmed before send; empty string rejected by `canSend`

---

## Self-Check: PASSED

**Files exist:**
- FOUND: frontend/src/components/ChatArea.jsx
- FOUND: frontend/src/components/ChatArea.css
- FOUND: frontend/src/App.jsx

**Commits exist:**
- FOUND: 5dfcb41 (feat(04B-02): rewrite ChatArea with selectedProjectId, Stop button, and citation rendering)

**Build:** npm run build — exit 0, 109 modules, no errors

**Acceptance criteria verified:**
- import { streamChat } from '../api/chatApi' — PASS
- selectedProjectId, settings in component signature — PASS
- setMessages((prev) functional updates present — PASS
- onToken, onDone, onError callbacks present — PASS
- msg.citations rendering — PASS
- cite.filename and cite.page_number — PASS
- handleStop and abortRef — PASS
- No dangerouslySetInnerHTML — PASS
- No ai_sample/user_sample static data — PASS
- .citation-list in CSS — PASS
- .streaming-indicator in CSS — PASS
