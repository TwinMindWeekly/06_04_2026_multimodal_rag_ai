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
        <ChatArea selectedProjectId={settings.project_id} settings={settings} />
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
