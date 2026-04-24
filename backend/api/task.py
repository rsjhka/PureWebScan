"""
Task API Routes.
Handles scan task creation, status, and management.
"""
import asyncio
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.dependencies import get_scan_manager, get_settings_dep
from backend.core.scanner import ScanTaskManager
from backend.models.task import ScanTask
from backend.models.result import ScanResult
from backend.schemas.schemas import (
    ScanTaskCreate,
    ScanTaskUpdate,
    ScanTaskResponse,
    StatisticsResponse
)
from backend.app.config import Settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/statistics/summary")
async def get_statistics(
    db: Session = Depends(get_db)
):
    """Get scanning statistics using database aggregation."""
    from sqlalchemy import func, case

    # Use database aggregation instead of loading all records
    task_stats = db.query(
        func.count(ScanTask.id).label("total"),
        func.sum(case((ScanTask.status == "completed", 1), else_=0)).label("completed"),
        func.sum(case((ScanTask.status == "failed", 1), else_=0)).label("failed"),
        func.sum(case((ScanTask.status == "running", 1), else_=0)).label("running")
    ).first()

    # Use subquery for aggregated counts
    total_urls = db.query(func.count(ScanResult.id)).scalar() or 0
    unique_domains = db.query(func.count(func.distinct(ScanResult.base_domain))).scalar() or 0

    # Aggregate technologies count from database
    results_with_techs = db.query(ScanResult.technologies).filter(
        ScanResult.technologies != None,
        ScanResult.technologies != []
    ).all()

    total_technologies = sum(
        len(r.technologies) for r in results_with_techs
        if r.technologies
    )

    return StatisticsResponse(
        total_tasks=task_stats.total or 0,
        completed_tasks=task_stats.completed or 0,
        failed_tasks=task_stats.failed or 0,
        running_tasks=task_stats.running or 0,
        total_urls_scanned=total_urls,
        total_technologies_detected=total_technologies,
        unique_domains=unique_domains
    )


@router.post("/", response_model=ScanTaskResponse)
async def create_task(
    task_data: ScanTaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    scan_manager: ScanTaskManager = Depends(get_scan_manager),
    settings: Settings = Depends(get_settings_dep)
):
    """Create a new scan task."""
    try:
        task_id = scan_manager.create_task(
            urls=task_data.urls,
            config=task_data.config,
            name=task_data.name
        )

        db_task = ScanTask(
            task_id=task_id,
            name=task_data.name,
            urls=task_data.urls,
            total_urls=len(task_data.urls),
            config=task_data.config,
            status="pending"
        )
        db.add(db_task)
        db.commit()
        db.refresh(db_task)

        background_tasks.add_task(scan_manager.start_task, task_id)

        db_task.status = "running"
        db_task.started_at = datetime.now()
        db.commit()

        return db_task

    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[ScanTaskResponse])
async def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all scan tasks."""
    query = db.query(ScanTask)

    if status:
        query = query.filter(ScanTask.status == status)

    tasks = query.order_by(ScanTask.created_at.desc()).offset(skip).limit(limit).all()
    return tasks


@router.get("/{task_id}", response_model=ScanTaskResponse)
async def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    scan_manager: ScanTaskManager = Depends(get_scan_manager)
):
    """Get task details."""
    db_task = db.query(ScanTask).filter(ScanTask.task_id == task_id).first()

    if not db_task:
        task_status = scan_manager.get_task_status(task_id)
        if task_status:
            return task_status
        raise HTTPException(status_code=404, detail="Task not found")

    live_status = scan_manager.get_task_status(task_id)
    if live_status and live_status["status"] == "running":
        db_task.progress = live_status["progress"]
        db_task.completed_urls = live_status["completed_urls"]
        db_task.status = live_status["status"]

    return db_task


@router.get("/{task_id}/status")
async def get_task_status(
    task_id: str,
    scan_manager: ScanTaskManager = Depends(get_scan_manager)
):
    """Get live task status."""
    status = scan_manager.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return status


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    scan_manager: ScanTaskManager = Depends(get_scan_manager),
    db: Session = Depends(get_db)
):
    """Cancel a running task."""
    success = scan_manager.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel task")

    db_task = db.query(ScanTask).filter(ScanTask.task_id == task_id).first()
    if db_task:
        db_task.status = "cancelled"
        db_task.completed_at = datetime.now()
        db.commit()

    return {"message": "Task cancelled"}


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    scan_manager: ScanTaskManager = Depends(get_scan_manager),
    db: Session = Depends(get_db)
):
    """Delete a task and its results."""
    db_task = db.query(ScanTask).filter(ScanTask.task_id == task_id).first()

    if not db_task:
        success = scan_manager.delete_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"message": "Task deleted from memory"}

    db.query(ScanResult).filter(ScanResult.task_id == task_id).delete()
    db.delete(db_task)
    db.commit()

    scan_manager.delete_task(task_id)

    return {"message": "Task deleted"}
