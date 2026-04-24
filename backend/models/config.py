"""
Application Configuration Model.
"""
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON

from backend.app.database import Base


class AppConfig(Base):
    """Application configuration storage model."""
    __tablename__ = "app_config"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(128), unique=True, index=True, nullable=False)
    value = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
