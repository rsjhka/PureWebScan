"""
PureWebScan - Main FastAPI Application.
Web fingerprint scanner compatible with Wappalyzer rules.
"""
import logging
import time
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text

from backend.app.config import get_settings, check_port_availability, setup_logging

settings = get_settings()
setup_logging(settings)
logger = logging.getLogger(__name__)

start_time = time.time()

FRONTEND_PATH = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - lazy initialization."""
    global start_time
    start_time = time.time()

    logger.info("Starting PureWebScan...")

    if not check_port_availability(settings.server.port, settings.server.host):
        logger.warning(f"Port {settings.server.port} is already in use!")
        logger.warning("Please change the port in config.yaml or stop the existing service using that port.")

    try:
        from backend.app.database import init_db
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    logger.info(f"PureWebScan is running on http://{settings.server.host}:{settings.server.port}")
    logger.info("Press Ctrl+C to stop the server")

    yield

    logger.info("Shutting down PureWebScan...")
    try:
        from backend.app.database import close_db
        from backend.core.probes.http_probe import HttpProbe
        close_db()
        await HttpProbe.close_shared_session()
    except Exception:
        pass


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": errors}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


def register_routes():
    """Lazy register API routes."""
    from backend.api import task, rule, result
    app.include_router(task.router)
    app.include_router(rule.router)
    app.include_router(result.router)


register_routes()


@app.get("/api/health", tags=["system"])
async def health_check():
    """Health check endpoint."""
    from backend.schemas.schemas import HealthResponse

    db_ok = True
    try:
        from backend.app.database import get_engine
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    rules_count = 0
    try:
        from backend.app.dependencies import get_rule_parser
        parser = get_rule_parser()
        rules_count = len(parser.rules)
    except Exception:
        pass

    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        version=settings.app_version,
        database_connected=db_ok,
        rules_loaded=rules_count,
        uptime=time.time() - start_time
    )


def create_frontend_app() -> FastAPI:
    """Create FastAPI app with frontend serving."""
    frontend_app = FastAPI()

    @frontend_app.get("/{path:path}")
    async def serve_all(path: str):
        file_path = FRONTEND_PATH / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_PATH / "index.html"))

    @frontend_app.get("/")
    async def serve_index():
        return FileResponse(str(FRONTEND_PATH / "index.html"))

    return frontend_app


if FRONTEND_PATH.exists():
    logger.info(f"Serving frontend from: {FRONTEND_PATH}")

    frontend_api = create_frontend_app()
    app.mount("/", frontend_api)
else:
    logger.warning(f"Frontend not found at: {FRONTEND_PATH}")
    logger.warning("Run 'cd frontend && npm install && npm run build' to build the frontend")


def run_server():
    """Run the server using uvicorn."""
    import uvicorn

    logger.info(f"Frontend path: {FRONTEND_PATH}")
    logger.info(f"Frontend exists: {FRONTEND_PATH.exists()}")

    uvicorn.run(
        "backend.app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
        log_level=settings.logging.level.lower(),
        workers=1
    )


if __name__ == "__main__":
    run_server()
