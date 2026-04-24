"""
Scan Task Model.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON

from backend.app.database import Base


class ScanTask(Base):
    """Scan task database model."""
    __tablename__ = "scan_tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)
    urls = Column(JSON, nullable=False)
    total_urls = Column(Integer, default=0)
    completed_urls = Column(Integer, default=0)
    status = Column(String(32), default="pending")
    progress = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    config = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "name": self.name,
            "urls": self.urls,
            "total_urls": self.total_urls,
            "completed_urls": self.completed_urls,
            "status": self.status,
            "progress": self.progress,
            "error_message": self.error_message,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
