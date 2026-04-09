import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { getProjects } from '../api/projectApi';
import { uploadDocument } from '../api/documentApi';
import './Sidebar.css';

const Sidebar = ({ onOpenArch }) => {
  const { t } = useTranslation();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const data = await getProjects();
      setProjects(data);
    } catch (error) {
      console.error("Failed to fetch projects", error);
    } finally {
      setLoading(false);
    }
  };

  const handleUploadClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFileChange = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    try {
      setUploading(true);
      // We upload to root for now (no project_id specific parsing logic yet)
      await uploadDocument(file, null, null);
      alert("Upload successful!");
      // Option to refresh document list inside projects here
      fetchProjects();
    } catch (error) {
      console.error("Upload error", error);
      alert(error.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
      // reset input
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };
  return (
    <aside className="sidebar flex-column glass-panel">
      <div className="sidebar-header flex-row align-center justify-between">
        <h2 className="title">Multimodal RAG</h2>
        <button className="btn-icon" title="New Chat">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </button>
      </div>

      <div className="sidebar-content flex-column">
        { /* Project Trees Placeholder */ }
        <div className="section-title">{t('sidebar.projects_title')}</div>
        {loading ? (
          <div style={{ padding: '0 10px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>Loading...</div>
        ) : (
          projects.length > 0 ? projects.map(proj => (
            <div key={proj.id} className="tree-item flex-row align-center">
              <svg className="folder-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
              <span className="truncate">{proj.name}</span>
            </div>
          )) : (
            <>
              <div className="tree-item active flex-row align-center">
                <svg className="folder-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
                <span className="truncate">{t('sidebar.general_project')}</span>
              </div>
            </>
          )
        )}
        
        <div className="section-title mt-lg">{t('sidebar.recent_chats')}</div>
        <div className="chat-history-item flex-row align-center">
          <svg className="msg-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
          <span className="truncate">{t('sidebar.chat_history_1')}</span>
        </div>
        <div className="chat-history-item flex-row align-center">
          <svg className="msg-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
          <span className="truncate">{t('sidebar.chat_history_2')}</span>
        </div>
      </div>

      <div className="sidebar-footer flex-column">
        <button 
          className="arch-btn flex-row align-center justify-center mt-md"
          onClick={onOpenArch}
          style={{ marginBottom: '10px', background: 'rgba(255,255,255,0.1)', color: 'var(--text-muted)' }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{marginRight: '8px'}}><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="9" y1="3" x2="9" y2="21"></line><line x1="9" y1="12" x2="21" y2="12"></line></svg>
          {t('architecture.view_btn')}
        </button>

        <button 
          className="upload-btn flex-row align-center justify-center"
          onClick={handleUploadClick}
          disabled={uploading}
        >
          {uploading ? (
             <span className="truncate">Uploading...</span>
          ) : (
            <>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{marginRight: '8px'}}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
              {t('sidebar.upload_btn')}
            </>
          )}
        </button>
        <input 
          type="file" 
          ref={fileInputRef} 
          style={{ display: 'none' }} 
          onChange={handleFileChange}
        />
      </div>
    </aside>
  );
};

export default Sidebar;
