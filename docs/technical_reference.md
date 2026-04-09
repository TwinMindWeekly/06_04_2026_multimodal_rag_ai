# Technical Reference & System Architecture

## Current Features
1. **Premium Modern UI**: Built with React + Vite using Glassmorphism design and smooth animations (`main.css`). 
2. **Internationalization (i18n)**: Fully supports English (`en`) and Vietnamese (`vi`). Instantly switchable via the Settings menu without reloading the page.
3. **Multimodal API Backend**: A FastAPI server constructed to ingest diverse document types (PDFs, PPTX) robustly.
4. **Document Parser Pipeline**: Integrated with `unstructured.io` to parse document text and extract image components into a local folder format to prepare them for Vector Embeddings.
5. **Relational Database**: Uses SQLite & SQLAlchemy for hierarchical tracking of Projects, Folders, and Documents to ensure all uploads have complete metadata.

## File Hierarchy and Responsibilities

### Frontend (`frontend/`)
- `src/App.jsx`: Main UI application orchestrator binding the Sidebar, Chat Area, and Settings Panel.
- `src/components/Sidebar.jsx`: Component for the left sidebar handling Tree Navigation (Projects/Folders), Recent Chats, and the main Upload button.
- `src/components/ChatArea.jsx`: Center interface displaying conversational messages, document citations, and handling user input.
- `src/components/SettingsPanel.jsx`: Right contextual panel for tuning ML model parameters (Max Tokens, Provider, Temperature) and changing the overall UI language.
- `src/components/ArchitectureModal.jsx`: Explanatory UI modal showing the block architecture of the platform.
- `src/i18n.js` & `src/locales/`: Contains global dictionary configurations.

### Backend (`backend/`)
- `app/main.py`: The entrypoint declaring the FastAPI application and registering routers.
- `app/core/i18n.py`: Request-level middleware that inspects HTTP headers (`Accept-Language`) and provides a localized dictionary for API error handling.
- `app/core/database.py`: SQLAlchemy and SQLite connections bindings. 
- `app/models/domain.py`: Database table descriptions mapped directly into python objects via ORM `declarative_base`.
- `app/schemas/domain.py`: Pydantic definitions strictly enforcing JSON schema validation upon incoming HTTP requests and outputs.
- `app/routers/`: Individual API routing classes (projects, documents) enforcing RESTful logic.
- `app/services/document_parser.py`: Implementation of `unstructured` auto-partioning logic to break files down into manageable semantic chunks + image outputs.
