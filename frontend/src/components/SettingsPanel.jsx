import React from 'react';
import { useTranslation } from 'react-i18next';
import './SettingsPanel.css';

const SettingsPanel = () => {
  const { t, i18n } = useTranslation();
  return (
    <aside className="settings-panel flex-column glass-panel">
      <div className="settings-header">
        <h3 className="title">{t('settings.title')}</h3>
      </div>
      
      <div className="settings-content flex-column">
        
        <div className="form-group flex-column">
          <label>{t('settings.provider')}</label>
          <select className="ui-select" defaultValue="gemini">
            <option value="gemini">Google Gemini 1.5 Pro</option>
            <option value="openai">OpenAI GPT-4o</option>
            <option value="claude">Anthropic Claude 3.5</option>
            <option value="ollama">Local Ollama</option>
          </select>
        </div>

        <div className="form-group flex-column">
          <label>{t('settings.api_key')}</label>
          <input type="password" placeholder="sk-..." className="ui-input" />
        </div>

        <div className="form-group flex-column">
          <div className="flex-row justify-between align-center">
            <label>{t('settings.temperature')}</label>
            <span className="value-label">0.7</span>
          </div>
          <input type="range" className="ui-slider" min="0" max="2" step="0.1" defaultValue="0.7" />
        </div>

        <div className="form-group flex-column">
          <div className="flex-row justify-between align-center">
            <label>{t('settings.max_tokens')}</label>
            <span className="value-label">2048</span>
          </div>
          <input type="range" className="ui-slider" min="256" max="8192" step="256" defaultValue="2048" />
        </div>

        <div className="divider"></div>

        <div className="form-group flex-column">
          <div className="flex-row justify-between align-center">
            <label>{t('settings.target_project')}</label>
          </div>
          <select className="ui-select" defaultValue="general">
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

        <button className="primary-btn mt-lg">{t('settings.save_btn')}</button>
      </div>
    </aside>
  );
};

export default SettingsPanel;
