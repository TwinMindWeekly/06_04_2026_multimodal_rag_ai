import React, { useState } from 'react'
import Sidebar from './components/Sidebar'
import ChatArea from './components/ChatArea'
import SettingsPanel from './components/SettingsPanel'
import ArchitectureModal from './components/ArchitectureModal'
import './App.css'

function App() {
  const [isArchOpen, setIsArchOpen] = useState(false);

  return (
    <div className="app-container">
      <Sidebar onOpenArch={() => setIsArchOpen(true)} />
      <div className="main-content">
        <ChatArea />
        <SettingsPanel />
      </div>
      
      <ArchitectureModal 
        isOpen={isArchOpen} 
        onClose={() => setIsArchOpen(false)} 
      />
    </div>
  )
}

export default App
