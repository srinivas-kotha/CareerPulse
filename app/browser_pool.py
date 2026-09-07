import asyncio
import json
import logging
import os

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    async_playwright = None
    PLAYWRIGHT_AVAILABLE = False

try:
    from playwright_stealth import stealth_async
    STEALTH_AVAILABLE = True
except ImportError:
    stealth_async = None
    STEALTH_AVAILABLE = False

COOKIE_DIR = os.path.join("data", "cookies")

LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class BrowserPool:
    """Manages a single shared browser instance with cookie persistence."""

    def __init__(self, cookie_dir=None):
        self.cookie_dir = os.fspath(cookie_dir) if cookie_dir is not None else COOKIE_DIR
        self._lock = asyncio.Lock()
        self._playwright: "Playwright | None" = None
        self._browser: "Browser | None" = None

    async def _launch_browser(self) -> "Browser":
        self._playwright = await async_playwright().start()
        # Try real Chrome first for better TLS fingerprint
        try:
            browser = await self._playwright.chromium.launch(
                headless=True,
                channel="chrome",
                args=LAUNCH_ARGS,
            )
            logger.info("Browser pool: launched with Chrome channel")
            return browser
        except Exception:
            logger.info("Browser pool: Chrome not available, falling back to bundled Chromium")
            return await self._playwright.chromium.launch(
                headless=True,
                args=LAUNCH_ARGS,
            )

    async def get_context(self, domain: str) -> "BrowserContext":
        """Get a browser context with optional cookie persistence for domain."""
        async with self._lock:
            if self._browser is None or not self._browser.is_connected():
                self._browser = await self._launch_browser()

        context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=USER_AGENT,
            locale="en-US",
            timezone_id="America/New_York",
        )

        cookies = self._load_cookies(domain)
        if cookies:
            await context.add_cookies(cookies)

        return context

    def save_cookies(self, domain: str, cookies: list[dict]):
        """Save cookies to disk for a domain."""
        os.makedirs(self.cookie_dir, exist_ok=True)
        path = self._cookie_path(domain)
        try:
            with open(path, "w") as f:
                json.dump(cookies, f)
        except Exception as e:
            logger.debug(f"Failed to save cookies for {domain}: {e}")

    def _load_cookies(self, domain: str) -> list[dict]:
        """Load persisted cookies for a domain."""
        path = self._cookie_path(domain)
        if not os.path.exists(path):
            return []
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Failed to load cookies for {domain}: {e}")
            return []

    def _cookie_path(self, domain: str) -> str:
        if not domain or any(c in domain for c in '/\\:') or domain in {'.', '..'}:
            raise ValueError("Invalid cookie domain")
        path = os.path.realpath(os.path.join(self.cookie_dir, f"{domain}.json"))
        root = os.path.realpath(self.cookie_dir)
        if os.path.commonpath([root, path]) != root:
            raise ValueError("Cookie path escapes browser directory")
        return path

    async def shutdown(self):
        """Close the browser and playwright instance."""
        async with self._lock:
            if self._browser:
                try:
                    await self._browser.close()
                except Exception:
                    pass
                self._browser = None
            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None


_pool: BrowserPool | None = None


def get_browser_pool() -> BrowserPool:
    """Get the module-level browser pool singleton."""
    global _pool
    if _pool is None:
        _pool = BrowserPool()
    return _pool


async def shutdown_browser_pool():
    """Shutdown the global browser pool if it exists."""
    global _pool
    if _pool is not None:
        await _pool.shutdown()
        _pool = None
