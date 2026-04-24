"""
Rule Model.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON

from backend.app.database import Base


class Rule(Base):
    """Technology detection rule database model."""
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(128), unique=True, index=True, nullable=False)
    slug = Column(String(128), index=True, nullable=True)

    description = Column(Text, nullable=True)
    website = Column(String(512), nullable=True)
    categories = Column(JSON, default=list)
    icons = Column(JSON, default=dict)
    confidence = Column(Integer, default=100)

    rules = Column(JSON, default=dict)

    version = Column(String(32), nullable=True)
    file_path = Column(String(512), nullable=True)
    file_hash = Column(String(64), nullable=True)

    is_enabled = Column(Boolean, default=True)
    is_builtin = Column(Boolean, default=True)

    loaded_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "website": self.website,
            "categories": self.categories,
            "icons": self.icons,
            "confidence": self.confidence,
            "rules": self.rules,
            "version": self.version,
            "file_path": self.file_path,
            "file_hash": self.file_hash,
            "is_enabled": self.is_enabled,
            "is_builtin": self.is_builtin,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
