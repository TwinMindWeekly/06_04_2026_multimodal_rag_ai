from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.models import domain

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Multimodal RAG API")

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import projects, documents

app.include_router(projects.router)
app.include_router(documents.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Multimodal RAG Backend API!"}
