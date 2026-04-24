"""
Result API Routes.
Handles scan result queries and management.
"""
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.database import get_db
from backend.app.dependencies import get_scan_manager
from backend.core.scanner import ScanTaskManager
from backend.models.task import ScanTask
from backend.models.result import ScanResult
from backend.schemas.schemas import ScanResultResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/results", tags=["results"])


@router.get("/", response_model=List[ScanResultResponse])
async def list_results(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    task_id: Optional[str] = None,
    domain: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List scan results with optional filtering."""
    query = db.query(ScanResult)

    if task_id:
        query = query.filter(ScanResult.task_id == task_id)

    if domain:
        query = query.filter(ScanResult.base_domain.like(f"%{domain}%"))

    results = query.order_by(desc(ScanResult.created_at)).offset(skip).limit(limit).all()
    return results


@router.get("/{result_id}", response_model=ScanResultResponse)
async def get_result(
    result_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific scan result."""
    result = db.query(ScanResult).filter(ScanResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result


@router.get("/by-url/{url:path}")
async def get_result_by_url(
    url: str,
    db: Session = Depends(get_db)
):
    """Get the most recent scan result for a URL."""
    result = db.query(ScanResult).filter(
        ScanResult.url == url
    ).order_by(desc(ScanResult.created_at)).first()

    if not result:
        raise HTTPException(status_code=404, detail="No result found for this URL")
    return result


@router.get("/technologies/list")
async def list_technologies(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all detected technologies across all scans using aggregation."""
    from sqlalchemy import func

    # Use SQL aggregation for better performance
    results = db.query(ScanResult.technologies).filter(
        ScanResult.technologies != None,
        ScanResult.technologies != []
    ).all()

    tech_count = {}
    for result in results:
        if result.technologies:
            for tech in result.technologies:
                name = tech.get("name", "Unknown")
                if name not in tech_count:
                    tech_count[name] = {
                        "name": name,
                        "slug": tech.get("slug", name.lower().replace(" ", "-")),
                        "count": 0,
                        "categories": tech.get("categories", [])
                    }
                tech_count[name]["count"] += 1

    tech_list = sorted(tech_count.values(), key=lambda x: x["count"], reverse=True)

    if category:
        tech_list = [
            t for t in tech_list
            if any(c.get("slug") == category for c in t.get("categories", []))
        ]

    return tech_list[skip:skip + limit]


@router.get("/technologies/{tech_name}")
async def get_technology_details(
    tech_name: str,
    db: Session = Depends(get_db)
):
    """Get details about a specific technology."""
    # Filter in database to reduce memory usage
    results = db.query(ScanResult).filter(
        ScanResult.technologies != None
    ).all()

    occurrences = []
    for result in results:
        if result.technologies:
            for tech in result.technologies:
                if tech.get("name") == tech_name:
                    occurrences.append({
                        "url": result.url,
                        "domain": result.base_domain,
                        "confidence": tech.get("confidence", 0),
                        "version": tech.get("version"),
                        "scan_date": result.created_at.isoformat() if result.created_at else None
                    })

    if not occurrences:
        raise HTTPException(status_code=404, detail="Technology not found in any scan results")

    return {
        "name": tech_name,
        "total_detections": len(occurrences),
        "occurrences": occurrences
    }


@router.delete("/{result_id}")
async def delete_result(
    result_id: int,
    db: Session = Depends(get_db)
):
    """Delete a specific scan result."""
    result = db.query(ScanResult).filter(ScanResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    db.delete(result)
    db.commit()

    return {"message": "Result deleted successfully"}


@router.delete("/task/{task_id}")
async def delete_task_results(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Delete all results for a specific task."""
    deleted = db.query(ScanResult).filter(ScanResult.task_id == task_id).delete()
    db.commit()

    return {
        "message": f"Deleted {deleted} results for task {task_id}",
        "deleted_count": deleted
    }


@router.get("/domains/list")
async def list_domains(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List all scanned domains."""
    from sqlalchemy import func

    results = db.query(
        ScanResult.base_domain,
        func.count(ScanResult.id).label("scan_count"),
        func.max(ScanResult.created_at).label("last_scan")
    ).group_by(ScanResult.base_domain).all()

    domains = [
        {
            "domain": r.base_domain,
            "scan_count": r.scan_count,
            "last_scan": r.last_scan.isoformat() if r.last_scan else None
        }
        for r in results
    ]

    return domains[skip:skip + limit]


@router.get("/export/{task_id}")
async def export_task_results(
    task_id: str,
    format: str = Query("json", regex="^(json|csv)$"),
    db: Session = Depends(get_db)
):
    """Export scan results for a task."""
    results = db.query(ScanResult).filter(ScanResult.task_id == task_id).all()

    if not results:
        raise HTTPException(status_code=404, detail="No results found for this task")

    if format == "json":
        return {
            "task_id": task_id,
            "total_results": len(results),
            "results": [r.to_dict() for r in results]
        }
    else:
        csv_lines = ["URL,Domain,Status,Technologies,Technologies Count,Scan Date"]

        for r in results:
            techs = "; ".join([t.get("name", "") for t in (r.technologies or [])])
            csv_lines.append(
                f'"{r.url}","{r.base_domain}","{r.status_code}","{techs}",{r.technology_count},"{r.created_at}"'
            )

        return {"format": "csv", "data": "\n".join(csv_lines)}
