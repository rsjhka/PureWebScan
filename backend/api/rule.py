"""
Rule API Routes.
Handles rule file management and queries.
"""
import os
import logging
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.dependencies import get_rule_parser, reset_rule_parser
from backend.core.wappalyzer.parser import WappalyzerRuleParser
from backend.models.rule import Rule
from backend.schemas.schemas import RuleResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("/", response_model=List[dict])
async def list_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    category: Optional[str] = None,
    search: Optional[str] = None,
    parser: WappalyzerRuleParser = Depends(get_rule_parser)
):
    """List all loaded rules."""
    rules = parser.get_all_rules()

    result = []
    for name, rule in rules.items():
        if category:
            if not any(cat.get("slug") == category for cat in rule.categories):
                continue

        if search:
            if search.lower() not in name.lower() and search.lower() not in (rule.description or "").lower():
                continue

        result.append({
            "name": rule.name,
            "slug": rule.slug,
            "description": rule.description,
            "website": rule.website,
            "categories": rule.categories,
            "icons": rule.icons,
            "confidence": rule.confidence,
            "version": rule.version
        })

    return result[skip:skip + limit]


@router.get("/categories")
async def list_categories(
    parser: WappalyzerRuleParser = Depends(get_rule_parser)
):
    """List all technology categories."""
    return [
        {"id": cat_id, **cat_info}
        for cat_id, cat_info in parser.categories.items()
    ]


@router.get("/{rule_name}", response_model=dict)
async def get_rule(
    rule_name: str,
    parser: WappalyzerRuleParser = Depends(get_rule_parser)
):
    """Get a specific rule by name."""
    rule = parser.get_rule(rule_name)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return {
        "name": rule.name,
        "slug": rule.slug,
        "description": rule.description,
        "website": rule.website,
        "categories": rule.categories,
        "icons": rule.icons,
        "confidence": rule.confidence,
        "version": rule.version,
        "raw_rules": rule.raw_rules
    }


@router.post("/upload")
async def upload_rules(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload rule files."""
    parser = get_rule_parser()

    saved_files = []
    for file in files:
        if not file.filename.endswith((".json", ".yml", ".yaml")):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.filename}. Only .json, .yml, .yaml are supported."
            )

        try:
            contents = await file.read()

            rules_dir = Path("rules")
            if not rules_dir.exists():
                rules_dir.mkdir(parents=True, exist_ok=True)

            filepath = rules_dir / file.filename
            with open(filepath, "wb") as f:
                f.write(contents)

            parser.load_rule_file(str(filepath))
            saved_files.append(file.filename)

        except Exception as e:
            logger.error(f"Failed to save rule file {file.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save {file.filename}: {str(e)}")

    reset_rule_parser()
    parser = get_rule_parser()

    return {
        "message": f"Successfully uploaded {len(saved_files)} rule files",
        "saved_files": saved_files,
        "total_rules": len(parser.rules)
    }


@router.post("/reload")
async def reload_rules():
    """Reload all rules from disk."""
    reset_rule_parser()
    parser = get_rule_parser()
    count = parser.reload_rules()

    return {
        "message": "Rules reloaded successfully",
        "total_rules": count
    }


@router.delete("/{rule_name}")
async def delete_custom_rule(
    rule_name: str,
    db: Session = Depends(get_db)
):
    """Delete a custom rule file."""
    rules_dir = Path("rules")

    for ext in [".json", ".yml", ".yaml"]:
        filepath = rules_dir / f"{rule_name}{ext}"
        if filepath.exists():
            try:
                os.remove(filepath)
                reset_rule_parser()
                return {"message": f"Rule {rule_name} deleted successfully"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

    raise HTTPException(status_code=404, detail="Rule file not found")


@router.get("/stats/count")
async def get_rule_count(
    parser: WappalyzerRuleParser = Depends(get_rule_parser)
):
    """Get total number of loaded rules."""
    return {
        "total_rules": len(parser.rules),
        "categories_count": len(parser.categories)
    }
