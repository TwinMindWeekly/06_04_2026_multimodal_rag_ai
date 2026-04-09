import React from 'react';
import './SettingsPanel.css';

const SettingsPanel = () => {
  return (
    <aside className="settings-panel flex-column glass-panel">
      <div className="settings-header">
        <h3 className="title">Model Settings</h3>
      </div>
      
      <div className="settings-content flex-column">
        
        <div className="form-group flex-column">
          <label>AI Provider</label>
          <select className="ui-select" defaultValue="gemini">
            <option value="gemini">Google Gemini 1.5 Pro</option>
            <option value="openai">OpenAI GPT-4o</option>
            <option value="claude">Anthropic Claude 3.5</option>
            <option value="ollama">Local Ollama</option>
          </select>
        </div>

        <div className="form-group flex-column">
          <label>API Key / Base URL</label>
          <input type="password" placeholder="sk-..." className="ui-input" />
        </div>

        <div className="form-group flex-column">
          <div className="flex-row justify-between align-center">
            <label>Temperature</label>
            <span className="value-label">0.7</span>
          </div>
          <input type="range" className="ui-slider" min="0" max="2" step="0.1" defaultValue="0.7" />
        </div>

        <div className="form-group flex-column">
          <div className="flex-row justify-between align-center">
            <label>Max Tokens</label>
            <span className="value-label">2048</span>
          </div>
          <input type="range" className="ui-slider" min="256" max="8192" step="256" defaultValue="2048" />
        </div>

        <div className="divider"></div>

        <div className="form-group flex-column">
          <div className="flex-row justify-between align-center">
            <label>Target Project</label>
          </div>
          <select className="ui-select" defaultValue="general">
            <option value="general">General Project Framework</option>
          </select>
          <span className="helper-text">Changes which Vector DB is queried during chat.</span>
        </div>

        <button className="primary-btn mt-lg">Save Settings</button>
      </div>
    </aside>
  );
};

export default SettingsPanel;
