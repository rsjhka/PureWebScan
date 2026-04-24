"""
Pydantic Schemas for API Request/Response.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class ScanTaskCreate(BaseModel):
    """Schema for creating a scan task."""
    name: Optional[str] = Field(None, max_length=255, description="Task name")
    urls: List[str] = Field(..., min_length=1, description="List of URLs to scan")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Scan configuration")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "My Scan Task",
                "urls": ["https://example.com"],
                "config": {
                    "timeout": 10,
                    "max_retries": 3
                }
            }
        }


class ScanTaskUpdate(BaseModel):
    """Schema for updating a scan task."""
    name: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = None


class ScanTaskResponse(BaseModel):
    """Schema for scan task response."""
    id: int
    task_id: str
    name: Optional[str]
    urls: List[str]
    total_urls: int
    completed_urls: int
    status: str
    progress: int
    error_message: Optional[str]
    config: Optional[Dict[str, Any]]
    created_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ScanResultResponse(BaseModel):
    """Schema for scan result response."""
    id: int
    task_id: str
    url: str
    base_domain: Optional[str]
    status_code: Optional[int]
    content_type: Optional[str]
    server: Optional[str]
    powered_by: Optional[str]
    technologies: List[Dict[str, Any]]
    technology_count: int
    headers: Optional[Dict[str, str]]
    cookies: Optional[Dict[str, str]]
    error_message: Optional[str]
    scan_duration: Optional[int]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class TechnologyInfo(BaseModel):
    """Schema for technology information."""
    name: str
    slug: str
    description: Optional[str]
    website: Optional[str]
    categories: List[Dict[str, Any]]
    icons: Dict[str, Any]
    confidence: int
    version: Optional[str]


class RuleCreate(BaseModel):
    """Schema for creating a rule."""
    name: str = Field(..., min_length=1)
    slug: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    categories: List[Dict[str, Any]] = []
    icons: Dict[str, Any] = {}
    rules: Dict[str, Any] = {}


class RuleResponse(BaseModel):
    """Schema for rule response."""
    id: int
    name: str
    slug: Optional[str]
    description: Optional[str]
    website: Optional[str]
    categories: List[Dict[str, Any]]
    icons: Dict[str, Any]
    confidence: int
    rules: Dict[str, Any]
    version: Optional[str]
    file_path: Optional[str]
    is_enabled: bool
    is_builtin: bool
    loaded_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class StatisticsResponse(BaseModel):
    """Schema for statistics response."""
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    running_tasks: int
    total_urls_scanned: int
    total_technologies_detected: int
    unique_domains: int


class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    version: str
    database_connected: bool
    rules_loaded: int
    uptime: float


class ErrorResponse(BaseModel):
    """Schema for error response."""
    detail: str
    error_code: Optional[str] = None
