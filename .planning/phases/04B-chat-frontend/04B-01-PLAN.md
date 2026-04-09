---
phase: 04B-chat-frontend
plan: "01"
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/api/chatApi.js
  - frontend/src/App.jsx
  - frontend/src/components/SettingsPanel.jsx
  - frontend/src/components/Sidebar.jsx
  - frontend/src/locales/en.json
  - frontend/src/locales/vi.json
autonomous: true
requirements: [UI-01, UI-04]

must_haves:
  truths:
    - "SSE client utility exports a streamChat function that calls POST /api/chat with fetch and parses ReadableStream"
    - "App.jsx holds settings state (provider, apiKey, temperature, maxTokens, embeddingProvider, embeddingApiKey) and selectedProjectId"
    - "SettingsPanel receives settings and onSettingsChange props, renders controlled inputs (value + onChange, not defaultValue)"
    - "Sidebar receives onSelectProject callback, clicking a project updates selectedProjectId in App.jsx"
    - "Changing provider in SettingsPanel updates settings.provider in App.jsx state"
    - "Embedding provider selector exists in SettingsPanel with local/openai/gemini options"
  artifacts:
    - path: "frontend/src/api/chatApi.js"
      provides: "SSE streaming utility with fetch + ReadableStream"
      exports: ["streamChat"]
      min_lines: 40
    - path: "frontend/src/App.jsx"
      provides: "Root component with lifted settings state and selectedProjectId"
      contains: "settings"
      min_lines: 25
    - path: "frontend/src/components/SettingsPanel.jsx"
      provides: "Controlled settings panel with embedding provider selector"
      contains: "onSettingsChange"
      min_lines: 50
    - path: "frontend/src/components/Sidebar.jsx"
      provides: "Project list with click-to-select and highlight"
      contains: "onSelectProject"
  key_links:
    - from: "frontend/src/api/chatApi.js"
      to: "POST /api/chat"
      via: "fetch with ReadableStream"
      pattern: "fetch.*api.*chat"
    - from: "frontend/src/App.jsx"
      to: "frontend/src/components/SettingsPanel.jsx"
      via: "settings prop and onSettingsChange callback"
      pattern: "settings.*onSettingsChange"
    - from: "frontend/src/App.jsx"
      to: "frontend/src/components/Sidebar.jsx"
      via: "onSelectProject callback"
      pattern: "onSelectProject"
---

<objective>
Create the SSE streaming utility and wire App-level state so ChatArea (Plan 02) can send chat requests with correct provider settings and project context.

Purpose: UI-01 requires fetch + ReadableStream (not EventSource). UI-04 requires settings from SettingsPanel to flow into chat requests. Both need foundational wiring before ChatArea can consume them.

Output: chatApi.js utility, App.jsx with lifted state, controlled SettingsPanel, selectable Sidebar projects.
</objective>

<execution_context>
@.claude/get-shit-done/workflows/execute-plan.md
@.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/04B-chat-frontend/04B-RESEARCH.md
@.planning/phases/04A-chat-backend/04A-01-SUMMARY.md

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From backend/app/schemas/domain.py (ChatRequest body shape):
```python
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    project_id: int
    provider: str = 'openai'
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    top_k: int = 5
    score_threshold: float = 0.3
    embedding_provider: str = 'local'
    embedding_api_key: Optional[str] = None
```

From backend/app/routers/chat.py (SSE event format):
```
Text chunk:    data: {"text": "Hello world"}\n\n
Terminal:      data: {"done": true, "citations": [{"filename":"doc.pdf","page_number":3,"chunk_index":5,"marker":"[1]"}]}\n\n
Error:         data: {"error": "LLM provider failed"}\n\n
```

From frontend/src/api/client.js (API URL pattern):
```javascript
const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
```

From frontend/src/App.jsx (current structure):
```jsx
function App() {
  const [isArchOpen, setIsArchOpen] = useState(false);
  return (
    <div className="app-container">
      <Sidebar onOpenArch={() => setIsArchOpen(true)} />
      <div className="main-content">
        <ChatArea />
        <SettingsPanel />
      </div>
      <ArchitectureModal isOpen={isArchOpen} onClose={() => setIsArchOpen(false)} />
    </div>
  );
}
```

From frontend/src/components/SettingsPanel.jsx (currently uncontrolled):
```jsx
<select className="ui-select" defaultValue="gemini">  // PROBLEM: uncontrolled
<input type="range" ... defaultValue="0.7" />          // PROBLEM: uncontrolled
```

From frontend/src/components/Sidebar.jsx (no selection callback):
```jsx
const Sidebar = ({ onOpenArch }) => { ... }  // Missing onSelectProject, selectedProjectId
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create SSE streaming utility chatApi.js</name>
  <files>frontend/src/api/chatApi.js</files>
  <read_first>
    - frontend/src/api/client.js (VITE_API_URL pattern, language interceptor pattern)
    - backend/app/routers/chat.py (SSE event format — data: JSON\n\n)
    - backend/app/schemas/domain.py (ChatRequest fields)
  </read_first>
  <action>
Create `frontend/src/api/chatApi.js` with a single exported async function:

```
export async function streamChat(request, onChunk, onDone, onError)
```

Implementation details:
1. Read `BASE_URL` from `import.meta.env.VITE_API_URL || 'http://localhost:8000/api'` (same pattern as client.js).
2. Create `AbortController` at function start.
3. Read language from `localStorage.getItem('i18nextLng') || 'en'` for `Accept-Language` header (mirrors client.js interceptor pattern).
4. Call `fetch(\`${BASE_URL}/chat\`, { method: 'POST', headers: {'Content-Type': 'application/json', 'Accept-Language': lang}, body: JSON.stringify(request), signal: controller.signal })`.
5. If `!response.ok`, read `response.text()` and call `onError(errText || \`HTTP ${response.status}\`)`, then return controller.
6. Get `reader = response.body.getReader()` and `decoder = new TextDecoder()`.
7. Accumulate into `buffer` string. Loop with `while(true)` calling `reader.read()`. On `done`, break.
8. Append `decoder.decode(value, { stream: true })` to buffer.
9. Split buffer by `'\n\n'`. `parts.pop()` stays as incomplete buffer. For each completed part:
   - Trim, skip if not starting with `'data: '`.
   - Parse JSON from `line.slice(6)`.
   - If `payload.error` -> call `onError(payload.error)`.
   - If `payload.done` -> call `onDone(payload.citations || [])`.
   - If `payload.text` -> call `onChunk(payload.text)`.
   - Wrap JSON.parse in try/catch, silently skip malformed events.
10. Catch block: if `err.name !== 'AbortError'`, call `onError(err.message || 'Network error')`.
11. Return `controller` so caller can abort.

CRITICAL constraints:
- Do NOT import axios — fetch is required for streaming (axios buffers entire response).
- Do NOT use EventSource — it only supports GET, backend requires POST.
- Do NOT use `console.log` — silent error handling via callbacks only.
  </action>
  <verify>
    <automated>cd frontend && npx eslint src/api/chatApi.js --no-error-on-unmatched-pattern</automated>
  </verify>
  <acceptance_criteria>
    - grep "export async function streamChat" frontend/src/api/chatApi.js
    - grep "fetch(" frontend/src/api/chatApi.js
    - grep "getReader" frontend/src/api/chatApi.js
    - grep "AbortController" frontend/src/api/chatApi.js
    - grep "onChunk\|onDone\|onError" frontend/src/api/chatApi.js returns all three
    - File does NOT contain "EventSource" or "import axios"
  </acceptance_criteria>
  <done>chatApi.js exports streamChat function using fetch + ReadableStream with proper SSE parsing, buffer accumulation, and AbortController support. No EventSource, no axios.</done>
</task>

<task type="auto">
  <name>Task 2: Lift settings state to App.jsx, convert SettingsPanel to controlled, add project selection to Sidebar</name>
  <files>
    frontend/src/App.jsx,
    frontend/src/components/SettingsPanel.jsx,
    frontend/src/components/Sidebar.jsx,
    frontend/src/locales/en.json,
    frontend/src/locales/vi.json
  </files>
  <read_first>
    - frontend/src/App.jsx (current component tree, state)
    - frontend/src/components/SettingsPanel.jsx (current uncontrolled inputs)
    - frontend/src/components/Sidebar.jsx (current project list rendering, props)
    - frontend/src/locales/en.json (existing i18n keys)
    - frontend/src/locales/vi.json (existing i18n keys)
  </read_first>
  <action>
**A. App.jsx — Lift state:**

Add two new state variables to App component:
```jsx
const [selectedProjectId, setSelectedProjectId] = useState(null);
const [settings, setSettings] = useState({
  provider: 'gemini',
  apiKey: '',
  temperature: 0.7,
  maxTokens: 2048,
  embeddingProvider: 'local',
  embeddingApiKey: '',
});
```

Update component tree to pass props:
- `<Sidebar onOpenArch={...} selectedProjectId={selectedProjectId} onSelectProject={setSelectedProjectId} />`
- `<ChatArea selectedProjectId={selectedProjectId} settings={settings} />`
- `<SettingsPanel settings={settings} onSettingsChange={setSettings} />`

**B. SettingsPanel.jsx — Controlled inputs:**

1. Change function signature: `const SettingsPanel = ({ settings, onSettingsChange }) => {`
2. Create helper: `const update = (key, value) => onSettingsChange({ ...settings, [key]: value });`  (immutable update per coding-style.md)
3. Convert ALL `defaultValue` to `value` + `onChange`:
   - Provider select: `value={settings.provider}` + `onChange={e => update('provider', e.target.value)}`
   - API key input: `value={settings.apiKey}` + `onChange={e => update('apiKey', e.target.value)}`
   - Temperature slider: `value={settings.temperature}` + `onChange={e => update('temperature', parseFloat(e.target.value))}` — also update the `<span className="value-label">` to show `{settings.temperature}`
   - Max tokens slider: `value={settings.maxTokens}` + `onChange={e => update('maxTokens', parseInt(e.target.value, 10))}` — also update the `<span className="value-label">` to show `{settings.maxTokens}`
4. Remove the "Target Project" selector (project_id comes from Sidebar selection, not Settings — per research Pitfall 5).
5. Add NEW embedding provider section AFTER the divider:
   - Label: `{t('settings.embedding_provider')}` with select: options `local` (default, label "Local (all-MiniLM-L6-v2)"), `openai` (label "OpenAI text-embedding-3-small"), `gemini` (label "Google text-embedding-004"). Controlled: `value={settings.embeddingProvider}`, `onChange={e => update('embeddingProvider', e.target.value)}`.
   - Conditionally show embedding API key input ONLY when `settings.embeddingProvider !== 'local'`: `<input type="password" placeholder="Embedding API Key" value={settings.embeddingApiKey} onChange={e => update('embeddingApiKey', e.target.value)} />`
6. Remove the "Save Settings" button — state is live via onChange (no save action needed).

**C. Sidebar.jsx — Project selection:**

1. Update props: `const Sidebar = ({ onOpenArch, selectedProjectId, onSelectProject }) => {`
2. For each project in the `.map()`, add `onClick={() => onSelectProject(proj.id)}` and add `className` logic: `className={\`tree-item flex-row align-center\${selectedProjectId === proj.id ? ' active' : ''}\`}`
3. For the fallback "General Project" item, it already has `active` class — leave as-is (no projects = no selection possible).

**D. i18n keys — Add new keys:**

Add to BOTH en.json and vi.json under `"settings"` section:

en.json additions:
```json
"embedding_provider": "Embedding Provider",
"embedding_api_key": "Embedding API Key",
"embedding_local": "Local (all-MiniLM-L6-v2)",
"embedding_openai": "OpenAI text-embedding-3-small",
"embedding_gemini": "Google text-embedding-004"
```

vi.json additions:
```json
"embedding_provider": "Nguon Embedding",
"embedding_api_key": "Khoa API Embedding",
"embedding_local": "Cuc bo (all-MiniLM-L6-v2)",
"embedding_openai": "OpenAI text-embedding-3-small",
"embedding_gemini": "Google text-embedding-004"
```

Add to BOTH under `"chat"` section:

en.json:
```json
"sending": "Sending...",
"streaming": "AI is thinking...",
"error_empty": "Please type a message",
"error_no_project": "Please select a project first",
"error_network": "Network error. Please try again.",
"stop_generating": "Stop generating"
```

vi.json:
```json
"sending": "Dang gui...",
"streaming": "AI dang suy nghi...",
"error_empty": "Vui long nhap tin nhan",
"error_no_project": "Vui long chon du an truoc",
"error_network": "Loi mang. Vui long thu lai.",
"stop_generating": "Dung tao"
```

CRITICAL constraints:
- Do NOT mutate settings object — always spread: `{ ...settings, [key]: value }`.
- Do NOT use `console.log` in any modified file.
- Keep language selector as-is (already controlled via i18n.changeLanguage).
- SettingsPanel and Sidebar MUST remain functional components with hooks.
  </action>
  <verify>
    <automated>cd frontend && npx eslint src/App.jsx src/components/SettingsPanel.jsx src/components/Sidebar.jsx --no-error-on-unmatched-pattern</automated>
  </verify>
  <acceptance_criteria>
    - grep "selectedProjectId" frontend/src/App.jsx
    - grep "settings.*setSettings" frontend/src/App.jsx (both state vars present)
    - grep "onSettingsChange" frontend/src/components/SettingsPanel.jsx
    - grep "onSelectProject" frontend/src/components/Sidebar.jsx
    - grep "value={settings" frontend/src/components/SettingsPanel.jsx (controlled inputs)
    - SettingsPanel.jsx does NOT contain "defaultValue" for provider/temperature/maxTokens
    - grep "embeddingProvider" frontend/src/components/SettingsPanel.jsx
    - grep "embedding_provider" frontend/src/locales/en.json
    - grep "embedding_provider" frontend/src/locales/vi.json
  </acceptance_criteria>
  <done>App.jsx holds settings and selectedProjectId state, passes to children. SettingsPanel uses controlled inputs with embedding provider selector. Sidebar supports project click-to-select with visual highlight. i18n keys added for embedding settings and chat states.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Browser -> Backend API | Chat request body crosses from untrusted client to server |
| LLM response -> DOM | SSE text rendered in UI (potential XSS if using dangerouslySetInnerHTML) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-4b-01 | Information Disclosure | chatApi.js | accept | API key sent in request body to localhost — single-user local tool, acceptable per T-4a-02 |
| T-4b-02 | Tampering | chatApi.js | mitigate | Validate message is non-empty string before calling streamChat (Task 2 in Plan 02 handles this in ChatArea send handler) |
| T-4b-03 | Denial of Service | SettingsPanel.jsx | mitigate | Temperature clamped 0-2 via slider min/max, maxTokens clamped 256-8192 via slider min/max — prevents extreme values |
</threat_model>

<verification>
1. `cd frontend && npx eslint src/ --no-error-on-unmatched-pattern` — zero errors
2. `grep "streamChat" frontend/src/api/chatApi.js` — function exported
3. `grep "selectedProjectId" frontend/src/App.jsx` — state exists
4. `grep "onSettingsChange" frontend/src/components/SettingsPanel.jsx` — prop consumed
5. `grep "onSelectProject" frontend/src/components/Sidebar.jsx` — prop consumed
6. `grep "embeddingProvider" frontend/src/components/SettingsPanel.jsx` — embedding selector present
</verification>

<success_criteria>
- chatApi.js exports streamChat using fetch + ReadableStream (NOT EventSource, NOT axios)
- App.jsx manages settings state and selectedProjectId, passes as props
- SettingsPanel is fully controlled (no defaultValue for settings fields)
- SettingsPanel has embedding provider selector (local/openai/gemini) with conditional API key
- Sidebar supports click-to-select project with visual active state
- All new user-facing strings have en.json and vi.json translations
- ESLint passes on all modified files
</success_criteria>

<output>
After completion, create `.planning/phases/04B-chat-frontend/04B-01-SUMMARY.md`
</output>
