# Phase 4b: Chat Frontend — Research

**Researched:** 2026-04-09
**Domain:** React SSE client, streaming state management, citation rendering, settings integration
**Confidence:** HIGH (codebase đọc trực tiếp từ file thực; SSE format xác nhận từ backend đã implement)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-01 | SSE client dùng fetch + ReadableStream (KHÔNG dùng EventSource — GET-only limitation) | Backend POST /api/chat đã confirm; fetch + ReadableStream là pattern duy nhất đúng cho POST SSE |
| UI-02 | Parse SSE data events, append text vào message buffer incrementally (typing effect) | Backend stream format đã xác nhận: `data: {"text": "..."}\n\n` per chunk; React useState + functional update pattern |
| UI-03 | Render citations từ terminal SSE event với filename và page number | Terminal event format: `data: {"done": true, "citations": [{"filename":"...","page_number":N,"chunk_index":N,"marker":"[N]"}]}\n\n` |
| UI-04 | Load provider và credential settings từ SettingsPanel state vào chat request body | SettingsPanel hiện là uncontrolled (defaultValue); cần lift state lên App.jsx để share với ChatArea |
</phase_requirements>

---

## Summary

Phase 4b là frontend-only integration phase. Backend đã hoàn chỉnh (chat.py router, rag_chain.py, SSE format cụ thể). Công việc là: wire ChatArea.jsx để gọi POST /api/chat, parse ReadableStream SSE, và render response streaming + citations.

**Ba thay đổi chính:**
1. **`App.jsx`** — lift settings state lên top-level, pass xuống ChatArea và SettingsPanel qua props
2. **`ChatArea.jsx`** — thêm SSE client logic, convert textarea thành controlled input, render real messages + citations
3. **`frontend/src/api/chatApi.js`** (mới) — SSE streaming utility tách riêng

Không cần cài thêm npm package nào. `fetch` là Web API có sẵn, không dùng axios cho streaming (axios buffer toàn bộ response).

**Primary recommendation:** Tạo `chatApi.js` với `streamChat(request, onChunk, onDone, onError)` callback-based API. ChatArea.jsx consume callback này, update state với functional update để tránh stale closure.

---

## Project Constraints (from CLAUDE.md)

| Directive | Source | Impact on Phase 4b |
|-----------|--------|-------------------|
| Immutability — dùng spread, không mutate | common/coding-style.md | `setMessages(prev => [...prev, newMsg])` không `messages.push()` |
| No `console.log` trong production code | typescript/hooks.md | Dùng silent error handling hoặc toast |
| Error handling toàn diện | common/coding-style.md | Handle SSE error event, network failure, abort |
| Files 200–400 dòng, tối đa 800 | common/coding-style.md | ChatArea.jsx hiện 82 dòng — có thể mở rộng; nếu vượt 400 tách MessageList.jsx |
| Input validation tại system boundaries | common/coding-style.md | Validate message không rỗng trước khi gọi API |
| No hardcoded values | common/coding-style.md | API URL qua `import.meta.env.VITE_API_URL` (đã có trong client.js) |

---

## Standard Stack

### Core (đã có, không cần cài thêm)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| React | 19.2.4 | Component rendering, state management | INSTALLED [VERIFIED: package.json] |
| Vite | 8.0.4 | Build + dev server với CORS proxy | INSTALLED [VERIFIED: package.json] |
| Vanilla CSS | — | Styling với CSS variables đã định nghĩa | EXISTING [VERIFIED: index.css] |
| fetch (Web API) | built-in | SSE client với ReadableStream | BROWSER BUILT-IN [ASSUMED: modern browser] |
| axios | 1.15.0 | Dùng cho các API calls khác (projects, documents) | INSTALLED [VERIFIED: package.json] |
| react-i18next | 17.0.2 | i18n cho UI labels | INSTALLED [VERIFIED: package.json] |

### Không cần cài thêm

| Mục đích | Đừng dùng | Dùng thay vào | Lý do |
|---------|-----------|--------------|-------|
| SSE streaming | EventSource | fetch + ReadableStream | EventSource chỉ GET — backend dùng POST |
| SSE streaming | axios | fetch native | axios buffer toàn bộ response, không stream |
| SSE streaming | socket.io | fetch native | WebSocket overkill, SSE là đủ cho one-way stream |
| Markdown rendering | react-markdown | dangerouslySetInnerHTML đơn giản hoặc plain text | Không có requirement markdown; tránh dep mới |
| State management | Redux/Zustand | React useState + props lifting | Scope nhỏ, không cần global store |

**Installation:** Không cần `npm install` gì thêm.

---

## Architecture Patterns

### Recommended Project Structure (thay đổi)

```
frontend/src/
├── api/
│   ├── client.js           # axios instance (unchanged)
│   ├── projectApi.js       # (unchanged)
│   ├── documentApi.js      # (unchanged)
│   └── chatApi.js          # MỚI: SSE streaming utility
├── components/
│   ├── ChatArea.jsx        # SỬA: thêm SSE client, real messages, citations
│   ├── ChatArea.css        # SỬA nhẹ: loading state, citation list styling
│   ├── SettingsPanel.jsx   # SỬA: controlled inputs, nhận props từ App
│   └── SettingsPanel.css   # (unchanged)
└── App.jsx                 # SỬA: lift settings state, pass props
```

### Pattern 1: Lift Settings State lên App.jsx

**Vấn đề hiện tại:** SettingsPanel dùng `defaultValue` (uncontrolled) — state không share được với ChatArea.

**Giải pháp:** App.jsx giữ settings state, pass xuống cả hai component.

```jsx
// Source: Codebase analysis [VERIFIED: App.jsx, SettingsPanel.jsx]

// App.jsx
function App() {
  const [isArchOpen, setIsArchOpen] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [settings, setSettings] = useState({
    provider: 'gemini',
    apiKey: '',
    temperature: 0.7,
    maxTokens: 2048,
    embeddingProvider: 'local',
    embeddingApiKey: '',
  });

  return (
    <div className="app-container">
      <Sidebar
        onOpenArch={() => setIsArchOpen(true)}
        selectedProjectId={selectedProjectId}
        onSelectProject={setSelectedProjectId}
      />
      <div className="main-content">
        <ChatArea
          selectedProjectId={selectedProjectId}
          settings={settings}
        />
        <SettingsPanel
          settings={settings}
          onSettingsChange={setSettings}
          selectedProjectId={selectedProjectId}
          onSelectProject={setSelectedProjectId}
        />
      </div>
      <ArchitectureModal isOpen={isArchOpen} onClose={() => setIsArchOpen(false)} />
    </div>
  );
}
```

### Pattern 2: SSE Client Utility (chatApi.js)

**Không dùng axios** cho streaming — axios buffer toàn bộ response. Dùng `fetch` native với `ReadableStream`.

```javascript
// Source: Web API specification [ASSUMED: MDN ReadableStream API]
// frontend/src/api/chatApi.js

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

/**
 * Stream chat response từ POST /api/chat.
 * @param {Object} request - ChatRequest body (message, project_id, provider, api_key, ...)
 * @param {Function} onChunk - callback(text: string) cho mỗi text chunk
 * @param {Function} onDone - callback(citations: Array) khi terminal event nhận được
 * @param {Function} onError - callback(errorMsg: string) khi có lỗi
 * @returns {AbortController} - gọi .abort() để cancel stream
 */
export async function streamChat(request, onChunk, onDone, onError) {
  const controller = new AbortController();
  const lang = localStorage.getItem('i18nextLng') || 'en';

  try {
    const response = await fetch(`${BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept-Language': lang,
      },
      body: JSON.stringify(request),
      signal: controller.signal,
    });

    if (!response.ok) {
      const errText = await response.text();
      onError(errText || `HTTP ${response.status}`);
      return controller;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE events được phân cách bởi \n\n
      const parts = buffer.split('\n\n');
      buffer = parts.pop(); // giữ lại phần chưa hoàn chỉnh

      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith('data: ')) continue;

        try {
          const payload = JSON.parse(line.slice(6)); // bỏ 'data: '
          if (payload.error) {
            onError(payload.error);
          } else if (payload.done) {
            onDone(payload.citations || []);
          } else if (payload.text) {
            onChunk(payload.text);
          }
        } catch {
          // Bỏ qua malformed JSON event
        }
      }
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      onError(err.message || 'Network error');
    }
  }

  return controller;
}
```

### Pattern 3: ChatArea State Management cho Streaming

**Key insight:** Dùng functional update `setMessages(prev => ...)` để tránh stale closure trong callbacks.

```jsx
// Source: React docs pattern [ASSUMED: React functional update pattern]
// ChatArea.jsx — message state structure

const [messages, setMessages] = useState([]); // [{role, content, citations, isStreaming}]
const [input, setInput] = useState('');
const [isLoading, setIsLoading] = useState(false);
const abortControllerRef = useRef(null);

const handleSend = async () => {
  if (!input.trim() || isLoading) return;

  const userMessage = { role: 'user', content: input.trim(), citations: [], isStreaming: false };
  const aiMessage = { role: 'assistant', content: '', citations: [], isStreaming: true };

  setMessages(prev => [...prev, userMessage, aiMessage]); // immutable update
  setInput('');
  setIsLoading(true);

  const request = {
    message: userMessage.content,
    project_id: selectedProjectId,
    provider: settings.provider,
    api_key: settings.apiKey || null,
    temperature: settings.temperature,
    max_tokens: settings.maxTokens,
    embedding_provider: settings.embeddingProvider || 'local',
    embedding_api_key: settings.embeddingApiKey || null,
  };

  abortControllerRef.current = await streamChat(
    request,
    // onChunk — append text incrementally (typing effect)
    (text) => {
      setMessages(prev => {
        const updated = [...prev];
        const last = { ...updated[updated.length - 1] };
        last.content = last.content + text; // immutable: new object
        updated[updated.length - 1] = last;
        return updated;
      });
    },
    // onDone — set citations, mark not streaming
    (citations) => {
      setMessages(prev => {
        const updated = [...prev];
        const last = { ...updated[updated.length - 1] };
        last.citations = citations;
        last.isStreaming = false;
        updated[updated.length - 1] = last;
        return updated;
      });
      setIsLoading(false);
    },
    // onError
    (errorMsg) => {
      setMessages(prev => {
        const updated = [...prev];
        const last = { ...updated[updated.length - 1] };
        last.content = `Error: ${errorMsg}`;
        last.isStreaming = false;
        updated[updated.length - 1] = last;
        return updated;
      });
      setIsLoading(false);
    },
  );
};
```

### Pattern 4: Citation Rendering

Backend terminal event: `{"done": true, "citations": [{"filename": "doc.pdf", "page_number": 3, "chunk_index": 5, "marker": "[1]"}]}`

```jsx
// Citation component (inline trong ChatArea hoặc tách riêng)
// CSS class 'citation' đã tồn tại trong ChatArea.css [VERIFIED: ChatArea.css line 102]

{message.citations && message.citations.length > 0 && (
  <div className="citation-list">
    {message.citations.map((cite, idx) => (
      <div key={idx} className="citation flex-row align-center">
        <svg width="12" height="12" .../>
        <span>{cite.marker} {cite.filename} — trang {cite.page_number}</span>
      </div>
    ))}
  </div>
)}
```

### Anti-Patterns to Avoid

- **Dùng EventSource:** GET-only, không gửi POST body được
- **Dùng axios cho streaming:** Buffer toàn bộ response, không stream incrementally
- **Mutate message array trực tiếp:** `messages[last].content += text` — React không detect thay đổi
- **Đặt settings state trong SettingsPanel:** Không share được với ChatArea
- **`await streamChat(...)` blocking toàn bộ function:** `streamChat` đã xử lý async internally qua callbacks; cần `abortControllerRef` để cancel
- **Không handle AbortError:** Khi user navigate away hoặc cancel, AbortError phải được ignored

---

## Don't Hand-Roll

| Problem | Đừng tự build | Dùng thay vào | Lý do |
|---------|--------------|--------------|-------|
| SSE text frame parsing | Custom regex | Split on `\n\n`, check `data:` prefix | SSE format đơn giản, không cần parser library |
| ReadableStream | polyfill | Native browser API | React 19 + Vite modern target — không cần polyfill |
| Auto-scroll to bottom | IntersectionObserver complex | `useRef` + `scrollIntoView` | Đơn giản hơn, đủ cho v1 |
| Markdown rendering | react-markdown | Plain text | Không có requirement markdown trong UI-01..04 |

---

## Common Pitfalls

### Pitfall 1: EventSource thay vì fetch + ReadableStream

**What goes wrong:** EventSource chỉ hỗ trợ GET requests. Backend POST /api/chat yêu cầu JSON body.

**Why it happens:** EventSource là API phổ biến cho SSE nhưng thiếu POST support.

**How to avoid:** Luôn dùng `fetch()` với `response.body.getReader()`. Không import hoặc dùng `EventSource` bất kỳ đâu.

**Warning signs:** `EventSource` trong import hoặc `new EventSource(url)` trong code.

### Pitfall 2: Stale closure trong streaming callbacks

**What goes wrong:** `onChunk` closure capture `messages` từ lần render đầu — tất cả chunks overwrite nhau thay vì append.

**Why it happens:** `setMessages(messages => ...)` capture `messages` biến ngoài, không phải state mới nhất.

**How to avoid:** Luôn dùng functional update form: `setMessages(prev => [...prev, ...])`.

**Warning signs:** Messages chỉ hiển thị chunk cuối cùng, không accumulate.

### Pitfall 3: axios cho streaming

**What goes wrong:** axios buffer toàn bộ SSE response trước khi return — không có incremental rendering.

**Why it happens:** axios không expose `ReadableStream`, chỉ return complete response.

**How to avoid:** `chatApi.js` dùng `fetch` native, không import axios. `client.js` vẫn dùng axios cho tất cả non-streaming calls.

**Warning signs:** Text chỉ xuất hiện một lần sau khi stream hoàn tất.

### Pitfall 4: SettingsPanel là uncontrolled → state không share được

**What goes wrong:** ChatArea không access được provider/apiKey từ Settings vì chúng là local DOM state (`defaultValue`).

**Why it happens:** SettingsPanel hiện tại dùng `defaultValue` thay vì `value` + onChange.

**How to avoid:** Lift state lên App.jsx, pass `settings` prop xuống cả SettingsPanel và ChatArea.

**Warning signs:** Chat request luôn gửi default provider bất kể user chọn gì.

### Pitfall 5: project_id là null khi chưa chọn project

**What goes wrong:** Backend yêu cầu `project_id: int` (required field trong ChatRequest). Gửi null gây 422.

**Why it happens:** Sidebar hiện không có selection state; App.jsx không track `selectedProjectId`.

**How to avoid:** Disable Send button khi `selectedProjectId === null`. Sidebar cần `onSelectProject` callback.

**Warning signs:** 422 Unprocessable Entity khi gửi chat.

### Pitfall 6: Buffer không xử lý split SSE frames

**What goes wrong:** Network có thể split SSE frame ở giữa `\n\n` separator — parse ngay `value` sẽ miss data.

**Why it happens:** TCP không đảm bảo message boundaries khớp với SSE frame boundaries.

**How to avoid:** Accumulate trong `buffer` string, split bởi `\n\n`, giữ lại phần incomplete (`parts.pop()`).

**Warning signs:** Citations bị drop, hoặc occasional JSON parse error.

---

## Code Examples

Verified patterns từ codebase và Web API specs:

### Đọc VITE_API_URL (đã có trong codebase)
```javascript
// Source: frontend/src/api/client.js [VERIFIED: file đọc trực tiếp]
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
```

### SSE Event Format (từ backend đã implement)
```
// Source: backend/app/routers/chat.py [VERIFIED: file đọc trực tiếp]
// Text chunk:
data: {"text": "Hello world"}\n\n

// Terminal event:
data: {"done": true, "citations": [{"filename": "doc.pdf", "page_number": 3, "chunk_index": 5, "marker": "[1]"}]}\n\n

// Error event:
data: {"error": "LLM provider failed"}\n\n
```

### ChatRequest body shape (từ backend schema)
```javascript
// Source: backend/app/schemas/domain.py [VERIFIED: file đọc trực tiếp]
{
  message: string,          // required, max 10000 chars
  project_id: number,       // required integer
  provider: string,         // 'openai'|'gemini'|'claude'|'ollama', default 'openai'
  api_key: string | null,   // LLM API key
  temperature: number,      // 0.0–2.0, default 0.7
  max_tokens: number,       // default 1000
  top_k: number,            // default 5
  score_threshold: number,  // default 0.3
  embedding_provider: string, // 'local'|'openai'|'gemini', default 'local'
  embedding_api_key: string | null,
}
```

### CSS Variables hiện có (dùng trong citation rendering)
```css
/* Source: frontend/src/index.css [VERIFIED: file đọc trực tiếp] */
--accent-primary: #6366f1;
--bg-surface-hover: #1c1d22;
--text-secondary: #9ca3af;
--spacing-xs: 0.25rem;
--spacing-sm: 0.5rem;
--spacing-md: 1rem;

/* Citation class đã tồn tại: [VERIFIED: ChatArea.css line 102-112] */
.citation {
  border-left: 3px solid var(--accent-primary);
  /* ... */
}
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|-----------------|--------|
| EventSource for SSE | fetch + ReadableStream | Cho phép POST với JSON body |
| Controlled via axios | Native fetch cho streaming | No buffering, true incremental render |
| Uncontrolled inputs (defaultValue) | Controlled inputs (value + onChange) | Settings có thể shared qua props |

**Deprecated/outdated:**
- `EventSource`: Vẫn hoạt động cho GET SSE nhưng không áp dụng được cho case này

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Không có test framework frontend hiện tại (package.json không có vitest/jest) |
| Config file | Không có — Wave 0 phải setup nếu test được yêu cầu |
| Quick run command | `npm run lint` (ESLint hiện có) |
| Full suite command | N/A — xem Wave 0 Gaps |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-01 | fetch + ReadableStream SSE parse | unit | vitest nếu setup, else manual | ❌ Wave 0 |
| UI-02 | Text append incrementally | unit | vitest nếu setup, else manual | ❌ Wave 0 |
| UI-03 | Citation rendering từ terminal event | unit | vitest nếu setup, else manual | ❌ Wave 0 |
| UI-04 | Settings state pass vào request | unit | vitest nếu setup, else manual | ❌ Wave 0 |

**Lưu ý:** Frontend test framework (`vitest`) chưa có trong `package.json`. Với `nyquist_validation: true` trong config.json, planner phải quyết định: (a) thêm vitest và tests, hoặc (b) dùng manual smoke test thay thế. Phase frontend nhỏ (4 requirements) — manual smoke test có thể đủ.

### Sampling Rate
- **Per task commit:** `npm run lint` (ESLint check)
- **Per wave merge:** Manual smoke test trong browser
- **Phase gate:** Visual verification streaming + citations trước `/gsd-verify-work`

### Wave 0 Gaps

- [ ] Không có frontend test framework — nếu cần unit tests thêm vitest: `npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom`
- [ ] Không có test files `frontend/src/__tests__/` hoặc `*.test.jsx`

*(Nếu planner chọn manual smoke test, Wave 0 gaps là "None — manual verification approach")*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Single-user local tool |
| V3 Session Management | No | No sessions |
| V4 Access Control | No | No access control layer |
| V5 Input Validation | Yes | Validate `message.trim()` trước khi send; `project_id` phải là integer |
| V6 Cryptography | No | API keys không encrypt client-side (local tool) |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key exposed trong browser DevTools | Information Disclosure | Accept — single-user local tool, không có server-side logging (per T-4a-02 từ Phase 4a) |
| XSS via LLM response text | Tampering | Render text dưới dạng plain text, KHÔNG dùng `dangerouslySetInnerHTML` cho LLM output |
| Empty message spam | Denial of Service | Disable send button khi message rỗng hoặc isLoading=true |

**Critical:** ChatArea.jsx hiện có một chỗ dùng `dangerouslySetInnerHTML` cho sample AI message. Khi render real LLM output, PHẢI dùng plain text (`{message.content}`) hoặc safe markdown renderer — không bao giờ `dangerouslySetInnerHTML` với LLM output.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js / npm | Frontend build | ✓ | Detected via package.json | — |
| fetch API | UI-01 SSE client | ✓ | Browser built-in (modern) | — |
| ReadableStream | UI-01 SSE parsing | ✓ | Browser built-in (modern) | — |
| Backend /api/chat | UI-01..04 | ✓ (Phase 4a done) | Implemented in chat.py | — |

**Missing dependencies with no fallback:** Không có.

**Note:** Backend Phase 4a đã hoàn thành Plan 01. Plan 02 (chat.py router) cần verified là executed trước khi Phase 4b integration testing có thể diễn ra.

---

## Open Questions

1. **Project selection state — Sidebar cần refactor không?**
   - What we know: Sidebar.jsx hiện không emit selected project. App.jsx không track `selectedProjectId`.
   - What's unclear: Scope refactor của Sidebar — có cần click-to-select project không?
   - Recommendation: Thêm `onSelectProject` callback vào Sidebar, highlight selected project, disable chat khi không có project được chọn. Nằm trong scope Phase 4b vì UI-04 cần project_id.

2. **Embedding provider in SettingsPanel — cần expose không?**
   - What we know: ChatRequest có `embedding_provider` và `embedding_api_key` riêng biệt với LLM provider (Pitfall 7 từ Phase 4a research).
   - What's unclear: SettingsPanel hiện không có embedding provider selector. Có cần thêm không?
   - Recommendation: Thêm embedding provider selector vào SettingsPanel (local/openai/gemini). Default `local` không cần API key. Phù hợp với EMBED-02 requirement đã implement ở backend.

3. **Frontend testing approach**
   - What we know: Không có vitest trong package.json.
   - What's unclear: Planner muốn unit tests hay chỉ manual smoke test?
   - Recommendation: Manual smoke test đủ cho v1 local tool với 4 frontend requirements. Thêm vitest chỉ nếu planner explicitly yêu cầu — tránh scope creep.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `fetch` + `ReadableStream` hoạt động trong browser target (modern Chrome/Firefox) | Standard Stack | Thấp — Vite default target là modern browsers |
| A2 | Backend /api/chat endpoint (Plan 02 của Phase 4a) đã được execute và working | Environment Availability | Cao — Phase 4b không thể test nếu backend chưa chạy |
| A3 | `decoder.decode(value, { stream: true })` xử lý đúng UTF-8 multi-byte characters trong tiếng Việt | Code Examples | Thấp — TextDecoder stream mode được thiết kế cho multi-byte |
| A4 | Provider list hiện tại (gemini/openai/claude/ollama) khớp với `LLMProviderFactory` backend | Standard Stack | Thấp — verified từ SettingsPanel.jsx và llm_provider.py |

---

## Sources

### Primary (HIGH confidence)
- `frontend/src/components/ChatArea.jsx` — structure thực tế, state hiện tại [VERIFIED: đọc trực tiếp]
- `frontend/src/components/SettingsPanel.jsx` — uncontrolled inputs, provider list [VERIFIED: đọc trực tiếp]
- `frontend/src/App.jsx` — component tree, state hiện tại [VERIFIED: đọc trực tiếp]
- `frontend/package.json` — dependencies thực tế [VERIFIED: đọc trực tiếp]
- `frontend/src/api/client.js` — axios instance, VITE_API_URL pattern [VERIFIED: đọc trực tiếp]
- `backend/app/routers/chat.py` — SSE format chính xác [VERIFIED: đọc trực tiếp]
- `backend/app/schemas/domain.py` — ChatRequest fields [VERIFIED: đọc trực tiếp]
- `.planning/codebase/STACK.md` — tech stack overview [VERIFIED: đọc trực tiếp]

### Secondary (MEDIUM confidence)
- `.planning/phases/04A-chat-backend/04A-02-PLAN.md` — SSE event format spec [VERIFIED: đọc trực tiếp]
- `.planning/phases/04A-chat-backend/04A-01-SUMMARY.md` — confirmed schemas [VERIFIED: đọc trực tiếp]
- `frontend/src/index.css` — CSS variables, class utilities [VERIFIED: đọc trực tiếp]
- `frontend/src/components/ChatArea.css` — existing citation class [VERIFIED: đọc trực tiếp]

### Tertiary (ASSUMED)
- ReadableStream + TextDecoder streaming pattern — training knowledge, standard Web API

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — package.json verified, không cần cài thêm
- Architecture: HIGH — codebase đọc trực tiếp, SSE format confirmed từ backend file
- Pitfalls: HIGH — derived từ code analysis (EventSource trap, stale closure, axios buffering)
- Validation: MEDIUM — frontend test gap identified, planner phải decide approach

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable stack — Vite + React + fetch API không thay đổi nhanh)
