---
phase: 04B-chat-frontend
plan: "02"
type: execute
wave: 2
depends_on: ["04B-01"]
files_modified:
  - frontend/src/components/ChatArea.jsx
  - frontend/src/components/ChatArea.css
autonomous: false
requirements: [UI-01, UI-02, UI-03, UI-04]

must_haves:
  truths:
    - "User types a message and clicks Send — text appears as user message bubble in chat area"
    - "AI response text streams word-by-word into an assistant message bubble (typing effect via onChunk)"
    - "After stream completes, citations appear below the AI response with filename and page number"
    - "Send button is disabled when message is empty, no project selected, or stream is in progress"
    - "Chat request body includes provider, apiKey, temperature, maxTokens, embeddingProvider, embeddingApiKey from settings prop"
    - "SSE error events display error text in the AI message bubble instead of silent failure"
    - "User can abort an in-progress stream"
    - "Chat area auto-scrolls to bottom as new content streams in"
  artifacts:
    - path: "frontend/src/components/ChatArea.jsx"
      provides: "Real chat interface with SSE streaming, message list, citations"
      contains: "streamChat"
      min_lines: 100
    - path: "frontend/src/components/ChatArea.css"
      provides: "Styling for message list, streaming indicator, citation list, disabled states"
      contains: "citation-list"
      min_lines: 150
  key_links:
    - from: "frontend/src/components/ChatArea.jsx"
      to: "frontend/src/api/chatApi.js"
      via: "import { streamChat } from '../api/chatApi'"
      pattern: "import.*streamChat.*chatApi"
    - from: "frontend/src/components/ChatArea.jsx"
      to: "POST /api/chat"
      via: "streamChat function call with request body"
      pattern: "streamChat"
---

<objective>
Rewrite ChatArea.jsx to be a fully functional chat interface — send messages, stream AI responses via SSE, display citations, handle errors.

Purpose: This plan delivers the user-visible chat experience (UI-01 through UI-04). User types a question, sees streaming response with citations from their uploaded documents.

Output: Working ChatArea.jsx that consumes streamChat utility from Plan 01 and settings/selectedProjectId props from App.jsx.
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
@.planning/phases/04B-chat-frontend/04B-01-SUMMARY.md

<interfaces>
<!-- Key contracts from Plan 01 that this plan consumes -->

From frontend/src/api/chatApi.js (created in Plan 01):
```javascript
/**
 * @param {Object} request - ChatRequest body
 * @param {Function} onChunk - callback(text: string) for each text chunk
 * @param {Function} onDone - callback(citations: Array) when terminal event received
 * @param {Function} onError - callback(errorMsg: string) on error
 * @returns {AbortController} - call .abort() to cancel stream
 */
export async function streamChat(request, onChunk, onDone, onError)
```

From frontend/src/App.jsx (modified in Plan 01 — props passed to ChatArea):
```jsx
<ChatArea selectedProjectId={selectedProjectId} settings={settings} />
```

Settings shape:
```javascript
{
  provider: 'gemini',       // LLM provider
  apiKey: '',               // LLM API key
  temperature: 0.7,         // 0.0–2.0
  maxTokens: 2048,          // 256–8192
  embeddingProvider: 'local', // 'local'|'openai'|'gemini'
  embeddingApiKey: '',      // embedding API key (only when not local)
}
```

Backend ChatRequest body (what streamChat sends):
```javascript
{
  message: string,           // required, max 10000 chars
  project_id: number,        // required integer
  provider: string,          // 'openai'|'gemini'|'claude'|'ollama'
  api_key: string | null,    // LLM API key
  temperature: number,       // 0.0–2.0
  max_tokens: number,        // default 1000
  top_k: number,             // default 5
  score_threshold: number,   // default 0.3
  embedding_provider: string, // 'local'|'openai'|'gemini'
  embedding_api_key: string | null,
}
```

SSE event format:
```
data: {"text": "Hello"}\n\n           — text chunk
data: {"done": true, "citations": [{"filename":"doc.pdf","page_number":3,"chunk_index":5,"marker":"[1]"}]}\n\n — terminal
data: {"error": "LLM failed"}\n\n     — error
```

Existing CSS classes available (from ChatArea.css):
- .message-wrapper, .user-message, .ai-message, .message-content
- .ai-avatar (32px gradient circle with "AI" text)
- .citation (border-left accent, bg-surface-hover, inline-flex)
- .empty-state, .ai-avatar-large
- .chat-input, .chat-input-area, .input-wrapper

Existing i18n keys (from en.json/vi.json — including new keys from Plan 01):
- chat.placeholder, chat.send, chat.welcome_title, chat.welcome_subtitle
- chat.footer_disclaimer, chat.sending, chat.streaming
- chat.error_empty, chat.error_no_project, chat.error_network, chat.stop_generating
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rewrite ChatArea.jsx with SSE streaming, message state, and citations</name>
  <files>frontend/src/components/ChatArea.jsx, frontend/src/components/ChatArea.css</files>
  <read_first>
    - frontend/src/components/ChatArea.jsx (current structure — will be largely replaced)
    - frontend/src/components/ChatArea.css (existing styles to preserve and extend)
    - frontend/src/api/chatApi.js (streamChat function signature — created in Plan 01)
    - frontend/src/App.jsx (props passed: selectedProjectId, settings)
  </read_first>
  <action>
**A. ChatArea.jsx — Full rewrite (keep structure, replace content):**

1. **Imports:** Add `useRef, useEffect` to React import. Add `import { streamChat } from '../api/chatApi';`. Keep `useTranslation`.

2. **Component signature:** `const ChatArea = ({ selectedProjectId, settings }) => {`

3. **State and refs:**
```jsx
const [messages, setMessages] = useState([]);
// Each message: { role: 'user'|'assistant', content: string, citations: [], isStreaming: boolean }
const [input, setInput] = useState('');
const [isLoading, setIsLoading] = useState(false);
const abortControllerRef = useRef(null);
const messagesEndRef = useRef(null);
```

4. **Auto-scroll effect:** `useEffect` that calls `messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })` whenever `messages` changes.

5. **Cleanup effect:** `useEffect` with cleanup function that calls `abortControllerRef.current?.abort()` on unmount (prevent memory leak).

6. **handleSend function (async):**
   - Guard: if `!input.trim() || isLoading` return.
   - Guard: if `selectedProjectId === null || selectedProjectId === undefined` return (button should be disabled but double-check).
   - Create `userMessage = { role: 'user', content: input.trim(), citations: [], isStreaming: false }`.
   - Create `aiMessage = { role: 'assistant', content: '', citations: [], isStreaming: true }`.
   - `setMessages(prev => [...prev, userMessage, aiMessage])` — immutable append.
   - `setInput('')`.
   - `setIsLoading(true)`.
   - Build request object:
     ```
     {
       message: userMessage.content,
       project_id: selectedProjectId,
       provider: settings.provider,
       api_key: settings.apiKey || null,
       temperature: settings.temperature,
       max_tokens: settings.maxTokens,
       top_k: 5,
       score_threshold: 0.3,
       embedding_provider: settings.embeddingProvider || 'local',
       embedding_api_key: settings.embeddingApiKey || null,
     }
     ```
   - Call `streamChat(request, onChunk, onDone, onError)` and store result in `abortControllerRef.current`.

   **onChunk callback:** Use FUNCTIONAL update to avoid stale closure:
   ```jsx
   (text) => {
     setMessages(prev => {
       const updated = [...prev];
       const last = { ...updated[updated.length - 1] };
       last.content = last.content + text;
       updated[updated.length - 1] = last;
       return updated;
     });
   }
   ```

   **onDone callback:**
   ```jsx
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
   }
   ```

   **onError callback:**
   ```jsx
   (errorMsg) => {
     setMessages(prev => {
       const updated = [...prev];
       const last = { ...updated[updated.length - 1] };
       last.content = last.content || `Error: ${errorMsg}`;
       last.isStreaming = false;
       updated[updated.length - 1] = last;
       return updated;
     });
     setIsLoading(false);
   }
   ```

7. **handleStop function:** Calls `abortControllerRef.current?.abort()` and sets `isLoading(false)`. Also update last message `isStreaming = false` via functional setMessages update.

8. **handleKeyDown:** On Enter (without Shift), call `handleSend()`. On Shift+Enter, allow newline.

9. **Compute derived state:** `const canSend = input.trim() && selectedProjectId != null && !isLoading;`

10. **JSX structure:**

```jsx
<main className="chat-area flex-column">
  <div className="chat-messages flex-column">

    {/* Empty state — show only when messages.length === 0 */}
    {messages.length === 0 && (
      <div className="empty-state flex-column align-center justify-center">
        {/* Keep existing AI avatar SVG and welcome text */}
        <div className="ai-avatar-large">...</div>
        <h3>{t('chat.welcome_title')}</h3>
        <p>{t('chat.welcome_subtitle')}</p>
      </div>
    )}

    {/* Message list */}
    {messages.map((msg, idx) => (
      <div key={idx} className={`message-wrapper ${msg.role === 'user' ? 'user-message' : 'ai-message'} flex-row`}>
        {msg.role === 'assistant' && <div className="ai-avatar">AI</div>}
        <div className="message-content">
          {/* Render text as plain text — NEVER dangerouslySetInnerHTML for LLM output (XSS risk) */}
          <p className="message-text">{msg.content}</p>

          {/* Streaming indicator */}
          {msg.isStreaming && <span className="streaming-indicator">{t('chat.streaming')}</span>}

          {/* Citations — only show after stream completes with citations */}
          {!msg.isStreaming && msg.citations && msg.citations.length > 0 && (
            <div className="citation-list">
              {msg.citations.map((cite, cIdx) => (
                <div key={cIdx} className="citation flex-row align-center">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
                  <span>{cite.marker} {cite.filename} — p.{cite.page_number}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    ))}

    {/* Scroll anchor */}
    <div ref={messagesEndRef} />
  </div>

  <div className="chat-input-area">
    <div className="input-wrapper flex-row align-end">
      <textarea
        className="chat-input"
        placeholder={selectedProjectId == null ? t('chat.error_no_project') : t('chat.placeholder')}
        rows="1"
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={selectedProjectId == null}
      />
      {isLoading ? (
        <button className="btn-icon" onClick={handleStop} title={t('chat.stop_generating')}>
          {/* Stop icon — square */}
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
        </button>
      ) : (
        <button
          className={`btn-icon ${canSend ? 'primary text-color' : ''}`}
          onClick={handleSend}
          disabled={!canSend}
          title={t('chat.send')}
        >
          {/* Send icon — existing arrow SVG */}
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        </button>
      )}
    </div>
    <div className="chat-footer-text">{t('chat.footer_disclaimer')}</div>
  </div>
</main>
```

CRITICAL constraints:
- NEVER use `dangerouslySetInnerHTML` for LLM output text — XSS risk per research security domain.
- ALWAYS use functional update form for setMessages inside callbacks: `setMessages(prev => ...)` — prevents stale closure (research Pitfall 2).
- Do NOT mutate arrays: always spread `[...prev]` and create new object `{ ...updated[n] }`.
- Remove ALL sample/hardcoded messages (user_sample, ai_sample items). The empty state replaces them.
- Remove the attach file button (not in UI-01..04 scope).
- Keep the existing ai-avatar-large SVG gradient for empty state.

**B. ChatArea.css — Add new styles:**

Add these new CSS rules BELOW existing rules (do not remove existing):

```css
/* Message text */
.message-text {
  white-space: pre-wrap;
  word-break: break-word;
}

/* Streaming indicator */
.streaming-indicator {
  display: inline-block;
  margin-top: var(--spacing-xs);
  font-size: 0.8rem;
  color: var(--text-muted);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* Citation list (multiple citations) */
.citation-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  margin-top: var(--spacing-md);
}

/* Disabled input state */
.chat-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Stop button */
.btn-icon[title] svg rect {
  fill: var(--danger);
}
```
  </action>
  <verify>
    <automated>cd frontend && npx eslint src/components/ChatArea.jsx --no-error-on-unmatched-pattern && npm run build 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - grep "import.*streamChat.*chatApi" frontend/src/components/ChatArea.jsx
    - grep "selectedProjectId.*settings" frontend/src/components/ChatArea.jsx
    - grep "setMessages(prev" frontend/src/components/ChatArea.jsx (functional update)
    - grep "onChunk\|onDone\|onError" frontend/src/components/ChatArea.jsx (all three callbacks)
    - grep "msg.citations" frontend/src/components/ChatArea.jsx (citation rendering)
    - grep "cite.filename" frontend/src/components/ChatArea.jsx (filename in citation)
    - grep "cite.page_number" frontend/src/components/ChatArea.jsx (page number in citation)
    - grep "AbortController\|abortControllerRef\|handleStop" frontend/src/components/ChatArea.jsx (abort support)
    - ChatArea.jsx does NOT contain "dangerouslySetInnerHTML"
    - ChatArea.jsx does NOT contain "ai_sample\|user_sample" (static samples removed)
    - grep "citation-list" frontend/src/components/ChatArea.css
    - grep "streaming-indicator" frontend/src/components/ChatArea.css
    - npm run build succeeds (exit code 0)
  </acceptance_criteria>
  <done>ChatArea.jsx is a fully functional chat interface: sends messages via streamChat, renders streaming AI responses word-by-word, displays citations with filename and page number after stream completes, supports abort, auto-scrolls, handles errors. No dangerouslySetInnerHTML for LLM output. Build passes.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Verify complete chat frontend integration</name>
  <files>frontend/src/components/ChatArea.jsx</files>
  <action>
Human verification of the complete Phase 4b integration. No automated action — this is a visual/functional checkpoint.
  </action>
  <what-built>
Complete chat frontend integration: SSE streaming client, settings state lifting, controlled SettingsPanel with embedding provider, project selection in Sidebar, ChatArea with real message sending/streaming/citations.
  </what-built>
  <how-to-verify>
1. Start both backend and frontend dev servers (backend: `uvicorn app.main:app --reload`, frontend: `npm run dev`)
2. Open browser to http://localhost:5173
3. Verify SettingsPanel:
   - Change AI provider dropdown — should update immediately (no Save button)
   - Change temperature slider — value label should update live
   - Select embedding provider "OpenAI" — embedding API key field should appear
   - Select embedding provider "Local" — embedding API key field should hide
4. Verify Sidebar:
   - Click on a project name — it should highlight (active class)
   - The chat input placeholder should change from "Please select a project" to "Type a message..."
5. Verify Chat (requires backend running with documents uploaded):
   - Type a question and press Enter or click Send
   - User message should appear as a right-aligned bubble
   - AI response should stream in word-by-word (typing effect)
   - After streaming completes, citations should appear below the response with filename and page number
   - Click the Stop button during streaming — stream should abort
6. Verify error handling:
   - Try sending with no project selected — Send button should be disabled
   - Try sending with empty message — Send button should be disabled
  </how-to-verify>
  <verify>
    <automated>cd frontend && npm run build</automated>
  </verify>
  <done>User has visually confirmed: streaming chat works, citations display correctly, settings flow into requests, project selection works.</done>
  <resume-signal>Type "approved" or describe issues</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| LLM response text -> DOM | AI-generated text rendered in chat bubbles |
| User input -> Backend | Chat message sent to POST /api/chat |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-4b-04 | Tampering (XSS) | ChatArea.jsx | mitigate | Render LLM output as plain text via `{msg.content}` — NEVER use dangerouslySetInnerHTML. React auto-escapes JSX text content. |
| T-4b-05 | Denial of Service | ChatArea.jsx handleSend | mitigate | Disable Send button when isLoading=true or input empty — prevents rapid-fire requests. AbortController allows cancellation. |
| T-4b-06 | Spoofing | ChatArea.jsx input | mitigate | Input trimmed before send, empty strings rejected. Backend validates min_length=1 as second defense. |
</threat_model>

<verification>
1. `cd frontend && npm run build` — build succeeds with no errors
2. `cd frontend && npx eslint src/ --no-error-on-unmatched-pattern` — no ESLint errors
3. `grep "streamChat" frontend/src/components/ChatArea.jsx` — SSE utility imported and used
4. `grep "dangerouslySetInnerHTML" frontend/src/components/ChatArea.jsx` — should return NO matches (XSS mitigation)
5. `grep "cite.filename" frontend/src/components/ChatArea.jsx` — citation rendering present
6. Manual: open dev tools, send a chat, verify SSE events in Network tab
</verification>

<success_criteria>
- User types message, sees it as user bubble, AI response streams word-by-word
- Citations with filename and page number appear below AI response after stream ends
- Settings from SettingsPanel (provider, apiKey, temperature, maxTokens, embeddingProvider) are included in chat request
- selectedProjectId from Sidebar click is included in chat request body
- Error events show error text in message bubble (not silent failure)
- Abort/stop button cancels in-progress stream
- No dangerouslySetInnerHTML used for LLM output
- Frontend builds successfully (npm run build)
</success_criteria>

<output>
After completion, create `.planning/phases/04B-chat-frontend/04B-02-SUMMARY.md`
</output>
