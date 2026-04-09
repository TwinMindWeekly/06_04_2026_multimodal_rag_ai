import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import './ChatArea.css';

const ChatArea = () => {
  const { t } = useTranslation();
  const [messages, setMessages] = useState([]);

  return (
    <main className="chat-area flex-column">
      <div className="chat-messages flex-column">
        
        {/* Helper UI / Empty State */}
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

        {/* Example User Message */}
        <div className="message-wrapper user-message flex-row">
            <div className="message-content">
              {t('chat.user_sample')}
            </div>
        </div>

        {/* Example AI Message */}
        <div className="message-wrapper ai-message flex-row">
          <div className="ai-avatar">AI</div>
          <div className="message-content">
            <p dangerouslySetInnerHTML={{__html: t('chat.ai_sample_heading').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}}></p>
            <ol>
              <li>{t('chat.ai_sample_1')}</li>
              <li>{t('chat.ai_sample_2')}</li>
              <li>{t('chat.ai_sample_3')}</li>
              <li>{t('chat.ai_sample_4')}</li>
              <li>{t('chat.ai_sample_5')}</li>
            </ol>
            <div className="citation flex-row align-center">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="8" y1="6" x2="21" y2="6"></line><line x1="8" y1="12" x2="21" y2="12"></line><line x1="8" y1="18" x2="21" y2="18"></line><line x1="3" y1="6" x2="3.01" y2="6"></line><line x1="3" y1="12" x2="3.01" y2="12"></line><line x1="3" y1="18" x2="3.01" y2="18"></line></svg>
              <span>{t('chat.citation')}</span>
            </div>
          </div>
        </div>

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
          ></textarea>
          <button className="btn-icon primary text-color" title={t('chat.send')}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
          </button>
        </div>
        <div className="chat-footer-text">{t('chat.footer_disclaimer')}</div>
      </div>
    </main>
  );
};

export default ChatArea;
