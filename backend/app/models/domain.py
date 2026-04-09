from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    folders = relationship("Folder", back_populates="project", cascade="all, delete-orphan")

class Folder(Base):
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    parent_id = Column(Integer, ForeignKey("folders.id"), nullable=True)

    project = relationship("Project", back_populates="folders")
    # Tự liên kết để tạo cây thư mục lồng nhau
    subfolders = relationship("Folder", backref="parent", remote_side=[id])
    documents = relationship("Document", back_populates="folder", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    file_path = Column(String)
    folder_id = Column(Integer, ForeignKey("folders.id"))
    metadata_json = Column(String, nullable=True) # Lưu json metadata dưới dạng string
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending", nullable=False)

    folder = relationship("Folder", back_populates="documents")
