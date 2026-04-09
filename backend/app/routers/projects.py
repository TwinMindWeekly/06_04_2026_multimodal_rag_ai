from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.i18n import get_language, t
from app.models.domain import Project, Folder
from app.schemas.domain import ProjectCreate, ProjectResponse, FolderCreate, FolderResponse

router = APIRouter(prefix="/api/projects", tags=["projects"])

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    db_project = Project(name=project.name)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@router.get("/", response_model=List[ProjectResponse])
def get_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Project).offset(skip).limit(limit).all()

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db), lang: str = Depends(get_language)):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail=t("errors.project_not_found", lang))
    db.delete(db_project)
    db.commit()
    return None

@router.post("/{project_id}/folders", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
def create_folder(project_id: int, folder: FolderCreate, db: Session = Depends(get_db), lang: str = Depends(get_language)):
    # Verify project exists
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail=t("errors.project_not_found", lang))
        
    db_folder = Folder(name=folder.name, project_id=project_id, parent_id=folder.parent_id)
    db.add(db_folder)
    db.commit()
    db.refresh(db_folder)
    return db_folder

@router.get("/{project_id}/folders", response_model=List[FolderResponse])
def get_folders(project_id: int, db: Session = Depends(get_db)):
    return db.query(Folder).filter(Folder.project_id == project_id).all()
