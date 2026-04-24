"""
HTTP Probe for web scanning.
Performs HTTP requests and collects response data.
"""
import asyncio
import logging
import re
from typing import Dict, Optional, Any
from urllib.parse import urlparse

from backend.core.wappalyzer.runner import ProbeResult

logger = logging.getLogger(__name__)

_aiohttp_loaded = False
_aiohttp = None


def _load_aiohttp():
    """Lazy load aiohttp."""
    global _aiohttp_loaded, _aiohttp
    if not _aiohttp_loaded:
        import aiohttp
        _aiohttp = aiohttp
        _aiohttp_loaded = True
    return _aiohttp


class HttpProbe:
    """HTTP probe for collecting web response data."""

    COMMON_SERVER_HEADERS = [
        "server", "x-powered-by", "x-aspnet-version",
        "x-generator", "x-drupal-cache", "x-shopify-stage"
    ]

    _shared_session = None
    _shared_ssl_context = None

    def __init__(
        self,
        timeout: int = 10,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0",
        verify_ssl: bool = True,
        proxy: Optional[str] = None,
        follow_redirects: bool = True,
        max_redirects: int = 5
    ):
        """Initialize HTTP probe."""
        self.timeout_val = timeout
        self.user_agent = user_agent
        self.verify_ssl = verify_ssl
        self.proxy = proxy
        self.follow_redirects = follow_redirects
        self.max_redirects = max_redirects
        self._session = None

    @classmethod
    def _get_shared_ssl_context(cls, verify_ssl: bool = True):
        """Get or create shared SSL context."""
        if cls._shared_ssl_context is None or cls._shared_ssl_context.get("verify") != verify_ssl:
            if not verify_ssl:
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                cls._shared_ssl_context = {"verify": verify_ssl, "context": ctx}
            else:
                cls._shared_ssl_context = {"verify": verify_ssl, "context": None}
        return cls._shared_ssl_context["context"]

    @classmethod
    def _get_shared_session(cls, timeout: int = 10, verify_ssl: bool = True):
        """Get or create a shared aiohttp session for connection pooling."""
        if cls._shared_session is None or cls._shared_session.closed:
            aiohttp = _load_aiohttp()
            connector = aiohttp.TCPConnector(
                limit=200,
                limit_per_host=20,
                keepalive_timeout=60,
                ssl=cls._get_shared_ssl_context(verify_ssl)
            )
            cls._shared_session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=timeout)
            )
        return cls._shared_session

    async def _get_session(self):
        """Get or create aiohttp session."""
        return self._get_shared_session(self.timeout_val, self.verify_ssl)

    async def run(self, url: str) -> ProbeResult:
        """Execute probe on URL."""
        result = ProbeResult(url=url)

        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                url = f"https://{url}"
                parsed = urlparse(url)

            session = await self._get_session()

            headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }

            async with session.request(
                "GET",
                url,
                headers=headers,
                allow_redirects=self.follow_redirects,
                max_redirects=self.max_redirects,
                proxy=self.proxy
            ) as response:
                result.status_code = response.status
                result.headers = {k.lower(): v for k, v in response.headers.items()}

                result.cookies = {
                    name: cookie.value
                    for name, cookie in response.cookies.items()
                }

                try:
                    result.html_content = await response.text()
                except Exception:
                    result.html_content = ""

                # Extract script URLs and inline scripts for Wappalyzer
                result.scripts = self._extract_script_urls(result.html_content)
                result.inline_scripts = self._extract_inline_scripts(result.html_content)

        except Exception as e:
            if "ClientError" in type(e).__name__ or "TimeoutError" in type(e).__name__:
                result.error = f"Request error: {str(e)}"
                logger.warning(f"HTTP probe error for {url}: {e}")
            else:
                result.error = str(e)
                logger.error(f"HTTP probe unexpected error for {url}: {e}")

        return result

    def _extract_script_urls(self, html: str) -> list:
        """Extract script URLs from HTML <script src=""> tags."""
        if not html:
            return []

        import re
        scripts = []
        pattern = re.compile(r'<script[^>]+src=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)
        for match in pattern.finditer(html):
            src = match.group(1)
            if src:
                scripts.append(src)
        return scripts

    def _extract_inline_scripts(self, html: str) -> list:
        """Extract inline JavaScript code from HTML."""
        if not html:
            return []

        import re
        inline_scripts = []
        # Match script tags without src attribute
        pattern = re.compile(r'<script(?![^>]*src)[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE)
        for match in pattern.finditer(html):
            content = match.group(1)
            if content and content.strip():
                inline_scripts.append(content)
        return inline_scripts

    async def close(self) -> None:
        """Close the HTTP session (shared session is not closed)."""
        self._session = None

    @classmethod
    async def close_shared_session(cls) -> None:
        """Close the shared session on application shutdown."""
        if cls._shared_session and not cls._shared_session.closed:
            await cls._shared_session.close()
            cls._shared_session = None
