"""
Dependency Injection for FastAPI.
Provides shared resources and common dependencies.
"""
from typing import Generator, Optional
from datetime import datetime

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db, get_session_local
from backend.app.config import get_settings, Settings
from backend.core.wappalyzer.parser import WappalyzerRuleParser
from backend.core.scanner import ScanTaskManager

_scan_task_manager: Optional[ScanTaskManager] = None
_rule_parser: Optional[WappalyzerRuleParser] = None


def get_settings_dep() -> Settings:
    """Get application settings."""
    return get_settings()


def get_scan_manager() -> ScanTaskManager:
    """Get or create scan task manager singleton."""
    global _scan_task_manager
    if _scan_task_manager is None:
        settings = get_settings()
        _scan_task_manager = ScanTaskManager(
            max_concurrent=settings.scan.max_concurrent,
            timeout=settings.scan.timeout,
            user_agent=settings.scan.user_agent
        )
    return _scan_task_manager


def get_rule_parser() -> WappalyzerRuleParser:
    """Get or create rule parser singleton."""
    global _rule_parser
    if _rule_parser is None:
        settings = get_settings()
        rules_dir = settings.get_rules_directory()
        _rule_parser = WappalyzerRuleParser(rules_dir)
        _rule_parser.load_all_rules()
    return _rule_parser


def reset_rule_parser() -> None:
    """Reset rule parser to reload rules."""
    global _rule_parser
    _rule_parser = None
