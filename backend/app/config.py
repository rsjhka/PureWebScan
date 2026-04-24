"""
Configuration Management for PureWebScan.
Handles loading and validation of all application settings.
"""
import os
import socket
import logging
from pathlib import Path
from typing import Optional, List
from functools import lru_cache
from pydantic import BaseModel, Field, AnyHttpUrl
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class ServerConfig(BaseModel):
    """Server configuration."""
    host: str = "0.0.0.0"
    port: int = 9933
    debug: bool = False
    reload: bool = False


class DatabaseConfig(BaseModel):
    """Database configuration."""
    type: str = "sqlite"
    url: str = "sqlite:///./data/purewebscan.db"


class ScanConfig(BaseModel):
    """Scan engine configuration."""
    max_concurrent: int = 100
    timeout: int = 10
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"
    max_retries: int = 3
    retry_delay: float = 1.0


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    file: str = "data/purewebscan.log"


class RulesConfig(BaseModel):
    """Rules directory configuration."""
    directory: str = "rules"
    auto_reload: bool = True


class RedTeamConfig(BaseModel):
    """Red team specific configuration."""
    stealth: bool = True
    delay: int = 2
    proxy: Optional[str] = None
    verify_ssl: bool = True


class Settings(BaseSettings):
    """Main application settings."""
    app_name: str = "PureWebScan"
    app_version: str = "1.0.0"
    app_description: str = "Web Fingerprint Scanner compatible with Wappalyzer"

    server: ServerConfig = Field(default_factory=ServerConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    scan: ScanConfig = Field(default_factory=ScanConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    rules: RulesConfig = Field(default_factory=RulesConfig)
    red_team: RedTeamConfig = Field(default_factory=RedTeamConfig)

    cors_origins: List[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    class Config:
        env_prefix = "PUREWEBSCAN_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    def get_database_url(self) -> str:
        """Get the database URL, creating directory if needed."""
        if self.database.type == "sqlite":
            db_path = self.database.url.replace("sqlite:///", "")
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
        return self.database.url

    def get_rules_directory(self) -> Path:
        """Get the rules directory path."""
        rules_dir = Path(self.rules.directory)
        if not rules_dir.is_absolute():
            base_dir = Path(__file__).parent.parent.parent
            rules_dir = base_dir / rules_dir
        return rules_dir


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def check_port_availability(port: int, host: str = "0.0.0.0") -> bool:
    """Check if a port is available for binding."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        return True
    except socket.error:
        return False
    finally:
        sock.close()


def setup_logging(settings: Settings) -> None:
    """Configure logging based on settings."""
    log_file = settings.logging.file
    if not os.path.isabs(log_file):
        base_dir = Path(__file__).parent.parent.parent
        log_file = base_dir / log_file

    log_dir = os.path.dirname(str(log_file))
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, settings.logging.level.upper()),
        format=settings.logging.format,
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )


settings = get_settings()
