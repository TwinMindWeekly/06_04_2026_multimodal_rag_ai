# Multimodal RAG Application

This is a generic template project for a Multimodal Retrieval-Augmented Generation (RAG) system. It demonstrates how to build a flexible chat interface supporting multiple AI providers (Gemini, OpenAI, Claude, local Ollama) and various document formats.

**Project Repository:** [https://github.com/TwinMindWeekly/06_04_2026_multimodal_rag_ai](https://github.com/TwinMindWeekly/06_04_2026_multimodal_rag_ai)

## Features

- **Multi-Provider Support:** Switch between Gemini, OpenAI, Claude, and Local Ollama easily.
- **Multimodal Document Processing:** Analyze Text, PDFs, Office Documents, and Images.
- **Multi-language UI:** Support for multiple languages (English, Vietnamese).
- **Project Structure:** Organized tree structure for file management.
- **Modern UI:** Built with React/Vite using a glassmorphism design.

## Structure

- `frontend/`: The React + Vite application.
- `docs/`: Concept documentation and tech stack choices.

## System Architecture

```mermaid
graph TD
    %% Frontend Layer
    subgraph UI ["Frontend (Vite + React)"]
        A[User Interface]
        B[Settings Panel <br> i18n & API Keys]
        A <--> B
    end
    
    %% API Gateway & Backend Layer
    subgraph Backend ["Backend (FastAPI)"]
        C[REST API Gateway]
        D[Router: documents.py]
        E[Router: projects.py]
        C --> D
        C --> E
    end
    
    UI <-->|HTTP/JSON| C
    
    %% Processing & Database Layer
    subgraph Services ["Processing & Database"]
        F[Unstructured.io Parser<br>PDF, Image, Text]
        G[(SQLite DB<br>Projects, Folders)]
        H[(ChromaDB<br>Vector Embeddings)]
    end
    
    D -->|Stores Metadata| G
    E -->|Manages Tree| G
    D -->|Sends File| F
    F -->|Raw Text & Image| H
    
    %% AI Inference Layer
    subgraph LLM ["AI Engine"]
        I[Gemini 1.5 Pro<br>Vision & Text Reasoning]
    end
    
    H <-->|Context Retrieval| I
    I -->|Generated Response| C
```

## Getting Started

1. Navigate to the `frontend` directory.
2. Run `npm install` to install dependencies.
3. Run `npm run dev` to start the frontend.
