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

  // Cancel in-flight stream on component unmount
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

  const errorMessage = useCallback(
    (msgId, errorText) => {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === msgId
            ? {
                ...msg,
                isStreaming: false,
                text: `[${t('chat.error_prefix')}: ${errorText}]`,
                citations: [],
              }
            : msg
        )
      );
      setIsStreaming(false);
    },
    [t]
  );

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
      temperature: settings.temperature != null ? settings.temperature : 0.7,
      max_tokens: settings.max_tokens != null ? settings.max_tokens : 2048,
      onToken: (token) => appendToken(aiMsgId, token),
      onDone: (citations) => finalizeMessage(aiMsgId, citations),
      onError: (err) => errorMessage(aiMsgId, err),
    });

    abortRef.current = abort;
  }, [inputValue, isStreaming, settings, appendToken, finalizeMessage, errorMessage]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  return (
    <main className="chat-area flex-column">
      <div className="chat-messages flex-column">
        {messages.length === 0 && (
          <div className="empty-state flex-column align-center justify-center">
            <div className="ai-avatar-large">
              <svg
                width="32"
                height="32"
                viewBox="0 0 24 24"
                fill="none"
                stroke="url(#gradient)"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
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

        {messages.map((msg) =>
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
                  {msg.isStreaming && (
                    <span className="streaming-cursor" aria-label={t('chat.streaming')}>
                      |
                    </span>
                  )}
                </p>
                {!msg.isStreaming && msg.citations && msg.citations.length > 0 && (
                  <div className="citations-container">
                    {msg.citations.map((cite, i) => (
                      <div key={i} className="citation flex-row align-center">
                        <svg
                          width="12"
                          height="12"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <line x1="8" y1="6" x2="21" y2="6"></line>
                          <line x1="8" y1="12" x2="21" y2="12"></line>
                          <line x1="8" y1="18" x2="21" y2="18"></line>
                          <line x1="3" y1="6" x2="3.01" y2="6"></line>
                          <line x1="3" y1="12" x2="3.01" y2="12"></line>
                          <line x1="3" y1="18" x2="3.01" y2="18"></line>
                        </svg>
                        <span>
                          {t('chat.citation_label', {
                            filename: cite.filename,
                            page: cite.page_number,
                          })}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <div className="input-wrapper flex-row align-end">
          <button className="btn-icon" title={t('chat.attach_file')}>
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
            </svg>
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
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </div>
        <div className="chat-footer-text">{t('chat.footer_disclaimer')}</div>
      </div>
    </main>
  );
};

export default ChatArea;
