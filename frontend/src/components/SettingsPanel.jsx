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
            <span className="value-label">{(settings.temperature != null ? settings.temperature : 0.7).toFixed(1)}</span>
          </div>
          <input
            type="range"
            className="ui-slider"
            min="0"
            max="2"
            step="0.1"
            value={settings.temperature != null ? settings.temperature : 0.7}
            onChange={(e) => update('temperature', parseFloat(e.target.value))}
          />
        </div>

        <div className="form-group flex-column">
          <div className="flex-row justify-between align-center">
            <label>{t('settings.max_tokens')}</label>
            <span className="value-label">{settings.max_tokens != null ? settings.max_tokens : 2048}</span>
          </div>
          <input
            type="range"
            className="ui-slider"
            min="256"
            max="8192"
            step="256"
            value={settings.max_tokens != null ? settings.max_tokens : 2048}
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
            value={settings.project_id != null ? settings.project_id : 'general'}
            onChange={(e) =>
              update('project_id', e.target.value === 'general' ? null : parseInt(e.target.value, 10))
            }
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
