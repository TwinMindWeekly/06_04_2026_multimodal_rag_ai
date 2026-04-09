---
phase: 04B-chat-frontend
plan: 01
type: execute
wave: 1
depends_on: [04A-chat-backend]
autonomous: true
requirements: [UI-01, UI-02, UI-03, UI-04]

must_haves:
  truths:
    - "SSE client uses fetch + ReadableStream (not EventSource)"
    - "Text tokens stream incrementally into message buffer"
    - "Citations render from terminal SSE event"
    - "Settings state (provider, api_key, temperature, max_tokens, project_id) flows into chat request"
  artifacts:
    - path: "frontend/src/api/chatApi.js"
      provides: "streamChat() function using fetch + ReadableStream for SSE"
      contains: "ReadableStream"
    - path: "frontend/src/components/ChatArea.jsx"
      provides: "Stateful chat component with SSE streaming and citation rendering"
      contains: "streamChat"
    - path: "frontend/src/App.jsx"
      provides: "Shared settings state passed to SettingsPanel and ChatArea"
      contains: "settings"
    - path: "frontend/src/locales/en.json"
      provides: "i18n keys for streaming and error states"
      contains: "streaming"
---

<objective>
Wire the frontend chat UI to the backend SSE streaming endpoint.

Purpose: Replace the static mock UI in ChatArea.jsx with a live SSE client that streams LLM responses token by token, renders citations, and sends provider settings from SettingsPanel in each request.

Output: Working chat UI that streams responses from POST /api/chat using fetch + ReadableStream, with citation rendering and settings integration.
</objective>

<context>
@frontend/src/App.jsx
@frontend/src/components/ChatArea.jsx
@frontend/src/components/SettingsPanel.jsx
@frontend/src/api/client.js
@frontend/src/locales/en.json

<interfaces>
Backend SSE contract (from REQUIREMENTS.md CHAT-04, CHAT-05):
- Endpoint: POST /api/chat
- Request body: { message: string, project_id: number|null, provider: string, api_key: string, temperature: number, max_tokens: number }
- SSE stream format:
  - Token chunk: data: {"text": "..."}\n\n
  - Terminal event: data: {"done": true, "citations": [{"filename": "...", "page_number": 0, "chunk_index": 0}]}\n\n
  - Error event: data: {"error": "..."}\n\n

Frontend current state:
- ChatArea.jsx: static mock messages, no state, no API calls
- SettingsPanel.jsx: uncontrolled inputs with defaultValue, no state lifted
- App.jsx: no shared state, just renders components side by side
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create chatApi.js — SSE streaming client</name>
  <files>frontend/src/api/chatApi.js</files>
  <action>
    Create `frontend/src/api/chatApi.js` with a `streamChat()` function.

    **Decision (UI-01):** Use fetch + ReadableStream, NOT EventSource. EventSource is GET-only; chat needs POST with JSON body.

    ```javascript
    const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

    /**
     * Stream a chat message via Server-Sent Events using fetch + ReadableStream.
     *
     * @param {object} params
     * @param {string} params.message - User message text
     * @param {number|null} params.project_id - Target project for vector search (null = general)
     * @param {string} params.provider - LLM provider: "gemini" | "openai" | "claude" | "ollama"
     * @param {string} params.api_key - Provider API key or Ollama base URL
     * @param {number} params.temperature - Sampling temperature (0–2)
     * @param {number} params.max_tokens - Max tokens in response
     * @param {function} params.onToken - Called with each text token string
     * @param {function} params.onDone - Called with citations array when stream completes
     * @param {function} params.onError - Called with error message string on failure
     * @returns {function} abort - Call to cancel the stream
     */
    export async function streamChat({
      message,
      project_id = null,
      provider = 'gemini',
      api_key = '',
      temperature = 0.7,
      max_tokens = 2048,
      onToken,
      onDone,
      onError,
    }) {
      const controller = new AbortController();

      try {
        const response = await fetch(`${BASE_URL}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
          },
          body: JSON.stringify({ message, project_id, provider, api_key, temperature, max_tokens }),
          signal: controller.signal,
        });

        if (!response.ok) {
          const errText = await response.text();
          onError && onError(`Request failed: ${response.status} ${errText}`);
          return () => {};
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        const processChunk = async () => {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            // Keep the last (potentially incomplete) line in the buffer
            buffer = lines.pop();

            for (const line of lines) {
              if (!line.startsWith('data: ')) continue;
              const jsonStr = line.slice(6).trim();
              if (!jsonStr) continue;

              try {
                const event = JSON.parse(jsonStr);
                if (event.error) {
                  onError && onError(event.error);
                } else if (event.done) {
                  onDone && onDone(event.citations || []);
                } else if (event.text !== undefined) {
                  onToken && onToken(event.text);
                }
              } catch {
                // Skip malformed SSE lines
              }
            }
          }
        };

        processChunk().catch((err) => {
          if (err.name !== 'AbortError') {
            onError && onError(err.message || 'Stream read error');
          }
        });

      } catch (err) {
        if (err.name !== 'AbortError') {
          onError && onError(err.message || 'Connection failed');
        }
      }

      return () => controller.abort();
    }
    ```
  </action>
  <verify>
    Manual: File exists at frontend/src/api/chatApi.js and contains "ReadableStream" and "streamChat"
  </verify>
  <done>chatApi.js exists with streamChat() using fetch + ReadableStream. Handles token events, done event with citations, and error events.</done>
</task>

<task type="auto">
  <name>Task 2: Rewrite ChatArea.jsx with streaming state management and citation rendering</name>
  <files>frontend/src/components/ChatArea.jsx</files>
  <action>
    Rewrite `frontend/src/components/ChatArea.jsx` to:
    1. Accept `settings` prop from parent (provider, api_key, temperature, max_tokens, project_id)
    2. Manage messages array state: each message has { id, role: 'user'|'ai', text, citations, isStreaming }
    3. On send: append user message, append empty AI message with isStreaming=true, call streamChat()
    4. On token: append token to the last AI message's text (immutable update)
    5. On done: set isStreaming=false, set citations on last AI message
    6. On error: set isStreaming=false, set error text on last AI message
    7. Show empty state only when messages array is empty
    8. Auto-scroll to bottom after each message update

    Key patterns:
    - Use `useRef` for textarea (to clear after send)
    - Use `useRef` for messages container (to scroll to bottom)
    - Use `useCallback` for abort ref to cancel in-flight streams on component unmount
    - Immutable message updates: spread array, spread message object
    - Citations: render below AI message content when citations array is non-empty
    - isStreaming: show blinking cursor or "..." indicator

    Rewrite the component (remove static mock messages, keep the UI structure):

    ```jsx
    import React, { useState, useRef, useEffect, useCallback } from 'react';
    import { useTranslation } from 'react-i18next';
    import { streamChat } from '../api/chatApi';
    import './ChatArea.css';

    const ChatArea = ({ settings = {} }) => {
      const { t } = useTranslation();
      const [messages, setMessages] = useState([]);
      const [inputValue, setInputValue] = useState('');
      const [isStreaming, setIsStreaming] = useState(false);
      const messagesEndRef = useRef(null);
      const abortRef = useRef(null);

      const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, []);

      useEffect(() => {
        scrollToBottom();
      }, [messages, scrollToBottom]);

      useEffect(() => {
        return () => {
          if (abortRef.current) abortRef.current();
        };
      }, []);

      const appendToken = useCallback((msgId, token) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === msgId ? { ...msg, text: msg.text + token } : msg
          )
        );
      }, []);

      const finalizeMessage = useCallback((msgId, citations) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === msgId ? { ...msg, isStreaming: false, citations } : msg
          )
        );
        setIsStreaming(false);
      }, []);

      const errorMessage = useCallback((msgId, errorText) => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === msgId
              ? { ...msg, isStreaming: false, text: `[${t('chat.error_prefix')}: ${errorText}]`, citations: [] }
              : msg
          )
        );
        setIsStreaming(false);
      }, [t]);

      const handleSend = useCallback(async () => {
        const text = inputValue.trim();
        if (!text || isStreaming) return;

        const userMsgId = `user-${Date.now()}`;
        const aiMsgId = `ai-${Date.now()}`;

        setMessages((prev) => [
          ...prev,
          { id: userMsgId, role: 'user', text, citations: [], isStreaming: false },
          { id: aiMsgId, role: 'ai', text: '', citations: [], isStreaming: true },
        ]);
        setInputValue('');
        setIsStreaming(true);

        const abort = await streamChat({
          message: text,
          project_id: settings.project_id || null,
          provider: settings.provider || 'gemini',
          api_key: settings.api_key || '',
          temperature: settings.temperature ?? 0.7,
          max_tokens: settings.max_tokens ?? 2048,
          onToken: (token) => appendToken(aiMsgId, token),
          onDone: (citations) => finalizeMessage(aiMsgId, citations),
          onError: (err) => errorMessage(aiMsgId, err),
        });

        abortRef.current = abort;
      }, [inputValue, isStreaming, settings, appendToken, finalizeMessage, errorMessage]);

      const handleKeyDown = useCallback((e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          handleSend();
        }
      }, [handleSend]);

      return (
        <main className="chat-area flex-column">
          <div className="chat-messages flex-column">
            {messages.length === 0 && (
              <div className="empty-state flex-column align-center justify-center">
                <div className="ai-avatar-large">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="url(#gradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <defs>
                      <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#6366f1" />
                        <stop offset="100%" stopColor="#a855f7" />
                      </linearGradient>
                    </defs>
                    <path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"></path>
                    <path d="M21 16v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2"></path>
                    <path d="M12 22a2 2 0 0 1-2-2v-6a2 2 0 0 1 2-2a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2z"></path>
                    <path d="M4 12v-2"></path>
                    <path d="M20 12v-2"></path>
                  </svg>
                </div>
                <h3>{t('chat.welcome_title')}</h3>
                <p>{t('chat.welcome_subtitle')}</p>
              </div>
            )}

            {messages.map((msg) => (
              msg.role === 'user' ? (
                <div key={msg.id} className="message-wrapper user-message flex-row">
                  <div className="message-content">{msg.text}</div>
                </div>
              ) : (
                <div key={msg.id} className="message-wrapper ai-message flex-row">
                  <div className="ai-avatar">AI</div>
                  <div className="message-content">
                    <p>
                      {msg.text}
                      {msg.isStreaming && <span className="streaming-cursor">|</span>}
                    </p>
                    {!msg.isStreaming && msg.citations && msg.citations.length > 0 && (
                      <div className="citations-container">
                        {msg.citations.map((cite, i) => (
                          <div key={i} className="citation flex-row align-center">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>
                            <span>{t('chat.citation_label', { filename: cite.filename, page: cite.page_number })}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )
            ))}
            <div ref={messagesEndRef} />
          </div>

          <div className="chat-input-area">
            <div className="input-wrapper flex-row align-end">
              <button className="btn-icon" title={t('chat.attach_file')}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>
              </button>
              <textarea
                className="chat-input"
                placeholder={t('chat.placeholder')}
                rows="1"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isStreaming}
              />
              <button
                className="btn-icon primary text-color"
                title={t('chat.send')}
                onClick={handleSend}
                disabled={isStreaming || !inputValue.trim()}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
              </button>
            </div>
            <div className="chat-footer-text">{t('chat.footer_disclaimer')}</div>
          </div>
        </main>
      );
    };

    export default ChatArea;
    ```
  </action>
  <verify>
    Manual: ChatArea.jsx contains "streamChat", "settings", "citations", "isStreaming", "ReadableStream" indirectly via chatApi import
  </verify>
  <done>ChatArea.jsx is a stateful component that streams tokens from the backend, renders citations, and accepts settings prop.</done>
</task>

<task type="auto">
  <name>Task 3: Lift settings state to App.jsx and wire SettingsPanel as controlled component</name>
  <files>frontend/src/App.jsx, frontend/src/components/SettingsPanel.jsx</files>
  <action>
    **Step 1: Update App.jsx** to hold shared `settings` state and pass it down to both SettingsPanel and ChatArea.

    ```jsx
    import React, { useState } from 'react'
    import Sidebar from './components/Sidebar'
    import ChatArea from './components/ChatArea'
    import SettingsPanel from './components/SettingsPanel'
    import ArchitectureModal from './components/ArchitectureModal'
    import './App.css'

    const DEFAULT_SETTINGS = {
      provider: 'gemini',
      api_key: '',
      temperature: 0.7,
      max_tokens: 2048,
      project_id: null,
    };

    function App() {
      const [isArchOpen, setIsArchOpen] = useState(false);
      const [settings, setSettings] = useState(DEFAULT_SETTINGS);

      return (
        <div className="app-container">
          <Sidebar onOpenArch={() => setIsArchOpen(true)} />
          <div className="main-content">
            <ChatArea settings={settings} />
            <SettingsPanel settings={settings} onSettingsChange={setSettings} />
          </div>

          <ArchitectureModal
            isOpen={isArchOpen}
            onClose={() => setIsArchOpen(false)}
          />
        </div>
      )
    }

    export default App
    ```

    **Step 2: Update SettingsPanel.jsx** to be a controlled component receiving `settings` and `onSettingsChange` props. Replace `defaultValue` with `value` on all inputs, and call `onSettingsChange` on each change.

    Key changes:
    - Temperature: use `value={settings.temperature}` and `onChange` that calls `onSettingsChange({ ...settings, temperature: parseFloat(e.target.value) })`
    - Max tokens: similar pattern
    - Provider: `value={settings.provider}` on select
    - API key: `value={settings.api_key}` on input
    - Project: `value={settings.project_id ?? 'general'}` on select
    - Remove the Save Settings button (settings are applied live on each change — no save needed for v1)
    - The "Save Settings" button can remain but becomes a no-op confirmation, or remove it entirely

    Rewrite SettingsPanel.jsx:

    ```jsx
    import React from 'react';
    import { useTranslation } from 'react-i18next';
    import './SettingsPanel.css';

    const SettingsPanel = ({ settings = {}, onSettingsChange }) => {
      const { t, i18n } = useTranslation();

      const update = (field, value) => {
        onSettingsChange && onSettingsChange({ ...settings, [field]: value });
      };

      return (
        <aside className="settings-panel flex-column glass-panel">
          <div className="settings-header">
            <h3 className="title">{t('settings.title')}</h3>
          </div>

          <div className="settings-content flex-column">

            <div className="form-group flex-column">
              <label>{t('settings.provider')}</label>
              <select
                className="ui-select"
                value={settings.provider || 'gemini'}
                onChange={(e) => update('provider', e.target.value)}
              >
                <option value="gemini">Google Gemini 1.5 Pro</option>
                <option value="openai">OpenAI GPT-4o</option>
                <option value="claude">Anthropic Claude 3.5</option>
                <option value="ollama">Local Ollama</option>
              </select>
            </div>

            <div className="form-group flex-column">
              <label>{t('settings.api_key')}</label>
              <input
                type="password"
                placeholder="sk-..."
                className="ui-input"
                value={settings.api_key || ''}
                onChange={(e) => update('api_key', e.target.value)}
              />
            </div>

            <div className="form-group flex-column">
              <div className="flex-row justify-between align-center">
                <label>{t('settings.temperature')}</label>
                <span className="value-label">{(settings.temperature ?? 0.7).toFixed(1)}</span>
              </div>
              <input
                type="range"
                className="ui-slider"
                min="0"
                max="2"
                step="0.1"
                value={settings.temperature ?? 0.7}
                onChange={(e) => update('temperature', parseFloat(e.target.value))}
              />
            </div>

            <div className="form-group flex-column">
              <div className="flex-row justify-between align-center">
                <label>{t('settings.max_tokens')}</label>
                <span className="value-label">{settings.max_tokens ?? 2048}</span>
              </div>
              <input
                type="range"
                className="ui-slider"
                min="256"
                max="8192"
                step="256"
                value={settings.max_tokens ?? 2048}
                onChange={(e) => update('max_tokens', parseInt(e.target.value, 10))}
              />
            </div>

            <div className="divider"></div>

            <div className="form-group flex-column">
              <div className="flex-row justify-between align-center">
                <label>{t('settings.target_project')}</label>
              </div>
              <select
                className="ui-select"
                value={settings.project_id ?? 'general'}
                onChange={(e) => update('project_id', e.target.value === 'general' ? null : parseInt(e.target.value, 10))}
              >
                <option value="general">{t('settings.target_general')}</option>
              </select>
              <span className="helper-text">{t('settings.target_hint')}</span>
            </div>

            <div className="divider"></div>

            <div className="form-group flex-column">
              <label>{t('settings.language')}</label>
              <select
                className="ui-select"
                value={i18n.language}
                onChange={(e) => i18n.changeLanguage(e.target.value)}
              >
                <option value="en">{t('settings.language_en')}</option>
                <option value="vi">{t('settings.language_vi')}</option>
              </select>
            </div>

          </div>
        </aside>
      );
    };

    export default SettingsPanel;
    ```
  </action>
  <verify>
    Manual: App.jsx contains "settings" state and passes it to both ChatArea and SettingsPanel. SettingsPanel.jsx uses value= on all inputs.
  </verify>
  <done>Settings state is lifted to App.jsx. SettingsPanel is a controlled component. ChatArea receives settings and uses them in streamChat() calls.</done>
</task>

<task type="auto">
  <name>Task 4: Add i18n keys for streaming states and citation template</name>
  <files>frontend/src/locales/en.json, frontend/src/locales/vi.json, frontend/src/components/ChatArea.css</files>
  <action>
    **Step 1: Update frontend/src/locales/en.json** — add keys used by ChatArea:
    - `chat.streaming` — "Thinking..."
    - `chat.error_prefix` — "Error"
    - `chat.citation_label` — "Source: {{filename}}, Page {{page}}"

    **Step 2: Update frontend/src/locales/vi.json** — add Vietnamese equivalents:
    - `chat.streaming` — "Đang trả lời..."
    - `chat.error_prefix` — "Lỗi"
    - `chat.citation_label` — "Nguồn: {{filename}}, Trang {{page}}"

    **Step 3: Update ChatArea.css** — add streaming cursor animation:
    ```css
    .streaming-cursor {
      display: inline-block;
      animation: blink 1s step-end infinite;
      color: var(--accent-primary);
      margin-left: 2px;
    }

    @keyframes blink {
      0%, 100% { opacity: 1; }
      50% { opacity: 0; }
    }

    .citations-container {
      margin-top: var(--spacing-sm);
      display: flex;
      flex-direction: column;
      gap: var(--spacing-xs);
    }
    ```
  </action>
  <verify>
    Manual: en.json and vi.json contain "citation_label", "streaming", "error_prefix". ChatArea.css contains "streaming-cursor".
  </verify>
  <done>i18n keys for streaming states and citations added. CSS animation for streaming cursor added.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User Input → Chat Request | Message text and settings sent to backend |
| Backend SSE → Frontend | Streaming tokens and citations parsed from SSE |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-4b-01 | Information Disclosure | api_key in SettingsPanel | accept | API key stored only in React state (in-memory), never persisted to localStorage or sent anywhere except to backend; single-user local tool |
| T-4b-02 | Tampering | SSE JSON parsing | mitigate | try/catch around JSON.parse in processChunk; malformed events are silently skipped, stream continues |
| T-4b-03 | Denial of Service | Unaborted streams on unmount | mitigate | useEffect cleanup calls abort() when ChatArea unmounts; AbortController cancels fetch |
</threat_model>

<verification>
After all 4 tasks complete:
1. frontend/src/api/chatApi.js exists and contains "streamChat" and "ReadableStream"
2. frontend/src/components/ChatArea.jsx contains "streamChat", "settings", "citations", "isStreaming"
3. frontend/src/App.jsx contains "DEFAULT_SETTINGS" and passes settings to ChatArea and SettingsPanel
4. frontend/src/components/SettingsPanel.jsx uses "value={settings" (controlled inputs)
5. frontend/src/locales/en.json contains "citation_label" and "streaming"
6. frontend/src/components/ChatArea.css contains "streaming-cursor"
</verification>

<success_criteria>
- SSE client uses fetch + ReadableStream (UI-01)
- Text tokens stream incrementally into message buffer (UI-02)
- Citations render from terminal SSE event with filename and page number (UI-03)
- Settings state (provider, api_key, temperature, max_tokens, project_id) flows from SettingsPanel into each chat request (UI-04)
- No EventSource usage in the codebase
- No static mock messages in ChatArea (replaced by dynamic state)
- Settings are controlled (value= not defaultValue=)
</success_criteria>

<output>
After completion, create `.planning/phases/04B-chat-frontend/04B-01-SUMMARY.md`
</output>
