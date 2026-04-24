"""
Scan Task Manager.
Manages concurrent scanning tasks with proper cancellation support.
"""
import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from urllib.parse import urlparse

from backend.core.wappalyzer.parser import WappalyzerRuleParser
from backend.core.wappalyzer.runner import WappalyzerScanner
from backend.core.probes.http_probe import HttpProbe

logger = logging.getLogger(__name__)


@dataclass
class ScanTask:
    """Represents a scan task."""
    task_id: str
    urls: List[str]
    config: Dict[str, Any]
    status: str = "pending"
    progress: float = 0.0
    completed_urls: int = 0
    total_urls: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    results: List[Dict[str, Any]] = field(default_factory=list)


class ScanTaskManager:
    """Manages scan tasks and execution with proper cancellation support."""

    def __init__(
        self,
        max_concurrent: int = 100,
        timeout: int = 10,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0",
        verify_ssl: bool = True,
        proxy: Optional[str] = None
    ):
        """Initialize task manager."""
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.user_agent = user_agent
        self.verify_ssl = verify_ssl
        self.proxy = proxy
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.tasks: Dict[str, ScanTask] = {}
        self.rule_parser: Optional[WappalyzerRuleParser] = None
        self._cancel_flags: Dict[str, bool] = {}

    def set_rule_parser(self, parser: WappalyzerRuleParser) -> None:
        """Set the rule parser."""
        self.rule_parser = parser

    def create_task(
        self,
        urls: List[str],
        config: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None
    ) -> str:
        """Create a new scan task."""
        task_id = str(uuid.uuid4())[:8]

        normalized_urls = []
        for url in urls:
            url = url.strip()
            if url:
                if not url.startswith(("http://", "https://")):
                    url = f"https://{url}"
                normalized_urls.append(url)

        task = ScanTask(
            task_id=task_id,
            urls=normalized_urls,
            config=config or {},
            total_urls=len(normalized_urls)
        )

        self.tasks[task_id] = task
        self._cancel_flags[task_id] = False
        logger.info(f"Created task {task_id} with {len(normalized_urls)} URLs")

        return task_id

    async def _update_task_in_db(self, task_id: str, status: str = None, progress: int = None) -> None:
        """Update task in database."""
        try:
            from backend.app.database import get_session_local
            from backend.models.task import ScanTask as DBScanTask

            db = get_session_local()()
            try:
                db_task = db.query(DBScanTask).filter(DBScanTask.task_id == task_id).first()
                if db_task:
                    if status is not None:
                        db_task.status = status
                    if progress is not None:
                        db_task.progress = progress
                    if status == "completed":
                        db_task.completed_at = datetime.now()
                    db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to update task in DB: {e}")

    def _is_cancelled(self, task_id: str) -> bool:
        """Check if task is cancelled."""
        return self._cancel_flags.get(task_id, False)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        task = self.tasks.get(task_id)
        if not task:
            return False

        if task.status == "running":
            self._cancel_flags[task_id] = True
            task.status = "cancelled"
            logger.info(f"Task {task_id} cancellation requested")
            return True
        return False

    async def start_task(self, task_id: str) -> None:
        """Start executing a scan task."""
        task = self.tasks.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return

        task.status = "running"
        task.started_at = datetime.now()

        try:
            await self._execute_task(task)

            # Check if cancelled
            if self._is_cancelled(task_id):
                task.status = "cancelled"
                await self._update_task_in_db(task_id, "cancelled")
                logger.info(f"Task {task_id} was cancelled")
                return

            # Save results
            await self._save_results_to_db(task)
            task.status = "completed"
            task.progress = 100
            await self._update_task_in_db(task_id, "completed", 100)
            logger.info(f"Task {task_id} completed with {len(task.results)} results")

        except asyncio.CancelledError:
            task.status = "cancelled"
            task.completed_at = datetime.now()
            await self._update_task_in_db(task_id, "cancelled")
            logger.info(f"Task {task_id} cancelled (CancelledError)")
            raise
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            await self._update_task_in_db(task_id, "failed")
            logger.error(f"Task {task_id} failed: {e}")
        finally:
            task.completed_at = datetime.now()
            self._cancel_flags[task_id] = False

    async def _save_results_to_db(self, task: ScanTask) -> None:
        """Save scan results to database."""
        try:
            from backend.app.database import get_session_local
            from backend.models.result import ScanResult

            db = get_session_local()()
            try:
                for result_data in task.results:
                    db_result = ScanResult(
                        task_id=task.task_id,
                        url=result_data.get("url", ""),
                        base_domain=result_data.get("base_domain", ""),
                        status_code=result_data.get("status_code", 0),
                        content_type=result_data.get("content_type", ""),
                        server=result_data.get("server", ""),
                        powered_by=result_data.get("powered_by", ""),
                        technologies=result_data.get("technologies", []),
                        technology_count=result_data.get("technology_count", 0),
                        headers=result_data.get("headers", {}),
                        cookies=result_data.get("cookies", {}),
                        error_message=result_data.get("error", ""),
                        scan_duration=result_data.get("scan_duration", 0)
                    )
                    db.add(db_result)

                from backend.models.task import ScanTask as DBScanTask
                db_task = db.query(DBScanTask).filter(DBScanTask.task_id == task.task_id).first()
                if db_task:
                    db_task.status = "completed"
                    db_task.progress = 100
                    db_task.completed_urls = task.completed_urls
                    db_task.completed_at = task.completed_at

                db.commit()
                logger.info(f"Saved {len(task.results)} results to database")
            except Exception as e:
                logger.error(f"Failed to save results: {e}")
                db.rollback()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Database save error: {e}")

    async def _execute_task(self, task: ScanTask) -> None:
        """Execute the scan task."""
        if not self.rule_parser:
            from backend.app.config import get_settings
            settings = get_settings()
            rules_dir = settings.get_rules_directory()
            self.rule_parser = WappalyzerRuleParser(rules_dir)
            self.rule_parser.load_all_rules()
            logger.info(f"Loaded {len(self.rule_parser.rules)} rules")

        scanner = WappalyzerScanner(self.rule_parser)

        async def scan_url(url: str) -> Dict[str, Any]:
            # Check cancellation before starting
            if self._is_cancelled(task.task_id):
                raise asyncio.CancelledError("Task cancelled")

            async with self.semaphore:
                # Check again after acquiring semaphore
                if self._is_cancelled(task.task_id):
                    raise asyncio.CancelledError("Task cancelled")

                start_time = time.time()
                try:
                    result = await self._scan_single_url(url, scanner)
                    result["scan_duration"] = int((time.time() - start_time) * 1000)
                    return result
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Error scanning {url}: {e}")
                    return {"url": url, "error": str(e), "technologies": []}

        # Create tasks
        scan_tasks = [scan_url(url) for url in task.urls]

        # Process with asyncio.as_completed for better responsiveness
        for coro in asyncio.as_completed(scan_tasks):
            # Check cancellation periodically
            if self._is_cancelled(task.task_id):
                logger.info(f"Task {task.task_id} cancelled, stopping execution")
                raise asyncio.CancelledError("Task cancelled")

            try:
                result = await coro
                task.results.append(result)
                task.completed_urls += 1
                task.progress = (task.completed_urls / task.total_urls) * 100
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error processing result: {e}")
                task.completed_urls += 1

    async def _scan_single_url(
        self,
        url: str,
        scanner: WappalyzerScanner
    ) -> Dict[str, Any]:
        """Scan a single URL."""
        probe = HttpProbe(
            timeout=self.timeout,
            user_agent=self.user_agent,
            verify_ssl=self.verify_ssl,
            proxy=self.proxy
        )

        try:
            probe_result = await probe.run(url)

            if probe_result.error:
                return {
                    "url": url,
                    "error": probe_result.error,
                    "technologies": []
                }

            technologies = await scanner.analyze(probe_result)
            parsed = urlparse(url)
            base_domain = parsed.netloc

            return {
                "url": url,
                "base_domain": base_domain,
                "status_code": probe_result.status_code,
                "headers": probe_result.headers,
                "cookies": probe_result.cookies,
                "technologies": [
                    {
                        "name": t.name,
                        "slug": t.slug,
                        "confidence": t.confidence,
                        "version": t.version,
                        "categories": t.categories,
                        "icons": t.icons,
                        "website": t.website
                    }
                    for t in technologies
                ],
                "technology_count": len(technologies)
            }
        except Exception as e:
            logger.error(f"Error scanning {url}: {e}")
            return {
                "url": url,
                "error": str(e),
                "technologies": []
            }

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status."""
        task = self.tasks.get(task_id)
        if not task:
            return None

        return {
            "task_id": task.task_id,
            "status": task.status,
            "progress": task.progress,
            "completed_urls": task.completed_urls,
            "total_urls": task.total_urls,
            "error_message": task.error_message,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        }

    def get_task_results(self, task_id: str) -> List[Dict[str, Any]]:
        """Get task results."""
        task = self.tasks.get(task_id)
        if not task:
            return []
        return task.results

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        if task_id in self.tasks:
            del self.tasks[task_id]
        if task_id in self._cancel_flags:
            del self._cancel_flags[task_id]
        return True

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks."""
        return [self.get_task_status(task_id) for task_id in self.tasks]
