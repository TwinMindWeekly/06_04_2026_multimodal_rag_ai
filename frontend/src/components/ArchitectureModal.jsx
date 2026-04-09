import React from 'react';
import { useTranslation } from 'react-i18next';
import './ArchitectureModal.css';

const ArchitectureModal = ({ isOpen, onClose }) => {
  const { t } = useTranslation();

  if (!isOpen) return null;

  return (
    <div className="modal-overlay flex-row align-center justify-center">
      <div className="architecture-modal glass-panel flex-column">
        
        <div className="modal-header flex-row align-center justify-between">
          <h2 className="title text-color">{t('architecture.modal_title')}</h2>
          <button className="btn-icon close-btn" onClick={onClose} title={t('architecture.close')}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div className="modal-body flex-column">
          <p className="description">{t('architecture.description')}</p>
          
          <div className="diagram-container">
            {/* Frontend Layer */}
            <div className="diagram-row">
              <div className="diagram-node ui-node">
                <strong>{t('architecture.frontend')}</strong>
                <span>(Vite, React, Glassmorphism)</span>
              </div>
            </div>

            <div className="diagram-arrow">↓↑</div>
            
            {/* Backend Layer */}
            <div className="diagram-row">
              <div className="diagram-node backend-node">
                <strong>{t('architecture.backend')}</strong>
                <span>(FastAPI, SQLAlchemy, i18n)</span>
              </div>
            </div>

            <div className="diagram-branch flex-row justify-center">
              <div className="arrow-left">↙</div>
              <div className="arrow-right">↘</div>
            </div>
            
            {/* Services Layer */}
            <div className="diagram-row split-row flex-row justify-between">
              <div className="diagram-node parser-node flex-column">
                <strong>{t('architecture.parser')}</strong>
                <span>(Unstructured.io)</span>
                <div className="sub-node mt-sm">↳ {t('architecture.images_text')}</div>
              </div>
              
              <div className="diagram-node db-node flex-column">
                <strong>{t('architecture.database')}</strong>
                <span>(SQLite + ChromaDB Vector)</span>
                <div className="sub-node mt-sm">↳ {t('architecture.metadata_embeds')}</div>
              </div>
            </div>

            <div className="diagram-arrow mt-lg">↓</div>
            
            {/* Inference Layer */}
            <div className="diagram-row">
              <div className="diagram-node ai-node">
                <strong>{t('architecture.ai_engine')}</strong>
                <span>(Gemini 1.5 Pro / LLMs)</span>
                <div className="sub-node mt-sm">{t('architecture.multimodal_reasoning')}</div>
              </div>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
};

export default ArchitectureModal;
