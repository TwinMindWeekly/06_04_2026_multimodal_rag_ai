from dotenv import load_dotenv
load_dotenv()  # Must be BEFORE app.core imports so DATABASE_PATH/CHROMADB_PATH env vars are available

import shutil
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine, Base
from app.models import domain  # noqa: F401 -- registers models with Base

logger = logging.getLogger(__name__)


def probe_system_dependencies() -> None:
    """Check for system binaries needed by document parsing.
    Per D-07: WARNING log only, does NOT block server startup.
    """
    missing: list[str] = []
    if not shutil.which("pdfinfo"):
        missing.append("poppler (pdfinfo)")
    if not shutil.which("tesseract"):
        missing.append("tesseract")

    if missing:
        logger.warning(
            "System dependencies not found: %s. "
            "PDF parsing will fail when documents are processed. "
            "Install missing tools and restart the server.",
            ", ".join(missing),
        )


# Probe at startup -- warning only
probe_system_dependencies()

# Create database tables
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

from app.routers import projects, documents, search  # noqa: E402

app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(search.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Multimodal RAG Backend API!"}
