"""
Scan Result Model.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from backend.app.database import Base


class ScanResult(Base):
    """Scan result database model."""
    __tablename__ = "scan_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(String(64), ForeignKey("scan_tasks.task_id"), nullable=False, index=True)
    url = Column(String(2048), nullable=False, index=True)
    base_domain = Column(String(512), nullable=True, index=True)

    status_code = Column(Integer, nullable=True)
    content_type = Column(String(128), nullable=True)
    server = Column(String(256), nullable=True)
    powered_by = Column(String(256), nullable=True)

    technologies = Column(JSON, default=list)
    technology_count = Column(Integer, default=0)

    headers = Column(JSON, nullable=True)
    cookies = Column(JSON, nullable=True)
    html_content = Column(Text, nullable=True)

    error_message = Column(Text, nullable=True)
    scan_duration = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.now, index=True)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "url": self.url,
            "base_domain": self.base_domain,
            "status_code": self.status_code,
            "content_type": self.content_type,
            "server": self.server,
            "powered_by": self.powered_by,
            "technologies": self.technologies,
            "technology_count": self.technology_count,
            "headers": self.headers,
            "cookies": self.cookies,
            "error_message": self.error_message,
            "scan_duration": self.scan_duration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
