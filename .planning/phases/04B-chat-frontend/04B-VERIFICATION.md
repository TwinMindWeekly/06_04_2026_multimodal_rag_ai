---
phase: 04B-chat-frontend
verified: 2026-04-09T10:30:00Z
status: human_needed
score: 4/4 must-haves verified
overrides_applied: 0
gaps:
human_verification:
  - test: "Kiểm tra i18n keys bị thiếu trong UI"
    expected: "Khi chat bị disabled (no project), placeholder hiển thị 'Please select a project' hoặc tương đương — không phải key thô 'chat.error_no_project'. Nút Stop hiển thị tooltip 'Stop generating' — không phải key thô 'chat.stop_generating'."
    why_human: "Thiếu 2 i18n keys trong en.json và vi.json: 'chat.error_no_project' và 'chat.stop_generating'. React-i18next fallback trả về key thô khi key không tồn tại. Hành vi thực tế (key thô vs fallback đã cấu hình) cần xác minh trực quan trong browser."
  - test: "Luồng chat end-to-end với backend"
    expected: "Gõ câu hỏi, nhấn Enter → thấy user bubble → AI response stream từng từ → sau khi xong thấy citations với filename và page number bên dưới"
    why_human: "Không thể kiểm tra streaming SSE thực tế mà không khởi động cả backend (Phase 4a) và frontend dev server. Yêu cầu môi trường runtime."
  - test: "Provider/apiKey từ SettingsPanel đi vào request body"
    expected: "Mở Network tab, thay đổi provider thành 'openai', nhập API key, gửi message → request body trong POST /api/chat chứa đúng provider='openai' và api_key đã nhập"
    why_human: "Cần kiểm tra Network devtools thực tế với backend running."
---

# Phase 4B: Chat Frontend — Báo Cáo Xác Minh

**Mục tiêu Phase:** User types a question in ChatArea, sees streaming response with citations from their uploaded documents.
**Thời điểm xác minh:** 2026-04-09T10:30:00Z
**Trạng thái:** human_needed
**Re-verification:** Không — xác minh lần đầu

---

## Kết Quả Đạt Mục Tiêu

### Observable Truths

| # | Truth | Trạng thái | Bằng chứng |
|---|-------|-----------|------------|
| 1 | SSE client uses fetch + ReadableStream (not EventSource) | VERIFIED | `chatApi.js:56` — `response.body.getReader()` + `TextDecoder`. Comment dòng 6: "EventSource is GET-only". Không có `new EventSource` trong codebase. |
| 2 | Text tokens stream incrementally into message buffer | VERIFIED | `ChatArea.jsx:29-35` — `appendToken` callback dùng `setMessages((prev) => prev.map(...))` immutable update. Mỗi token nối vào `msg.text + token`. |
| 3 | Citations render from terminal SSE event | VERIFIED | `ChatArea.jsx:182-207` — `msg.citations.map()` render `cite.filename` và `cite.page_number` khi `!msg.isStreaming && msg.citations.length > 0`. |
| 4 | Settings state (provider, api_key, temperature, max_tokens, project_id) flows into chat request | VERIFIED | `App.jsx:24` — `<ChatArea selectedProjectId={settings.project_id} settings={settings} />`. `ChatArea.jsx:101-111` — streamChat nhận `settings.provider`, `settings.apiKey/api_key`, `settings.temperature`, `settings.maxTokens/max_tokens`. |

**Điểm số:** 4/4 truths đã xác minh

---

### Deferred Items

Không có.

---

### Required Artifacts

| Artifact | Mô tả mong đợi | Trạng thái | Chi tiết |
|----------|---------------|-----------|----------|
| `frontend/src/api/chatApi.js` | streamChat() dùng fetch + ReadableStream | VERIFIED | 104 dòng. Chứa `ReadableStream` (comment), `getReader()`, `TextDecoder`, `AbortController`. Export `streamChat`. |
| `frontend/src/components/ChatArea.jsx` | Stateful chat với SSE streaming và citation rendering | VERIFIED | 270 dòng. Chứa `streamChat` import, `isStreaming`, `citations`, `handleStop`, immutable updates. |
| `frontend/src/App.jsx` | Shared settings state | VERIFIED | `DEFAULT_SETTINGS` object, `useState(DEFAULT_SETTINGS)`, pass `settings` và `onSettingsChange` đến cả hai component. |
| `frontend/src/locales/en.json` | i18n keys cho streaming và error states | PARTIAL | `streaming`, `error_prefix`, `citation_label` có mặt. Thiếu: `chat.error_no_project` và `chat.stop_generating`. |

---

### Key Link Verification

| From | To | Via | Trạng thái | Chi tiết |
|------|----|-----|-----------|---------|
| `ChatArea.jsx` | `frontend/src/api/chatApi.js` | `import { streamChat } from '../api/chatApi'` | WIRED | Dòng 3 của ChatArea.jsx — import đúng path. `streamChat()` được gọi tại dòng 101. |
| `ChatArea.jsx` | POST /api/chat | `streamChat()` call với request body | WIRED | `streamChat({message, project_id, provider, api_key, temperature, max_tokens})` tại dòng 101-111. chatApi.js gửi POST đến `${BASE_URL}/chat`. |
| `App.jsx` | `ChatArea.jsx` | `settings` prop | WIRED | `<ChatArea selectedProjectId={settings.project_id} settings={settings} />` tại App.jsx dòng 24. |
| `App.jsx` | `SettingsPanel.jsx` | `settings` + `onSettingsChange` props | WIRED | `<SettingsPanel settings={settings} onSettingsChange={setSettings} />` tại App.jsx dòng 25. |
| `SettingsPanel.jsx` | App state | controlled inputs `value=` | WIRED | Tất cả 5 inputs dùng `value={settings.*}` (không phải `defaultValue`). `update()` gọi `onSettingsChange({ ...settings, [field]: value })`. |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Trạng thái |
|----------|---------------|--------|--------------------|-----------|
| `ChatArea.jsx` | `messages` | `streamChat()` → `onToken`/`onDone` callbacks | Có (khi backend running) | FLOWING — wired đúng, phụ thuộc backend Phase 4a |
| `ChatArea.jsx` | `settings` | `App.jsx` state từ `SettingsPanel` | Có (user input) | FLOWING — state lifting đúng cách |

---

### Behavioral Spot-Checks

| Hành vi | Lệnh | Kết quả | Trạng thái |
|---------|------|---------|-----------|
| Build thành công | `npx vite build` | 109 modules, built in 1.43s, exit 0 | PASS |
| Không dùng EventSource | `grep -r "new EventSource" src/` | Không có kết quả | PASS |
| Không dùng dangerouslySetInnerHTML | `grep -r "dangerouslySetInnerHTML" src/` | Không có kết quả | PASS |
| ESLint sạch | `npx eslint src/` | Không có lỗi, không có output | PASS |
| chatApi.js export streamChat | File đọc trực tiếp | `export async function streamChat` tại dòng 21 | PASS |
| i18n key chat.error_no_project | `grep "error_no_project" en.json` | Không tồn tại | FAIL |
| i18n key chat.stop_generating | `grep "stop_generating" en.json` | Không tồn tại | FAIL |

---

### Requirements Coverage

| Requirement | Plan | Mô tả | Trạng thái | Bằng chứng |
|-------------|------|-------|-----------|------------|
| UI-01 | 04B-01, 04B-02 | SSE client using fetch + ReadableStream (NOT EventSource) | SATISFIED | `chatApi.js` dùng `fetch + response.body.getReader()`. Không có `EventSource` trong codebase. |
| UI-02 | 04B-01, 04B-02 | Parse SSE data events và append text incremental (typing effect) | SATISFIED | `onToken` callback + `appendToken` dùng functional `setMessages(prev => ...)`. `streaming-cursor` CSS blink animation. |
| UI-03 | 04B-01, 04B-02 | Render citations từ terminal SSE event với filename và page number | SATISFIED | `cite.filename` và `cite.page_number` render trong `citation-list` div sau khi stream kết thúc. |
| UI-04 | 04B-01, 04B-02 | Load provider và credential settings từ SettingsPanel state vào chat request body | SATISFIED | `settings.provider`, `settings.apiKey/api_key`, `settings.temperature`, `settings.max_tokens` truyền vào `streamChat()`. |

---

### Anti-Patterns Phát Hiện

| File | Dòng | Pattern | Mức độ | Tác động |
|------|------|---------|--------|---------|
| `frontend/src/locales/en.json` | — | Thiếu key `chat.error_no_project` | Warning | UI hiển thị key thô `"chat.error_no_project"` thay vì text khi không có project được chọn |
| `frontend/src/locales/vi.json` | — | Thiếu key `chat.error_no_project` | Warning | Tương tự en.json nhưng cho tiếng Việt |
| `frontend/src/locales/en.json` | — | Thiếu key `chat.stop_generating` | Warning | Tooltip nút Stop hiển thị key thô thay vì text |
| `frontend/src/locales/vi.json` | — | Thiếu key `chat.stop_generating` | Warning | Tương tự en.json nhưng cho tiếng Việt |

**Phân loại stub:** Các thiếu sót i18n này là WarningUI — không ngăn chức năng hoạt động (React-i18next hiển thị key thô làm fallback), nhưng text người dùng thấy sẽ không đúng. Đây KHÔNG phải blocker cho mục tiêu phase (streaming + citations hoạt động đúng).

**Không phát hiện:**
- Không có `dangerouslySetInnerHTML`
- Không có `EventSource`
- Không có static/hardcoded messages (`ai_sample`, `user_sample` đã xóa)
- Không có `defaultValue` trong SettingsPanel (tất cả đã chuyển sang `value=`)
- Không có empty return stubs trong ChatArea

---

### Human Verification Cần Thiết

#### 1. Kiểm tra i18n fallback keys trong trình duyệt

**Test:** Mở app trong browser. Không chọn project nào. Xem placeholder của textarea.
**Mong đợi:** Placeholder hiển thị text có nghĩa (ví dụ: "Please select a project") — KHÔNG phải chuỗi `"chat.error_no_project"`.
**Lý do cần human:** 2 i18n keys bị thiếu trong file locales (`chat.error_no_project`, `chat.stop_generating`). Hành vi fallback phụ thuộc cấu hình i18next (`fallbackLng`, `defaultNS`). Cần xác minh trực quan.
**Fix nhanh nếu thấy key thô:** Thêm vào `en.json` và `vi.json`:
```json
"error_no_project": "Please select a project first",
"stop_generating": "Stop generating"
```
(vi.json: `"Vui lòng chọn dự án trước"`, `"Dừng tạo"`)

#### 2. Luồng chat streaming end-to-end

**Test:** Khởi động backend (`uvicorn app.main:app --reload`) và frontend (`npm run dev`). Chọn một project trong Sidebar. Gõ câu hỏi và nhấn Enter.
**Mong đợi:**
- User message xuất hiện ngay là bubble bên phải
- AI response stream từng từ (typing effect) với cursor nhấp nháy
- Sau khi stream kết thúc, citations xuất hiện bên dưới với filename và page number
- Nút Stop xuất hiện trong quá trình streaming
**Lý do cần human:** Không thể kiểm tra SSE streaming thực tế mà không có backend running.

#### 3. Settings flow vào request body

**Test:** Mở browser DevTools → Network tab. Thay đổi AI Provider thành "openai". Nhập API key "test-key-123". Gửi message.
**Mong đợi:** Request body của POST /api/chat chứa `"provider": "openai"` và `"api_key": "test-key-123"`.
**Lý do cần human:** Cần runtime để capture network request thực tế.

---

### Tóm Tắt Gaps

Tất cả 4 observable truths của phase đã được xác minh tự động:
- SSE client: fetch + ReadableStream, không dùng EventSource
- Streaming incremental: immutable state updates, functional callbacks
- Citations: render đúng từ terminal event với filename + page_number
- Settings flow: toàn bộ chuỗi App → SettingsPanel → ChatArea → streamChat

Phát hiện 2 i18n keys bị thiếu (`chat.error_no_project`, `chat.stop_generating`) trong cả en.json và vi.json. Đây là warning-level — chức năng chính không bị ảnh hưởng, nhưng text UI không đúng. Fix nhanh 2-3 phút.

Build frontend thành công (109 modules, exit 0). ESLint sạch không lỗi. Không có anti-pattern nghiêm trọng (no dangerouslySetInnerHTML, no EventSource, no static mocks).

**Khuyến nghị:** Fix 4 i18n keys thiếu, sau đó human verify luồng streaming end-to-end với backend.

---

_Đã xác minh: 2026-04-09T10:30:00Z_
_Verifier: Claude (gsd-verifier)_
